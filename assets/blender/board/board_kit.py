"""Board kit: hex tiles, gothic towers, ruin walls and table props for the 3D Charter Trial board.

    python assets/blender/board/board_kit.py [--only name ...]      (needs the pip `bpy` module)

Units are Three.js scene units: one hex has circumradius 1 and a tile's top face is at y = 0 (its body goes down to -0.4).
Colour is baked into vertex colours (stone variation, mortar, moss, plus per-corner ambient occlusion), so the GLBs carry no
textures. Blender is Z-up and the glTF exporter turns that into the web's Y-up. Pieces are written to apps/web/public/board/.
"""
import math
import random
import sys
from pathlib import Path

import bpy  # noqa: I001  (bpy must be imported before bmesh)
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

OUT = Path(__file__).resolve().parents[3] / "apps" / "web" / "public" / "board"
TILE_R = 0.97
TILE_DEPTH = 0.4


def lin(h):
    return tuple(((h >> s & 255) / 255) ** 2.2 for s in (16, 8, 0)) + (1.0,)


STONE = [lin(c) for c in (0xa5a299, 0x97948b, 0xb0ada3, 0x9d9a90)]
MORTAR = lin(0x4a4843)
DARK = lin(0x5a5750)
WALL = [lin(c) for c in (0xa8a59a, 0x96938a, 0xb3b0a3)]
TRIM = lin(0xbab7aa)
ROOF = lin(0x55524c)
WOOD = lin(0x7a5632)
MOSS = lin(0x5f7448)
SOOT = lin(0x24221f)
METAL = lin(0x6c7078)
GLOW = lin(0xffa43a)


# ---------------------------------------------------------------- helpers
def clean():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def new_obj(name, bm):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def box(bm, size, pos=(0, 0, 0), rot_z=0.0, bevel=0.0):
    sx, sy, sz = size
    res = bmesh.ops.create_cube(bm, size=1.0)
    verts = res["verts"]
    m = Matrix.Translation(pos) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Diagonal((sx, sy, sz, 1))
    bmesh.ops.transform(bm, matrix=m, verts=verts)
    if bevel:
        edges = {e for v in verts for e in v.link_edges}
        res = bmesh.ops.bevel(bm, geom=list(edges) + verts, offset=bevel, segments=1, affect="EDGES")
        verts = [v for v in res["verts"]]
    return verts


def pyramid(bm, width, height, pos, rot_z=math.pi / 4):
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=width / math.sqrt(2), radius2=0.0, depth=height)
    m = Matrix.Translation((pos[0], pos[1], pos[2] + height / 2)) @ Matrix.Rotation(rot_z, 4, "Z")
    bmesh.ops.transform(bm, matrix=m, verts=res["verts"])


def arch_cutter(w, h, depth, pos, face):
    """A pointed-arch prism used to cut a window; face is the axis the wall faces: +Y, -Y, +X, -X."""
    bm = bmesh.new()
    pts = [(-w / 2, 0), (w / 2, 0), (w / 2, h), (w * 0.28, h + w * 0.22), (0, h + w * 0.42), (-w * 0.28, h + w * 0.22), (-w / 2, h)]
    vs = [bm.verts.new((x, -depth / 2, z)) for x, z in pts]
    f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(0, depth, 0), verts=[v for v in ext["geom"] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ang = {"+Y": 0, "-Y": math.pi, "+X": -math.pi / 2, "-X": math.pi / 2}[face]
    bmesh.ops.transform(bm, matrix=Matrix.Translation(pos) @ Matrix.Rotation(ang, 4, "Z"), verts=bm.verts)
    return new_obj("cutter", bm)


def boolean_cut(target, cutters):
    for c in cutters:
        mod = target.modifiers.new("cut", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.object = c
        mod.solver = "EXACT"
        bpy.context.view_layer.objects.active = target
        target.select_set(True)
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(c, do_unlink=True)


def join(objs, name):
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


def colourise(obj, classify, seed, ao_len=0.45, ao_strength=0.35, rays=18):
    """Bake colour and per-corner ambient occlusion into the `Col` vertex colours."""
    rng = random.Random(seed)
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    layer = bm.loops.layers.float_color.new("Col")
    dirs = []
    for i in range(rays):  # fibonacci hemisphere around +Z
        z = (i + 0.5) / rays
        r = math.sqrt(1 - z * z)
        a = i * 2.399963
        dirs.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    face_rng = {}
    for f in bm.faces:
        face_rng[f.index] = rng.random()
        base = classify(f, face_rng[f.index])
        n = f.normal
        t = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).normalized()
        b = n.cross(t)
        for loop in f.loops:
            origin = loop.vert.co + n * 0.004
            hits = 0.0
            for d in dirs:
                w = t * d.x + b * d.y + n * d.z
                hit = tree.ray_cast(origin, w, ao_len)
                if hit[0] is not None:
                    hits += 1.0 - hit[3] / ao_len * 0.5
            ao = 1.0 - ao_strength * hits / rays
            # sunken faces and low corners read darker, as if grime collects there
            loop[layer] = (base[0] * ao, base[1] * ao, base[2] * ao, 1.0)
    bm.to_mesh(me)
    bm.free()
    mat = bpy.data.materials.new("board")
    mat.diffuse_color = (1, 1, 1, 1)
    me.materials.clear()
    me.materials.append(mat)
    me.polygons.foreach_set("use_smooth", [False] * len(me.polygons))


def export(objs, name):
    OUT.mkdir(parents=True, exist_ok=True)
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(OUT / f"{name}.glb"), export_format="GLB", use_selection=True, export_yup=True,
        export_apply=True, export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
    )
    print("wrote", name)


def vary(base, k):
    return tuple(min(1.0, c * (0.82 + 0.36 * k)) for c in base[:3]) + (1.0,)


# ---------------------------------------------------------------- tiles
def hex_prism(bm, top=0.0, depth=TILE_DEPTH, r=TILE_R):
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r, radius2=r, depth=depth)
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0, 0, top - depth / 2)) @ Matrix.Rotation(math.pi / 6, 4, "Z"), verts=res["verts"])
    return res["verts"]


def paving(bm, rng, cuts=2, gap=0.03, jitter=0.006, ragged=0.0):
    """Break the hex top into irregular flagstones separated by mortar gaps."""
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.poke(bm, faces=top)
    top = [f for f in bm.faces if f.normal.z > 0.9]
    if cuts:
        edges = list({e for f in top for e in f.edges})
        bmesh.ops.subdivide_edges(bm, edges=[e for e in edges if all(f.normal.z > 0.9 for f in e.link_faces)], cuts=cuts, use_grid_fill=True)
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.join_triangles(bm, faces=top, angle_face_threshold=0.2, angle_shape_threshold=1.2)
    top = [f for f in bm.faces if f.normal.z > 0.9]
    bmesh.ops.inset_individual(bm, faces=top, thickness=gap, use_even_offset=True)
    stones = [f for f in top if f.is_valid]  # inset keeps the original face as the inner stone; the new ring stays at 0 as mortar
    for f in stones:
        dz = rng.uniform(-jitter, jitter)
        for v in f.verts:
            v.co.z += 0.035 + dz
        if ragged and rng.random() < ragged:
            for v in f.verts:
                v.co.z -= rng.uniform(0.015, 0.03)
    # cut the stones into soft, chipped blocks
    return stones


def tile(name, variant, seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    hex_prism(bm)
    big = variant in ("slab",)
    if variant == "plate":
        pass
    else:
        paving(bm, rng, cuts=0 if big else 1, gap=0.05 if big else 0.035, ragged=0.1 if variant in ("rough", "rubble") else 0.0)
    bm.normal_update()
    verts_before = len(bm.verts)
    extra = []
    if variant == "plate":
        # a riveted steel plate with a raised rim, like the grey hex in the concept art
        top = [f for f in bm.faces if f.normal.z > 0.9][0]
        ring = bmesh.ops.inset_individual(bm, faces=[top], thickness=0.1)
        top = [f for f in bm.faces if f.normal.z > 0.9][0]
        for v in top.verts:
            v.co.z += 0.045
        for k in range(6):
            a = math.radians(30 + 60 * k + 0.0)
            res = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.035, radius2=0.03, depth=0.04)
            bmesh.ops.transform(bm, matrix=Matrix.Translation((0.74 * math.cos(a), 0.74 * math.sin(a), 0.067)), verts=res["verts"])
    if variant == "rubble":
        for i in range(7):
            s = rng.uniform(0.1, 0.22)
            ang = rng.uniform(0, math.tau)
            d = rng.uniform(0.0, 0.62)
            box(bm, (s * 1.3, s, s * 0.8), (d * math.cos(ang), d * math.sin(ang), s * 0.35), rng.uniform(0, 3), bevel=0.025)
    obj = new_obj(name, bm)
    mossy = variant in ("moss", "rough")

    def classify(f, k):
        c = f.calc_center_median()
        if f.normal.z > 0.5:
            if variant == "plate":
                return METAL if c.z > 0.03 else DARK
            if c.z < 0.012:
                return MORTAR
            base = STONE[int(k * 4) % 4]
            if variant == "scorched":
                return vary(SOOT, k)
            if variant == "rough":
                return vary(lin(0x8a7b62), k)
            if variant == "moss":
                tint = (math.sin(c.x * 5.1 + seed) + math.sin(c.y * 4.3) + 2) / 4
                return tuple(a * (1 - tint * 0.8) + b * tint * 0.8 for a, b in zip(vary(base, k), MOSS)) 
            return vary(base, k)
        return DARK if f.normal.z > -0.5 else DARK

    colourise(obj, classify, seed)
    export([obj], name)


# ---------------------------------------------------------------- towers and walls
def wall_classify(f, k):
    if f.normal.z > 0.5:
        return TRIM
    c = f.calc_center_median()
    return vary(WALL[int(k * 3) % 3], k) if c.z > 0.02 else DARK


def tower(name, kind, seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    h = rng.uniform(1.9, 2.5)
    box(bm, (1.18, 1.18, 0.22), (0, 0, 0.11), bevel=0.02)
    box(bm, (1.02, 1.02, 0.14), (0, 0, 0.29), bevel=0.02)
    base = 0.36
    box(bm, (0.82, 0.82, h), (0, 0, base + h / 2), bevel=0.012)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (0.15, 0.15, h + 0.06), (sx * 0.43, sy * 0.43, base + h / 2), bevel=0.02)
            box(bm, (0.21, 0.21, 0.06), (sx * 0.43, sy * 0.43, base + h * 0.5), bevel=0.01)
            box(bm, (0.2, 0.2, 0.1), (sx * 0.43, sy * 0.43, base + 0.1), bevel=0.01)
    levels = max(2, int(h / 0.78))
    for i in range(levels):
        box(bm, (0.92, 0.92, 0.055), (0, 0, base + 0.82 + i * 0.64), bevel=0.01)  # string course
    box(bm, (0.98, 0.98, 0.1), (0, 0, base + h), bevel=0.02)  # corbel table
    # flying buttresses on the long sides
    for sx in (-1, 1):
        box(bm, (0.24, 0.16, 0.68), (sx * 0.55, 0, base + 0.34), bevel=0.02)
        box(bm, (0.26, 0.16, 0.12), (sx * 0.5, 0, base + 0.74), 0.0, bevel=0.02)
        slab = box(bm, (0.5, 0.12, 0.09), (sx * 0.5, 0, base + 1.0), bevel=0.01)
        bmesh.ops.rotate(bm, cent=(sx * 0.5, 0, base + 1.0), matrix=Matrix.Rotation(sx * 0.55, 3, "Y"), verts=slab)
    obj = new_obj(name + "_body", bm)
    cutters = []
    for i in range(levels):
        z = base + 0.5 + i * 0.64
        for face, pos in (("+Y", (0, 0.41, z)), ("-Y", (0, -0.41, z)), ("+X", (0.41, 0, z)), ("-X", (-0.41, 0, z))):
            cutters.append(arch_cutter(0.17, 0.3, 0.22, pos, face))
    boolean_cut(obj, cutters)
    top = base + h
    bm2 = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm2, (0.17, 0.17, 0.3), (sx * 0.42, sy * 0.42, top + 0.2), bevel=0.015)
            pyramid(bm2, 0.2, 0.32, (sx * 0.42, sy * 0.42, top + 0.35))
    parts = [obj]
    if kind == "spire":
        box(bm2, (0.62, 0.62, 0.55), (0, 0, top + 0.32), bevel=0.012)
        pyramid(bm2, 0.74, 1.25, (0, 0, top + 0.6))
        box(bm2, (0.04, 0.04, 0.34), (0, 0, top + 1.95))
    elif kind == "chimney":
        box(bm2, (0.26, 0.26, 0.95), (0.25, 0.25, top + 0.55), bevel=0.02)
        box(bm2, (0.34, 0.34, 0.09), (0.25, 0.25, top + 1.04), bevel=0.02)
    elif kind == "ruined":
        # a jagged, collapsed top: scatter broken blocks and lop the pinnacles
        for i in range(6):
            box(bm2, (rng.uniform(0.15, 0.3), rng.uniform(0.15, 0.3), rng.uniform(0.15, 0.4)), (rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), top + 0.1), rng.uniform(0, 3), bevel=0.02)
    head = new_obj(name + "_head", bm2)
    parts.append(head)
    obj = join(parts, name)
    if kind == "chimney":
        bpy.ops.object.empty_add(location=(0.25, 0.25, top + 1.12))
        anchor = bpy.context.object
        anchor.name = "smoke"
        anchor.parent = obj
        anchor.matrix_parent_inverse = obj.matrix_world.inverted()

    def classify(f, k):
        c = f.calc_center_median()
        if f.normal.z > 0.5 and c.z > top + 0.3:
            return ROOF
        if c.z > top + 0.2 and abs(f.normal.z) < 0.5 and kind == "spire" and c.z > top + 0.75:
            return vary(ROOF, k)
        return wall_classify(f, k)

    colourise(obj, classify, seed, ao_len=0.4)
    export([obj] + ([anchor] if kind == "chimney" else []), name)


def wall(name, length, seed, kind="arched"):
    rng = random.Random(seed)
    bm = bmesh.new()
    bays = max(2, round(length / 0.75))
    seg = length / bays
    box(bm, (length + 0.1, 0.44, 0.16), (0, 0, 0.08), bevel=0.02)
    cutters = []
    for i in range(bays):
        x = -length / 2 + seg * (i + 0.5)
        hh = rng.uniform(0.8, 1.7) if kind != "low" else rng.uniform(0.35, 0.6)
        box(bm, (seg, 0.3, hh), (x, 0, 0.16 + hh / 2), bevel=0.012)
        box(bm, (0.13, 0.4, hh + 0.12), (x - seg / 2, 0, 0.16 + hh / 2 + 0.04), bevel=0.02)  # pier
        if kind != "low" and hh > 1.0:
            for s in (1, -1):
                cutters.append(arch_cutter(0.2, 0.38, 0.5, (x, 0, 0.16 + hh * 0.38), "+Y" if s > 0 else "-Y"))
        box(bm, (0.12, 0.2, 0.22), (x + seg * 0.2, rng.uniform(-0.4, 0.4), 0.11 + 0.1), rng.uniform(0, 3), bevel=0.02)  # fallen blocks
    box(bm, (0.13, 0.4, 0.9), (length / 2, 0, 0.16 + 0.45), bevel=0.02)
    obj = new_obj(name, bm)
    boolean_cut(obj, cutters)
    colourise(obj, wall_classify, seed, ao_len=0.4)
    export([obj], name)


def crate(name, seed):
    bm = bmesh.new()
    box(bm, (0.5, 0.5, 0.5), (0, 0, 0.25), bevel=0.02)
    for s in (-1, 1):
        box(bm, (0.54, 0.07, 0.54), (0, s * 0.22, 0.25), bevel=0.01)
        box(bm, (0.07, 0.54, 0.54), (s * 0.22, 0, 0.25), bevel=0.01)
    obj = new_obj(name, bm)

    def classify(f, k):
        return vary(WOOD, k) if f.normal.z > 0.5 or abs(f.calc_center_median().z - 0.25) < 0.3 else DARK

    colourise(obj, classify, seed, ao_len=0.3)
    export([obj], name)


def rubble_pile(name, seed):
    rng = random.Random(seed)
    bm = bmesh.new()
    for i in range(10):
        s = rng.uniform(0.1, 0.26)
        ang = rng.uniform(0, math.tau)
        d = rng.uniform(0, 0.5)
        box(bm, (s * 1.3, s, s * 0.8), (d * math.cos(ang), d * math.sin(ang), s * 0.3 + (0.12 if d < 0.2 else 0)), rng.uniform(0, 3), bevel=0.03)
    obj = new_obj(name, bm)
    colourise(obj, lambda f, k: vary(WALL[int(k * 3) % 3], k), seed, ao_len=0.3)
    export([obj], name)


def main():
    only = set(sys.argv[sys.argv.index("--only") + 1:]) if "--only" in sys.argv else None

    def want(n):
        return not only or n in only

    for i, (variant, seed) in enumerate([("plain", 1), ("plain", 2), ("cracked", 3), ("slab", 4), ("moss", 5), ("rough", 6), ("rubble", 7), ("plate", 8), ("scorched", 9)]):
        n = f"tile_{variant}_{seed}"
        if want(n):
            clean()
            tile(n, variant, seed)
    for n, kind, seed in [("tower_spire", "spire", 11), ("tower_chimney", "chimney", 12), ("tower_ruined", "ruined", 13)]:
        if want(n):
            clean()
            tower(n, kind, seed)
    for n, length, seed, kind in [("wall_arched", 1.5, 21, "arched"), ("wall_long", 2.25, 22, "arched"), ("wall_low", 1.5, 23, "low")]:
        if want(n):
            clean()
            wall(n, length, seed, kind)
    if want("crate"):
        clean()
        crate("crate", 31)
    if want("rubble_pile"):
        clean()
        rubble_pile("rubble_pile", 32)


if __name__ == "__main__":
    main()
