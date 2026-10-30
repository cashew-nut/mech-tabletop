"""Package 2: torsos and pelvises for the three factions.

    ~/bvenv/bin/python assets/blender/parts/torso/torso.py preview [faction ...] [--frame titan] [--samples 32]
    ~/bvenv/bin/python assets/blender/parts/torso/torso.py publish [faction ...] [--frame titan]

`preview` builds each part in place on its frame's stand-ins and renders it
with live node materials, front three-quarter and back, beside the faction's
art. `publish` builds each part alone, moves it into its joint's space and
sends it through kit.publish() (bake, GLB, manifest).

Parts are per frame (`<faction>_torso_<frame>`, `<faction>_pelvis_<frame>`),
so every class on a frame shares them. Frames come from data/chassis.json.

What the art asks for, by faction:

* Iron Covenant: a heroic V of blackened iron. A keeled breastplate in two
  gold-edged pectoral plates with filigree inlays, stacked abdominal lames,
  and the caged furnace lantern glowing amber in the sternum. A fluted back
  plate with vents. At the hips, gold-edged tassets in lames, front and sides.
* Ashen Foundries: a hunched riveted box. Red enamel hull plates with the
  stenciled 07, a big square-cornered furnace porthole with grille bars, pipes
  and a gauge, a heavy waist ring with pistons. A blocky plated skirt.
* Reliquary: a slender cage. Bone ribs curving from an exposed spine round a
  dark teal core with a teal heart-light behind them, a gold sternum with a
  sunburst, a bone clavicle plate. A narrow pelvis with long hanging plates.
"""
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: F401  (before bmesh)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # assets/blender
import kit  # noqa: E402
from common import REPO, script_args  # noqa: E402
from kit import shapes  # noqa: E402
from kit.core import Vector, bmesh, empty, mesh_obj, mod, parent_keep  # noqa: E402

HERE = Path(__file__).resolve().parent
ART = {"covenant": "hero_covenant", "foundries": "hero_foundries", "reliquary": "hero_reliquary"}
DETAIL = {"covenant": "covenant_lantern", "foundries": "detail_foundries_furnace", "reliquary": "detail_reliquary_sunburst"}


def frames_by_faction():
    out = {}
    for c in json.loads((REPO / "data" / "chassis.json").read_text())["chassis"]:
        if c.get("faction") and c.get("frame"):
            out.setdefault(c["faction"], [])
            if c["frame"] not in out[c["faction"]]:
                out[c["faction"]].append(c["frame"])
    order = list(kit.skeleton.FRAMES)
    return {f: sorted(v, key=order.index) for f, v in out.items()}


# ------------------------------------------------------------------ helpers


def loft(name, sections, mat, n=2.5, segs=40, parent=None, subsurf=1):
    """A closed body through horizontal rounded-rectangle sections.
    Each section is (z, half_width, front_depth, back_depth, y_offset):
    a superellipse of exponent `n` (2 = ellipse, higher = squarer), front
    half reaching -front_depth in Y, back half +back_depth."""
    bm = bmesh.new()
    rings = []
    for z, hw, df, db, cy in sections:
        ring = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            s, c = math.sin(a), math.cos(a)
            x = hw * math.copysign(abs(s) ** (2 / n), s)
            d = df if c > 0 else db
            y = cy - d * math.copysign(abs(c) ** (2 / n), c)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    for ring, top in ((rings[0], False), (rings[-1], True)):
        c = sum((v.co for v in ring), Vector()) / len(ring)
        hub = bm.verts.new(c)
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((ring[i], ring[j], hub) if top else (ring[j], ring[i], hub))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, mat, parent=parent)
    if subsurf:
        mod(ob, "SUBSURF", levels=subsurf, render_levels=subsurf)
    shapes.decal_uv(ob)
    return ob


def rivet_ring(name, centre, radius, count, r, mat, normal=(0, -1, 0), parent=None):
    """Rivets round a circle facing `normal`."""
    nrm = Vector(normal).normalized()
    rot = nrm.to_track_quat("Z", "Y").to_matrix()
    bm = bmesh.new()
    for k in range(count):
        a = 2 * math.pi * k / count
        c = Vector(centre) + rot @ Vector((math.cos(a) * radius, math.sin(a) * radius, 0))
        geom = bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=r)
        for v in geom["verts"]:
            v.co = c + rot @ Vector((v.co.x, v.co.y, max(v.co.z, -r * 0.2) * 0.7))
    ob = mesh_obj(name, bm, mat, parent=parent)
    shapes.decal_uv(ob)
    return ob


def facing(ob, normal):
    """Turn an object built facing -Y to face `normal`."""
    ob.rotation_euler = Vector(normal).to_track_quat("-Y", "Z").to_euler()
    return ob


def stencil_plate(name, size, loc, mat, parent, rot=(0, 0, 0)):
    """A hull plate with one stencil spanning its face. Built facing -Y so
    the Decal map is laid in X/Z before it is turned."""
    p = shapes.box_plate(name, size, mat, bevel=min(size) * 0.25, loc=(0, 0, 0))
    me = p.data
    me.uv_layers.remove(me.uv_layers["Decal"])
    bpy.context.view_layer.update()
    tile = max(size[0], size[2]) * 1.05
    shapes.decal_uv(p, tile_mm=tile)
    for lp in me.uv_layers["Decal"].data:
        lp.uv = (lp.uv[0] + 0.5, lp.uv[1] + 0.5)
    p.location = loc
    p.rotation_euler = rot
    p.parent = parent
    return p


def gothic_disc_stack(name, z0, z1, r, mat, trim, count, parent):
    """The waist: a stack of discs (vertebrae), every other one gilded."""
    out = []
    for k in range(count):
        t = (k + 0.5) / count
        z = z0 + (z1 - z0) * t
        h = (z1 - z0) / count * 0.62
        rr = r * (0.92 + 0.08 * math.sin(t * math.pi))
        out.append(shapes.cylinder(f"{name}_{k}", rr, h, trim if k % 2 else mat, loc=(0, 0, z), verts=24, bevel=h * 0.2, parent=parent))
    return out


# ------------------------------------------------------------------ Iron Covenant


def covenant_torso(sk, m, root):
    H, W = sk.H, sk.W
    z0 = sk.joint("spine").z
    X = H * W
    th = max(0.006 * H, 0.35)                      # plate thickness, >= 0.35 mm
    trim = max(0.0045 * H, 0.22)
    body = loft("cov_chest", [
        (z0 - 0.005 * H, 0.068 * X, 0.050 * H, 0.050 * H, 0),
        (z0 + 0.040 * H, 0.095 * X, 0.070 * H, 0.060 * H, 0),
        (z0 + 0.100 * H, 0.140 * X, 0.090 * H, 0.070 * H, -0.004 * H),
        (z0 + 0.160 * H, 0.160 * X, 0.098 * H, 0.075 * H, -0.006 * H),
        (z0 + 0.205 * H, 0.155 * X, 0.090 * H, 0.075 * H, -0.004 * H),
        (z0 + 0.235 * H, 0.120 * X, 0.068 * H, 0.066 * H, 0),
        (z0 + 0.250 * H, 0.070 * X, 0.040 * H, 0.050 * H, 0),
    ], m["metal"], n=2.6, parent=root)
    bpy.context.view_layer.update()
    c = Vector((0, 0.0, z0 + 0.13 * H))
    sh = shapes.Shell(body, centre=c)

    # Pectoral plates: two gold-edged plates either side of the keel, filigree inlays,
    # each with a raised gothic arch in gold.
    for sx in (1, -1):
        side = "L" if sx > 0 else "R"
        a0, a1 = (6, 80) if sx > 0 else (-80, -6)
        sh.patch(f"cov_pec_{side}", a0, a1, lambda a: 2 - abs(a) * 0.06, 34, m["armour"], lift=th * 0.3, thick=th * 1.4,
                 trim_mat=m["trim"], trim=trim, decal=(m["filigree"], (2.0, 1.0)), lip=th * 2.0, parent=root)
        arch = [(sx * (20 + 34 * t), 7 + 20 * (1 - abs(2 * t - 1) ** 1.7)) for t in [k / 16 for k in range(17)]]
        sh.trim(f"cov_pec_arch_{side}", arch, trim * 0.9, m["trim"], lift=th * 2.6, parent=root)
        sh.studs(f"cov_pec_studs_{side}", [(sx * a, 5) for a in (16, 30, 44, 58, 72)], trim * 1.1, m["trim"], parent=root)
    # The gorget band across the top of the chest, under the collar.
    sh.patch("cov_gorget", -70, 70, 34, 46, m["filigree"], lift=th * 0.4, thick=th, trim_mat=m["trim"], trim=trim, parent=root)
    # The keel: a raised gold ridge down the sternum, framing the lantern.
    sh.trim("cov_keel_top", [(0, e) for e in range(44, 27, -2)], trim * 1.6, m["trim"], lift=th * 1.6, parent=root)
    # Abdominal lames below the chest, stacked and overlapping.
    sh.lames("cov_abs", -72, 72, [(-14, 0), (-27, -13), (-40, -26), (-52, -39)], m["armour"], trim_mat=m["trim"], lift=th * 0.3,
             step=th * 0.6, thick=th * 1.2, lip=th * 1.5, parent=root, trim=trim * 0.8)
    # Side plates over the ribs, plain iron with studs.
    for side, (a0, a1) in (("L", (84, 130)), ("R", (-130, -84))):
        sh.patch(f"cov_flank_{side}", a0, a1, -30, 32, m["armour"], lift=th * 0.3, thick=th * 1.2, trim_mat=m["trim"], trim=trim * 0.7, parent=root)
        mid = (a0 + a1) / 2
        sh.studs(f"cov_flank_studs_{side}", [(mid, e) for e in (-20, -6, 8, 22)], trim * 1.2, m["trim"], parent=root)

    # The furnace lantern: a caged lamp in a lancet niche in the sternum, as on the board.
    p, _ = sh.at(0, 14, 0)
    nw, nh = 0.075 * X, 0.115 * H
    shapes.lancet("cov_niche", nw, nh, 0.02 * H, m["trim"], loc=(0, p.y - 0.004 * H, p.z - nh * 0.5), parent=root, frame=nw * 0.12)
    shapes.box_plate("cov_niche_back", (nw, 0.01 * H, nh * 0.9), m["metal"], bevel=0, loc=(0, p.y + 0.008 * H, p.z - nh * 0.05), parent=root)
    lamp = Vector((0, p.y - 0.016 * H, p.z - 0.004 * H))
    lr, lh = 0.024 * X, 0.062 * H
    shapes.cylinder("cov_lantern", lr * 0.85, lh, m["glow"], loc=lamp, verts=6, bevel=0, parent=root)
    for k in range(6):
        a = math.pi / 6 + k * math.pi / 3
        shapes.box_plate(f"cov_lantern_bar{k}", (lr * 0.16, lr * 0.16, lh * 1.02), m["trim"], bevel=0,
                         loc=lamp + Vector((math.cos(a) * lr, math.sin(a) * lr, 0)), parent=root)
    shapes.cylinder("cov_lantern_base", lr * 1.2, lh * 0.12, m["trim"], loc=lamp - Vector((0, 0, lh * 0.55)), verts=6, bevel=lr * 0.05, parent=root)
    shapes.cylinder("cov_lantern_roof", lr * 1.25, lh * 0.45, m["trim"], loc=lamp + Vector((0, 0, lh * 0.72)), verts=6, bevel=0, r2=lr * 0.12, parent=root)
    shapes.sphere("cov_lantern_finial", lr * 0.22, m["trim"], loc=lamp + Vector((0, 0, lh * 1.0)), parent=root, segments=10)
    shapes.cylinder("cov_lantern_drop", lr * 0.35, lh * 0.25, m["trim"], loc=lamp - Vector((0, 0, lh * 0.72)), verts=6, bevel=0, r2=0.001,
                    rot=(math.pi, 0, 0), parent=root)
    # Two small side lanterns low on the chest, as on the board's lantern tile.
    for side, az in (("L", 46), ("R", -46)):
        q, n_ = sh.at(az, -6, th * 3.0)
        cage = shapes.cylinder(f"cov_sidelamp_{side}", 0.011 * H, 0.028 * H, m["glow"], loc=q, verts=6, bevel=0, parent=root)
        for k in range(6):
            a = math.pi / 6 + k * math.pi / 3
            shapes.box_plate(f"cov_sidelamp_{side}_bar{k}", (0.0025 * H, 0.0025 * H, 0.029 * H), m["trim"], bevel=0,
                             loc=(math.cos(a) * 0.012 * H, math.sin(a) * 0.012 * H, 0)).parent = cage
        shapes.cylinder(f"cov_sidelamp_{side}_cap", 0.015 * H, 0.012 * H, m["trim"], loc=(0, 0, 0.019 * H), verts=6, bevel=0, r2=0.002 * H).parent = cage
        shapes.cylinder(f"cov_sidelamp_{side}_base", 0.014 * H, 0.004 * H, m["trim"], loc=(0, 0, -0.016 * H), verts=6, bevel=0).parent = cage

    # Back: a fluted plate and twin vent grilles.
    sh.patch("cov_back", 140, 220, -18, 34, m["armour"], lift=th * 0.3, thick=th, trim_mat=m["trim"], trim=trim, parent=root)
    sh.flutes("cov_back_flute", [160, 172, 188, 200], -12, 28, trim * 0.9, m["armour"], trim_mat=m["trim"], parent=root)
    for side, x in (("L", 0.055), ("R", -0.055)):
        for k in range(4):
            q, _ = sh.at(180 + (12 if x > 0 else -12) * 2.2, -24 + k * 3.2, th * 1.4)
            shapes.box_plate(f"cov_vent_{side}{k}", (0.035 * X, 0.006 * H, 0.004 * H), m["metal"], bevel=0, loc=q, parent=root)

    # The waist: gilded vertebrae and two pistons either side.
    gothic_disc_stack("cov_waist", z0 - 0.035 * H, z0 + 0.03 * H, 0.05 * X, m["metal"], m["metal"], 4, root)
    for side in (1, -1):
        shapes.pipe(f"cov_waist_piston_{side}", [(side * 0.05 * X, 0.01 * H, z0 - 0.03 * H), (side * 0.065 * X, 0.0, z0 + 0.07 * H)],
                    0.008 * H, m["metal"], parent=root, bands=(0.15, 0.85), band_mat=m["trim"])
    return root


def covenant_pelvis(sk, m, root):
    H, W = sk.H, sk.W
    X = H * W
    pz = sk.joint("pelvis").z
    th = max(0.006 * H, 0.35)
    trim = max(0.0045 * H, 0.22)
    core = loft("cov_hips", [
        (pz - 0.045 * H, 0.050 * X, 0.040 * H, 0.040 * H, 0),
        (pz - 0.020 * H, 0.090 * X, 0.055 * H, 0.050 * H, 0),
        (pz + 0.020 * H, 0.095 * X, 0.058 * H, 0.052 * H, 0),
        (pz + 0.040 * H, 0.070 * X, 0.048 * H, 0.045 * H, 0),
    ], m["metal"], n=3.0, parent=root)
    bpy.context.view_layer.update()
    sh = shapes.Shell(core, centre=(0, 0, pz))
    # A filigree belt with gold edges.
    sh.patch("cov_belt", -179, 179, 4, 30, m["filigree"], lift=th * 0.3, thick=th, trim_mat=m["trim"], trim=trim, parent=root, nu=64)
    # Front tasset: a tall shield-shaped plate hanging from the belt in three lames.
    fw, top = 0.07 * X, pz + 0.02 * H
    for k in range(4):
        h = 0.045 * H
        z = top - k * h * 0.78 - h / 2
        w = fw * (1 - k * 0.1)
        pl = shapes.box_plate(f"cov_tasset_front_{k}", (w, th * 1.4, h), m["filigree" if k == 0 else "armour"], bevel=th * 0.4,
                              loc=(0, -0.062 * H - k * th * 0.8, z), rot=(math.radians(-8 - k * 4), 0, 0), parent=root, taper=-0.15)
        shapes.sweep(f"cov_tasset_front_{k}_trim", [(-w / 2 * 1.08, -th, -h / 2), (w / 2 * 1.08, -th, -h / 2)], trim, m["trim"], parent=pl)
    # A gold point at the bottom.
    shapes.cylinder("cov_tasset_point", 0.018 * X, 0.03 * H, m["trim"], loc=(0, -0.075 * H, top - 0.17 * H), rot=(math.pi, 0, 0),
                    verts=4, bevel=0, r2=0.001, parent=root)
    # Side tassets: three lames per side, flaring out over the hips.
    for side in (1, -1):
        for k in range(3):
            h = 0.045 * H
            w = 0.085 * H
            z = top - 0.005 * H - k * h * 0.8 - h / 2
            pl = shapes.box_plate(f"cov_tasset_{side}_{k}", (th * 1.4, w, h), m["armour"], bevel=th * 0.4,
                                  loc=(side * (0.125 * X + k * 0.008 * H), -0.005 * H, z), rot=(0, math.radians(side * (18 + k * 6)), 0), parent=root)
            shapes.sweep(f"cov_tasset_{side}_{k}_trim", [(side * th, -w / 2, -h / 2), (side * th, w / 2, -h / 2)], trim, m["trim"], parent=pl)
            shapes.rivet_row(f"cov_tasset_{side}_{k}_rv", (side * th * 0.8, -w * 0.4, h * 0.3), (side * th * 0.8, w * 0.4, h * 0.3), 4, trim * 0.8,
                             m["trim"], parent=pl, normal=(side, 0, 0))
    # Rear plate.
    shapes.box_plate("cov_tasset_back", (0.11 * X, th * 1.4, 0.07 * H), m["armour"], bevel=th * 0.4, loc=(0, 0.058 * H, top - 0.04 * H),
                     rot=(math.radians(10), 0, 0), parent=root, taper=-0.2)
    return root


# ------------------------------------------------------------------ Ashen Foundries


def foundries_torso(sk, m, root):
    H, W = sk.H, sk.W
    X = H * W
    z0 = sk.joint("spine").z
    th = max(0.008 * H, 0.45)
    rv = max(0.0045 * H, 0.22)
    hy = -0.02 * H                                # the hunch: the hull rides forward of the spine
    bev = 0.012 * H

    def rivets(name, a, b_, n, normal, parent=root):
        shapes.rivet_row(name, a, b_, n, rv, m["trim"], parent=parent, normal=normal)

    # The hull: a dark iron box, wider at the top, under rusted armour slabs.
    hw, hd, hz, hh = 0.15 * X, 0.10 * H, z0 + 0.135 * H, 0.17 * H
    shapes.box_plate("fdy_hull", (hw * 2, hd * 2, hh), m["metal"], bevel=bev, loc=(0, hy, hz), parent=root, taper=-0.14)
    # The yoke: a heavy plate across the shoulders, the walker's hunched back.
    yz = hz + hh / 2 + 0.018 * H
    shapes.box_plate("fdy_yoke", (hw * 2.2, hd * 2.1, 0.045 * H), m["armour"], bevel=bev * 0.8, loc=(0, hy + 0.01 * H, yz), parent=root, taper=0.12)
    rivets("fdy_yoke_rv", (-hw * 1.0, hy - hd * 1.06, yz), (hw * 1.0, hy - hd * 1.06, yz), 11, (0, -1, 0))
    # The belly: tapering down into the waist ring.
    bz = hz - hh / 2 - 0.035 * H
    shapes.box_plate("fdy_belly", (hw * 1.4, hd * 1.6, 0.07 * H), m["armour"], bevel=bev * 0.8, loc=(0, hy * 0.5, bz), parent=root, taper=-0.35)
    shapes.box_plate("fdy_belly_hull", (hw * 0.9, th, 0.04 * H), m["hull"], bevel=th * 0.3, loc=(0, hy * 0.5 - hd * 0.8 - th * 0.3, bz + 0.004 * H),
                     parent=root, panel_lines=2, rot=(math.radians(-12), 0, 0))
    # The front slab the furnace sits in.
    fy = hy - hd - th / 2
    shapes.box_plate("fdy_front", (hw * 1.75, th * 1.5, hh * 0.86), m["armour"], bevel=th * 0.4, loc=(0, fy, hz), parent=root, panel_lines=2)
    for k, z in enumerate((hz + hh * 0.4, hz - hh * 0.4)):
        rivets(f"fdy_front_rv{k}", (-hw * 0.82, fy - th * 0.8, z), (hw * 0.82, fy - th * 0.8, z), 10, (0, -1, 0))
    for k, x in enumerate((-hw * 0.84, hw * 0.84)):
        rivets(f"fdy_front_rvs{k}", (x, fy - th * 0.8, hz - hh * 0.32), (x, fy - th * 0.8, hz + hh * 0.32), 6, (0, -1, 0))

    # The furnace: a square-cornered housing, a deep fire behind a grate, a brass-hinged door frame.
    p = Vector((0, fy - th * 0.75, hz - 0.004 * H))
    R = 0.06 * X
    shapes.box_plate("fdy_furnace_frame", (R * 2.4, 0.02 * H, R * 2.5), m["metal"], bevel=R * 0.25, loc=p - Vector((0, 0.008 * H, 0)), parent=root)
    shapes.box_plate("fdy_furnace_bezel", (R * 2.0, 0.012 * H, R * 2.1), m["trim"], bevel=R * 0.22, loc=p - Vector((0, 0.018 * H, 0)), parent=root)
    shapes.box_plate("fdy_furnace_fire", (R * 1.6, 0.004 * H, R * 1.7), m["glow"], bevel=0, loc=p - Vector((0, 0.025 * H, 0)), parent=root)
    shapes.box_plate("fdy_furnace_coals", (R * 1.4, 0.01 * H, R * 0.35), m["glow"], bevel=0, loc=p - Vector((0, 0.028 * H, R * 0.62)), parent=root)
    for k in range(5):
        x = (k - 2) * R * 0.34
        shapes.box_plate(f"fdy_grate_v{k}", (R * 0.08, R * 0.12, R * 1.7), m["metal"], bevel=0, loc=p + Vector((x, -0.03 * H, 0)), parent=root)
    for k, z in enumerate((-R * 0.45, R * 0.45)):
        shapes.box_plate(f"fdy_grate_h{k}", (R * 1.65, R * 0.12, R * 0.08), m["metal"], bevel=0, loc=p + Vector((0, -0.031 * H, z)), parent=root)
    rivet_ring("fdy_furnace_bolts", p - Vector((0, 0.03 * H, 0)), R * 1.08, 14, rv, m["trim"], parent=root)
    for k, z in enumerate((-R * 0.7, R * 0.7)):
        shapes.cylinder(f"fdy_furnace_hinge{k}", R * 0.12, R * 0.45, m["trim"], loc=p + Vector((-R * 1.2, -0.03 * H, z)), verts=10, parent=root)
    shapes.box_plate("fdy_furnace_latch", (R * 0.4, R * 0.15, R * 0.2), m["trim"], bevel=R * 0.04, loc=p + Vector((R * 1.18, -0.032 * H, 0)), parent=root)

    # Red enamel hull plates: the stenciled 07 on the left flank, a plain one on the right,
    # and a red chest plate high on the right as on the Artillery.
    for sx in (1, -1):
        x = sx * (hw * 1.07 + th * 0.8)
        size = (0.15 * H, th * 1.6, 0.12 * H)
        rot = (0, 0, sx * math.pi / 2)
        if sx > 0:
            stencil_plate("fdy_plate_07", size, (x, hy, hz + 0.01 * H), m["stencil"], root, rot=rot)
        else:
            shapes.box_plate("fdy_plate_R", size, m["hull"], bevel=th * 0.4, loc=(x, hy, hz + 0.01 * H), rot=rot, parent=root, panel_lines=1)
        for z in (hz + 0.01 * H - 0.052 * H, hz + 0.01 * H + 0.052 * H):
            rivets(f"fdy_plate_rv{sx}{z:.2f}", (x + sx * th, hy - 0.065 * H, z), (x + sx * th, hy + 0.065 * H, z), 6, (sx, 0, 0))
    q = Vector((-hw * 0.55, fy - th * 1.4, hz + hh * 0.3))
    shapes.box_plate("fdy_chest_hull", (0.07 * X, th, 0.05 * H), m["hull"], bevel=th * 0.3, loc=q, parent=root)
    # A pressure gauge on the left of the furnace.
    shapes.gauge("fdy_gauge", 0.02 * X, m["trim"], m["armour"], m["metal"], loc=(hw * 0.6, fy - th * 1.2, hz + hh * 0.28), parent=root)

    # Steam pipes: from the back up over the yoke corners and down into the furnace frame.
    for sx in (1, -1):
        pts = [(sx * hw * 0.8, hy + hd * 1.15, hz - hh * 0.3), (sx * hw * 0.9, hy + hd * 1.15, yz + 0.02 * H),
               (sx * hw * 0.85, hy - hd * 0.4, yz + 0.03 * H), (sx * hw * 0.7, hy - hd * 1.2, yz), (sx * R * 1.4, hy - hd * 1.3, hz + R * 1.0)]
        shapes.pipe(f"fdy_pipe_{sx}", pts, 0.011 * H, m["metal"], parent=root, bands=(0.1, 0.45, 0.8), band_mat=m["trim"])
    # Back: a riveted boiler hatch with a wheel valve.
    by = hy + hd + th / 2
    shapes.box_plate("fdy_hatch", (hw * 1.4, th * 1.5, hh * 0.75), m["armour"], bevel=th * 0.4, loc=(0, by, hz), parent=root, panel_lines=1)
    rivet_ring("fdy_hatch_rv", (0, by + th, hz), hw * 0.5, 16, rv, m["trim"], normal=(0, 1, 0), parent=root)
    wheel = shapes.lathe("fdy_valve", [(hw * 0.2, -0.004 * H), (hw * 0.24, 0.0), (hw * 0.2, 0.004 * H)], m["trim"], segments=24,
                         rot=(-math.pi / 2, 0, 0), loc=(0, by + th + 0.012 * H, hz), parent=root)
    for k in range(3):
        shapes.box_plate(f"fdy_valve_spoke{k}", (hw * 0.42, 0.004 * H, 0.004 * H), m["trim"], bevel=0,
                         loc=(0, by + th + 0.012 * H, hz), rot=(0, k * math.pi / 3, 0), parent=root)

    # The waist: a heavy ring and pistons.
    shapes.cylinder("fdy_waist", 0.07 * X, 0.07 * H, m["metal"], loc=(0, 0, z0 + 0.0 * H), verts=24, bevel=0.004 * H, parent=root)
    shapes.cylinder("fdy_waist_ring", 0.085 * X, 0.016 * H, m["trim"], loc=(0, 0, z0 + 0.012 * H), verts=24, bevel=0.003 * H, parent=root)
    for sx in (1, -1):
        for dy in (-0.035, 0.035):
            shapes.pipe(f"fdy_piston_{sx}{dy}", [(sx * 0.07 * X, dy * H, z0 - 0.03 * H), (sx * 0.1 * X, dy * H, z0 + 0.05 * H)],
                        0.009 * H, m["metal"], parent=root, bands=(0.1, 0.55), band_mat=m["trim"])
    return root


def foundries_pelvis(sk, m, root):
    H, W = sk.H, sk.W
    X = H * W
    pz = sk.joint("pelvis").z
    th = max(0.007 * H, 0.4)
    rv = max(0.004 * H, 0.2)
    shapes.box_plate("fdy_hipblock", (0.17 * X, 0.11 * H, 0.07 * H), m["metal"], bevel=0.008 * H, loc=(0, 0, pz), parent=root, taper=-0.15)
    # Front skirt: a red hull plate over riveted iron.
    f = shapes.box_plate("fdy_skirt_front", (0.12 * X, th * 1.6, 0.075 * H), m["armour"], bevel=th * 0.4, loc=(0, -0.06 * H, pz - 0.01 * H),
                         rot=(math.radians(-10), 0, 0), parent=root, taper=-0.2)
    shapes.box_plate("fdy_skirt_front_hull", (0.085 * X, th, 0.05 * H), m["hull"], bevel=th * 0.3, loc=(0, -th, 0.005 * H), parent=f)
    shapes.rivet_row("fdy_skirt_front_rv", (-0.05 * X, -th * 1.1, 0.032 * H), (0.05 * X, -th * 1.1, 0.032 * H), 6, rv, m["trim"], parent=f)
    shapes.rivet_row("fdy_skirt_front_rv2", (-0.05 * X, -th * 1.1, -0.032 * H), (0.05 * X, -th * 1.1, -0.032 * H), 6, rv, m["trim"], parent=f)
    # Side plates, blocky, hinged off the hip block.
    for side in (1, -1):
        s = shapes.box_plate(f"fdy_skirt_{side}", (th * 1.6, 0.09 * H, 0.065 * H), m["armour"], bevel=th * 0.4,
                             loc=(side * 0.1 * X, -0.005 * H, pz - 0.012 * H), rot=(0, math.radians(side * 16), 0), parent=root, panel_lines=0)
        shapes.rivet_row(f"fdy_skirt_{side}_rv", (side * th, -0.035 * H, 0.025 * H), (side * th, 0.035 * H, 0.025 * H), 5, rv, m["trim"], parent=s, normal=(side, 0, 0))
        shapes.cylinder(f"fdy_skirt_{side}_hinge", 0.012 * H, 0.06 * H, m["trim"], loc=(side * 0.09 * X, -0.005 * H, pz + 0.025 * H),
                        rot=(math.pi / 2, 0, 0), verts=12, parent=root)
    shapes.box_plate("fdy_skirt_back", (0.13 * X, th * 1.6, 0.06 * H), m["armour"], bevel=th * 0.4, loc=(0, 0.06 * H, pz - 0.005 * H),
                     rot=(math.radians(10), 0, 0), parent=root)
    return root


# ------------------------------------------------------------------ Reliquary


def reliquary_torso(sk, m, root):
    H, W = sk.H, sk.W
    X = H * W
    z0 = sk.joint("spine").z
    th = max(0.005 * H, 0.35)
    rib = max(0.0042 * H, 0.36)
    # The dark teal core the ribs close round.
    core = loft("rlq_core", [
        (z0 + 0.03 * H, 0.035 * X, 0.030 * H, 0.03 * H, 0),
        (z0 + 0.09 * H, 0.060 * X, 0.048 * H, 0.04 * H, 0),
        (z0 + 0.17 * H, 0.075 * X, 0.055 * H, 0.045 * H, 0),
        (z0 + 0.22 * H, 0.060 * X, 0.045 * H, 0.045 * H, 0),
        (z0 + 0.24 * H, 0.035 * X, 0.030 * H, 0.035 * H, 0),
    ], m["metal"], n=2.2, parent=root)
    # A teal heart-light glowing between the ribs.
    shapes.sphere("rlq_heart", 0.03 * X, m["glow"], loc=(0, -0.045 * H, z0 + 0.15 * H), scale=(1.0, 0.6, 1.3), parent=root)
    # The ribcage: a guide shell, ribs swept round it from spine to sternum.
    guide = loft("rlq_guide", [
        (z0 + 0.06 * H, 0.06 * X, 0.05 * H, 0.04 * H, 0),
        (z0 + 0.11 * H, 0.11 * X, 0.075 * H, 0.05 * H, 0),
        (z0 + 0.17 * H, 0.125 * X, 0.082 * H, 0.055 * H, 0),
        (z0 + 0.215 * H, 0.12 * X, 0.075 * H, 0.055 * H, 0),
        (z0 + 0.245 * H, 0.08 * X, 0.05 * H, 0.05 * H, 0),
    ], m["armour"], n=2.2, parent=root)
    bpy.context.view_layer.update()
    sh = shapes.Shell(guide, centre=(0, 0, z0 + 0.16 * H))
    guide.hide_render = guide.hide_viewport = True
    guide["kit_cutter"] = True                    # a guide only: dropped at bake, never exported
    ribs = (-46, -30, -14, 2)
    for k, el in enumerate(ribs):
        for side in (1, -1):
            # Each rib leaves the spine high, sweeps round and falls towards the sternum.
            pts = [(side * a, el + 14 * (a - 90) / 90 + 3 * math.sin(math.radians(a))) for a in range(172, 13 + 10 * (k == 0), -6)]
            r = sh.trim(f"rlq_rib{k}_{side}", pts, rib * (1.0 + k * 0.08), m["armour"], profile="round", lift=rib * 0.2, parent=root)
            # Ribs thin towards the sternum.
            spts = r.data.splines[0].points
            for i, sp in enumerate(spts):
                sp.radius = 1.0 - 0.55 * (i / (len(spts) - 1)) ** 1.5
            # A gold band near the spine on every rib.
            q, n_ = sh.at(side * 150, el + 14 * 60 / 90 + 1.5, rib * 0.3)
            band = shapes.cylinder(f"rlq_ribband{k}_{side}", rib * 1.35, rib * 1.2, m["trim"], loc=q, verts=12, bevel=rib * 0.15, parent=root)
            band.rotation_euler = Vector((side * 0.5, -0.86, 0)).to_track_quat("Z", "Y").to_euler()
    # The sternum: a gold bar with a sunburst medallion.
    sh.trim("rlq_sternum", [(0, e) for e in range(30, -40, -4)], rib * 1.3, m["trim"], profile="square", lift=rib * 0.6, parent=root)
    q, n_ = sh.at(0, 24, rib * 2.5)
    med = shapes.cylinder("rlq_sun", 0.024 * X, rib * 1.4, m["trim"], loc=q, rot=(math.pi / 2, 0, 0), verts=24, bevel=rib * 0.3, parent=root)
    for k in range(12):
        a = 2 * math.pi * k / 12
        L = 0.05 * X if k % 3 == 0 else 0.034 * X
        ray = shapes.cylinder(f"rlq_sun_ray{k}", rib * 0.55, L, m["trim"], verts=6, bevel=0, r2=0.001,
                              loc=(math.sin(a) * (0.024 * X + L / 2), math.cos(a) * (0.024 * X + L / 2), 0))
        ray.rotation_euler = Vector((math.sin(a), math.cos(a), 0)).to_track_quat("Z", "Y").to_euler()
        ray.parent = med
    shapes.sphere("rlq_sun_eye", 0.009 * X, m["glow"], loc=(0, 0, rib * 0.8), parent=med, segments=12)
    # The clavicle plate: bone, gold-edged, glyph inlay, over the top of the cage.
    sh.patch("rlq_clavicle", -95, 95, 24, 46, m["armour"], lift=th * 0.5, thick=th, trim_mat=m["trim"], trim=rib * 0.6,
             decal=(m["filigree"], (3.0, 1.0)), lip=th, parent=root)
    sh.patch("rlq_clavicle_back", 130, 230, 18, 46, m["armour"], lift=th * 0.5, thick=th, trim_mat=m["trim"], trim=rib * 0.6, parent=root)
    # The spine: bone vertebrae up the back with gold rings.
    for k in range(9):
        el = -40 + k * 9
        q, n_ = sh.at(180, el, rib * 0.6)
        v = shapes.box_plate(f"rlq_vert{k}", (0.03 * X, 0.022 * H, 0.012 * H), m["armour"], bevel=rib * 0.3, loc=q, parent=root, taper=0.3)
        v.rotation_euler = n_.to_track_quat("-Y", "Z").to_euler()
    # The waist: an exposed column of vertebrae.
    gothic_disc_stack("rlq_waist", z0 - 0.04 * H, z0 + 0.06 * H, 0.03 * X, m["armour"], m["trim"], 7, root)
    shapes.cylinder("rlq_waist_core", 0.018 * X, 0.11 * H, m["metal"], loc=(0, 0, z0 + 0.01 * H), verts=12, parent=root)
    return root


def reliquary_pelvis(sk, m, root):
    H, W = sk.H, sk.W
    X = H * W
    pz = sk.joint("pelvis").z
    th = max(0.005 * H, 0.35)
    trim = max(0.004 * H, 0.22)
    core = loft("rlq_hips", [
        (pz - 0.04 * H, 0.04 * X, 0.03 * H, 0.03 * H, 0),
        (pz - 0.01 * H, 0.08 * X, 0.045 * H, 0.04 * H, 0),
        (pz + 0.025 * H, 0.07 * X, 0.04 * H, 0.04 * H, 0),
        (pz + 0.04 * H, 0.04 * X, 0.03 * H, 0.03 * H, 0),
    ], m["metal"], n=2.4, parent=root)
    bpy.context.view_layer.update()
    sh = shapes.Shell(core, centre=(0, 0, pz))
    sh.patch("rlq_girdle", -179, 179, 6, 32, m["filigree"], lift=th * 0.3, thick=th, trim_mat=m["trim"], trim=trim, parent=root, nu=64)
    # Long hanging plates, front and back: the tabard of the board's walkers.
    for name, y, tilt, n_pl in (("front", -1, -6, 3), ("back", 1, 6, 2)):
        for k in range(n_pl):
            h = (0.17 if k == (n_pl - 1) / 2 or n_pl == 2 else 0.13) * H
            w = 0.032 * X
            x = (k - (n_pl - 1) / 2) * w * 1.25
            pl = shapes.box_plate(f"rlq_tabard_{name}{k}", (w, th * 1.3, h), m["armour"], bevel=th * 0.4,
                                  loc=(x, y * 0.05 * H, pz + 0.015 * H - h / 2), rot=(math.radians(y * -tilt), 0, 0), parent=root, taper=0.25)
            shapes.sweep(f"rlq_tabard_{name}{k}_trim", [(-w * 0.38, y * -th, -h / 2 + trim), (0, y * -th, -h / 2 - trim * 2), (w * 0.38, y * -th, -h / 2 + trim)],
                         trim * 0.8, m["trim"], parent=pl)
            shapes.sphere(f"rlq_tabard_{name}{k}_stud", trim * 1.4, m["trim"], loc=(0, y * -th * 0.8, h * 0.38), parent=pl, segments=10)
    # Narrow hip guards.
    for side in (1, -1):
        shapes.box_plate(f"rlq_hipguard_{side}", (th * 1.3, 0.05 * H, 0.07 * H), m["armour"], bevel=th * 0.4,
                         loc=(side * 0.085 * X, 0, pz - 0.015 * H), rot=(0, math.radians(side * 12), 0), parent=root, taper=0.35)
    return root


BUILD = {
    "covenant": (covenant_torso, covenant_pelvis),
    "foundries": (foundries_torso, foundries_pelvis),
    "reliquary": (reliquary_torso, reliquary_pelvis),
}


def build(faction, frame, component):
    """Build one part in place on the walker (world space). Returns the root."""
    sk = kit.skeleton.Skeleton(faction, frame)
    m = kit.materials.library(faction)
    root = empty(kit.part_name(faction, component, frame), size=0.05 * sk.H)
    root["kit_component"] = component
    BUILD[faction][0 if component == "torso" else 1](sk, m, root)
    return root


def to_joint_space(root, faction, frame, component):
    """kit.skeleton.to_joint moves the root; keep the children where they sit
    relative to the joint by building at the origin and shifting the meshes."""
    off = kit.skeleton.Skeleton(faction, frame).socket(component)
    for ob in root.children:
        ob.location = ob.location - off
    return root


# ------------------------------------------------------------------ entry points


def preview(factions, frames, samples, out):
    shots = []
    for faction in factions:
        for frame in frames.get(faction, []):
            kit.reset_scene()
            kit.render.studio()
            body = kit.skeleton.build_frame(faction, frame)
            for o in body.children_recursive:
                if o.get("standin") in {"torso", "pelvis"}:
                    for c in (o, *o.children_recursive):
                        c.hide_render = True
            parts = [build(faction, frame, c) for c in ("torso", "pelvis")]
            objs = [o for p in parts for o in kit.meshes(p) if not o.get("kit_cutter")]
            body_objs = [o for o in kit.meshes(body) if not o.hide_render]
            front = kit.render.shot(objs, out / f"{faction}-{frame}-front.png", az=28, el=8, samples=samples, res=(720, 820), margin=1.05)
            back = kit.render.shot(objs, out / f"{faction}-{frame}-back.png", az=200, el=10, samples=samples, res=(720, 820), margin=1.05)
            whole = kit.render.shot(objs + body_objs, out / f"{faction}-{frame}-body.png", az=25, el=5, samples=samples, res=(620, 820), margin=0.85)
            for p in (front, back, whole):
                kit.render.post(p)
            sheet = out / f"{faction}-{frame}-compare.png"
            kit.render.compare([front, back, whole], DETAIL[faction], sheet, height=560,
                               labels=["torso + pelvis, front", "back", "on the frame"], title=f"{faction} torso and pelvis, {frame} frame")
            shots.append(sheet)
            print("wrote", sheet)
    return shots


def publish(factions, frames):
    for faction in factions:
        for frame in frames.get(faction, []):
            for component in ("torso", "pelvis"):
                kit.reset_scene()
                root = build(faction, frame, component)
                to_joint_space(root, faction, frame, component)
                bpy.context.view_layer.update()
                # Drop guides before baking so they don't take atlas space.
                for o in list(root.children_recursive):
                    if o.get("kit_cutter") and o.parent is root:
                        bpy.data.objects.remove(o)
                kit.publish(root, size=1024, source=HERE / "src" / f"{root.name}.blend")


def main():
    args = script_args()
    mode = args[0] if args and args[0] in {"preview", "publish"} else "preview"
    rest = args[1:] if args and args[0] == mode else args
    opts = {"--frame": None, "--samples": "32", "--out": str(REPO / "renders" / "torso")}
    pos = []
    i = 0
    while i < len(rest):
        if rest[i] in opts:
            opts[rest[i]] = rest[i + 1]
            i += 2
        else:
            pos.append(rest[i])
            i += 1
    factions = pos or list(kit.materials.FACTIONS)
    frames = frames_by_faction()
    if opts["--frame"]:
        frames = {f: [opts["--frame"]] for f in factions}
    if mode == "preview":
        preview(factions, frames, int(opts["--samples"]), Path(opts["--out"]))
    else:
        publish(factions, frames)


main()
