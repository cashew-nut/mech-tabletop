"""Masonry building blocks for the board kit: tagged meshes, coursed stone walls with gothic lancet windows,
and flagstones clipped to a hex. Every face carries a `kind` tag (kind * 1000 + piece id) that board_kit.py
turns into a colour, so each brick or slab gets one consistent shade.
"""
import math
import random

import bpy  # noqa: F401,I001  (bpy must be imported before bmesh)
import bmesh
from mathutils import Matrix, Vector

# face kinds
CORE, BRICK, TRIM, WINDOW, ROOF, SLAB, MOSS, DIRT, METAL, WOOD, GLOW, SOOT, BED = range(13)
Z = Vector((0, 0, 1))


class TaggedMesh:
    """A bmesh whose new faces get tagged with a kind and a running piece id."""

    def __init__(self):
        self.bm = bmesh.new()
        self.tag = self.bm.faces.layers.int.new("kind")
        self.piece = 0

    def _start(self):
        self.bm.faces.ensure_lookup_table()
        return len(self.bm.faces)

    def _finish(self, start, kind):
        self.bm.faces.ensure_lookup_table()
        self.piece += 1
        value = kind * 1000 + self.piece % 1000
        for i in range(start, len(self.bm.faces)):
            self.bm.faces[i][self.tag] = value

    def box(self, size, center, basis=None, kind=BRICK):
        """An oriented box. basis is a 3x3 matrix whose columns are the box's local x, y, z axes in world space."""
        start = self._start()
        res = bmesh.ops.create_cube(self.bm, size=1.0)
        rot = (basis or Matrix.Identity(3)).to_4x4()
        m = Matrix.Translation(center) @ rot @ Matrix.Diagonal((size[0], size[1], size[2], 1))
        bmesh.ops.transform(self.bm, matrix=m, verts=res["verts"])
        self._finish(start, kind)

    def prism(self, poly, z0, z1, chamfer=0.0, kind=SLAB):
        """Extrude a CCW 2D polygon from z0 to z1, with a chamfered top edge."""
        start = self._start()
        bm = self.bm
        cx = sum(p[0] for p in poly) / len(poly)
        cy = sum(p[1] for p in poly) / len(poly)
        inner = []
        for x, y in poly:
            d = math.hypot(x - cx, y - cy) or 1
            k = max(0.0, 1 - chamfer / d)
            inner.append((cx + (x - cx) * k, cy + (y - cy) * k))
        zc = z1 - chamfer if chamfer else z1
        bot = [bm.verts.new((x, y, z0)) for x, y in poly]
        mid = [bm.verts.new((x, y, zc)) for x, y in poly]
        top = [bm.verts.new((x, y, z1)) for x, y in inner] if chamfer else mid
        n = len(poly)
        bm.faces.new(list(reversed(bot)))
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((bot[i], bot[j], mid[j], mid[i]))
            if chamfer:
                bm.faces.new((mid[i], mid[j], top[j], top[i]))
        bm.faces.new(top)
        self._finish(start, kind)

    def pyramid(self, width, height, base, rot=math.pi / 4, kind=ROOF, sides=4):
        start = self._start()
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, segments=sides, radius1=width / math.sqrt(2), radius2=0.0, depth=height)
        m = Matrix.Translation((base[0], base[1], base[2] + height / 2)) @ Matrix.Rotation(rot, 4, "Z")
        bmesh.ops.transform(self.bm, matrix=m, verts=res["verts"])
        self._finish(start, kind)


def face_basis(u, n):
    """Basis with x along the wall (u), y out of the wall (n) and z up. Kept right-handed so normals face out."""
    x = u.normalized()
    y = n.normalized()
    return Matrix((x, y, x.cross(y))).transposed()


def incline_basis(u, n, angle):
    """Like face_basis, but the box's x axis tilts up by angle within the wall plane."""
    x = (u.normalized() * math.cos(angle) + Z * math.sin(angle)).normalized()
    y = n.normalized()
    return Matrix((x, y, x.cross(y))).transposed()


class Face:
    """One flat face of masonry: origin is the bottom centre on the core surface, u runs along it, n points out."""

    def __init__(self, origin, u, n, width):
        self.origin = Vector(origin)
        self.u = Vector(u).normalized()
        self.n = Vector(n).normalized()
        self.width = width

    def at(self, x, z, d=0.0):
        return self.origin + self.u * x + Z * z + self.n * d


class LancetHole:
    """A pointed-arch opening (plus its stone surround) that courses of stone are trimmed around."""

    def __init__(self, xc, z0, w, h):
        self.xc, self.z0, self.w, self.h = xc, z0, w, h
        self.head = w * 0.62

    def half_width(self, z):
        if z < self.z0:
            return None
        if z <= self.z0 + self.h:
            return self.w / 2
        t = (z - self.z0 - self.h) / self.head
        if t > 1:
            return None
        return (self.w / 2) * math.sqrt(max(0.0, 1 - t * t)) * (1 - 0.35 * t)

    def span(self, zlo, zhi):
        """The widest x interval the opening covers between two heights, or None."""
        widths = [self.half_width(zlo + (zhi - zlo) * i / 4) for i in range(5)]
        widths = [w for w in widths if w is not None]
        if not widths:
            return None
        hw = max(widths)
        return (self.xc - hw, self.xc + hw)


def lancet_hole(xc, z0, w, h):
    return LancetHole(xc, z0, w, h)


def subtract(intervals, cut):
    out = []
    for a, b in intervals:
        if cut[1] <= a or cut[0] >= b:
            out.append((a, b))
            continue
        if cut[0] > a:
            out.append((a, cut[0]))
        if cut[1] < b:
            out.append((cut[1], b))
    return out


def coursed(m, face, height, rng, course=0.1, brick=(0.15, 0.27), depth=0.045, gap=0.014, holes=(), top=None, z0=0.0, quoins=False):
    """Lay staggered courses of dressed stone over a face, skipping openings and stopping under a ragged top."""
    basis = face_basis(face.u, face.n)
    half = face.width / 2
    z = z0
    row = 0
    while z < height - 1e-4:
        ch = min(course * rng.uniform(0.85, 1.15), height - z)
        x = -half - (rng.uniform(0.05, brick[0]) if row % 2 else 0.0)
        while x < half - 1e-4:
            bw = rng.uniform(*brick)
            if quoins and (x < -half + 0.01 or x + bw > half - 0.01):
                bw = brick[1] * (1.2 if row % 2 else 0.75)  # long and short blocks alternate at the corners
            x0, x1 = max(x, -half), min(x + bw, half)
            x += bw
            if top is not None and z + ch > top((x0 + x1) / 2):
                continue
            pieces = [(x0, x1)]
            for hole in holes:  # trim the stone round any opening it crosses
                cut = hole.span(z, z + ch)
                if cut:
                    pieces = subtract(pieces, cut)
            d = depth * rng.uniform(0.8, 1.15)
            zc = z + ch / 2
            for p0, p1 in pieces:
                if p1 - p0 < 0.035:
                    continue
                m.box((p1 - p0 - gap, d, ch - gap), face.at((p0 + p1) / 2, zc, d / 2), basis, BRICK)
        z += ch
        row += 1


def lancet(m, face, xc, z0, w, h, depth, through=0.0, mullion=True):
    """Stone surround for a lancet window: jambs, sill, a two-piece pointed arch, a mullion and a dark recess."""
    basis = face_basis(face.u, face.n)
    fd = depth + 0.02
    head = w * 0.62
    jw = 0.045
    for s in (-1, 1):
        m.box((jw, fd + through, h), face.at(xc + s * (w / 2 + jw / 2), z0 + h / 2, (fd - through) / 2), basis, TRIM)
        # arch voussoirs: a slanted block from each springing point up to the apex
        sx, sz = xc + s * (w / 2 + jw / 2), z0 + h
        ax, az = xc, z0 + h + head + jw * 0.6
        length = math.hypot(ax - sx, az - sz)
        ang = math.atan2(az - sz, (ax - sx) * s)
        m.box((length + jw, fd + through, jw * 1.1), face.at((sx + ax) / 2, (sz + az) / 2, (fd - through) / 2), incline_basis(face.u * s, face.n, ang), TRIM)
    m.box((w + jw * 3, fd + 0.03, 0.05), face.at(xc, z0 - 0.025, fd / 2 + 0.01), basis, TRIM)  # sill
    if through <= 0:
        m.box((w + 0.01, 0.01, h + head), face.at(xc, z0 + (h + head) / 2, 0.004), basis, WINDOW)  # dark recess
    if mullion:
        m.box((0.022, fd * 0.6, h + head * 0.5), face.at(xc, z0 + (h + head * 0.5) / 2, fd * 0.3 - through / 2), basis, TRIM)
        m.box((w, fd * 0.6, 0.022), face.at(xc, z0 + h * 0.62, fd * 0.3 - through / 2), basis, TRIM)


def string_course(m, face, z, depth, kind=TRIM, extra=0.04):
    m.box((face.width + extra, depth + 0.035, 0.05), face.at(0, z, (depth + 0.035) / 2), face_basis(face.u, face.n), kind)


# ---------------------------------------------------------------- flagstones
def clip(poly, a, b, c):
    """Keep the part of a polygon where a*x + b*y <= c (Sutherland-Hodgman against one half-plane)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        dp, dq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if dp <= 0:
            out.append(p)
        if (dp < 0) != (dq < 0) and dp != dq:
            t = dp / (dp - dq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def clip_hex(poly, r):
    """Clip to a pointy-top hex (vertices on the +/-Y axis) of circumradius r."""
    apothem = r * math.sqrt(3) / 2
    for k in range(6):
        ang = math.radians(60 * k)  # edge normals of a pointy-top hex sit at 0, 60, 120... degrees
        poly = clip(poly, math.cos(ang), math.sin(ang), apothem)
        if len(poly) < 3:
            return []
    return poly


def area(poly):
    return abs(sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))) / 2


def flagstones(rng, r, rows=(0.34, 0.48), widths=(0.3, 0.62), gap=0.035, angle=0.0):
    """Rows of rectangular flagstones in a running bond, turned by angle and clipped to the hex."""
    ca, sa = math.cos(angle), math.sin(angle)
    stones = []
    y = -r - rng.uniform(0, 0.2)
    while y < r:
        h = rng.uniform(*rows)
        x = -r - rng.uniform(0, 0.3)
        while x < r:
            w = rng.uniform(*widths)
            rect = [(x + gap / 2, y + gap / 2), (x + w - gap / 2, y + gap / 2), (x + w - gap / 2, y + h - gap / 2), (x + gap / 2, y + h - gap / 2)]
            rect = [(px * ca - py * sa, px * sa + py * ca) for px, py in rect]
            poly = clip_hex(rect, r)
            if len(poly) >= 3 and area(poly) > 0.012:
                stones.append(poly)
            x += w
        y += h
    return stones


def crack(poly, rng, gap=0.02):
    """Split a stone along a random line through its middle, leaving a thin crack."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    ang = rng.uniform(0, math.pi)
    a, b = math.cos(ang), math.sin(ang)
    c = a * cx + b * cy
    halves = [clip(poly, a, b, c - gap / 2), clip(poly, -a, -b, -c - gap / 2)]
    return [h for h in halves if len(h) >= 3 and area(h) > 0.004]
