"""The Iron Covenant Paladin's dressing: cape and tabard, back towers, helm crown.

    ~/bvenv/bin/python assets/blender/parts/paladin/paladin.py [cloth back crown ...] [--render OUT] [--no-publish]

Parts (covenant frame titan, class paladin, so they only dress the Paladin):
    covenant_cloth_paladin   a tattered crimson cape with a gold snowflake sigil, and a front tabard
    covenant_back_paladin    two launcher pods on posts behind the shoulders
    covenant_crown_paladin   the head's gothic tower: traceried shaft, corner pinnacles, tall spire
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
    """Angular gothic pauldron: a tall shield-shaped outer plate with a crimson
    inlay and gold arch, a raked top plate, two lames below and a peak spike,
    as on the north-star render (modelled for the left, mirrored on the right)."""
    H = sk.H
    S = sk.joint("shoulder")
    k = H / 62.0
    tilt = math.radians(14)
    # Outer plate: faces +X, leaning in at the top.
    u = Vector((0, -1, 0))                         # across: toward the front
    v = Vector((-math.sin(tilt), 0, math.cos(tilt)))  # up, leaning inward
    o = S + Vector((0.083 * H, 0.0, -0.012 * H))
    w, hi, lo = 0.085 * H, 0.06 * H, -0.085 * H
    outer = [(-w, hi * 0.75), (-w * 0.35, hi), (w * 0.55, hi * 1.12), (w, hi * 0.7), (w * 0.92, lo * 0.55), (0.0, lo), (-w * 0.92, lo * 0.55)]
    _, at = facet("pauldron_outer", o, u, v, outer, 1.4 * k, m["filigree"], root, m["trim"], m["hull"], inlay=0.66, frame_r=0.28 * k)
    arch = shapes.lancet("pauldron_arch", 0.06 * H, 0.075 * H, 0.35 * k, m["trim"], loc=at(0.0, -0.045 * H, 1.1 * k), parent=root)
    arch.rotation_euler = (0, -tilt, math.pi / 2)   # its face (-Y) turned to face +X
    # Top plate: from over the shoulder joint out to the outer plate's top edge.
    tu = Vector((0, -1, 0))
    tv = Vector((math.cos(math.radians(24)), 0, -math.sin(math.radians(24))))   # outward and down
    to = S + Vector((0.005 * H, 0.0, 0.088 * H))
    top = [(-0.075 * H, -0.035 * H), (0.075 * H, -0.035 * H), (0.085 * H, 0.06 * H), (0.03 * H, 0.085 * H), (-0.07 * H, 0.07 * H)]
    facet("pauldron_top", to, tv.cross(tu).cross(tv) * 0 + tu, tv, top, 1.3 * k, m["armour"], root, m["trim"], None, frame_r=0.24 * k)
    # Front cheek: closes the gap ahead of the shoulder.
    fu = Vector((1, 0, 0))
    fv = Vector((0, 0, 1))
    front = [(-0.035 * H, 0.07 * H), (0.045 * H, 0.075 * H), (0.045 * H, -0.06 * H), (-0.01 * H, -0.075 * H), (-0.035 * H, -0.03 * H)]
    bo = S + Vector((0.035 * H, 0.085 * H, 0.0))
    facet("pauldron_back", bo, fu, fv, front, 1.0 * k, m["armour"], root, m["trim"], None, frame_r=0.2 * k)
    # Lames under the outer plate.
    for i in range(2):
        lo_ = S + Vector((0.074 * H - i * 0.006 * H, 0.0, -0.11 * H - i * 0.03 * H))
        lame = [(-0.075 * H, 0.016 * H), (0.075 * H, 0.016 * H), (0.065 * H, -0.016 * H), (-0.065 * H, -0.016 * H)]
        facet(f"pauldron_lame{i}", lo_, u, v, lame, 1.0 * k, m["armour"], root, m["trim"], None, frame_r=0.17 * k)
    # Peak spike and finial studs.
    peak = at(w * 0.55, hi * 1.12, 0.0) + Vector((-0.01 * H, 0, 0.005 * H))
    spike = shapes.cylinder("pauldron_spike", 0.012 * H, 0.06 * H, m["trim"], loc=peak + Vector((0, 0, 0.03 * H)), parent=root, verts=8, bevel=0.05, r2=0.0005)
    shapes.sphere("pauldron_spike_ball", 0.014 * H, m["trim"], loc=peak, parent=root, segments=12)
    for a, b in ((-w * 0.7, hi * 0.5), (w * 0.7, hi * 0.45), (-w * 0.6, lo * 0.4), (w * 0.6, lo * 0.4)):
        shapes.sphere("pauldron_stud", 0.006 * H, m["trim"], loc=at(a, b, 1.0 * k), parent=root, segments=8)
    # Turn the whole pauldron about the shoulder so its crimson face looks
    # forward-out, as the render shows it from the front.
    bpy.context.view_layer.update()
    turn = Matrix.Translation(S) @ Matrix.Rotation(math.radians(-32), 4, "Z") @ Matrix.Translation(-S)
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
    top = head + Vector((0, 0.01 * H, 0.08 * H))
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


BUILDERS = {"cloth": cloth, "back": back, "crown": crown, "pauldron": pauldron}


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
            kit.render.compare(shots, None, render / f"{comp}-compare.png", title=f"covenant {comp} paladin")
        if "--no-publish" not in argv:
            kit.skeleton.to_joint(root, FACTION, FRAME, comp)
            kit.publish(root, source=HERE / f"{FACTION}_{comp}_{CLS}.blend")


if __name__ == "__main__":
    main(sys.argv[1:] if "--" not in sys.argv else sys.argv[sys.argv.index("--") + 1:])
