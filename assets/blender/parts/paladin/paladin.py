"""The Iron Covenant Paladin's dressing: cape and tabard, back towers, helm crown.

    ~/bvenv/bin/python assets/blender/parts/paladin/paladin.py [cloth back crown ...] [--render OUT] [--no-publish]

Parts (covenant frame titan, class paladin, so they only dress the Paladin):
    covenant_cloth_paladin   a tattered crimson cape with a gold snowflake sigil, and a front tabard
    covenant_back_paladin    two launcher pods on posts behind the shoulders
    covenant_pauldron_paladin angular shield-shaped pauldrons with crimson inlays

All are modelled in place on the walker from the frame's joints, then moved
into their joint's space. Reference: the north-star render
(docs/concept-art/north-star-paladin.jpg) and the Iron Covenant board.
"""
import math
import random
import sys
from pathlib import Path

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # assets/blender
import kit
from kit import shapes
from kit.core import bmesh, mesh_obj, mod
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
FACTION, FRAME, CLS = "covenant", "titan", "paladin"


def sheet(name, surf, nu, nv, mat, thick=0.35, parent=None):
    """A cloth sheet: surf(u, v) -> point, u across 0..1, v down 0..1, thickened."""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    grid = [[bm.verts.new(surf(i / nu, j / nv)) for i in range(nu + 1)] for j in range(nv + 1)]
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            for loop, (di, dj) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                loop[uvl].uv = ((i + di) / nu, 1 - (j + dj) / nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, mat, parent=parent)
    mod(ob, "SOLIDIFY", thickness=thick, offset=0)
    shapes.decal_uv(ob, 6.0)
    return ob


def cape(sk, m, root):
    H, W = sk.H, sk.W
    sh = sk.joint("shoulder")
    top_z = sh.z - 0.012 * H
    hip_z = sk.joint("hip").z
    ankle_z = sk.joint("ankle").z
    half = 0.17 * H * W
    rnd = random.Random(7)
    teeth = [rnd.uniform(0.0, 1.0) for _ in range(64)]

    def hem(u):
        # Long on the walker's right (-X, u = 0), flying out; ragged teeth.
        base = ankle_z + 0.02 * H + (0.20 * H) * u ** 1.3
        i = u * 24
        k = int(i)
        t = i - k
        tooth = abs(2 * t - 1)
        return base - tooth * (0.03 + 0.07 * teeth[k % 64]) * H

    def surf(u, v):
        x = -half + 2 * half * u
        top = Vector((x, 0.098 * H, top_z - 0.02 * H * abs(2 * u - 1) ** 2))
        z = top.z + (hem(u) - top.z) * v
        flare = 1 + 0.55 * v ** 1.3
        sweep_x = -0.30 * H * v ** 1.8 * (1 - u * 0.45)
        y = top.y + 0.035 * H * v + 0.11 * H * v ** 1.7 * (1.2 - u * 0.6)
        wave = 0.022 * H * v * math.sin(u * 9.0 + v * 4.0) + 0.012 * H * v * math.sin(u * 23 + v * 7.0)
        return Vector((x * flare + sweep_x, y + wave, z))

    c = sheet("cape", surf, 56, 70, m["cloth"], thick=0.4, parent=root)
    # Gold hem along the shoulder line, and a trim down the open edge.
    top = [surf(i / 24, 0.0) + Vector((0, 0.15, 0.1)) for i in range(25)]
    shapes.sweep("cape_yoke", top, 0.28, m["trim"], parent=root)
    for edge, name in ((0.0, "cape_edge_r"), (1.0, "cape_edge_l")):
        pts = [surf(edge, j / 30) + Vector((0, 0.1, 0)) for j in range(31)]
        shapes.sweep(name, pts, 0.17, m["trim"], parent=root)
    # The sigil: a six-armed snowflake picked out in raised gold.
    u0, v0, size = 0.45, 0.36, 0.12 * H

    c0 = surf(u0, v0)
    tu = (surf(u0 + 0.01, v0) - surf(u0 - 0.01, v0)).normalized()
    tv = (surf(u0, v0 + 0.01) - surf(u0, v0 - 0.01)).normalized()
    nrm = tu.cross(tv).normalized()
    if nrm.y < 0:
        nrm = -nrm
    tv = nrm.cross(tu).normalized()

    def on(a, b):
        # A flat sigil in the cloth's tangent plane, lifted off the surface.
        return c0 + tu * a + tv * b + nrm * 1.3

    for k in range(6):
        ang = math.pi * k / 3 + math.pi / 6
        d, perp = (math.cos(ang), math.sin(ang)), (-math.sin(ang), math.cos(ang))
        shapes.sweep(f"sigil_arm{k}", [on(d[0] * size * t, d[1] * size * t) for t in (0, 0.5, 1.0)], 0.3, m["trim"], parent=root)
        for t, br in ((0.45, 0.32), (0.75, 0.22)):
            for s in (-1, 1):
                pts = [on(d[0] * size * t, d[1] * size * t),
                       on(d[0] * size * (t + br * 0.8) + s * perp[0] * size * br, d[1] * size * (t + br * 0.8) + s * perp[1] * size * br)]
                shapes.sweep(f"sigil_twig{k}_{t}_{s}", pts, 0.22, m["trim"], parent=root)
    shapes.sphere("sigil_hub", 0.7, m["trim"], loc=on(0, 0), parent=root, segments=12)
    return c


def tabard(sk, m, root):
    H, W = sk.H, sk.W
    top_z = sk.joint("pelvis").z + 0.04 * H
    bot_z = sk.joint("knee").z - 0.03 * H
    half = 0.04 * H

    def surf(u, v):
        x = -half + 2 * half * u
        hem = bot_z - 0.05 * H * (1 - abs(2 * u - 1))   # a swallow-tail point
        z = top_z + (hem - top_z) * v
        y = -0.082 * H - 0.03 * H * v + 0.01 * H * v * math.sin(u * 5 + v * 3)
        return Vector((x * (1 + 0.25 * v), y, z))

    t = sheet("tabard", surf, 16, 40, m["cloth"], thick=0.4, parent=root)
    for edge, name in ((0.0, "tabard_edge_r"), (1.0, "tabard_edge_l")):
        shapes.sweep(name, [surf(edge, j / 20) + Vector((0, -0.12, 0)) for j in range(21)], 0.13, m["trim"], parent=root)
    shapes.sweep("tabard_belt", [surf(i / 8, 0) + Vector((0, -0.2, 0.1)) for i in range(9)], 0.24, m["trim"], parent=root)
    shapes.sphere("tabard_clasp", 0.7, m["trim"], loc=surf(0.5, 0.03) + Vector((0, -0.6, 0)), parent=root, segments=14)
    return t


def sash(sk, m, root):
    """A crimson banner hung over the left pauldron's front, as in the render."""
    H = sk.H
    sh, el = sk.joint("shoulder"), sk.joint("elbow")
    top = sh + Vector((0.035 * H, -0.072 * H, 0.06 * H))
    drop = top.z - (el.z + 0.02 * H)
    half = 0.028 * H

    def surf(u, v):
        x = -half + 2 * half * u
        lean = 0.05 * H * v ** 1.5           # falls clear of the pauldron's rim
        hem = 0.03 * H * (1 - abs(2 * u - 1))  # pointed hem
        return top + Vector((x + 0.02 * H * v, -0.02 * H * math.sin(min(v * 4, 1.0) * math.pi / 2) - 0.004 * H * math.sin(u * 7) * v, -(drop + hem) * v + 0 * lean))

    sheet("sash", surf, 12, 30, m["cloth"], thick=0.35, parent=root)
    for edge, name in ((0.0, "sash_edge_r"), (1.0, "sash_edge_l")):
        shapes.sweep(name, [surf(edge, j / 16) + Vector((0, -0.12, 0)) for j in range(17)], 0.12, m["trim"], parent=root)
    shapes.sweep("sash_bar", [surf(i / 6, 0.0) + Vector((0, -0.25, 0.1)) for i in range(7)], 0.3, m["trim"], parent=root)
    # A small gold cross on the banner.
    c = surf(0.5, 0.45) + Vector((0, -0.3, 0))
    shapes.sweep("sash_cross_v", [c + Vector((0, 0, 0.045 * H)), c - Vector((0, 0, 0.045 * H))], 0.18, m["trim"], parent=root)
    shapes.sweep("sash_cross_h", [c + Vector((0.017 * H, 0, 0.012 * H)), c + Vector((-0.017 * H, 0, 0.012 * H))], 0.18, m["trim"], parent=root)


def cloth(sk, m, root):
    cape(sk, m, root)
    tabard(sk, m, root)
    sash(sk, m, root)


def facet(name, origin, u, v, pts, thick, mat, parent, frame_mat=None, inlay_mat=None, inlay=0.72, frame_r=0.16):
    """A flat armour plate: polygon `pts` (in units along u, v from origin),
    `thick` deep along u x v, with a raised gold frame round its edge and an
    optional enamel inlay panel inset by the `inlay` scale."""
    u, v = Vector(u).normalized(), Vector(v).normalized()
    n = u.cross(v).normalized()
    o = Vector(origin)
    at = lambda a, b, h=0.0: o + u * a + v * b + n * h  # noqa: E731
    bm = bmesh.new()
    front = [bm.verts.new(at(a, b, thick / 2)) for a, b in pts]
    back_ = [bm.verts.new(at(a, b, -thick / 2)) for a, b in pts]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back_)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((front[j], front[i], back_[i], back_[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, mat, smooth=False, parent=parent)
    mod(ob, "BEVEL", width=min(thick * 0.3, 0.25), segments=2, limit_method="ANGLE")
    shapes.decal_uv(ob, 4.0)
    if frame_mat is not None:
        edge = [at(a, b, thick / 2 + frame_r * 0.3) for a, b in pts]
        shapes.sweep(f"{name}_frame", edge, frame_r, frame_mat, cyclic=True, parent=parent, profile="square")
    if inlay_mat is not None:
        cx = sum(a for a, _ in pts) / len(pts)
        cy = sum(b for _, b in pts) / len(pts)
        ins = [(cx + (a - cx) * inlay, cy + (b - cy) * inlay) for a, b in pts]
        bm = bmesh.new()
        vs = [bm.verts.new(at(a, b, thick / 2 + 0.08)) for a, b in ins]
        bm.faces.new(vs)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        pl = mesh_obj(f"{name}_inlay", bm, inlay_mat, smooth=False, parent=parent)
        mod(pl, "SOLIDIFY", thickness=0.15, offset=1)
        shapes.decal_uv(pl, 4.0)
        if frame_mat is not None:
            shapes.sweep(f"{name}_inlay_frame", [at(a, b, thick / 2 + 0.2) for a, b in ins], frame_r * 0.6, frame_mat, cyclic=True, parent=parent, profile="square")
    return ob, at


def pauldron(sk, m, root):
    """A gothic pauldron of curved, overlapping plates round the shoulder: a
    filigree cap with a crimson inlay and gold arch, three flared lames below,
    a raised crest and a peak spike (north-star render; modelled for the left,
    mirrored on the right)."""
    H = sk.H
    S = sk.joint("shoulder")
    C = S + Vector((0.008 * H, 0.0, -0.018 * H))
    rx, ry, rz = 0.074 * H, 0.08 * H, 0.068 * H

    def shell(flare=0.0, drop=0.0):
        def surf(a, e):
            # a: azimuth in degrees from +X (out), positive toward the front; e: elevation.
            ar, er = math.radians(a), math.radians(e)
            k = 1 + flare * max(0.0, -e + 20) / 60
            sq = lambda c, q=0.45: math.copysign(abs(c) ** q, c)  # noqa: E731  squarish: flat faces, hard corners
            ce, se, ca, sa = sq(math.cos(er)), sq(math.sin(er)), sq(math.cos(ar)), sq(math.sin(ar))
            n = Vector((ce * ca / rx, -ce * sa / ry, se / rz)).normalized()
            p = C + Vector((ce * ca * rx * k, -ce * sa * ry * k, se * rz - drop))
            return p, n
        return surf

    # Cap: the big plate over the top and outside, crimson panel on its face.
    patch("pauldron_cap", shell(), -80, 80, 2, 86, 0.0, 1.2, m["filigree"], root, m["trim"], 0.26, n=4)
    # The crimson shield panel on the outer face, gold framed.
    patch("pauldron_panel", shell(), -34, 34, 10, 52, 0.45, 0.5, m["hull"], root, m["trim"], 0.2, n=2)
    # Lames: three overlapping bands below, each flaring further out.
    for i in range(3):
        e1 = 6 - i * 17
        patch(f"pauldron_lame{i}", shell(flare=0.08 + 0.05 * i, drop=0.004 * H * i), -70 + i * 4, 70 - i * 4, e1 - 20, e1, 0.25, 1.0,
              m["armour"], root, m["trim"], 0.2, n=3)
    # Crest: a gold ridge over the cap from front to back, and a flange behind it.
    # Gothic flange: a pointed-arch plate standing up along the top, front to back.
    base = C + Vector((0.035 * H, 0.0, rz * 0.7))
    L = 0.055 * H
    arch = [(-L, 0.0), (L, 0.0), (L, 0.035 * H), (L * 0.6, 0.07 * H), (0.0, 0.095 * H), (-L * 0.6, 0.07 * H), (-L, 0.035 * H)]
    facet("pauldron_flange", base, (0, -1, 0), (-0.25, 0, 1), arch, 0.9, m["filigree"], root, m["trim"], m["hull"], inlay=0.55, frame_r=0.24)
    # Gothic arch on the outer face, over the crimson panel.
    p, n = shell()(0, 16)
    arch = shapes.lancet("pauldron_arch", 0.032 * H, 0.045 * H, 0.3, m["trim"], loc=p + n * 0.9, parent=root)
    arch.rotation_euler = (n.to_track_quat("-Y", "Z")).to_euler()
    # Peak spike at the top.
    p = base + Vector((-0.25, 0, 1)).normalized() * 0.095 * H
    shapes.sphere("pauldron_spike_ball", 0.011 * H, m["trim"], loc=p, parent=root, segments=12)
    shapes.cylinder("pauldron_spike", 0.008 * H, 0.04 * H, m["trim"], loc=p + Vector((0, 0, 0.02 * H)), parent=root, verts=8, bevel=0.05, r2=0.0005)
    # Studs round the cap's rim.
    for a in range(-70, 75, 20):
        q, nn = shell()(a, 8)
        shapes.sphere("pauldron_stud", 0.0055 * H, m["trim"], loc=q + nn * 1.4, parent=root, segments=8)
    # Turn the pauldron about the shoulder so its crimson face looks forward-out.
    bpy.context.view_layer.update()
    turn = Matrix.Translation(S) @ Matrix.Rotation(math.radians(-28), 4, "Z") @ Matrix.Translation(-S)
    for c in root.children:
        c.matrix_world = turn @ c.matrix_world


def back(sk, m, root):
    """Two launcher pods on posts behind the shoulders, raked outward, faces
    pierced by a grid of tubes (north-star render)."""
    H = sk.H
    for s, side in ((1, "L"), (-1, "R")):
        sh = sk.joint("shoulder", side)
        piv = kit.empty(f"pod_pivot{side}", sh + Vector((s * -0.05 * H, 0.1 * H, 0.05 * H)), parent=root, size=1)
        piv.rotation_euler = (math.radians(-8), 0, s * math.radians(-28))
        shapes.cylinder(f"pod_post{side}", 0.014 * H, 0.06 * H, m["metal"], loc=(0, 0.01 * H, -0.03 * H), parent=piv, verts=12, bevel=0.15)
        body = shapes.box_plate(f"pod{side}", (0.075 * H, 0.1 * H, 0.06 * H), m["armour"], bevel=0.25, loc=(s * 0.03 * H, 0.0, 0.035 * H), parent=piv)
        for z in (0.008, 0.062):
            shapes.box_plate(f"pod_band{side}{z}", (0.079 * H, 0.104 * H, 0.006 * H), m["trim"], bevel=0.1, loc=(s * 0.03 * H, 0.0, z * H), parent=piv)
        for x in (-0.039, 0.039):
            shapes.box_plate(f"pod_rib{side}{x}", (0.005 * H, 0.104 * H, 0.06 * H), m["trim"], bevel=0.08, loc=(s * 0.03 * H + x * H, 0.0, 0.035 * H), parent=piv)
        for i in range(3):
            for j in range(2):
                c = Vector((s * 0.03 * H + (i - 1) * 0.022 * H, -0.05 * H, 0.022 * H + j * 0.026 * H))
                shapes.cylinder(f"pod_tube{side}{i}{j}", 0.0095 * H, 0.012 * H, m["metal"], loc=c, rot=(math.pi / 2, 0, 0), parent=piv, verts=14, bevel=0.06)
                shapes.cylinder(f"pod_bore{side}{i}{j}", 0.0062 * H, 0.004 * H, m["glow"], loc=c + Vector((0, -0.0045 * H, 0)), rot=(math.pi / 2, 0, 0), parent=piv, verts=12, bevel=0)
        shapes.spire(f"pod_finial{side}", 0.014 * H, 0.04 * H, m["armour"], trim=m["trim"], loc=(s * 0.03 * H, 0.04 * H, 0.065 * H), parent=piv, crockets=1, sides=6)


def crown(sk, m, root):
    """The head's gothic tower: a tall traceried spire with four corner
    pinnacles, rising from the helm (north-star render)."""
    H = sk.H
    head = sk.joint("head")
    top = head + Vector((0, 0.01 * H, 0.092 * H))
    shapes.cylinder("crown_base", 0.04 * H, 0.012 * H, m["trim"], loc=top, parent=root, verts=8, bevel=0.15)
    shaft_w, shaft_h = 0.062 * H, 0.09 * H
    shapes.box_plate("crown_shaft", (shaft_w, shaft_w, shaft_h), m["filigree"], bevel=0.2, loc=top + Vector((0, 0, shaft_h / 2 + 0.004 * H)), parent=root, taper=0.12)
    for k, rz in enumerate((0, math.pi / 2, math.pi, -math.pi / 2)):
        d = Vector((math.sin(rz), -math.cos(rz), 0))
        shapes.lancet(f"crown_window{k}", 0.024 * H, 0.06 * H, 0.3, m["trim"], glow=m["glow"],
                      loc=top + d * (shaft_w * 0.47) + Vector((0, 0, 0.014 * H)), rot=(0, 0, rz), parent=root)
    for k, (x, y) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        shapes.spire(f"crown_pinnacle{k}", 0.016 * H, 0.06 * H, m["armour"], trim=m["trim"],
                     loc=top + Vector((x * shaft_w * 0.52, y * shaft_w * 0.52, shaft_h * 0.72)), parent=root, crockets=1, sides=6)
    shapes.spire("crown_spire", 0.064 * H, 0.15 * H, m["armour"], trim=m["trim"], loc=top + Vector((0, 0, shaft_h + 0.004 * H)), parent=root, crockets=4, sides=8)


def loft(name, rings, mat, parent, smooth=False, cap=True):
    """Join closed rings of points (same count each, bottom to top) into a
    shell, capped at both ends. Few sides and flat shading keep it faceted."""
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for j in range(len(vs) - 1):
        for i in range(n):
            k = (i + 1) % n
            bm.faces.new((vs[j][i], vs[j][k], vs[j + 1][k], vs[j + 1][i]))
    if cap:
        bm.faces.new(list(reversed(vs[0])))
        bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, mat, smooth=smooth, parent=parent)
    shapes.decal_uv(ob, 4.0)
    return ob


def patch(name, surf, x0, x1, z0, z1, lift, thick, mat, parent, frame_mat=None, frame_r=0.2, n=8, inlay_mat=None, inlay=0.22):
    """A plate laid on a surface: surf(x, z) -> (point, outward normal). The
    plate covers x0..x1, z0..z1, sits `lift` off the surface, with a gold
    frame round it and an optional enamel panel inset by `inlay` of its size."""
    def grid(xa, xb, za, zb, h):
        return [[(lambda pn: pn[0] + pn[1] * h)(surf(xa + (xb - xa) * i / n, za + (zb - za) * j / n)) for i in range(n + 1)] for j in range(n + 1)]

    def plate(nm, g, m, t):
        bm = bmesh.new()
        vs = [[bm.verts.new(p) for p in row] for row in g]
        for j in range(n):
            for i in range(n):
                bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        ob = mesh_obj(nm, bm, m, smooth=True, parent=parent)
        mod(ob, "SOLIDIFY", thickness=t, offset=-1 if t > 0 else 0)
        mod(ob, "BEVEL", width=min(abs(t) * 0.35, 0.2), segments=2, limit_method="ANGLE")
        shapes.decal_uv(ob, 4.0)
        return ob

    g = grid(x0, x1, z0, z1, lift)
    plate(name, g, mat, thick)
    if frame_mat is not None:
        ring = [g[0][i] for i in range(n + 1)] + [g[j][n] for j in range(1, n + 1)] + [g[n][i] for i in range(n - 1, -1, -1)] + [g[j][0] for j in range(n - 1, 0, -1)]
        shapes.sweep(f"{name}_frame", ring, frame_r, frame_mat, cyclic=True, parent=parent, profile="square")
    if inlay_mat is not None:
        dx, dz = (x1 - x0) * inlay / 2, (z1 - z0) * inlay / 2
        gi = grid(x0 + dx, x1 - dx, z0 + dz, z1 - dz, lift + 0.12)
        plate(f"{name}_inlay", gi, inlay_mat, 0.15)
        if frame_mat is not None:
            ring = [gi[0][i] for i in range(n + 1)] + [gi[j][n] for j in range(1, n + 1)] + [gi[n][i] for i in range(n - 1, -1, -1)] + [gi[j][0] for j in range(n - 1, 0, -1)]
            shapes.sweep(f"{name}_inlay_frame", ring, frame_r * 0.55, frame_mat, cyclic=True, parent=parent, profile="square")


def torso(sk, m, root):
    """A faceted breastplate of gold-framed panels with crimson inlays over a
    narrow-waisted, keeled core, after the north-star render."""
    H = sk.H
    z0 = sk.joint("spine").z - 0.01 * H
    z1 = sk.joint("neck").z - 0.012 * H
    Z = z1 - z0

    def half(t):
        # Half width and half depth of the core at height fraction t (0 waist, 1 top).
        hx = 0.07 + 0.075 * min(t / 0.72, 1.0) ** 1.2 - 0.05 * max(0.0, (t - 0.82) / 0.18) ** 1.5
        hy = 0.052 + 0.03 * min(t / 0.7, 1.0) - 0.012 * max(0.0, (t - 0.85) / 0.15)
        return hx * H, hy * H

    def section(t, sides=10):
        hx, hy = half(t)
        z = z0 + Z * t
        pts = []
        for i in range(sides):
            a = 2 * math.pi * i / sides + math.pi / sides
            x, y = math.sin(a) * hx, -math.cos(a) * hy
            ca = abs(math.cos(a))
            # Keel: the front pulled forward at the middle, most at the chest.
            if math.cos(a) > 0.0:
                y -= 0.018 * H * ca ** 3 * (0.4 + 0.6 * min(t / 0.65, 1.0))
            pts.append(Vector((x, y, z)))
        return pts

    loft("torso_core", [section(t) for t in (0.0, 0.18, 0.38, 0.6, 0.78, 0.92, 1.0)], m["armour"], root)

    def front(x, t):
        """Point on the front of the core and its outward normal (x in mm from the keel)."""
        hx, hy = half(t)
        u = max(-0.98, min(0.98, x / hx))
        y = -hy * math.sqrt(1 - u * u) - 0.018 * H * (1 - abs(u)) ** 3 * (0.4 + 0.6 * min(t / 0.65, 1.0))
        p = Vector((x, y, z0 + Z * t))
        nrm = Vector((u / hx * hy * 0.9, -1.0, 0.15 * (0.5 - t))).normalized()
        return p, nrm

    for s, side in ((1, "L"), (-1, "R")):
        hx_top = half(0.75)[0]
        # Pectoral: a big slanted plate from the keel out to the arm, crimson inlay.
        patch(f"pectoral{side}", lambda x, t: front(s * x, t), 0.004 * H, hx_top * 0.86, 0.56, 0.9, 0.35, 1.0,
              m["filigree"], root, m["trim"], 0.22, inlay_mat=m["hull"], inlay=0.3)
        # Two rows of abdominal plates, narrowing to the waist.
        for k, (ta, tb, w) in enumerate(((0.3, 0.52, 0.62), (0.06, 0.28, 0.52))):
            hx = half((ta + tb) / 2)[0]
            patch(f"abdomen{side}{k}", lambda x, t: front(s * x, t), 0.004 * H, hx * w * 1.15, ta, tb, 0.6, 0.9,
                  m["filigree"], root, m["trim"], 0.22, inlay_mat=m["hull"] if k == 0 else None, inlay=0.32)
        # Flank plates wrapping round the sides.
        def flank(a, t, s=s):
            hx, hy = half(t)
            ang = math.radians(a)
            p = Vector((s * math.sin(ang) * hx, -math.cos(ang) * hy, z0 + Z * t))
            return p, Vector((s * math.sin(ang) / hx, -math.cos(ang) / hy, 0)).normalized()
        patch(f"flank{side}", flank, 70, 125, 0.18, 0.7, 0.3, 0.9, m["armour"], root, m["trim"], 0.17)
        # Back: two tall plates either side of the spine ridge.
        patch(f"back{side}", flank, 140, 176, 0.12, 0.88, 0.3, 0.9, m["armour"], root, m["trim"], 0.17)
    # The keel ridge and sternum rondel: a crimson boss in a gold ring, with a glowing core.
    keel = [front(0.0, t / 10)[0] + Vector((0, -0.45, 0)) for t in range(1, 10)]
    shapes.sweep("keel", keel, 0.35, m["trim"], parent=root, profile="square")
    c, nrm = front(0.0, 0.47)
    boss = shapes.cylinder("rondel", 0.034 * H, 0.9, m["hull"], loc=c + nrm * 0.7, parent=root, verts=24, bevel=0.2)
    boss.rotation_euler = nrm.to_track_quat("Z", "Y").to_euler()
    ring = shapes.cylinder("rondel_ring", 0.04 * H, 0.6, m["trim"], loc=c + nrm * 0.55, parent=root, verts=24, bevel=0.15)
    ring.rotation_euler = boss.rotation_euler
    eye = shapes.cylinder("rondel_core", 0.012 * H, 0.4, m["glow"], loc=c + nrm * 1.3, parent=root, verts=16, bevel=0.05)
    eye.rotation_euler = boss.rotation_euler
    # Gorget rim and waist belt.
    shapes.sweep("gorget", [p + Vector((0, 0, 0.1)) for p in section(1.0, 20)], 0.3, m["trim"], cyclic=True, parent=root, profile="square")
    shapes.sweep("waist", [p * 1.0 + Vector((0, 0, 0.3)) for p in section(0.0, 20)], 0.35, m["trim"], cyclic=True, parent=root, profile="square")
    # Spine ridge on the back.
    spine = [Vector((0, half(t / 10)[1] + 0.4, z0 + Z * t / 10)) for t in range(1, 10)]
    shapes.sweep("spine_ridge", spine, 0.4, m["trim"], parent=root, profile="square")


def helm(sk, m, root):
    """A sharp, faceted armet: an octagonal shell with a hard keel down the
    face, a pointed brow, a glowing eye slit and breaths, gold edged."""
    H = sk.H
    R = 0.058 * H
    c = sk.joint("head") + Vector((0, 0, 0.03 * H))
    # (height, half width, half depth, keel pull): chin up to the flat crown.
    rows = [(-1.15, 0.3, 0.42, 0.62), (-0.7, 0.66, 0.8, 0.5), (-0.18, 0.78, 0.9, 0.36),
            (0.24, 0.8, 0.96, 0.55), (0.62, 0.66, 0.84, 0.26), (1.0, 0.46, 0.6, 0.12), (1.32, 0.24, 0.32, 0.05), (1.62, 0.04, 0.05, 0.0)]

    def ring(z, hx, hy, keel, sides=8):
        pts = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            x, y = math.sin(a) * hx, -math.cos(a) * hy
            if i == 0:
                y -= keel
            pts.append(c + Vector((x, y, z)) * R)
        return pts

    shell = loft("helm_shell", [ring(*r) for r in rows], m["armour"], root)
    mod(shell, "BEVEL", width=0.12, segments=1, limit_method="ANGLE", angle_limit=math.radians(20))

    def face(z, x=0.0):
        """A point on the front face at height z (helm units), x across."""
        for (za, *ra), (zb, *rb) in zip(rows, rows[1:]):
            if za <= z <= zb:
                f = (z - za) / (zb - za)
                hx, hy, keel = [p + (q - p) * f for p, q in zip(ra, rb)]
                break
        y = -(hy + keel) + abs(x) * (keel + hy * (1 - math.cos(math.pi / 4))) / (hx * math.sin(math.pi / 4))
        return c + Vector((x, y - 0.03, z)) * R

    # Eye slit: a narrow glowing chevron across the brow, in a gold frame.
    for s in (-1, 1):
        a, b = face(0.06, 0.0), face(0.15, s * 0.62)
        mid = (a + b) / 2
        d = b - a
        slit = shapes.box_plate(f"eye{'LR'[s > 0]}", (d.length, 0.06 * R, 0.09 * R), m["glow"], bevel=0, loc=mid + Vector((0, -0.02 * R, 0)), parent=root)
        slit.rotation_euler = (0, -math.atan2(d.z, math.hypot(d.x, d.y)) * s, math.atan2(d.y, d.x) if s > 0 else math.atan2(-d.y, -d.x))
        brow = [face(0.26, 0.0) + Vector((0, -0.05 * R, 0)), face(0.33, s * 0.7) + Vector((0, -0.03 * R, 0))]
        shapes.sweep(f"brow{'LR'[s > 0]}", brow, 0.07 * R, m["trim"], parent=root, profile="square")
        # Breaths: vertical slits down the cheek either side of the keel.
        for k in range(3):
            x = s * (0.16 + 0.13 * k)
            top, bot = face(-0.12, x), face(-0.62 + 0.08 * k, x)
            pts = [top + Vector((0, -0.02 * R, 0)), bot + Vector((0, -0.02 * R, 0))]
            shapes.sweep(f"breath{'LR'[s > 0]}{k}", pts, 0.035 * R, m["glow"], parent=root, profile="square")
    keel = [face(z) + Vector((0, -0.06 * R, 0)) for z in (-0.98, -0.6, -0.15, 0.22, 0.55, 0.86)]
    shapes.sweep("helm_keel", keel, 0.07 * R, m["trim"], parent=root, profile="square")
    rim = [p + Vector((0, 0, 0.02 * R)) for p in ring(*rows[0])]
    shapes.sweep("helm_rim", rim, 0.06 * R, m["trim"], cyclic=True, parent=root, profile="square")
    shapes.sweep("helm_band", ring(*rows[4]), 0.06 * R, m["trim"], cyclic=True, parent=root, profile="square")
    # Gold ribs from the band up the four corners to the point, and a finial.
    tip = c + Vector((0, 0, 1.64)) * R
    for i in (1, 3, 5, 7):
        pts = [ring(*r)[i] for r in rows[4:7]] + [tip]
        shapes.sweep(f"helm_rib{i}", pts, 0.045 * R, m["trim"], parent=root, profile="square")
    shapes.sphere("helm_finial", 0.09 * R, m["trim"], loc=tip + Vector((0, 0, 0.05 * R)), parent=root, segments=12)


def collar(sk, m, root):
    """A low, faceted gorget between the breastplate and the helm."""
    H = sk.H
    z0 = sk.joint("neck").z - 0.016 * H
    rows = [(0.0, 0.075, 0.062), (0.022, 0.068, 0.058), (0.04, 0.05, 0.045)]
    rings = []
    for dz, rx, ry in rows:
        rings.append([Vector((math.sin(2 * math.pi * i / 8 + math.pi / 8) * rx * H, -math.cos(2 * math.pi * i / 8 + math.pi / 8) * ry * H, z0 + dz * H)) for i in range(8)])
    loft("gorget", rings, m["armour"], root)
    for k, ring in enumerate(rings[:2]):
        shapes.sweep(f"gorget_rim{k}", [p + Vector((0, 0, 0.1)) for p in ring], 0.22, m["trim"], cyclic=True, parent=root, profile="square")


BUILDERS = {"cloth": cloth, "back": back, "pauldron": pauldron, "torso": torso, "helm": helm, "collar": collar}


def build(component):
    kit.reset_scene()
    m = kit.materials.library(FACTION)
    sk = kit.skeleton.Skeleton(FACTION, FRAME)
    root = kit.empty(kit.part_name(FACTION, component, CLS), size=0.05 * sk.H)
    BUILDERS[component](sk, m, root)
    return root, sk


def main(argv):
    comps = [a for a in argv if a in BUILDERS] or list(BUILDERS)
    render = Path(argv[argv.index("--render") + 1]) if "--render" in argv else None
    for comp in comps:
        root, sk = build(comp)
        if render:
            frame = kit.skeleton.build_frame(FACTION, FRAME)
            for o in list(frame.children_recursive):
                if o.get("standin") == comp:
                    o.hide_render = True
                    for c in o.children_recursive:
                        c.hide_render = True
            kit.render.studio(floor=True)
            objs = kit.meshes(root) + kit.meshes(frame)
            shots = []
            for az, el in ((200, 8), (35, 8)):
                p = render / f"{comp}-{az}.png"
                kit.render.shot(objs, p, az=az, el=el, samples=32, res=(560, 900), margin=0.72)
                kit.render.post(p)
                shots.append(p)
            if comp in ("helm", "torso", "pauldron"):
                for az in (25, 70):
                    p = render / f"{comp}-close-{az}.png"
                    kit.render.shot(kit.meshes(root), p, az=az, el=10, samples=32, res=(600, 600), margin=0.8)
                    kit.render.post(p)
                    shots.append(p)
            kit.render.compare(shots, None, render / f"{comp}-compare.png", title=f"covenant {comp} paladin")
        if "--no-publish" not in argv:
            kit.skeleton.to_joint(root, FACTION, FRAME, comp)
            kit.publish(root, source=HERE / f"{FACTION}_{comp}_{CLS}.blend")


if __name__ == "__main__":
    main(sys.argv[1:] if "--" not in sys.argv else sys.argv[sys.argv.index("--") + 1:])
