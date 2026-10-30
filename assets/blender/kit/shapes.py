"""Hard-surface building blocks for armour parts, in millimetres.

Every function returns the new object (or list of objects), already linked
to the scene and, if `parent` is given, parented. Meshes get a "Decal" UV map
so filigree, tread and stencil masks land sensibly (see decal_uv).

Two ways of building:

* Free-standing pieces: box_plate, cylinder, lathe, spire, lancet, pipe,
  gauge, rivet_row, sweep. Place them with `loc`/`rot` or move them after.
* Layered armour over a curved shell, ported from the helm proof of concept:
  make a Shell from any closed mesh around a centre, then lay patch plates,
  swept trim, fluting ribs and stacked lames on it by azimuth and elevation.
"""
import math

import bpy
from mathutils import Euler, Vector
from mathutils.bvhtree import BVHTree

from .core import bmesh, direction, link, mesh_obj, mod

# ------------------------------------------------------------------ UVs


def decal_uv(ob, tile_mm=4.0):
    """Box-project a "Decal" UV map from world millimetres: one tile of the
    relief mask every `tile_mm`. Leaves an existing Decal map alone."""
    if ob.type != "MESH" or "Decal" in ob.data.uv_layers:
        return
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    uv = bm.loops.layers.uv.new("Decal")
    mw = ob.matrix_world
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        u, v = [(1, 2), (0, 2), (0, 1)][ax]
        for loop in f.loops:
            w = mw @ loop.vert.co
            loop[uv].uv = (w[u] / tile_mm, w[v] / tile_mm)
    bm.to_mesh(ob.data)
    bm.free()


def _grid_faces(bm, grid, uv, tile=(1.0, 1.0)):
    nv, nu = len(grid) - 1, len(grid[0]) - 1
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop, (di, dj) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                loop[uv].uv = ((i + di) / nu * tile[0], (j + dj) / nv * tile[1])


def _place(ob, loc, rot, parent):
    ob.location = loc
    ob.rotation_euler = Euler(rot)
    if parent is not None:
        ob.parent = parent
    return ob


# ------------------------------------------------------------------ free-standing pieces


def box_plate(name, size, mat, bevel=0.3, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, panel_lines=0, taper=0.0, segments=2):
    """A bevelled armour plate. `panel_lines` cuts that many shallow grooves
    across its width; `taper` narrows the top (+Z) by that fraction."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        k = 1 - taper * (v.co.z + 0.5)
        v.co = Vector((v.co.x * size[0] * k, v.co.y * size[1], v.co.z * size[2]))
    if panel_lines:
        for i in range(1, panel_lines + 1):
            x = -size[0] / 2 + size[0] * i / (panel_lines + 1)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    ob = mesh_obj(name, bm, mat, smooth=False)
    if panel_lines:
        # Sink the grooves: inset each front face strip a touch.
        me = ob.data
        bm = bmesh.new()
        bm.from_mesh(me)
        front = [f for f in bm.faces if f.normal.y < -0.9]
        bmesh.ops.inset_individual(bm, faces=front, thickness=min(size) * 0.04, depth=-min(size) * 0.03)
        bm.to_mesh(me)
        bm.free()
    if bevel:
        mod(ob, "BEVEL", width=bevel, segments=segments, limit_method="ANGLE", angle_limit=math.radians(35), harden_normals=True)
        ob.data.shade_smooth()
        mod(ob, "WEIGHTED_NORMAL", keep_sharp=True)
    _place(ob, loc, rot, parent)
    decal_uv(ob)
    return ob


def cylinder(name, radius, depth, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, verts=32, bevel=0.15, r2=None):
    """A bevelled cylinder (or cone frustum if r2 is given) along local Z."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=radius, radius2=radius if r2 is None else r2, depth=depth)
    ob = mesh_obj(name, bm, mat)
    if bevel:
        mod(ob, "BEVEL", width=bevel, segments=2, limit_method="ANGLE", angle_limit=math.radians(40), harden_normals=True)
        mod(ob, "WEIGHTED_NORMAL", keep_sharp=True)
    _place(ob, loc, rot, parent)
    decal_uv(ob)
    return ob


def sphere(name, radius, mat, loc=(0, 0, 0), scale=(1, 1, 1), parent=None, segments=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=max(8, segments // 2), radius=radius)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2]))
    ob = mesh_obj(name, bm, mat)
    _place(ob, loc, (0, 0, 0), parent)
    decal_uv(ob)
    return ob


def lathe(name, profile, mat, a0=0.0, a1=360.0, segments=48, scale=(1.0, 1.0), loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    """Spin a (radius, z) profile round Z between two azimuths (0 = front, -Y)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("Decal")
    full = abs(a1 - a0) >= 360
    n = segments if full else segments + 1
    rings = []
    for s in range(n):
        a = math.radians(a0 + (a1 - a0) * s / segments)
        rings.append([bm.verts.new((math.sin(a) * r * scale[0], -math.cos(a) * r * scale[1], z)) for r, z in profile])
    grid = [list(col) for col in zip(*rings)]
    if full:
        grid = [row + [row[0]] for row in grid]
    _grid_faces(bm, grid, uv, (segments / 8, len(profile) / 4))
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    ob = mesh_obj(name, bm, mat)
    return _place(ob, loc, rot, parent)


def sweep(name, pts, radius, mat, cyclic=False, parent=None, profile="round", resolution=3):
    """A tube or bar swept along points: piping, raised trim, cables, ribs.
    `profile` is "round" or "square" (a beaded edge vs a flat band)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = resolution if profile == "round" else 0
    cu.use_fill_caps = True
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, v in zip(sp.points, pts):
        p.co = (*v, 1)
    sp.use_cyclic_u = cyclic
    ob = link(bpy.data.objects.new(name, cu))
    ob.data.materials.append(mat)
    if parent is not None:
        ob.parent = parent
    return ob


def pipe(name, pts, radius, mat, parent=None, bands=None, band_mat=None):
    """A pipe through points, optionally with collar bands at the given fractions."""
    ob = sweep(name, pts, radius, mat, parent=parent, resolution=4)
    out = [ob]
    if bands and band_mat:
        for k, t in enumerate(bands):
            seg = t * (len(pts) - 1)
            i = min(int(seg), len(pts) - 2)
            a, b = Vector(pts[i]), Vector(pts[i + 1])
            p = a.lerp(b, seg - i)
            d = (b - a).normalized()
            band = cylinder(f"{name}_band{k}", radius * 1.35, radius * 0.9, band_mat, loc=p, parent=parent, verts=20, bevel=radius * 0.15)
            band.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
            out.append(band)
    return out


def rivet_row(name, p0, p1, count, radius, mat, parent=None, normal=(0, -1, 0)):
    """Domed rivets evenly spaced from p0 to p1, joined into one object."""
    bm = bmesh.new()
    p0, p1, nrm = Vector(p0), Vector(p1), Vector(normal).normalized()
    rot = nrm.to_track_quat("Z", "Y").to_matrix().to_4x4()
    for i in range(count):
        t = i / max(1, count - 1)
        c = p0.lerp(p1, t)
        geom = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=radius)
        vs = geom["verts"]
        for v in vs:
            v.co = c + (rot @ Vector((v.co.x, v.co.y, max(v.co.z, -radius * 0.2) * 0.7)))
    ob = mesh_obj(name, bm, mat)
    if parent is not None:
        ob.parent = parent
    decal_uv(ob)
    return ob


def spire(name, width, height, mat, trim=None, loc=(0, 0, 0), parent=None, crockets=4, glow=None, sides=8):
    """A gothic pinnacle: shaft, gold bands, crocketed cone and a finial ball.
    Pass `glow` to light a slit window in the shaft. Returns the shaft; the
    rest is parented to it."""
    shaft_h = height * 0.55
    shaft = cylinder(name, width / 2, shaft_h, mat, loc=(loc[0], loc[1], loc[2] + shaft_h / 2), parent=parent, verts=sides, bevel=width * 0.04)
    cone = cylinder(f"{name}_cone", width * 0.42, height * 0.45, mat, loc=(0, 0, shaft_h / 2 + height * 0.225), verts=sides, bevel=width * 0.02, r2=width * 0.02)
    cone.parent = shaft
    if trim is not None:
        for k, z in enumerate((shaft_h / 2, -shaft_h * 0.2)):
            b = cylinder(f"{name}_band{k}", width * 0.55, width * 0.12, trim, loc=(0, 0, z), verts=sides, bevel=width * 0.02)
            b.parent = shaft
        fin = sphere(f"{name}_finial", width * 0.12, trim, loc=(0, 0, shaft_h / 2 + height * 0.46))
        fin.parent = shaft
    for k in range(crockets):
        # Crockets: little hooked leaves climbing the cone's corners.
        for s in range(sides // 2):
            a = 2 * math.pi * s / (sides // 2) + math.pi / sides
            t = (k + 0.5) / crockets
            r = width * 0.42 * (1 - t) + width * 0.06
            c = cylinder(f"{name}_crocket{k}_{s}", width * 0.06, width * 0.22, trim or mat, verts=6, bevel=0,
                         loc=(math.cos(a) * r, math.sin(a) * r, shaft_h / 2 + height * 0.45 * t), r2=0.001)
            c.rotation_euler = (math.cos(a + math.pi / 2) * 0.9, math.sin(a + math.pi / 2) * -0.9, 0)
            c.parent = shaft
    if glow is not None:
        win = box_plate(f"{name}_window", (width * 0.22, width * 0.1, shaft_h * 0.45), glow, bevel=0, loc=(0, -width * 0.47, shaft_h * 0.08))
        win.parent = shaft
    return shaft


def lancet(name, width, height, depth, mat, glow=None, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, frame=None):
    """A pointed-arch window: a frame of `mat` round an opening filled with
    `glow` (or left open). The arch faces -Y."""
    def outline(w, h, n=12):
        # An equilateral arch: two arcs of radius w, each centred on the opposite jamb.
        spring = max(0.0, h - w * math.sqrt(3) / 2)
        right = [(-w / 2 + w * math.cos(math.radians(60 * i / n)), spring + w * math.sin(math.radians(60 * i / n))) for i in range(n + 1)]
        left = [(-x, z) for x, z in reversed(right[:-1])]
        return [(-w / 2, 0.0), (w / 2, 0.0), *right, *left]
    fw = frame or width * 0.16

    def prism(nm, pts, d, y, m):
        bm = bmesh.new()
        front = [bm.verts.new((x, y - d / 2, z)) for x, z in pts]
        back = [bm.verts.new((x, y + d / 2, z)) for x, z in pts]
        bm.faces.new(front)
        bm.faces.new(list(reversed(back)))
        for i in range(len(pts)):
            j = (i + 1) % len(pts)
            bm.faces.new((front[j], front[i], back[i], back[j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        return mesh_obj(nm, bm, m, smooth=False)
    outer = prism(name, outline(width + fw * 2, height + fw), depth, 0, mat)
    inner = prism(f"{name}_cut", [(x, z + fw * 0.5) for x, z in outline(width, height)], depth * 3, 0, mat)
    mod(outer, "BOOLEAN", object=inner, operation="DIFFERENCE", solver="EXACT")
    mod(outer, "BEVEL", width=fw * 0.15, segments=2, limit_method="ANGLE")
    inner.hide_render = inner.hide_viewport = True
    inner.parent = outer
    inner["kit_cutter"] = True
    _place(outer, loc, rot, parent)
    decal_uv(outer)
    if glow is not None:
        pane = prism(f"{name}_glass", [(x * 0.98, z + fw * 0.5) for x, z in outline(width, height)], depth * 0.3, depth * 0.2, glow)
        pane.parent = outer
        mullion = box_plate(f"{name}_mullion", (fw * 0.35, depth * 0.6, height * 0.9), mat, bevel=0, loc=(0, 0, height * 0.45))
        mullion.parent = outer
    return outer


def gauge(name, radius, mat, face, needle, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    """A pressure gauge facing -Y: a bezel, a pale face and a needle."""
    bezel = cylinder(name, radius, radius * 0.5, mat, loc=loc, rot=(math.pi / 2 + rot[0], rot[1], rot[2]), parent=parent, verts=24, bevel=radius * 0.12)
    f = cylinder(f"{name}_face", radius * 0.8, radius * 0.1, face, loc=(0, 0, radius * 0.24), verts=24, bevel=0)
    f.parent = bezel
    n = box_plate(f"{name}_needle", (radius * 0.08, radius * 0.7, radius * 0.05), needle, bevel=0, loc=(0, radius * 0.25, radius * 0.31), rot=(0, 0, 0.7))
    n.parent = bezel
    return bezel


def boolean(ob, cutter, operation="DIFFERENCE"):
    """Cut (or union) `cutter` into `ob` as a live modifier; hides the cutter."""
    mod(ob, "BOOLEAN", object=cutter, operation=operation, solver="EXACT")
    cutter.hide_render = cutter.hide_viewport = True
    cutter["kit_cutter"] = True
    return ob


# ------------------------------------------------------------------ layered armour on a shell


class Shell:
    """A curved surface to lay armour on, addressed by azimuth (0 = front, -Y,
    positive towards +X) and elevation (degrees above the horizon) round
    `centre`. Build it from any star-shaped mesh: a helm dome, a pauldron, a
    chest. Ray casts go against the mesh as it stands when the Shell is made,
    so make it before cutting visors with booleans."""

    def __init__(self, ob, centre=(0, 0, 0)):
        self.ob = ob
        self.centre = Vector(centre)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        mw = ob.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
        self.bvh = BVHTree.FromPolygons(verts, polys)
        self.reach = max((v - self.centre).length for v in verts) * 2 + 1

    def at(self, az, el, lift=0.0):
        """(point, normal) on the surface, lifted along the normal by `lift` mm."""
        d = direction(az, el)
        hit, normal, _, _ = self.bvh.ray_cast(self.centre + d * self.reach, -d)
        if hit is None:
            return self.centre + d * lift, d
        return hit + normal * lift, normal

    def line(self, pts, lift=0.0):
        """Surface points for a list of (az, el)."""
        return [self.at(a, e, lift)[0] for a, e in pts]

    def trim(self, name, pts, radius, mat, lift=0.0, cyclic=False, parent=None, profile="round"):
        """Raised trim swept along (az, el) points on the surface."""
        return sweep(name, self.line(pts, lift + radius * 0.6), radius, mat, cyclic=cyclic, parent=parent, profile=profile)

    def patch(self, name, az0, az1, el0, el1, mat, lift=0.2, thick=0.3, trim_mat=None, trim=0.12, decal=None, nu=32, nv=12,
              lip=0.0, parent=None):
        """An armour plate laid over the shell between two azimuths. `el0` and
        `el1` may be numbers or functions of azimuth, so edges can follow an
        arch. `lip` flares the lower edge out so stacked plates overlap.
        `trim_mat` edges the plate; `decal` is (mat, (u_tiles, v_tiles)) for a
        filigree inlay sheet laid just above it. Returns the plate."""
        lo = el0 if callable(el0) else (lambda a, v=el0: v)
        hi = el1 if callable(el1) else (lambda a, v=el1: v)

        def lift_at(j):
            return lift + lip * (1 - j / nv) ** 3

        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("Decal")
        grid = []
        for j in range(nv + 1):
            row = []
            for i in range(nu + 1):
                az = az0 + (az1 - az0) * i / nu
                el = lo(az) + (hi(az) - lo(az)) * j / nv
                row.append(bm.verts.new(self.at(az, el, lift_at(j))[0]))
            grid.append(row)
        _grid_faces(bm, grid, uv, ((az1 - az0) / 30, 1.0))
        ob = mesh_obj(name, bm, mat, parent=parent)
        mod(ob, "SOLIDIFY", thickness=thick, offset=1)
        mod(ob, "BEVEL", width=thick * 0.35, segments=2, limit_method="ANGLE")
        if trim_mat is not None and trim:
            edge = [(az0 + (az1 - az0) * i / nu, lo(az0 + (az1 - az0) * i / nu), lift_at(0)) for i in range(nu + 1)]
            edge += [(az1, lo(az1) + (hi(az1) - lo(az1)) * j / nv, lift_at(j)) for j in range(1, nv + 1)]
            edge += [(az1 - (az1 - az0) * i / nu, hi(az1 - (az1 - az0) * i / nu), lift) for i in range(1, nu + 1)]
            edge += [(az0, hi(az0) - (hi(az0) - lo(az0)) * j / nv, lift_at(nv - j)) for j in range(1, nv)]
            pts = [self.at(a, e, l + thick * 0.9)[0] for a, e, l in edge]
            sweep(name + "_trim", pts, trim, trim_mat, cyclic=True, parent=parent)
        if decal is not None:
            dmat, tiles = decal
            bm = bmesh.new()
            uv = bm.loops.layers.uv.new("Decal")
            m, k = 0.12, 0.76
            g = [[bm.verts.new(self.at(az0 + (az1 - az0) * (m + k * i / nu), lo(az0) + (hi(az0) - lo(az0)) * (m + k * j / nv), lift + thick + 0.02)[0])
                  for i in range(nu + 1)] for j in range(nv + 1)]
            _grid_faces(bm, g, uv, tiles)
            sheet = mesh_obj(name + "_inlay", bm, dmat, parent=parent)
            mod(sheet, "SOLIDIFY", thickness=0.04, offset=1)
        return ob

    def lames(self, name, az0, az1, bands, mat, trim_mat=None, lift=0.2, step=0.15, thick=0.25, lip=0.4, parent=None, **kw):
        """Stacked overlapping bands, top to bottom: `bands` is a list of
        (el_low, el_high); each lower lame rides `step` mm further out."""
        return [self.patch(f"{name}_{k}", az0, az1, e0, e1, mat, lift=lift + step * k, thick=thick, trim_mat=trim_mat, lip=lip, parent=parent, **kw)
                for k, (e0, e1) in enumerate(bands)]

    def flutes(self, name, azimuths, el0, el1, radius, mat, trim_mat=None, parent=None, steps=20):
        """Vertical ribs running up the surface at each azimuth."""
        out = []
        for az in azimuths:
            pts = [(az, el0 + (el1 - el0) * k / steps) for k in range(steps + 1)]
            out.append(self.trim(f"{name}_{az:g}", pts, radius, mat, parent=parent))
            if trim_mat is not None:
                out.append(self.trim(f"{name}_{az:g}_trim", pts, radius * 0.4, trim_mat, lift=radius * 1.1, parent=parent))
        return out

    def studs(self, name, pts, radius, mat, parent=None):
        """Domed studs at (az, el) points, joined into one object."""
        bm = bmesh.new()
        for a, e in pts:
            p, n = self.at(a, e, 0)
            rot = n.to_track_quat("Z", "Y").to_matrix()
            geom = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=radius)
            for v in geom["verts"]:
                v.co = p + rot @ Vector((v.co.x, v.co.y, max(v.co.z, -radius * 0.2) * 0.8))
        ob = mesh_obj(name, bm, mat, parent=parent)
        decal_uv(ob)
        return ob
