"""Package 1: the three faction helms, one per frame.

    ~/bvenv/bin/python assets/blender/parts/helm/helms.py [faction ...] [--frames titan,bulwark] [--render OUT] [--no-publish]

Iron Covenant: a beaked armet. A V-keeled faceplate pierced by an eye slot
and vertical amber slits, a peaked filigree brow, stacked cheek lames, a keel
crest and fluted skull (concept: covenant_helm, detail_covenant_helm).
Ashen Foundries: a slab head sunk under a red enamel hood, a recessed furnace
visor behind a cage grille, riveted cheek plates, a stack and a mast
(concept: hero_foundries, class_brute).
Reliquary: a pointed bone-ceramic cowl edged and ribbed in pale gold round a
long dark mask with a nose keel, gold kintsugi lines and teal eyes
(concept: detail_reliquary_helm).

Each helm is modelled in helm units (R = 1, centred on the skull, facing -Y),
then every piece is applied, scaled to the frame's head and moved into the
head joint's space before baking, so bevels and proportions stay the same at
every size while the wear masks see true millimetres.
"""
import math
import sys
from pathlib import Path

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # assets/blender
import kit
from kit import shapes
from kit.core import apply_all, bmesh, direction, mesh_obj, mod
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
FACTIONS = ("covenant", "foundries", "reliquary")
FRAMES = ("scout", "striker", "bulwark", "titan")
SAMPLES = 48

# Helm size and the skull centre above the head joint, as fractions of the
# frame's height. The frames' helm stand-in is 0.055 H round, 0.03 H up.
FIT = {
    "covenant": dict(R=0.056, up=0.03),
    "foundries": dict(R=0.054, up=0.022),
    "reliquary": dict(R=0.05, up=0.036),
}


# ------------------------------------------------------------------ helpers

def squarish(c, p):
    return math.copysign(abs(c) ** p, c)


def deformed_sphere(name, mat, fn, u=64, v=40, cut=None, parent=None):
    """A UV sphere with every vertex passed through fn(x, y, z) -> (x, y, z),
    optionally cut flat below z = cut."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=1.0)
    for vt in bm.verts:
        vt.co = Vector(fn(*vt.co))
    if cut is not None:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, cut), plane_no=(0, 0, 1), clear_inner=True)
    return mesh_obj(name, bm, mat, parent=parent)


def ray_cutter(name, outlines, mat, centre=(0, 0, 0), r0=0.25, r1=2.6, parent=None):
    """One cutter object holding a prism per outline of (az, el) points, cast
    outwards from `centre`: slits and openings through a shell."""
    c = Vector(centre)
    bm = bmesh.new()
    for pts in outlines:
        inner = [bm.verts.new(c + direction(a, e) * r0) for a, e in pts]
        outer = [bm.verts.new(c + direction(a, e) * r1) for a, e in pts]
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((inner[i], inner[j], outer[j], outer[i]))
        bm.faces.new(list(reversed(inner)))
        bm.faces.new(outer)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return mesh_obj(name, bm, mat, smooth=False, parent=parent)


def rect(a0, a1, e0, e1, n=6):
    """A rectangle in (az, el), densely sampled so cast prisms follow the shell."""
    pts = [(a0 + (a1 - a0) * i / n, e0) for i in range(n)]
    pts += [(a1, e0 + (e1 - e0) * i / n) for i in range(n)]
    pts += [(a1 - (a1 - a0) * i / n, e1) for i in range(n)]
    pts += [(a0, e1 - (e1 - e0) * i / n) for i in range(n)]
    return pts


def ridge(name, shell, pts, height, width, mat, parent):
    """A fin standing off the shell along (az, el) points: crests and keels.
    Returns the fin and the points along its top edge."""
    bm = bmesh.new()
    rows, top = [], []
    n = len(pts)
    for k, (a, e) in enumerate(pts):
        p, nrm = shell.at(a, e, 0.0)
        h = height(k / (n - 1)) if callable(height) else height
        side = Vector((1, 0, 0)) * width
        rows.append([bm.verts.new(p - side), bm.verts.new(p + nrm * h - side * 0.3),
                     bm.verts.new(p + nrm * h + side * 0.3), bm.verts.new(p + side)])
        top.append(p + nrm * (h + width * 0.15))
    for a, b in zip(rows, rows[1:]):
        for i in range(3):
            bm.faces.new((a[i], a[i + 1], b[i + 1], b[i]))
    fin = mesh_obj(name, bm, mat, parent=parent)
    mod(fin, "SOLIDIFY", thickness=width * 0.3)
    mod(fin, "BEVEL", width=width * 0.15, segments=2)
    return fin, top


def finalize(root, faction, frame):
    """Apply every piece, scale helm units to millimetres and move it into the
    head joint's space (the part's origin is the joint)."""
    sk = kit.skeleton.Skeleton(faction, frame)
    fit = FIT[faction]
    R = fit["R"] * sk.H
    offset = Vector((0, 0, fit["up"] * sk.H))   # skull centre relative to joint_head
    T = Matrix.Translation(offset) @ Matrix.Scale(R, 4)
    bpy.context.view_layer.update()
    objs = [o for o in kit.meshes(root) if not o.get("kit_cutter")]
    objs = [apply_all(o) for o in objs]
    for o in list(kit.subtree(root)):
        if o.get("kit_cutter"):
            bpy.data.objects.remove(o)
    bpy.context.view_layer.update()
    objs = [o for o in kit.meshes(root)]
    world = {o: o.matrix_world.copy() for o in objs}
    for o in objs:
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        o.data.transform(T @ world[o])
        o.parent = root
        o.matrix_parent_inverse = Matrix.Identity(4)
        # Relief masks are laid out in world mm at bake time; only the filigree
        # inlays keep the layout their patch gave them.
        if "Decal" in o.data.uv_layers and not any(s.material and s.material.get("kit_role") == "filigree" for s in o.material_slots):
            o.data.uv_layers.remove(o.data.uv_layers["Decal"])
    for o in [*kit.subtree(root)]:
        if o.type == "MESH" and not len(o.data.polygons):
            bpy.data.objects.remove(o)
    return root


# ------------------------------------------------------------------ Iron Covenant: beaked armet

def covenant(root):
    m = kit.materials.library("covenant")
    iron, gold, fili, glow = m["armour"], m["trim"], m["filigree"], m["glow"]

    def skull(x, y, z):
        x, y = squarish(x, 0.78), squarish(y, 0.9)
        x, y, z = x * 0.7, y * 0.94, z * 1.06
        # A taller, narrower crown than a round skull.
        x *= 1 - 0.14 * max(0.0, z) ** 2
        if y < 0:
            # The beak: two flat facets meeting in a sharp keel down the face,
            # pushed furthest forward at the visor and drawn in under the chin.
            face = max(0.0, 1 - ((z + 0.28) / 0.48) ** 2) ** 0.7
            y -= 0.82 * max(0.0, 1 - abs(x) / 0.52) ** 1.45 * face
            if z < -0.3:
                y *= 1 - 0.25 * (-0.3 - z)
        return x, y, z
    # Dense enough to stay smooth without a subdivision pass (which tripled the GLB).
    shell = deformed_sphere("helm_skull", iron, skull, u=88, v=52, cut=-0.74, parent=root)
    mod(shell, "SOLIDIFY", thickness=0.09, offset=-1)
    S = shapes.Shell(shell)

    # Amber visor glass a little inside the faceplate, seen through the slits.
    glass = deformed_sphere("helm_visor_glass", glow, lambda x, y, z: tuple(c * 0.86 for c in skull(x, y, z)), u=48, v=28, parent=root)
    bm = bmesh.new()
    bm.from_mesh(glass.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y > -0.1 or f.calc_center_median().z < -0.62], context="FACES")
    bm.to_mesh(glass.data)
    bm.free()

    # Vertical sight slits down both facets of the beak, the keel left whole.
    slits = []
    for az in (-26, -20.5, -15, -9.5, -4.5, 4.5, 9.5, 15, 20.5, 26):
        slits.append(rect(az - 1.4, az + 1.4, -34 + abs(az) * 0.25, -1 - abs(az) * 0.12))
    cut = ray_cutter("helm_visor_cut", slits, iron, parent=root)
    shapes.boolean(shell, cut)
    mod(shell, "BEVEL", width=0.01, segments=2, limit_method="ANGLE", angle_limit=math.radians(40))

    # Visor surround: a raised iron frame with a gold lip round the slits.
    outline = rect(-31, 31, -37, 2, n=16)
    S.trim("helm_visor_frame", outline, 0.04, iron, cyclic=True, parent=root)
    S.trim("helm_visor_frame_gold", outline, 0.016, gold, lift=0.05, cyclic=True, parent=root)
    S.trim("helm_keel_gold", [(0, e) for e in range(-40, 6, 2)], 0.014, gold, lift=0.01, parent=root)

    # A heavy brow, peaked over the keel, overhanging the eye slot.
    def brow_lo(a):
        return 4 + 8 * max(0.0, 1 - abs(a) / 40) ** 1.4
    S.patch("helm_brow", -52, 52, brow_lo, lambda a: brow_lo(a) + 15, iron, lift=0.03, thick=0.05, trim_mat=gold, trim=0.02,
            decal=(fili, (3.0, 0.6)), lip=0.07, parent=root)
    S.studs("helm_brow_studs", [(a, brow_lo(a) + 2.5) for a in (-46, -36, 36, 46)], 0.028, gold, parent=root)

    # Cheek lames stacked down each side, each lower one riding further out.
    for side in (-1, 1):
        a0, a1 = (40, 104) if side > 0 else (-104, -40)
        for k, (e0, e1) in enumerate(((-6, 13), (-22, -3), (-38, -19))):
            S.patch(f"helm_cheek_{'L' if side > 0 else 'R'}_{k}", a0, a1, e0, e1, iron, lift=0.02 + 0.018 * k, thick=0.035, lip=0.05,
                    trim_mat=gold, trim=0.008, decal=(fili, (2.2, 0.6)) if k == 1 else None, parent=root)
    # Bevor: the chin plate under the slits.
    S.patch("helm_bevor", -40, 40, -50, -38, iron, lift=0.05, thick=0.045, trim_mat=gold, trim=0.014, decal=(fili, (2.5, 0.5)), lip=0.06, parent=root)

    # Crown: gothic filigree panels either side of the crest, plain plates behind.
    for i, (a0, a1) in enumerate(((-36, -7), (7, 36))):
        S.patch(f"helm_crown_front_{i}", a0, a1, lambda a: brow_lo(a) + 19, 64, iron, lift=0.012, thick=0.025, trim_mat=gold, trim=0.011,
                decal=(fili, (0.8, 1.2)), parent=root)
    for i, (a0, a1) in enumerate(((-104, -46), (46, 104))):
        S.patch(f"helm_crown_side_{i}", a0, a1, 20, 58, iron, lift=0.012, thick=0.025, trim_mat=gold, trim=0.008,
                decal=(fili, (1.6, 1.0)), parent=root)

    # Keel crest from brow to nape, a gold spine and gold studs down its flanks.
    path = [(0 if el <= 90 else 180, el if el <= 90 else 180 - el) for el in [26 + i * (186 - 26) / 40 for i in range(41)]]
    fin, top = ridge("helm_crest", S, path, lambda t: 0.1 * math.sin(math.pi * min(1.0, t * 1.1)) ** 0.55 + 0.03, 0.035, iron, root)
    shapes.sweep("helm_crest_spine", top, 0.014, gold, parent=root)
    S.studs("helm_crest_studs", [(sx * 5, el) for el in range(34, 90, 12) for sx in (-1, 1)], 0.016, gold, parent=root)

    # Fluted skull behind, and a gold rim band with rivets round the nape.
    for az in (-150, -125, 125, 150):
        pts = [(az, -32 + 104 * k / 20) for k in range(21)]
        S.trim(f"helm_flute_{az}", pts, 0.026, iron, parent=root)
        S.trim(f"helm_flute_gold_{az}", pts, 0.009, gold, lift=0.03, parent=root)
    S.trim("helm_rim", [(i * 3, -42) for i in range(120)], 0.028, gold, cyclic=True, parent=root)
    S.studs("helm_rim_rivets", [(a, -34) for a in range(112, 252, 14)], 0.02, gold, parent=root)
    # Hinge bosses where the faceplate would swing, at the temples.
    for sx in (-1, 1):
        p, n = S.at(sx * 96, 6, 0.0)
        b = shapes.cylinder(f"helm_hinge_{sx}", 0.09, 0.06, gold, loc=p + n * 0.03, parent=root, verts=24, bevel=0.012)
        b.rotation_euler = n.to_track_quat("Z", "Y").to_euler()
        shapes.cylinder(f"helm_hinge_pin_{sx}", 0.045, 0.06, iron, loc=p + n * 0.07, parent=root, verts=16, bevel=0.01).rotation_euler = b.rotation_euler
    return root


# ------------------------------------------------------------------ Ashen Foundries: slab head with a cage grille

def foundries(root):
    m = kit.materials.library("foundries")
    plate, brass, metal, hull, glow = m["armour"], m["trim"], m["metal"], m["hull"], m["glow"]

    core = shapes.box_plate("helm_block", (1.7, 1.45, 1.15), plate, bevel=0.07, loc=(0, 0.02, -0.08), parent=root, taper=0.18)
    # The furnace visor: a deep rectangular recess with the lamp at its back.
    cut = shapes.box_plate("helm_visor_cut", (1.12, 0.7, 0.5), plate, bevel=0, loc=(0, -0.78, -0.14), parent=root)
    shapes.boolean(core, cut)
    shapes.box_plate("helm_visor_lamp", (1.1, 0.06, 0.48), glow, bevel=0, loc=(0, -0.42, -0.14), parent=root)
    # Soot-dark louvres inside the recess, in front of the lamp.
    for k in range(3):
        shapes.box_plate(f"helm_visor_louvre_{k}", (1.1, 0.12, 0.03), metal, bevel=0.008, loc=(0, -0.5, -0.3 + k * 0.16), rot=(0.5, 0, 0), parent=root)
    # The cage: a brass frame round the recess and heavy bars across it.
    for name, size, loc in (("top", (1.3, 0.1, 0.09), (0, -0.76, 0.15)), ("bottom", (1.3, 0.1, 0.09), (0, -0.76, -0.43)),
                            ("left", (0.09, 0.1, 0.66), (0.62, -0.76, -0.14)), ("right", (0.09, 0.1, 0.66), (-0.62, -0.76, -0.14))):
        shapes.box_plate(f"helm_cage_{name}", size, brass, bevel=0.015, loc=loc, parent=root)
    for i in range(7):
        x = -0.48 + i * 0.16
        shapes.cylinder(f"helm_cage_bar_{i}", 0.032, 0.6, metal, loc=(x, -0.8, -0.14), parent=root, verts=12, bevel=0.006)
    for z in (-0.02, -0.26):
        shapes.cylinder(f"helm_cage_rail_{z:g}", 0.028, 1.2, metal, loc=(0, -0.84, z), rot=(0, math.pi / 2, 0), parent=root, verts=12, bevel=0.006)
    shapes.rivet_row("helm_cage_rivets_top", (-0.58, -0.82, 0.15), (0.58, -0.82, 0.15), 8, 0.03, brass, parent=root)
    shapes.rivet_row("helm_cage_rivets_bottom", (-0.58, -0.82, -0.43), (0.58, -0.82, -0.43), 8, 0.03, brass, parent=root)

    # The hood: a red enamel plate sloping down over the visor like a cap's peak.
    shapes.box_plate("helm_hood", (1.7, 1.35, 0.16), hull, bevel=0.04, loc=(0, -0.2, 0.6), rot=(-0.3, 0, 0), parent=root, taper=0.0)
    shapes.box_plate("helm_hood_ridge", (0.22, 1.3, 0.1), plate, bevel=0.03, loc=(0, -0.2, 0.7), rot=(-0.3, 0, 0), parent=root)
    shapes.box_plate("helm_hood_lip", (1.78, 0.14, 0.22), plate, bevel=0.03, loc=(0, -0.86, 0.38), rot=(-0.3, 0, 0), parent=root)
    shapes.rivet_row("helm_hood_rivets", (-0.8, -0.94, 0.4), (0.8, -0.94, 0.4), 11, 0.03, brass, parent=root)
    # Side skirts angled down from the hood over the cheeks, like a welder's hood.
    for sx in (-1, 1):
        shapes.box_plate(f"helm_hood_skirt_{sx}", (0.12, 1.25, 0.5), hull, bevel=0.03, loc=(sx * 0.93, -0.22, 0.34), rot=(-0.3, sx * 0.1, 0), parent=root, taper=-0.1)

    # Riveted cheek plates and vent louvres down each side.
    for sx in (-1, 1):
        shapes.box_plate(f"helm_cheek_{sx}", (0.14, 1.2, 0.86), plate, bevel=0.03, loc=(sx * 0.9, -0.05, -0.12), parent=root, taper=0.08)
        shapes.rivet_row(f"helm_cheek_rivets_{sx}_a", (sx * 0.98, -0.58, 0.22), (sx * 0.98, 0.48, 0.22), 6, 0.03, brass, parent=root, normal=(sx, 0, 0))
        shapes.rivet_row(f"helm_cheek_rivets_{sx}_b", (sx * 0.98, -0.58, -0.48), (sx * 0.98, 0.48, -0.48), 6, 0.03, brass, parent=root, normal=(sx, 0, 0))
        for k in range(4):
            shapes.box_plate(f"helm_vent_{sx}_{k}", (0.06, 0.55, 0.05), metal, bevel=0.01, loc=(sx * 1.0, 0.05, 0.08 - k * 0.13),
                             rot=(0, sx * 0.4, 0), parent=root)
    # A jaw plate under the visor, grooved.
    shapes.box_plate("helm_jaw", (1.36, 0.42, 0.26), plate, bevel=0.03, loc=(0, -0.62, -0.6), rot=(0.25, 0, 0), parent=root, panel_lines=4)

    # Back: a heat box and a short exhaust stack.
    shapes.box_plate("helm_heatbox", (1.2, 0.36, 0.7), metal, bevel=0.03, loc=(0, 0.84, -0.05), parent=root, panel_lines=5)
    stack = shapes.cylinder("helm_stack", 0.12, 0.62, metal, loc=(-0.55, 0.55, 0.85), parent=root, verts=20, bevel=0.015)
    shapes.cylinder("helm_stack_band", 0.15, 0.08, brass, loc=(-0.55, 0.55, 1.0), parent=root, verts=20, bevel=0.01)
    shapes.cylinder("helm_stack_cap", 0.16, 0.06, metal, loc=(-0.55, 0.55, 1.18), parent=root, verts=20, bevel=0.01)
    # A brass-rimmed lamp on the hood's right edge.
    lamp = shapes.cylinder("helm_lamp", 0.11, 0.16, brass, loc=(-0.62, -0.78, 0.6), rot=(math.pi / 2, 0, 0), parent=root, verts=20, bevel=0.015)
    shapes.cylinder("helm_lamp_lens", 0.08, 0.04, glow, loc=(-0.62, -0.87, 0.6), rot=(math.pi / 2, 0, 0), parent=root, verts=20, bevel=0)
    del stack, lamp
    return root


# ------------------------------------------------------------------ Reliquary: hooded mask

def reliquary(root):
    m = kit.materials.library("reliquary")
    ceramic, gold, fili, metal, glow = m["armour"], m["trim"], m["filigree"], m["metal"], m["glow"]

    def cowl(x, y, z):
        x, y, z = x * 0.84, y * 0.95, z * 1.15
        t = max(0.0, z) / 1.15
        # Drawn up into a point, the peak leaning forward over the face.
        x *= 1 - 0.45 * t ** 2
        y *= 1 - 0.38 * t ** 2
        z += 0.3 * t ** 3
        y -= 0.22 * t ** 2
        # The hem flares out as it falls to the shoulders.
        b = max(0.0, -z - 0.45)
        x *= 1 + 0.4 * b
        y *= 1 + 0.3 * b
        return x, y, z
    hood = deformed_sphere("helm_cowl", ceramic, cowl, cut=-1.0, parent=root)
    mod(hood, "SOLIDIFY", thickness=0.07, offset=-1)
    S = shapes.Shell(hood)

    # The opening: a tall pointed arch from the hem to above the brow.
    def arch_top(a):
        return 22 + 26 * (1 - min(1.0, abs(a) / 38)) ** 0.7

    opening = [(a, -80) for a in range(-38, 39, 4)]
    opening += [(38, e) for e in range(-76, 22, 8)]
    opening += [(a, arch_top(a)) for a in range(38, -39, -4)]
    opening += [(-38, e) for e in range(22, -77, -8)]
    cut = ray_cutter("helm_cowl_cut", [opening], ceramic, parent=root)
    shapes.boolean(hood, cut)
    mod(hood, "BEVEL", width=0.012, segments=2, limit_method="ANGLE", angle_limit=math.radians(40))

    # Pale gold round the opening, a second thinner line just outside it.
    edge = [(a * 1.04, e + (2 if e > -60 else 0)) for a, e in opening if e > -72]
    S.trim("helm_cowl_rim", edge, 0.035, gold, parent=root)
    S.trim("helm_cowl_rim_outer", [(a * 1.24, e + 6) for a, e in edge if e > -50], 0.012, gold, lift=0.01, parent=root)
    # Gold ribs running back over the cowl from the peak, like a reliquary's ribbing.
    for az in (62, 100, 140, 180, -140, -100, -62):
        pts = [(az, -70 + 150 * k / 24) for k in range(25)]
        S.trim(f"helm_rib_{az}", pts, 0.018, gold, parent=root)
    # A glyph band round the hem, edged in gold, and studs where the ribs meet it.
    S.patch("helm_hem", 42, 318, -66, -54, ceramic, lift=0.01, thick=0.02, trim_mat=gold, trim=0.01, decal=(fili, (9.0, 0.5)), nu=64, parent=root)
    S.studs("helm_cowl_studs", [(a, -60) for a in (62, 100, 140, 180, 220, 260, 298)], 0.03, gold, parent=root)
    # A gold sunburst medallion on the brow of the hood, above the arch.
    p, n = S.at(0, 54, 0.0)
    q = n.to_track_quat("Z", "Y").to_euler()
    shapes.cylinder("helm_medallion", 0.075, 0.03, gold, loc=p + n * 0.015, parent=root, verts=24, bevel=0.008).rotation_euler = q
    for k in range(12):
        a = 2 * math.pi * k / 12
        ray = shapes.box_plate(f"helm_medallion_ray_{k}", (0.016, 0.012, 0.11 if k % 2 else 0.075), gold, bevel=0.003, parent=root)
        local = Vector((math.sin(a), 0, math.cos(a)))
        ray.matrix_world = Matrix.Translation(p + n * 0.012) @ n.to_track_quat("-Y", "Z").to_matrix().to_4x4() @ Matrix.Rotation(-a, 4, "Y") @ Matrix.Translation(Vector((0, 0, 0.09)))
        del local

    # A dark lining behind the face so the opening reads as deep shadow.
    deformed_sphere("helm_lining", metal, lambda x, y, z: (x * 0.7, y * 0.72 + 0.12, z * 0.98), u=32, v=20, parent=root)

    # The mask: long and narrow, with a nose keel and a pointed chin.
    def face(x, y, z):
        x, y, z = x * 0.44, y * 0.4, z * 0.78
        if z < 0:
            x *= 1 + 0.6 * z
        if y < 0:
            nose = max(0.0, 1 - ((z + 0.06) / 0.5) ** 2)
            y -= 0.17 * max(0.0, 1 - abs(x) / 0.2) * nose
            brow = max(0.0, 1 - ((z - 0.26) / 0.1) ** 2)
            y -= 0.04 * brow
            # Sunken eye sockets either side of the keel.
            for sx in (-1, 1):
                d = ((x - sx * 0.17) / 0.11) ** 2 + ((z - 0.14) / 0.07) ** 2
                y += 0.05 * max(0.0, 1 - d)
        return x * 1.06, y * 1.05 - 0.6, z * 1.04 - 0.1
    mask = deformed_sphere("helm_mask", metal, face, u=56, v=36, parent=root)
    M = shapes.Shell(mask, centre=(0, -0.6, -0.1))
    # Gold kintsugi: the nose keel, a brow line and cracks across the cheeks.
    M.trim("helm_mask_keel", [(0, e) for e in range(-62, 70, 4)], 0.012, gold, parent=root)
    M.trim("helm_mask_brow", [(a, 32 - abs(a) * 0.15) for a in range(-60, 61, 4)], 0.01, gold, parent=root)
    for sx in (-1, 1):
        M.trim(f"helm_mask_crack_{sx}_a", [(sx * (22 + k * 3), 4 - k * 3 - (k % 2) * 2) for k in range(12)], 0.006, gold, parent=root)
        M.trim(f"helm_mask_crack_{sx}_b", [(sx * (40 + k * 2), 22 + k * 2 - (k % 2) * 3) for k in range(8)], 0.005, gold, parent=root)
        # Almond eyes set into the sockets.
        p, n = M.at(sx * 21, 13, -0.01)
        eye = shapes.sphere(f"helm_eye_{sx}", 0.075, glow, loc=p, scale=(1.0, 0.45, 0.55), parent=root, segments=16)
        eye.rotation_euler = (0, sx * 0.25, sx * -0.25)
    return root


BUILD = {"covenant": covenant, "foundries": foundries, "reliquary": reliquary}


def build(faction, frame):
    kit.reset_scene()
    root = kit.empty(kit.part_name(faction, "helm", frame))
    BUILD[faction](root)
    finalize(root, faction, frame)
    return root


def main(argv):
    factions = [a for a in argv if a in FACTIONS] or list(FACTIONS)
    frames = list(FRAMES)
    render = None
    publish = "--no-publish" not in argv
    for i, a in enumerate(argv):
        if a == "--frames":
            frames = argv[i + 1].split(",")
        if a == "--render":
            render = Path(argv[i + 1])
    for faction in factions:
        for frame in frames:
            root = build(faction, frame)
            if render is not None:
                kit.render.studio()
                for az in (0, 35, 90):
                    out = render / f"{root.name}-{az}.png"
                    kit.render.shot(kit.meshes(root), out, az=az, el=8, samples=SAMPLES, res=(720, 900), lens=70)
                    kit.render.post(out)
            if publish:
                # The script is the source; the editable .blend goes to the (ignored) cache.
                kit.publish(root, source=kit.export.BAKE_DIR.parent / "blend" / f"{root.name}.blend")


if __name__ == "__main__":
    main(sys.argv[1:] if "--" not in sys.argv else sys.argv[sys.argv.index("--") + 1:])
