"""The Iron Covenant Paladin's dressing: cape and tabard, back towers, helm crown.

    ~/bvenv/bin/python assets/blender/parts/paladin/paladin.py [cloth back crown ...] [--render OUT] [--no-publish]

Parts (covenant frame titan, class paladin, so they only dress the Paladin):
    covenant_cloth_paladin   a tattered crimson cape with a gold snowflake sigil, and a front tabard
    covenant_back_paladin    two gothic chimney towers behind the shoulders
    covenant_crown_paladin   a tall central spire and two raked side spires on the helm

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
from mathutils import Vector

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
        sweep_x = -0.22 * H * v ** 2.1 * (1 - u * 0.5)
        y = top.y + 0.035 * H * v + 0.05 * H * v ** 1.6
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
    u0, v0, size = 0.42, 0.40, 0.085 * H

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


def cloth(sk, m, root):
    cape(sk, m, root)
    tabard(sk, m, root)


def back(sk, m, root):
    """Two chimney towers behind the shoulders, raked slightly outward."""
    H, W = sk.H, sk.W
    sh = sk.joint("shoulder")
    for s, side in ((1, "L"), (-1, "R")):
        base = Vector((s * 0.085 * H * W, 0.085 * H, sh.z - 0.03 * H))
        tower = shapes.box_plate(f"tower{side}", (0.07 * H, 0.065 * H, 0.15 * H), m["armour"], bevel=0.3, loc=base + Vector((0, 0, 0.075 * H)), parent=root, taper=0.15)
        for k, z in enumerate((0.04, 0.10)):
            shapes.box_plate(f"tower_band{side}{k}", (0.076 * H, 0.071 * H, 0.008 * H), m["trim"], bevel=0.12, loc=base + Vector((0, 0, z * H)), parent=root)
        shapes.lancet(f"tower_window{side}", 0.022 * H, 0.06 * H, 0.3, m["trim"], glow=m["glow"], loc=base + Vector((0, -0.0335 * H, 0.05 * H)), parent=root)
        sp = shapes.spire(f"tower_spire{side}", 0.07 * H, 0.14 * H, m["armour"], trim=m["trim"], loc=base + Vector((0, 0, 0.15 * H)), parent=root, crockets=3, sides=8)
        ch = shapes.cylinder(f"stack{side}", 0.012 * H, 0.07 * H, m["metal"], loc=base + Vector((s * 0.03 * H, 0.012 * H, 0.17 * H)), parent=root, verts=12, bevel=0.2)
        shapes.cylinder(f"stack_rim{side}", 0.016 * H, 0.008 * H, m["trim"], loc=base + Vector((s * 0.03 * H, 0.012 * H, 0.205 * H)), parent=root, verts=12, bevel=0.1)


def crown(sk, m, root):
    """A tall central spire and two raked side spires over the helm."""
    H = sk.H
    head = sk.joint("head")
    top = head + Vector((0, 0.012 * H, 0.085 * H))
    shapes.cylinder("crown_base", 0.02 * H, 0.012 * H, m["trim"], loc=top, parent=root, verts=16, bevel=0.15)
    shapes.spire("crown_spire", 0.05 * H, 0.17 * H, m["armour"], trim=m["trim"], loc=top + Vector((0, 0, 0.005 * H)), parent=root, crockets=4, sides=8)
    for s, side in ((1, "L"), (-1, "R")):
        sp = shapes.spire(f"crown_side{side}", 0.034 * H, 0.1 * H, m["armour"], trim=m["trim"], loc=top + Vector((s * 0.042 * H, 0.014 * H, -0.012 * H)), parent=root, crockets=2, sides=6)
        sp.rotation_euler = (0.1, s * 0.22, 0)


BUILDERS = {"cloth": cloth, "back": back, "crown": crown}


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
