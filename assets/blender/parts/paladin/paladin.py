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
    # Clasps: the cape hangs from two gold bars bolted to the back of the shoulder yokes.
    for u, side in ((0.12, "R"), (0.88, "L")):
        p0 = surf(u, 0.0)
        p1 = Vector((p0.x * 1.05, 0.03 * H, sh.z + 0.05 * H))
        shapes.sweep(f"cape_clasp{side}", [p0 + Vector((0, 0.1, 0.2)), (p0 + p1) / 2 + Vector((0, 0, 0.01 * H)), p1], 0.3, m["trim"], parent=root, profile="square")
        shapes.sphere(f"cape_clasp_boss{side}", 0.012 * H, m["trim"], loc=p0 + Vector((0, 0.2, 0.1)), parent=root, segments=12)
        shapes.sphere(f"cape_clasp_bolt{side}", 0.009 * H, m["trim"], loc=p1, parent=root, segments=10)
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
    top = sh + Vector((0.035 * H, -0.125 * H, -0.045 * H))   # under the pauldron's front lame
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


def face_rot(n):
    """Euler turning a part that faces -Y to face along n, kept upright."""
    y = -n.normalized()
    z = Vector((0, 0, 1))
    z = (z - y * z.dot(y)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_euler()


def solid(name, verts, faces, mats, parent, thick, face_mat=None, bevel=0.12):
    """A hard-surface plate from explicit faces: solidified inward by `thick`,
    flat shaded with crisp bevelled edges. face_mat[i] picks mats[k] per face."""
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for k, f in enumerate(faces):
        face = bm.faces.new([vs[i] for i in f])
        face.material_index = face_mat[k] if face_mat else 0
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, mats[0], smooth=True, parent=parent)
    ob.data.set_sharp_from_angle(angle=math.radians(28))
    for mt in mats[1:]:
        ob.data.materials.append(mt)
    mod(ob, "SOLIDIFY", thickness=thick, offset=-1, use_rim=True)
    mod(ob, "BEVEL", width=bevel, segments=2, limit_method="ANGLE", angle_limit=math.radians(25))
    shapes.decal_uv(ob, 4.0)
    return ob


def pauldron(sk, m, root):
    """The render's pauldron: one big angular plate. A roof that slopes up
    toward the neck and ends in an upturned crest, folding hard into a skirt
    that wraps the front and outside of the shoulder and flares to a hem
    drawn down to a point at the outer front corner. Crimson on the outer
    face. Modelled for the left, mirrored on the right."""
    H = sk.H
    S = sk.joint("shoulder")

    def P(o, f, u):
        """Shoulder space in fractions of H: o out, f forward, u up."""
        return S + Vector((o, -f, u)) * H

    # The fold between roof and skirt, in plan: a squarish U round the
    # shoulder, open on the neck side.
    angles = (150, 110, 70, 35, 0, -35, -70, -110, -150)

    def sq(v, q=0.62):
        return math.copysign(abs(v) ** q, v)
    plan = [(0.03 + 0.07 * sq(math.cos(math.radians(t))), 0.076 * sq(math.sin(math.radians(t)))) for t in angles]
    # The hem: drawn down to a point at the outer front corner (index 3).
    hem = [-0.02, -0.07, -0.12, -0.17, -0.118, -0.082, -0.058, -0.04, -0.025]
    flare = [0.0, -0.004, -0.008, -0.01, -0.008, -0.006, -0.004, -0.002, 0.0]

    def roof_z(o):
        # Rising gently from the outer edge, then more steeply to the crest.
        return 0.045 + 0.012 * max(0.0, (0.03 - o) / 0.075)

    def out_dir(o, f):
        d = Vector((o - 0.03, f, 0.0))
        return d.normalized() if d.length > 1e-6 else Vector((1, 0, 0))

    n = len(plan)
    crease = [(o, f, roof_z(o)) for o, f in plan]
    mid, bottom = [], []
    for (o, f, zc), zh, fl in zip(crease, hem, flare):
        d = out_dir(o, f)
        mid.append((o + d.x * 0.012, f + d.y * 0.012, zc + (zh - zc) * 0.4))
        bottom.append((o + d.x * fl, f + d.y * fl, zh))
    verts = [P(*v) for v in crease + mid + bottom]
    faces, fmat = [], []
    crimson = {2, 3, 4}  # the outer-front and outer facets of the skirt
    for r in range(2):
        for i in range(n - 1):
            a0, a1 = r * n + i, r * n + i + 1
            faces.append((a0, a1, a1 + n, a0 + n))
            fmat.append(1 if i in crimson else 0)
    # Roof: a low faceted dome fanned from a peak over the shoulder.
    verts.append(P(0.02, 0.0, 0.074))
    c = len(verts) - 1
    for i in range(n):
        faces.append((c, i, (i + 1) % n))
        fmat.append(0)
    solid("pauldron_plate", verts, faces, [m["armour"], m["hull"]], root, 0.0075 * H, fmat)

    # Gold on the edges only: hem, fold, the skirt's ends and the crest.
    r = 0.0036 * H
    shapes.sweep("pauldron_hem", [P(*v) for v in bottom], r, m["trim"], parent=root, profile="square")
    shapes.sweep("pauldron_fold", [P(*v) for v in crease], r * 0.8, m["trim"], parent=root, profile="square")
    for i in (0, n - 1):
        shapes.sweep(f"pauldron_end{i}", [P(*crease[i]), P(*mid[i]), P(*bottom[i])], r * 0.8, m["trim"], parent=root, profile="square")
    # The crimson field's frame.
    k0, k1 = min(crimson), max(crimson) + 1
    ring = crease[k0:k1 + 1] + [mid[k1]] + bottom[k0:k1 + 1][::-1] + [mid[k0]]
    shapes.sweep("pauldron_field", [P(*v) for v in ring], r * 0.7, m["trim"], cyclic=True, parent=root, profile="square")

    # Turn a little about the shoulder so the outer face looks forward-out.
    bpy.context.view_layer.update()
    turn = Matrix.Translation(S) @ Matrix.Rotation(math.radians(-12), 4, "Z") @ Matrix.Translation(-S)
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
    z1 = sk.joint("shoulder").z + 0.015 * H
    Z = z1 - z0

    def half(t):
        # Half width and half depth of the core at height fraction t (0 waist, 1 top).
        # Broad at the shoulders so the pauldrons and shoulder drums bolt onto it.
        hx = 0.07 + 0.09 * min(t / 0.75, 1.0) ** 1.2 - 0.03 * max(0.0, (t - 0.86) / 0.14) ** 1.5
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
        # Gothic lancets in the lower pectoral, as on the render's breastplate.
        for k, x in enumerate((0.3, 0.55)):
            p, nrm = front(s * x * hx_top, 0.6)
            shapes.lancet(f"chest_lancet{side}{k}", 0.022 * H, 0.05 * H, 0.35, m["trim"], glow=m["metal"], loc=p + nrm * 1.45,
                          rot=face_rot(nrm), parent=root)
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
    # Shoulder drums: the arm's pivot, bolted through the breastplate's top
    # corners, gold-ringed, with a bracket rising into the pauldron above.
    for s_, side in ((1, "L"), (-1, "R")):
        S = sk.joint("shoulder", side)
        x0 = s_ * half(0.8)[0] * 0.7
        length = abs(S.x + s_ * 0.015 * H - x0)
        mid = Vector(((S.x + s_ * 0.015 * H + x0) / 2, 0.0, S.z))
        drum = shapes.cylinder(f"shoulder_drum{side}", 0.05 * H, length, m["metal"], loc=mid, rot=(0, math.pi / 2, 0), parent=root, verts=10, bevel=0.2)
        for k, f_ in enumerate((0.15, 0.85)):
            shapes.cylinder(f"shoulder_ring{side}{k}", 0.056 * H, 0.012 * H, m["trim"], loc=Vector((x0 + (S.x + s_ * 0.015 * H - x0) * f_, 0, S.z)),
                            rot=(0, math.pi / 2, 0), parent=root, verts=10, bevel=0.1)
        for a in range(0, 360, 60):
            ar = math.radians(a)
            shapes.sphere(f"shoulder_bolt{side}{a}", 0.008 * H, m["trim"], loc=Vector((S.x + s_ * 0.016 * H, 0.04 * H * math.cos(ar), S.z + 0.04 * H * math.sin(ar))), parent=root, segments=8)
        # The yoke: a plate from the breastplate's top edge out over the drum.
        shapes.box_plate(f"yoke{side}", (abs(S.x - x0) + 0.02 * H, 0.11 * H, 0.025 * H), m["armour"], bevel=0.3,
                         loc=Vector(((S.x + x0) / 2, 0.0, S.z + 0.024 * H)), parent=root)
        shapes.box_plate(f"yoke_trim{side}", (abs(S.x - x0) + 0.022 * H, 0.112 * H, 0.006 * H), m["trim"], bevel=0.1,
                         loc=Vector(((S.x + x0) / 2, 0.0, S.z + 0.012 * H)), parent=root)
    # Gorget rim and waist belt.
    shapes.sweep("gorget", [p + Vector((0, 0, 0.1)) for p in section(1.0, 20)], 0.3, m["trim"], cyclic=True, parent=root, profile="square")
    shapes.sweep("waist", [p * 1.0 + Vector((0, 0, 0.3)) for p in section(0.0, 20)], 0.35, m["trim"], cyclic=True, parent=root, profile="square")
    # Spine ridge on the back.
    spine = [Vector((0, half(t / 10)[1] + 0.4, z0 + Z * t / 10)) for t in range(1, 10)]
    shapes.sweep("spine_ridge", spine, 0.4, m["trim"], parent=root, profile="square")


def helm(sk, m, root):
    """The render's head: a small, steep cowl of plate shaped like a pointed
    arch, set low between the pauldrons, projecting past a recessed, keeled
    faceplate so that from the front mostly the glow of the eye slit and the
    breaths shows. Hard, flat facets throughout."""
    H = sk.H
    S = sk.joint("shoulder")
    neck = sk.joint("neck")
    O = Vector((0.0, neck.y, S.z - 0.006 * H))

    def V(x, y, z):
        return O + Vector((x, y, z)) * H

    # The cowl's section: straight cheeks to the spring line, then a
    # faceted pointed arch.
    w0, ws, zs, rise = 0.041, 0.037, 0.06, 0.046
    r = (ws * ws + rise * rise) / (2 * ws)
    cx = ws - r
    top = math.atan2(rise, -cx)
    right = [(cx + r * math.cos(top * k / 3), zs + r * math.sin(top * k / 3)) for k in range(4)]
    arch = [(w0 + 0.008, -0.012), (w0, 0.012)] + right
    outline = [(-x, z) for x, z in arch] + [(x, z) for x, z in reversed(arch[:-1])]
    ztop = zs + rise

    # Rings from the face edge back to the nape: (y, x scale, z scale, z shift, lean).
    rings = [(-0.052, 1.0, 1.0, 0.0, -0.016), (-0.008, 1.06, 1.02, 0.0, -0.004), (0.036, 0.94, 0.86, -0.012, 0.0), (0.054, 0.62, 0.62, -0.006, 0.0)]
    verts, faces = [], []
    n = len(outline)
    for y, sx, sz, dz, lean in rings:
        for x, z in outline:
            verts.append(V(x * sx, y + lean * z / ztop, z * sz + dz))
    for j in range(len(rings) - 1):
        for i in range(n - 1):
            a0, a1 = j * n + i, j * n + i + 1
            faces.append((a0, a1, a1 + n, a0 + n))
    faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))  # the nape, closed
    solid("hood", verts, faces, [m["armour"]], root, 0.0045 * H)
    shapes.sweep("hood_edge", verts[:n], 0.0026 * H, m["trim"], parent=root, profile="square")

    # The faceplate, recessed behind the cowl's edge: two planes meeting in a
    # keel, the chin pushed a little forward.
    yf = -0.03
    fx = 0.034
    fp = [V(0, yf - 0.011, 0.004), V(0, yf - 0.009, 0.09), V(-fx, yf + 0.006, 0.084), V(-fx * 0.92, yf + 0.004, 0.006),
          V(fx, yf + 0.006, 0.084), V(fx * 0.92, yf + 0.004, 0.006)]
    solid("faceplate", fp, [(0, 1, 2, 3), (0, 5, 4, 1)], [m["metal"]], root, 0.004 * H)

    def face(x, z):
        return V(x, yf - 0.0115 + 0.017 * abs(x) / fx, z)

    eye = [face(x, 0.062 + 0.006 * abs(x) / fx) for x in (-0.026, -0.013, 0.0, 0.013, 0.026)]
    shapes.sweep("eye_slit", eye, 0.0028 * H, m["glow"], parent=root, profile="square")
    for k, x in enumerate((-0.017, -0.006, 0.006, 0.017)):
        shapes.sweep(f"breath{k}", [face(x, 0.02), face(x, 0.044)], 0.0016 * H, m["glow"], parent=root, profile="square")


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


# ------------------------------------------------------------------ angular limbs

def basis(a, b, front=(0, -1, 0)):
    """(d, f, x): unit vectors along the bone a->b, its front and its side."""
    d = (Vector(b) - Vector(a)).normalized()
    f = Vector(front)
    f = (f - f.dot(d) * d).normalized()
    return d, f, f.cross(d).normalized()


def hexa(c, f, x, rf, rx, keel=0.0, back=1.0, sides=6):
    """A faceted section round centre c: a vertex at the front pushed out by
    `keel`, `rf`/`rx` the half-depth/half-width, the back scaled by `back`."""
    pts = []
    for i in range(sides):
        t = 2 * math.pi * i / sides
        cf, cx = math.cos(t), math.sin(t)
        k = (rf + keel) if i == 0 else rf * (1.0 if cf >= 0 else back)
        pts.append(c + f * cf * k + x * cx * rx)
    return pts


def segment(name, a, b, prof, mat, root, front=(0, -1, 0), edge_mat=None, edge_r=0.2, edges=(0, 1, 5)):
    """A faceted limb plate from a to b. prof: [(t, rf, rx, keel)] along the
    bone. Gold sweeps run down the listed section vertices (0 = the keel)."""
    d, f, x = basis(a, b, front)
    L = (Vector(b) - Vector(a)).length
    rings = [hexa(Vector(a) + d * L * t, f, x, rf, rx, keel) for t, rf, rx, keel in prof]
    ob = loft(name, rings, mat, root)
    mod(ob, "BEVEL", width=edge_r * 0.6, segments=1, limit_method="ANGLE", angle_limit=math.radians(25))
    if edge_mat is not None:
        for i in edges:
            pts = [r[i] + (r[i] - (Vector(a) + d * L * t)).normalized() * edge_r * 0.6 for r, (t, *_) in zip(rings, prof)]
            shapes.sweep(f"{name}_edge{i}", pts, edge_r, edge_mat, parent=root, profile="square")
        for k in (0, len(rings) - 1):
            shapes.sweep(f"{name}_rim{k}", rings[k], edge_r * 0.9, edge_mat, cyclic=True, parent=root, profile="square")
    return ob, (d, f, x, L)


def point_cop(name, at, out, up, size, mat, root, trim=None):
    """A pointed four-sided cop (elbow or knee guard): a pyramid on a diamond plate."""
    out, up = Vector(out).normalized(), Vector(up).normalized()
    side = out.cross(up).normalized()
    up = side.cross(out).normalized()
    base = [at + up * size, at + side * size * 0.8, at - up * size * 1.3, at - side * size * 0.8]
    mid = [at + out * size * 0.35 + (p - at) * 0.7 for p in base]
    tip = at + out * size * 1.1 - up * size * 0.2
    loft(name, [base, mid, [tip] * 4], mat, root, cap=True)
    if trim is not None:
        shapes.sweep(f"{name}_rim", mid, size * 0.08, trim, cyclic=True, parent=root, profile="square")


def arm(sk, m, root):
    """Upper arm: a faceted rerebrace over a dark steel core."""
    H = sk.H
    a, b = sk.joint("shoulder"), sk.joint("elbow")
    r = sk.radius("arm")
    d, f, x = basis(a, b)
    L = (b - a).length
    shapes.cylinder("arm_core", r * 0.55, L, m["metal"], loc=(a + b) / 2, parent=root, verts=8, bevel=0.1).rotation_euler = \
        Vector((0, 0, 1)).rotation_difference(d).to_euler()
    segment("rerebrace", a + d * L * 0.12, b - d * L * 0.08,
            [(0.0, r * 0.95, r * 0.95, 0.0), (0.25, r * 1.08, r * 1.02, r * 0.25), (0.8, r * 1.0, r * 0.95, r * 0.2), (1.0, r * 0.82, r * 0.8, 0.0)],
            m["filigree"], root, edge_mat=m["trim"], edge_r=0.0055 * H)
    shapes.sphere("elbow_ball", r * 0.75, m["metal"], loc=b, parent=root, segments=12)


def forearm(sk, m, root):
    """A long angular vambrace flaring to the wrist, crimson-inlaid on its outer face,
    with a pointed couter at the elbow."""
    H = sk.H
    a, b = sk.joint("elbow"), sk.joint("wrist")
    r = sk.radius("forearm")
    seg, (d, f, x, L) = segment("vambrace", a + (b - a) * 0.08, b + (b - a).normalized() * 0.01 * H,
                                [(0.0, r * 0.95, r * 0.95, 0.0), (0.2, r * 1.15, r * 1.1, r * 0.35), (0.85, r * 1.35, r * 1.3, r * 0.45), (1.0, r * 1.2, r * 1.2, r * 0.2)],
                                m["armour"], root, edge_mat=m["trim"], edge_r=0.0055 * H, edges=(0, 1, 2, 4, 5))
    # Crimson panel on the outer (+X) face, gold framed.
    def outer(u, t):
        c = a + (b - a) * (0.08 + 0.9 * t)
        rr = r * (1.15 + 0.2 * t)
        ang = math.radians(u)
        n = (x * math.cos(ang) + f * math.sin(ang)).normalized()
        return c + n * rr * 1.02, n
    patch("vambrace_panel", outer, -28, 28, 0.22, 0.82, 0.25, 0.6, m["hull"], root, m["trim"], 0.15, n=2)
    point_cop("couter", a + d * 0.01 * H, -f * 0.3 + x * 0.6 - d * 0.5 + Vector((0, 0.6, 0)), d, r * 1.25, m["armour"], root, m["trim"])


def thigh(sk, m, root):
    """Faceted cuisse with a keel, gold edges and a crimson inlay, over a steel core."""
    H = sk.H
    a, b = sk.joint("hip"), sk.joint("knee")
    r = sk.radius("thigh")
    d, f, x = basis(a, b)
    L = (b - a).length
    shapes.sphere("hip_ball", r * 0.65, m["metal"], loc=a, parent=root, segments=12)
    shapes.cylinder("thigh_core", r * 0.5, L, m["metal"], loc=(a + b) / 2, parent=root, verts=8, bevel=0.1).rotation_euler = \
        Vector((0, 0, 1)).rotation_difference(d).to_euler()
    segment("cuisse", a + d * L * 0.06, b - d * L * 0.1,
            [(0.0, r * 0.95, r * 1.05, r * 0.2), (0.3, r * 1.1, r * 1.05, r * 0.4), (0.85, r * 0.95, r * 0.9, r * 0.35), (1.0, r * 0.75, r * 0.75, r * 0.1)],
            m["filigree"], root, edge_mat=m["trim"], edge_r=0.0055 * H)

    def front(u, t):
        c = a + d * L * (0.15 + 0.62 * t)
        ang = math.radians(u)
        n = (f * math.cos(ang) + x * math.sin(ang)).normalized()
        return c + n * r * (1.15 - 0.15 * t), n
    patch("cuisse_panel", front, 12, 62, 0.0, 1.0, 0.3, 0.5, m["hull"], root, m["trim"], 0.14, n=2)
    shapes.sphere("knee_ball", r * 0.6, m["metal"], loc=b, parent=root, segments=12)


def shin(sk, m, root):
    """An angular greave, keeled hard at the front and widening to the ankle, with a
    big pointed poleyn over the knee."""
    H = sk.H
    a, b = sk.joint("knee"), sk.joint("ankle")
    r = sk.radius("shin")
    _, (d, f, x, L) = segment("greave", a + (b - a) * 0.1, b + (b - a).normalized() * 0.02 * H,
                              [(0.0, r * 1.0, r * 1.0, r * 0.3), (0.25, r * 1.15, r * 1.1, r * 0.6), (0.8, r * 1.25, r * 1.2, r * 0.55), (1.0, r * 1.05, r * 1.1, r * 0.2)],
                              m["armour"], root, edge_mat=m["trim"], edge_r=0.0055 * H, edges=(0, 1, 2, 4, 5))

    def face(u, t):
        c = a + d * L * (0.25 + 0.55 * t)
        ang = math.radians(u)
        n = (f * math.cos(ang) + x * math.sin(ang)).normalized()
        return c + n * r * 1.35, n
    patch("greave_panel", face, 22, 64, 0.0, 1.0, 0.25, 0.6, m["filigree"], root, m["trim"], 0.14, n=2)
    point_cop("poleyn", a + f * r * 0.6, f + d * 0.25, -d, r * 1.25, m["filigree"], root, m["trim"])
    for s_ in (-1, 1):
        point_cop(f"poleyn_wing{'LR'[s_ > 0]}", a + x * s_ * r * 0.8 + f * r * 0.2, x * s_ + f * 0.3, -d, r * 0.7, m["armour"], root, m["trim"])


def foot(sk, m, root):
    """A long, pointed sabaton of lames with a heel spur."""
    H = sk.H
    an = sk.joint("ankle")
    g = 3.0   # base thickness
    W, Lf = 0.06 * H, 0.17 * H
    toe = an + Vector((0.01 * H, -Lf * 0.72, 0))

    def sec(y, w, h, z0=g):
        return [Vector((an.x - w, y, z0)), Vector((an.x + w, y, z0)), Vector((an.x + w * 0.85, y, z0 + h)), Vector((an.x, y, z0 + h * 1.25)), Vector((an.x - w * 0.85, y, z0 + h))]
    ys = [an.y + Lf * 0.28, an.y + Lf * 0.05, an.y - Lf * 0.25, an.y - Lf * 0.5, an.y - Lf * 0.7]
    rows = [sec(ys[0], W * 0.8, 0.07 * H), sec(ys[1], W, 0.075 * H), sec(ys[2], W * 0.95, 0.05 * H), sec(ys[3], W * 0.75, 0.035 * H), sec(ys[4], W * 0.25, 0.012 * H)]
    loft("sabaton", rows, m["armour"], root)
    for k, y in enumerate(ys[1:4]):
        r_ = rows[k + 1]
        shapes.sweep(f"sabaton_lame{k}", [p + Vector((0, -0.2, 0.15)) for p in r_[1:]] + [r_[0] + Vector((0, -0.2, 0.15))], 0.012 * H, m["trim"], parent=root, profile="square")
    shapes.sweep("sabaton_keel", [r[3] + Vector((0, 0, 0.2)) for r in rows[1:]], 0.012 * H, m["trim"], parent=root, profile="square")
    spur = an + Vector((0, Lf * 0.3, g + 0.02 * H))
    loft("heel_spur", [[spur + Vector((-0.012 * H, 0, -0.01 * H)), spur + Vector((0.012 * H, 0, -0.01 * H)), spur + Vector((0, 0, 0.015 * H))],
                       [spur + Vector((0, 0.05 * H, -0.005 * H))] * 3], m["trim"], root)
    shapes.sphere("ankle_ball", sk.radius("shin") * 0.7, m["metal"], loc=an, parent=root, segments=12)


BUILDERS = {"cloth": cloth, "back": back, "pauldron": pauldron, "torso": torso, "helm": helm, "collar": collar,
            "arm": arm, "forearm": forearm, "thigh": thigh, "shin": shin, "foot": foot}


def build(component):
    kit.reset_scene()
    m = kit.materials.library(FACTION)
    sk = kit.skeleton.Skeleton(FACTION, FRAME)
    root = kit.empty(kit.part_name(FACTION, component, CLS), size=0.05 * sk.H)
    BUILDERS[component](sk, m, root)
    return root, sk


SIDED = {"arm", "forearm", "thigh", "shin", "foot", "pauldron"}


def preview_all(comps, out, samples=24):
    """Every listed part on one frame (sided ones mirrored), from three angles."""
    kit.reset_scene()
    m = kit.materials.library(FACTION)
    sk = kit.skeleton.Skeleton(FACTION, FRAME)
    objs = []
    for comp in comps:
        root = kit.empty(kit.part_name(FACTION, comp, CLS), size=1)
        BUILDERS[comp](sk, m, root)
        bpy.context.view_layer.update()
        objs += kit.meshes(root)
        if comp in SIDED:
            mirror = kit.empty(f"{comp}_mirror", size=1)
            mirror.scale = (-1, 1, 1)
            for o in kit.meshes(root):
                c = o.copy()
                bpy.context.scene.collection.objects.link(c)
                c.parent = mirror
                c.matrix_parent_inverse.identity()
                c.matrix_world = mirror.matrix_world @ o.matrix_world
                objs.append(c)
    frame = kit.skeleton.build_frame(FACTION, FRAME)
    for o in list(frame.children_recursive):
        if o.get("standin") in comps or o.get("standin") == "base":
            for c in [o, *o.children_recursive]:
                c.hide_render = True
    import os
    kit.render.studio(floor=not os.environ.get("UPPER"))
    allobjs = objs + [o for o in kit.meshes(frame) if not o.hide_render]
    views = ((30, 6), (0, 4), (80, 4))
    import os
    if os.environ.get("UPPER"):
        # Frame the shoulders and head only, from the reference angles.
        def zc(o):
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            return sum(v.z for v in bb) / 8
        hide = [o for o in allobjs if zc(o) < 0.66 * sk.H]
        for o in hide:
            o.hide_render = True
        allobjs = [o for o in allobjs if o not in hide]
        views = ((35, 22), (-20, -12), (0, 2), (75, 4))
    shots = []
    for az, el in views:
        p = Path(out) / f"body-{az}.png"
        kit.render.shot(allobjs, p, az=az, el=el, samples=samples, res=(560, 900), margin=0.95)
        kit.render.post(p)
        shots.append(p)
    kit.render.compare(shots, None, Path(out) / "body-compare.png", title="covenant paladin parts")


def main(argv):
    if "--preview-all" in argv:
        out = Path(argv[argv.index("--preview-all") + 1])
        preview_all([a for a in argv if a in BUILDERS] or list(BUILDERS), out)
        return
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
