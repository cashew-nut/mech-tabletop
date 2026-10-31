"""Package 8a: the twelve faction signature weapons, as item_<id> parts.

    ~/bvenv/bin/python assets/blender/parts/weapons/weapons.py [id ...] [--publish] [--render] [--samples 48] [--out DIR]

With no ids it builds all twelve. --render makes review shots (side-on, as
the board's "Weapons & Systems" strip draws them, and a three-quarter hero)
and sheets beside the art crops (`weapon_<id>` in assets/art/crops.json).
--publish bakes and exports apps/web/public/parts/item_<id>.glb and lists it
in the manifest; the renders then show the baked textures the web gets.

Every weapon is built at Scout scale (the web scales items by frame), with
its origin where it clamps to the mount and pointing -Y. Arm weapons run
forward from the wrist; core weapons (Carapace Gun, Soul Lantern) stand up
from a chest mount. Silhouettes follow the board: Covenant black iron and
aged gold with crimson enamel, Foundries rusted plate and brass with red
enamel and furnace glow, Reliquary black-teal metal and pale gold with teal
glow (the board's Reliquary weapons are dark, not bone).
"""
import math
import sys
from pathlib import Path

import bpy  # noqa: F401  (before bmesh)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # assets/blender
import kit  # noqa: E402
from common import REPO, script_args  # noqa: E402
from kit import shapes  # noqa: E402
from kit.core import Vector, bmesh, empty, mesh_obj, mod  # noqa: E402

HERE = Path(__file__).resolve().parent
FACTION = {
    "lance": "covenant", "melee-blade": "covenant", "carapace-gun": "covenant", "missile-rack": "covenant",
    "autocannon": "foundries", "rail-cannon": "foundries", "rocket-pod": "foundries", "industrial-claw": "foundries",
    "arc-cannon": "reliquary", "hellfire-missiles": "reliquary", "kinetic-claws": "reliquary", "soul-lantern": "reliquary",
}
FWD = (math.pi / 2, 0, 0)  # turns a part's local +Z to -Y, the walker's front


# ------------------------------------------------------------------ helpers


def along(name, r, y0, y1, mat, parent, r2=None, x=0.0, z=0.0, verts=24, bevel=None):
    """A cylinder (or frustum, front radius r2) along Y from y0 back to y1 front (y1 < y0)."""
    return shapes.cylinder(name, r, abs(y0 - y1), mat, loc=(x, (y0 + y1) / 2, z), rot=FWD, parent=parent,
                           verts=verts, bevel=r * 0.08 if bevel is None else bevel, r2=r2)


def turned(name, profile, mat, parent, y=0.0, x=0.0, z=0.0, segments=32):
    """A lathe of (radius, distance forward) pairs, starting at y and running towards -Y."""
    return shapes.lathe(name, profile, mat, segments=segments, loc=(x, y, z), rot=FWD, parent=parent)


def ring(name, r, tube, y, mat, parent, x=0.0, z=0.0, n=32, square=False):
    """A band round the Y axis at y."""
    pts = [(x + r * math.cos(2 * math.pi * i / n), y, z + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return shapes.sweep(name, pts, tube, mat, cyclic=True, parent=parent, profile="square" if square else "round")


def box(name, size, loc, mat, parent, bevel=0.1, **kw):
    return shapes.box_plate(name, size, mat, bevel=bevel, loc=loc, parent=parent, **kw)


def relief(ob, tile):
    """Re-lay the Decal UVs so the filigree/tread/glyph mask tiles every `tile` mm."""
    if ob.type == "MESH" and "Decal" in ob.data.uv_layers:
        ob.data.uv_layers.remove(ob.data.uv_layers["Decal"])
    bpy.context.view_layer.update()
    shapes.decal_uv(ob, tile_mm=tile)
    return ob


def bezier(p0, p1, p2, n):
    p0, p1, p2 = Vector(p0), Vector(p1), Vector(p2)
    return [p0 * (1 - t) ** 2 + p1 * 2 * t * (1 - t) + p2 * t * t for t in (i / (n - 1) for i in range(n))]


def loft(name, path, w, t, mat, parent, shape="diamond", sides=12, up=(0, 0, 1), smooth=None):
    """Sweep a cross-section along `path`, sized per point: half-width `w`
    (across, perpendicular to `up`) and half-thickness `t` (towards `up`).
    `w` and `t` are numbers or functions of u in 0..1 along the path.
    Shapes: "diamond" (blades, talons), "blade" (a diamond with a flat fuller
    each side), "round", "box". Ends are capped; taper w to ~0 for a point."""
    path = [Vector(p) for p in path]
    up = Vector(up)
    f = lambda v, u: v(u) if callable(v) else v  # noqa: E731
    if shape == "diamond":
        sec = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    elif shape == "blade":
        sec = [(1, 0), (0.45, 0.55), (-0.45, 0.55), (-1, 0), (-0.45, -0.55), (0.45, -0.55)]
    elif shape == "box":
        sec = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
    else:
        sec = [(math.cos(2 * math.pi * i / sides), math.sin(2 * math.pi * i / sides)) for i in range(sides)]
    bm = bmesh.new()
    rings = []
    n = len(path)
    for i, p in enumerate(path):
        tan = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        side = tan.cross(up)
        if side.length < 1e-6:
            side = tan.cross(Vector((0, 1, 0)))
        side.normalize()
        nup = side.cross(tan).normalized()
        u = i / (n - 1)
        ww, tt = max(f(w, u), 0.01), max(f(t, u), 0.01)
        rings.append([bm.verts.new(p + side * (a * ww) + nup * (b * tt)) for a, b in sec])
    m = len(sec)
    for a, b in zip(rings, rings[1:]):
        for k in range(m):
            bm.faces.new((a[k], a[(k + 1) % m], b[(k + 1) % m], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, mat, smooth=shape == "round" if smooth is None else smooth, parent=parent)
    if shape != "round":
        mod(ob, "WEIGHTED_NORMAL", keep_sharp=True)
    shapes.decal_uv(ob, tile_mm=2.0)
    return ob


def clamp_block(m, root, w=2.0, h=2.2, d=2.4):
    """The clamp every arm weapon has at its origin, hidden in the wrist."""
    box("clamp", (w, d, h), (0, 0, 0), m["metal"], root, bevel=0.15)
    shapes.rivet_row("clamp_rivets", (-w / 2 - 0.02, -0.8, h / 2 - 0.4), (-w / 2 - 0.02, 0.8, h / 2 - 0.4), 3, 0.14, m["trim"],
                     parent=root, normal=(-1, 0, 0))


# ------------------------------------------------------------------ Iron Covenant


def lance(m, root, reach=13.0):
    """A jousting lance: a gold-bound grip, a flared vamplate with a crimson
    inlay, and a long fluted black spike."""
    clamp_block(m, root)
    turned("pommel", [(0.0, 0.0), (0.55, 0.05), (0.75, 0.3), (0.7, 0.6), (0.5, 0.75), (0.45, 1.0)], m["trim"], root, y=2.2)
    along("grip", 0.5, 1.3, -2.0, m["metal"], root)
    for k, y in enumerate((0.9, -0.2, -1.4)):
        ring(f"grip_band{k}", 0.52, 0.12, y, m["trim"], root)
    # Vamplate: a flared cone guarding the hand, gold rim, crimson enamel.
    turned("vamplate", [(0.5, 0.0), (0.7, 0.2), (1.35, 1.2), (1.45, 1.35), (1.3, 1.5), (0.95, 1.9), (0.95, 2.6)],
           m["armour"], root, y=-2.0, segments=48)
    turned("vamplate_enamel", [(0.78, 0.4), (1.3, 1.08)], m["hull"], root, y=-2.0, segments=48)
    ring("vamplate_rim", 1.42, 0.14, -3.35, m["trim"], root, n=48)
    ring("vamplate_neck", 0.98, 0.14, -4.55, m["trim"], root)
    for k in range(8):
        a = 2 * math.pi * k / 8 + math.pi / 8
        shapes.rivet_row(f"vamplate_stud{k}", (1.1 * math.cos(a), -2.75, 1.1 * math.sin(a)), (1.1 * math.cos(a), -2.75, 1.1 * math.sin(a)),
                         1, 0.12, m["trim"], parent=root, normal=(math.cos(a), -0.6, math.sin(a)))
    # The spike, round-sectioned, with gold flutes on its first third.
    n = 24 if reach < 18 else 48
    path = [(0, -4.4 - reach * i / (n - 1), 0) for i in range(n)]
    thin = 1.0 if reach < 18 else 0.85
    loft("spike", path, lambda u: thin * (1 - u) ** 1.1, lambda u: thin * (1 - u) ** 1.1, m["armour"], root, shape="round", sides=16)
    for k in range(6):
        a = 2 * math.pi * k / 6
        pts = [(0.98 * (1 - i / 9 * 0.33) * math.cos(a), -4.6 - 4.0 * i / 9, 0.98 * (1 - i / 9 * 0.33) * math.sin(a)) for i in range(10)]
        shapes.sweep(f"spike_flute{k}", pts, 0.07, m["trim"], parent=root)
    ring("spike_collar", 1.02, 0.16, -4.5, m["trim"], root)
    ring("spike_band", 0.7, 0.1, -8.7, m["trim"], root)
    if reach >= 18:
        for y in (-14.0, -19.0):
            ring(f"spike_band{int(-y)}", 0.5 * thin * (1 - (-y - 4.4) / reach) ** 1.1 + 0.25, 0.09, y, m["trim"], root)


def lance_paladin(m, root):
    """The Paladin's siege-blade: a long gold-hilted sword (the Covenant blade at
    twice the reach), hung point-down and forward as in the north-star render
    (about 52 degrees below the horizontal), its tip meeting the ground ahead
    of the feet."""
    # No clamp: the grip's middle (y = 0.4) sits on the origin, which the
    # Paladin's frame puts inside its gripping fist (gripMount in model-kit.json).
    pivot = empty("siege_pivot", size=2)
    pivot.parent = root
    hilt = empty("siege_hilt", (0, -0.4, 0), size=1)
    hilt.parent = pivot
    melee_blade(m, hilt, reach=16.5, width=0.95, clamp=False)
    pivot.rotation_euler = (math.radians(52), 0, 0)


def melee_blade(m, root, reach=10.0, width=1.05, clamp=True):
    """A long straight sword-blade on a gold-housed hilt with a swept guard."""
    if clamp:
        clamp_block(m, root)
    along("grip", 0.45, 1.6, -0.8, m["metal"], root)
    turned("pommel", [(0.0, 0.0), (0.5, 0.1), (0.62, 0.35), (0.45, 0.6)], m["trim"], root, y=2.2)
    # Crossguard: a gold bar swept back at the tips, with ball finials.
    guard = [(-2.2, -0.2, 0.35), (-1.4, -0.9, 0.0), (0, -1.1, 0), (1.4, -0.9, 0.0), (2.2, -0.2, 0.35)]
    shapes.sweep("guard", guard, 0.24, m["trim"], parent=root)
    for s in (-1, 1):
        shapes.sphere(f"guard_finial{'LR'[s > 0]}", 0.32, m["trim"], loc=(2.2 * s, -0.2, 0.35), parent=root, segments=12)
    # Ricasso housing: the ornate gold-framed block behind the blade.
    rc = box("ricasso", (1.9, 2.4, 1.6), (0, -2.2, 0), m["filigree"], root, bevel=0.12)
    relief(rc, 1.2)
    for s in (-1, 1):
        shapes.sweep(f"ricasso_rail{'LR'[s > 0]}", [(1.0 * s, -1.0, 0.82), (1.0 * s, -3.4, 0.82)], 0.1, m["trim"], parent=root, profile="square")
        shapes.sweep(f"ricasso_rail_lo{'LR'[s > 0]}", [(1.0 * s, -1.0, -0.82), (1.0 * s, -3.4, -0.82)], 0.1, m["trim"], parent=root, profile="square")
    shapes.lancet("ricasso_arch", 0.55, 0.85, 0.2, m["trim"], loc=(0, -2.2, 0.81), rot=(-math.pi / 2, 0, 0), parent=root)
    # The blade: flat-faced with a fuller, tapering to a needle point.
    n = 20
    n = max(n, int(reach * 2))
    path = [(0, -3.3 - reach * i / (n - 1), 0) for i in range(n)]
    w = lambda u: width * (1 - u ** 1.6) * (1 - 0.2 * u) + 0.01  # noqa: E731
    t = lambda u: 0.55 * (1 - u ** 1.6) + 0.01  # noqa: E731
    loft("blade", path, w, t, m["metal"], root, shape="blade", up=(0, 0, 1))
    # Gold edging up the spine of the blade's first third.
    spine = 3.5 * reach / 10.0
    shapes.sweep("blade_spine", [(0, -3.4 - spine * i / 7, 0.52 * (1 - (i / 7 * 0.35) ** 1.6)) for i in range(8)], 0.08, m["trim"], parent=root)


def carapace_gun(m, root):
    """A heavy shoulder cannon on a gold cradle: thick banded barrel, a
    crimson enamel breech housing in a filigree frame, and a rear block."""
    zc = 2.4
    # Pedestal and cradle down to the chest mount.
    shapes.cylinder("turntable", 1.6, 0.5, m["trim"], loc=(0, 0, 0.25), parent=root, verts=32, bevel=0.1)
    shapes.cylinder("pedestal", 1.1, 1.2, m["metal"], loc=(0, 0, 0.9), parent=root, verts=24, bevel=0.1)
    for s in (-1, 1):
        box(f"cradle{'LR'[s > 0]}", (0.35, 3.0, 0.7), (0.9 * s, -0.2, 0.95), m["trim"], root, bevel=0.08)
    # Breech block at the back.
    box("breech", (2.4, 2.6, 2.4), (0, 2.4, zc), m["armour"], root, bevel=0.2, panel_lines=1)
    shapes.rivet_row("breech_rivets", (-1.0, 3.72, zc + 0.95), (1.0, 3.72, zc + 0.95), 5, 0.12, m["trim"], parent=root, normal=(0, 1, 0))
    # The enamel housing: a crimson box framed in gold, filigree on the frame.
    box("housing", (2.6, 3.6, 2.6), (0, -0.4, zc), m["hull"], root, bevel=0.15)
    for k, y in enumerate((1.45, -2.25)):
        fr = box(f"housing_frame{k}", (2.9, 0.5, 2.9), (0, y, zc), m["filigree"], root, bevel=0.1)
        relief(fr, 1.0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            shapes.sweep(f"housing_edge{sx}{sz}", [(1.32 * sx, 1.2, zc + 1.32 * sz), (1.32 * sx, -2.0, zc + 1.32 * sz)], 0.1, m["trim"], parent=root)
    for s in (-1, 1):
        # A gold sunburst boss on each flank, as on the board's gun.
        shapes.cylinder(f"housing_boss{'LR'[s > 0]}", 0.55, 0.2, m["trim"], loc=(1.38 * s, -0.4, zc), rot=(0, math.pi / 2, 0), parent=root, verts=16)
        for k in range(8):
            a = 2 * math.pi * k / 8
            shapes.sweep(f"housing_ray{'LR'[s > 0]}{k}", [(1.4 * s, -0.4 + 0.5 * math.cos(a), zc + 0.5 * math.sin(a)),
                                                          (1.4 * s, -0.4 + 0.95 * math.cos(a), zc + 0.95 * math.sin(a))], 0.05, m["trim"], parent=root)
    # The barrel: a thick jacket, three gold bands and a flared muzzle.
    along("barrel", 0.82, -2.4, -8.4, m["armour"], root, z=zc, verts=32)
    for k, y in enumerate((-2.8, -4.6, -6.4)):
        ring(f"barrel_band{k}", 0.84, 0.1, y, m["trim"], root, z=zc, n=40, square=True)
    along("jacket", 0.95, -3.2, -6.0, m["metal"], root, z=zc, verts=12, bevel=0.05)
    turned("muzzle", [(0.82, 0.0), (1.08, 0.2), (1.08, 0.95), (0.95, 1.1), (0.6, 1.1), (0.55, 0.6)], m["armour"], root, y=-8.3, z=zc, segments=40)
    ring("muzzle_lip", 1.09, 0.1, -8.5, m["trim"], root, z=zc, n=40)
    along("bore", 0.52, -8.6, -9.4, m["metal"], root, z=zc, bevel=0)
    # A sighting tube along the top.
    along("sight", 0.3, 0.6, -2.6, m["metal"], root, z=zc + 1.65)
    for y in (0.4, -2.4):
        ring(f"sight_band{y}", 0.32, 0.08, y, m["trim"], root, z=zc + 1.65, n=16)


def missile_rack(m, root):
    """A gothic launcher box: a gold-framed housing with an arched side panel,
    a launch tube cluster at the front, and a carry rail on top."""
    clamp_block(m, root)
    zc = 0.8
    box("housing", (3.4, 6.4, 3.0), (0, -3.3, zc), m["armour"], root, bevel=0.18, panel_lines=2)
    for s in (-1, 1):
        p = box(f"side_panel{'LR'[s > 0]}", (0.3, 4.2, 2.1), (1.75 * s, -3.3, zc), m["filigree"], root, bevel=0.08)
        relief(p, 1.2)
        shapes.lancet(f"side_arch{'LR'[s > 0]}", 1.0, 1.7, 0.2, m["trim"], loc=(1.9 * s, -3.3, zc - 0.8), rot=(0, 0, s * math.pi / 2), parent=root)
    for sx in (-1, 1):
        for sz in (-1, 1):
            shapes.sweep(f"edge{sx}{sz}", [(1.72 * sx, -0.1, zc + 1.52 * sz), (1.72 * sx, -6.5, zc + 1.52 * sz)], 0.11, m["trim"], parent=root)
    # The launch head: a short drum with six tubes, gold-tipped missiles inside.
    along("head", 1.45, -6.4, -9.4, m["metal"], root, z=zc, verts=40)
    for k, y in enumerate((-6.7, -8.0, -9.25)):
        ring(f"head_band{k}", 1.48, 0.13, y, m["trim"], root, z=zc, n=40, square=True)
    for k in range(6):
        a = 2 * math.pi * k / 6 + math.pi / 6
        x, z = 0.85 * math.cos(a), zc + 0.85 * math.sin(a)
        along(f"tube{k}", 0.38, -9.0, -9.55, m["armour"], root, x=x, z=z, verts=16)
        turned(f"missile{k}", [(0.25, 0.0), (0.25, 0.2), (0.18, 0.4), (0.0, 0.55)], m["trim"], root, y=-9.3, x=x, z=z, segments=16)
    turned("hub", [(0.0, 0.0), (0.32, 0.0), (0.32, 0.2), (0.16, 0.35), (0.0, 0.4)], m["trim"], root, y=-9.4, z=zc, segments=16)
    # Carry rail and pinnacles on top.
    shapes.sweep("rail", [(0, -1.0, zc + 1.5), (0, -1.0, zc + 2.2), (0, -5.6, zc + 2.2), (0, -5.6, zc + 1.5)], 0.18, m["metal"], parent=root)
    for s in (-1, 1):
        shapes.spire(f"pinnacle{'LR'[s > 0]}", 0.5, 1.6, m["armour"], trim=m["trim"], loc=(1.35 * s, -0.5, zc + 1.5), parent=root, crockets=2)
    box("sight", (0.8, 1.4, 0.6), (-1.0, -6.0, zc + 1.75), m["metal"], root, bevel=0.08)


# ------------------------------------------------------------------ Ashen Foundries


def autocannon(m, root):
    """A rotary cannon: six barrels in clamp rings ahead of a banded brass
    receiver, a drum magazine on the flank and a feed chute."""
    clamp_block(m, root, w=2.4)
    zc = 0.4
    along("receiver", 1.55, 1.0, -3.4, m["metal"], root, z=zc, verts=32)
    for k, y in enumerate((0.7, -1.1, -3.1)):
        ring(f"receiver_band{k}", 1.58, 0.18, y, m["trim"], root, z=zc, n=36, square=True)
    box("receiver_top", (1.8, 3.6, 0.8), (0, -1.2, zc + 1.45), m["hull"], root, bevel=0.1)
    shapes.rivet_row("receiver_rivets", (-0.7, -2.7, zc + 1.86), (-0.7, 0.3, zc + 1.86), 6, 0.11, m["trim"], parent=root, normal=(0, 0, 1))
    shapes.rivet_row("receiver_rivets_r", (0.7, -2.7, zc + 1.86), (0.7, 0.3, zc + 1.86), 6, 0.11, m["trim"], parent=root, normal=(0, 0, 1))
    turned("nose", [(1.5, 0.0), (1.2, 0.5), (1.05, 0.7)], m["metal"], root, y=-3.4, z=zc)
    # The barrel cluster and its clamps.
    for k in range(6):
        a = 2 * math.pi * k / 6
        x, z = 0.62 * math.cos(a), zc + 0.62 * math.sin(a)
        along(f"barrel{k}", 0.34, -3.8, -13.2, m["metal"], root, x=x, z=z, verts=12)
        along(f"muzzle{k}", 0.4, -12.6, -13.3, m["armour"], root, x=x, z=z, verts=12)
    along("spindle", 0.3, -3.8, -13.0, m["armour"], root, z=zc, verts=12)
    for k, y in enumerate((-5.0, -8.8, -12.2)):
        along(f"clamp{k}", 1.12, y + 0.3, y - 0.3, m["armour"], root, z=zc, verts=6, bevel=0.06)
        ring(f"clamp_band{k}", 1.12, 0.08, y, m["trim"], root, z=zc, n=6)
    # Drum magazine on the left flank, with a feed chute into the receiver.
    box("ammo", (2.0, 2.6, 1.6), (0.9, -1.0, zc - 1.9), m["hull"], root, bevel=0.12)
    shapes.rivet_row("ammo_rivets", (1.92, -2.1, zc - 1.4), (1.92, 0.1, zc - 1.4), 5, 0.1, m["trim"], parent=root, normal=(1, 0, 0))
    box("ammo_lid", (2.2, 2.8, 0.25), (0.9, -1.0, zc - 1.05), m["trim"], root, bevel=0.05)
    shapes.pipe("chute", [(1.6, 0.0, zc - 1.0), (1.9, 0.6, zc - 0.2), (1.3, 0.5, zc + 0.6)], 0.32, m["metal"], parent=root,
                bands=(0.3, 0.7), band_mat=m["trim"])
    shapes.pipe("hose", [(-1.6, 0.6, zc - 0.2), (-1.9, -0.8, zc - 0.9), (-1.6, -2.6, zc - 1.0)], 0.22, m["metal"], parent=root,
                bands=(0.5,), band_mat=m["trim"])
    # A furnace glow in the receiver's vent.
    box("vent_glow", (0.1, 0.8, 0.4), (-1.53, -1.6, zc + 0.4), m["glow"], root, bevel=0)
    for k in range(3):
        box(f"vent_slat{k}", (0.18, 1.0, 0.08), (-1.56, -1.6, zc + 0.22 + 0.18 * k), m["metal"], root, bevel=0)


def rail_cannon(m, root):
    """A long slab gun: a riveted housing with capacitor drums, then twin rails
    with a glowing channel between them, held by brass clamps."""
    clamp_block(m, root, w=2.4)
    zc = 0.6
    box("housing", (3.2, 6.0, 3.0), (0, -2.0, zc), m["armour"], root, bevel=0.18, panel_lines=2)
    box("housing_plate", (2.6, 4.2, 0.4), (0, -2.0, zc + 1.6), m["stencil"], root, bevel=0.08)
    shapes.rivet_row("housing_rivets", (-1.62, 0.6, zc + 1.2), (-1.62, -4.6, zc + 1.2), 8, 0.12, m["trim"], parent=root, normal=(-1, 0, 0))
    shapes.rivet_row("housing_rivets_r", (1.62, 0.6, zc + 1.2), (1.62, -4.6, zc + 1.2), 8, 0.12, m["trim"], parent=root, normal=(1, 0, 0))
    for s in (-1, 1):
        along(f"capacitor{'LR'[s > 0]}", 0.6, 0.4, -4.2, m["metal"], root, x=2.0 * s, z=zc - 0.5, verts=20)
        for k, y in enumerate((-0.4, -1.8, -3.2)):
            ring(f"capacitor_coil{'LR'[s > 0]}{k}", 0.62, 0.12, y, m["trim"], root, x=2.0 * s, z=zc - 0.5, n=20)
    # Twin rails with the channel between them lit furnace-orange.
    for s in (-1, 1):
        box(f"rail{'LR'[s > 0]}", (0.75, 11.0, 2.2), (0.72 * s, -10.2, zc), m["metal"], root, bevel=0.1, panel_lines=0)
        for k in range(5):
            box(f"rail_slot{'LR'[s > 0]}{k}", (0.1, 1.2, 0.5), (1.1 * s, -6.2 - 2.1 * k, zc + 0.3), m["trim"], root, bevel=0.02)
    box("channel", (0.5, 10.6, 0.5), (0, -10.2, zc), m["glow"], root, bevel=0)
    for k, y in enumerate((-5.6, -9.4, -13.2)):
        box(f"rail_clamp{k}", (2.3, 0.6, 2.6), (0, y, zc), m["trim"], root, bevel=0.08)
    box("muzzle", (2.2, 0.8, 2.5), (0, -15.6, zc), m["metal"], root, bevel=0.12)
    shapes.pipe("cable", [(1.5, 0.6, zc - 1.2), (1.9, -2.0, zc - 1.5), (1.2, -5.2, zc - 1.2)], 0.22, m["metal"], parent=root,
                bands=(0.5,), band_mat=m["trim"])
    shapes.gauge("gauge", 0.5, m["trim"], m["armour"], m["metal"], loc=(-1.62, -1.0, zc + 0.2), rot=(0, 0, -math.pi / 2), parent=root)


def rocket_pod(m, root):
    """A boxy pod with a cluster of rocket tubes in its face, a stencilled red
    flank with lit tally lamps, and a brass cage."""
    clamp_block(m, root)
    zc = 0.8
    box("pod", (4.0, 4.6, 3.8), (0, -2.6, zc), m["metal"], root, bevel=0.2)
    for s in (-1, 1):
        p = box(f"flank{'LR'[s > 0]}", (0.3, 3.4, 2.8), (2.05 * s, -2.6, zc + 0.1), m["stencil"], root, bevel=0.08)
        # One stencil number across each flank panel.
        me = p.data
        me.uv_layers.remove(me.uv_layers["Decal"])
        uv = me.uv_layers.new(name="Decal")
        for poly in me.polygons:
            for li in poly.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                uv.data[li].uv = (0.5 + s * co.y / 3.4, 0.5 + co.z / 2.8)
        for k in range(2):
            shapes.sphere(f"lamp{'LR'[s > 0]}{k}", 0.2, m["glow"], loc=(2.2 * s, -1.4 - 1.0 * k, zc + 1.6), parent=root, segments=10)
    # Brass cage edges.
    for sx in (-1, 1):
        for sz in (-1, 1):
            shapes.sweep(f"cage{sx}{sz}", [(2.02 * sx, -0.3, zc + 1.92 * sz), (2.02 * sx, -4.9, zc + 1.92 * sz)], 0.13, m["trim"], parent=root, profile="square")
    for y in (-0.4, -4.8):
        shapes.sweep(f"cage_ring{y}", [(-2.02, y, zc - 1.92), (2.02, y, zc - 1.92), (2.02, y, zc + 1.92), (-2.02, y, zc + 1.92)], 0.13, m["trim"],
                     cyclic=True, parent=root, profile="square")
    # The face: four tubes, each with a rocket nose glowing at the back.
    face = box("face", (3.6, 0.5, 3.4), (0, -5.0, zc), m["metal"], root, bevel=0.1)
    for ix, x in enumerate((-0.9, 0.9)):
        for iz, z in enumerate((-0.85, 0.85)):
            along(f"tube{ix}{iz}", 0.72, -4.6, -5.8, m["metal"], root, x=x, z=zc + z, verts=20)
            ring(f"tube_lip{ix}{iz}", 0.72, 0.1, -5.8, m["trim"], root, x=x, z=zc + z, n=20)
            along(f"bore{ix}{iz}", 0.55, -5.6, -5.95, m["armour"], root, x=x, z=zc + z, verts=20, bevel=0)
            turned(f"rocket{ix}{iz}", [(0.32, 0.0), (0.3, 0.2), (0.15, 0.45), (0.0, 0.55)], m["glow"], root, y=-5.3, x=x, z=zc + z, segments=12)
    face.name = "face"
    shapes.pipe("exhaust", [(1.2, 0.2, zc + 1.9), (1.2, 0.2, zc + 3.0), (1.2, -0.3, zc + 3.4)], 0.35, m["metal"], parent=root, bands=(0.6,), band_mat=m["trim"])


def industrial_claw(m, root):
    """A crane grab: a hydraulic wrist, a riveted palm, two hooked upper jaws
    and a heavy lower jaw, every knuckle a brass pin."""
    clamp_block(m, root, w=2.4)
    along("wrist", 1.2, 0.6, -2.0, m["metal"], root, verts=24)
    ring("wrist_band", 1.24, 0.16, -1.6, m["trim"], root, n=32, square=True)
    for s in (-1, 1):
        shapes.pipe(f"ram{'LR'[s > 0]}", [(1.3 * s, 0.8, 0.9), (1.5 * s, -1.2, 1.0), (1.4 * s, -2.6, 0.7)], 0.28, m["metal"], parent=root,
                    bands=(0.45,), band_mat=m["trim"])
    palm = box("palm", (4.4, 2.6, 3.0), (0, -3.2, 0), m["armour"], root, bevel=0.22, panel_lines=1)
    shapes.rivet_row("palm_rivets", (-1.8, -4.52, 1.2), (1.8, -4.52, 1.2), 6, 0.13, m["trim"], parent=root)
    box("palm_plate", (2.4, 0.3, 1.6), (0, -4.6, 0.1), m["stencil"], root, bevel=0.06)
    box("palm_top", (3.8, 2.0, 0.4), (0, -3.0, 1.65), m["hull"], root, bevel=0.08)

    def jaw(name, x, z0, curve_down, length, w0):
        sgn = -1 if curve_down else 1
        p0 = (x, -4.3, z0)
        pts = bezier(p0, (x * 1.1, -4.3 - length * 0.8, z0 + sgn * -1.2), (x * 0.9, -4.3 - length * 0.9, z0 + sgn * length * 0.55), 16)
        ob = loft(name, pts, lambda u: w0 * (1 - 0.75 * u), lambda u: w0 * 1.05 * (1 - 0.75 * u ** 1.5), m["metal"], root, shape="box", up=(1, 0, 0))
        shapes.cylinder(f"{name}_pin", w0 * 0.75, w0 * 2.3, m["trim"], loc=p0, rot=(0, math.pi / 2, 0), parent=root, verts=16)
        # A brass tooth plate along the inside of the hook.
        k = len(pts) // 2
        shapes.sweep(f"{name}_edge", [p + Vector((0, 0, sgn * w0 * 0.55 * (1 - 0.6 * i / k))) for i, p in enumerate(pts[k - 4:k + 4])], 0.1, m["trim"], parent=root)
        return ob

    jaw("jaw_upper_l", 1.3, 1.0, True, 5.2, 0.62)
    jaw("jaw_upper_r", -1.3, 1.0, True, 5.2, 0.62)
    jaw("jaw_lower", 0.0, -1.0, False, 4.6, 0.8)


# ------------------------------------------------------------------ Reliquary


def arc_cannon(m, root):
    """A long reliquary rifle: a ring grip at the back, gold coil collars
    strung on a slender black barrel, and forked emitter prongs round a teal
    core at the muzzle."""
    clamp_block(m, root, w=1.8)
    loop = [(0, 2.2 + 0.95 * math.cos(2 * math.pi * i / 24), 0.95 * math.sin(2 * math.pi * i / 24)) for i in range(24)]
    shapes.sweep("grip_loop", loop, 0.16, m["trim"], cyclic=True, parent=root)
    along("breech", 0.8, 1.2, -2.2, m["metal"], root, verts=24)
    for k, y in enumerate((0.9, -0.6, -2.0)):
        ring(f"breech_band{k}", 0.82, 0.13, y, m["trim"], root)
    along("barrel", 0.46, -2.2, -14.0, m["metal"], root, verts=16)
    # Bulbous gold-and-teal coil collars.
    for k, y in enumerate((-3.4, -6.6, -9.8)):
        turned(f"coil{k}", [(0.46, 0.0), (0.85, 0.12), (0.98, 0.4), (0.98, 1.4), (0.85, 1.68), (0.46, 1.8)], m["trim"], root, y=y, segments=32)
        for j in range(4):
            ring(f"coil{k}_wind{j}", 1.0, 0.07, y - 0.55 - 0.25 * j, m["metal"], root, n=24)
        ring(f"coil{k}_glow", 1.0, 0.05, y - 1.55, m["glow"], root, n=24)
    for k, y in enumerate((-5.4, -8.6, -11.8)):
        ring(f"barrel_band{k}", 0.5, 0.08, y, m["trim"], root, n=16)
    # Emitter: a collar, a glowing core, and three swept prongs.
    turned("emitter", [(0.46, 0.0), (0.85, 0.3), (0.8, 0.8), (0.5, 1.0)], m["trim"], root, y=-13.0, segments=32)
    shapes.sphere("core", 0.38, m["glow"], loc=(0, -14.6, 0), parent=root, segments=16)
    for k in range(3):
        a = 2 * math.pi * k / 3 + math.pi / 2
        c, s = math.cos(a), math.sin(a)
        pts = bezier((0.55 * c, -13.8, 0.55 * s), (1.1 * c, -14.8, 1.1 * s), (0.45 * c, -16.0, 0.45 * s), 10)
        loft(f"prong{k}", pts, lambda u: 0.22 * (1 - 0.85 * u), lambda u: 0.14 * (1 - 0.85 * u), m["metal"], root, shape="diamond",
             up=(c, 0, s))


def hellfire_missiles(m, root):
    """A curved horn of black metal, ribbed and latticed in gold, with lit
    missile hatches along its back and a finial at the rear."""
    clamp_block(m, root, w=2.0)
    zc = 1.0
    path = bezier((0, 0.6, zc), (0, -5.0, zc + 1.6), (0, -11.0, zc - 1.2), 28)
    horn_w = lambda u: 1.55 * (1 - u) ** 0.9 + 0.02  # noqa: E731
    loft("horn", path, horn_w, lambda u: 1.35 * (1 - u) ** 0.9 + 0.02, m["metal"], root, shape="round", sides=20)
    # Gold ribs round the horn, following its taper.
    for k, i in enumerate((2, 6, 10, 14, 18)):
        p, q = path[i], path[i + 1]
        tan = (q - p).normalized()
        side = tan.cross(Vector((0, 0, 1))).normalized()
        nup = side.cross(tan)
        u = i / 27
        pts = [p + side * math.cos(a) * (horn_w(u) + 0.04) + nup * math.sin(a) * (1.35 * (1 - u) ** 0.9 + 0.06)
               for a in (2 * math.pi * j / 24 for j in range(24))]
        shapes.sweep(f"rib{k}", pts, 0.11 - 0.012 * k, m["trim"], cyclic=True, parent=root)
    # A lattice of gold strakes along the flanks.
    for s in (-1, 1):
        for j, off in enumerate((0.35, -0.35)):
            pts = []
            for i in range(2, 22):
                p, q = path[i], path[i + 1]
                tan = (q - p).normalized()
                side = tan.cross(Vector((0, 0, 1))).normalized()
                nup = side.cross(tan)
                u = i / 27
                a = s * (math.pi / 2) + off + 0.25 * math.sin(i * 0.9) * (1 if j else -1)
                pts.append(p + side * math.sin(a) * (horn_w(u) + 0.05) + nup * math.cos(a) * (1.35 * (1 - u) ** 0.9 + 0.05))
            shapes.sweep(f"strake{'LR'[s > 0]}{j}", pts, 0.07, m["trim"], parent=root)
    # Missile hatches along the spine, each a teal slot in a gold frame.
    for k, i in enumerate((5, 9, 13)):
        p = path[i]
        u = i / 27
        h = 1.35 * (1 - u) ** 0.9
        tan = (path[i + 1] - p).normalized()
        pitch = math.atan2(tan.z, -tan.y)
        hatch = box(f"hatch{k}", (0.9 - 0.12 * k, 0.9, 0.3), p + Vector((0, 0, h * 0.92)), m["trim"], root, bevel=0.05)
        hatch.rotation_euler = (pitch, 0, 0)
        glow = box(f"hatch_glow{k}", (0.6 - 0.1 * k, 0.6, 0.1), p + Vector((0, 0, h * 0.92 + 0.15)), m["glow"], root, bevel=0)
        glow.rotation_euler = (pitch, 0, 0)
    # Fins and the rear finial.
    for s in (-1, 1):
        pts = bezier((s * 1.2, -1.0, zc + 0.9), (s * 2.4, -2.4, zc + 2.4), (s * 1.0, -4.8, zc + 2.1), 10)
        loft(f"fin{'LR'[s > 0]}", pts, lambda u: 0.32 * (1 - 0.8 * u), lambda u: 0.1, m["trim"], root, shape="diamond", up=(0, 1, 0))
    turned("finial_cap", [(1.3, 0.0), (1.1, -0.4), (0.55, -0.8), (0.4, -1.4)], m["trim"], root, y=0.6, z=zc)
    shapes.sphere("finial_knob", 0.5, m["trim"], loc=(0, 2.2, zc), parent=root, segments=16)
    ring("finial_ring", 0.68, 0.12, 2.2, m["trim"], root, z=zc)


def kinetic_claws(m, root):
    """A gauntlet of black metal and gold with four long, hooked talons that
    sweep forward and down, each jointed with gold knuckles."""
    clamp_block(m, root, w=2.0)
    box("gauntlet", (2.6, 3.0, 2.0), (0, -1.6, 0.1), m["metal"], root, bevel=0.25, taper=0.15)
    box("gauntlet_plate", (2.0, 2.4, 0.3), (0, -1.6, 1.2), m["hull"], root, bevel=0.08)
    shapes.sweep("gauntlet_trim", [(-1.35, -0.2, 1.1), (-1.35, -3.1, 1.1), (1.35, -3.1, 1.1), (1.35, -0.2, 1.1)], 0.1, m["trim"], parent=root)
    shapes.sphere("gauntlet_eye", 0.32, m["glow"], loc=(0, -3.0, 1.0), parent=root, segments=12)
    for k, x in enumerate((-0.9, -0.3, 0.3, 0.9)):
        spread = x * 0.5
        length = 8.0 - abs(x) * 1.4
        knuckle = Vector((x, -3.2, 0.2))
        shapes.sphere(f"knuckle{k}", 0.36, m["trim"], loc=knuckle, parent=root, segments=12)
        # First phalanx: straight, then the talon hooks downward.
        mid = knuckle + Vector((spread, -length * 0.35, 0.35))
        loft(f"phalanx{k}", [knuckle, (knuckle + mid) / 2, mid], 0.28, 0.24, m["metal"], root, shape="box", up=(0, 0, 1))
        shapes.sphere(f"joint{k}", 0.3, m["trim"], loc=mid, parent=root, segments=12)
        pts = bezier(mid, mid + Vector((spread * 0.8, -length * 0.45, 0.2)), mid + Vector((spread * 1.2, -length * 0.65, -1.9)), 16)
        loft(f"talon{k}", pts, lambda u: 0.26 * (1 - u) ** 0.9 + 0.01, lambda u: 0.2 * (1 - u) ** 0.9 + 0.01, m["trim"], root,
             shape="diamond", up=(0, 0, 1))
    # The thumb hook below.
    pts = bezier((0.9, -2.6, -0.8), (1.4, -4.0, -1.4), (0.9, -5.0, -0.6), 12)
    loft("thumb", pts, lambda u: 0.3 * (1 - u) + 0.01, lambda u: 0.22 * (1 - u) + 0.01, m["trim"], root, shape="diamond", up=(1, 0, 0))
    # A back fin, as the board's claw has.
    loft("fin", bezier((0, 0.4, 1.2), (0, -0.6, 2.0), (0, -2.2, 1.4), 10), lambda u: 0.12, lambda u: 0.35 * (1 - u) + 0.05,
         m["trim"], root, shape="diamond", up=(0, 0, 1))


def soul_lantern(m, root):
    """A gothic lantern standing on a hexagonal socket: a gold base, a
    six-sided glass column glowing teal-white between slender posts, a crown
    of pointed arches under an onion cap, a finial and a hanging ring."""
    shapes.cylinder("socket", 1.0, 0.5, m["metal"], loc=(0, 0, 0.25), parent=root, verts=6, bevel=0.06)
    zb = 0.5

    def up(name, prof, mat, z0):
        return shapes.lathe(name, prof, mat, segments=6, loc=(0, 0, z0), parent=root)

    up("base", [(0.0, 0.0), (0.75, 0.0), (0.95, 0.25), (1.0, 0.5), (0.82, 0.65), (0.88, 0.8)], m["metal"], zb)
    shapes.cylinder("glass", 0.64, 2.6, m["glow"], loc=(0, 0, zb + 2.1), parent=root, verts=6, bevel=0)
    for k in range(6):
        a = 2 * math.pi * k / 6
        shapes.cylinder(f"post{k}", 0.1, 2.7, m["metal"], loc=(0.8 * math.cos(a), 0.8 * math.sin(a), zb + 2.1), parent=root, verts=6, bevel=0)
        b = a + math.pi / 6
        shapes.lancet(f"arch{k}", 0.5, 0.65, 0.08, m["trim"], loc=(0.72 * math.cos(b), 0.72 * math.sin(b), zb + 2.75),
                      rot=(0, 0, b + math.pi / 2), parent=root)
    up("crown", [(0.88, 0.0), (0.98, 0.1), (0.98, 0.25), (0.6, 0.6), (0.66, 0.78), (0.36, 1.2), (0.12, 1.6), (0.0, 1.7)], m["metal"], zb + 3.4)
    for k, z in enumerate((zb + 0.8, zb + 3.42)):
        shapes.sweep(f"band{k}", [(0.9 * math.cos(2 * math.pi * i / 6), 0.9 * math.sin(2 * math.pi * i / 6), z) for i in range(6)], 0.08,
                     m["trim"], cyclic=True, parent=root, profile="square")
    shapes.sphere("finial", 0.18, m["trim"], loc=(0, 0, zb + 5.15), parent=root, segments=10)
    ring("hang_ring", 0.32, 0.08, 0.0, m["trim"], root, z=zb + 5.65)


BUILDERS = {
    "lance": lance, "lance@paladin": lance_paladin, "melee-blade": melee_blade, "carapace-gun": carapace_gun, "missile-rack": missile_rack,
    "autocannon": autocannon, "rail-cannon": rail_cannon, "rocket-pod": rocket_pod, "industrial-claw": industrial_claw,
    "arc-cannon": arc_cannon, "hellfire-missiles": hellfire_missiles, "kinetic-claws": kinetic_claws, "soul-lantern": soul_lantern,
}


def build(item):
    faction = FACTION[item.split("@")[0]]
    m = kit.materials.library(faction)
    root = empty(f"item_{item}", size=2)
    BUILDERS[item](m, root)
    return root


# ------------------------------------------------------------------ review


def shots(item, root, out, samples):
    objs = kit.meshes(root)
    core = item in ("carapace-gun", "soul-lantern")
    side = kit.render.shot(objs, out / f"{item}-side.png", az=82, el=8, samples=samples, res=(1100, 560 if not core else 820), lens=80, margin=0.58 if not core else 0.78)
    hero = kit.render.shot(objs, out / f"{item}-34.png", az=-38 if not core else 35, el=18, samples=samples, res=(900, 900), lens=60, margin=0.92)
    for p in (side, hero):
        kit.render.post(p, bloom=0.8)
    return side, hero


def sheet(faction, out):
    """Each weapon's art crop above its side-on render and three-quarter view."""
    from PIL import Image, ImageDraw
    items = [i for i, f in FACTION.items() if f == faction]
    W, gap = 560, 18
    tiles = []
    for item in items:
        side, hero = out / f"{item}-side.png", out / f"{item}-34.png"
        if not side.exists():
            continue
        art = kit.render.crop(f"weapon_{item}")
        art = art.resize((W, round(art.height * W / art.width)), Image.LANCZOS)
        s = Image.open(side).convert("RGB")
        s = s.resize((W, round(s.height * W / s.width)), Image.LANCZOS)
        h = Image.open(hero).convert("RGB").resize((W, W), Image.LANCZOS)
        tile = Image.new("RGB", (W, art.height + s.height + h.height + 2 * gap + 30), (12, 13, 16))
        tile.paste(art, (0, 0))
        tile.paste(s, (0, art.height + gap))
        tile.paste(h, (0, art.height + s.height + 2 * gap))
        ImageDraw.Draw(tile).text((6, tile.height - 24), f"item_{item}", fill=(170, 165, 150), font=kit.render._font(16))
        tiles.append(tile)
    if not tiles:
        return None
    H = max(t.height for t in tiles)
    im = Image.new("RGB", (len(tiles) * (W + gap) + gap, H + 60), (12, 13, 16))
    ImageDraw.Draw(im).text((gap, 16), f"{faction} signature weapons: board crop, side-on, three-quarter", fill=(220, 210, 190), font=kit.render._font(22))
    for k, t in enumerate(tiles):
        im.paste(t, (gap + k * (W + gap), 50))
    path = out / f"weapons-{faction}.png"
    im.save(path)
    return path


def main():
    args = script_args()
    flags = {"--samples", "--out"}
    samples = int(args[args.index("--samples") + 1]) if "--samples" in args else 48
    out = Path(args[args.index("--out") + 1]) if "--out" in args else REPO / "renders" / "weapons"
    items = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in flags)] or list(BUILDERS)
    for item in items:
        kit.reset_scene()
        root = build(item)
        if "--publish" in args:
            kit.publish(root, size=512, source=HERE / f"item_{item}.blend")
        if "--render" in args:
            kit.render.studio()
            shots(item, root, out, samples)
            print("rendered", item)
    if "--render" in args:
        for faction in ("covenant", "foundries", "reliquary"):
            p = sheet(faction, out)
            if p:
                print("wrote", p)


main()
