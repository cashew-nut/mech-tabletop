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

sys.path.insert(0, str(Path(__file__).parent))
from masonry import (  # noqa: E402
    BED, BRICK, CORE, DIRT, GLOW as K_GLOW, METAL as K_METAL, MOSS as K_MOSS, ROOF as K_ROOF, SLAB, SOOT as K_SOOT, TRIM as K_TRIM, WINDOW,
    Face, TaggedMesh, coursed, crack, flagstones, lancet, lancet_hole, string_course,
)

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
    tags = bm.faces.layers.int.get("kind")
    dirs = []
    for i in range(rays):  # fibonacci hemisphere around +Z
        z = (i + 0.5) / rays
        r = math.sqrt(1 - z * z)
        a = i * 2.399963
        dirs.append(Vector((r * math.cos(a), r * math.sin(a), z)))
    face_rng = {}
    for f in bm.faces:
        face_rng[f.index] = rng.random()
        base = classify(f, face_rng[f.index], f[tags] if tags else 0)
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


# ---------------------------------------------------------------- colour
WINDOW_DARK = lin(0x121318)
DIRT_C = lin(0x6e5c45)


def kind_colour(f, tag, soot_above=None):
    """Colour for a tagged face: one shade per brick or slab, so stones read as separate blocks."""
    kind, pid = divmod(tag, 1000)
    h = random.Random(pid * 7919 + kind).random()
    up = f.normal.z > 0.5
    c = f.calc_center_median()
    if kind == BRICK:
        col = vary(WALL[pid % 3], h)
    elif kind == K_TRIM:
        col = vary(TRIM, 0.35 + h * 0.3)
    elif kind == WINDOW:
        return WINDOW_DARK
    elif kind == K_ROOF:
        col = vary(ROOF, h)
    elif kind == SLAB:
        col = vary(STONE[pid % 4], 0.3 + h * 0.4)  # flagstones vary less than masonry, so the paving reads calm
    elif kind == K_MOSS:
        base = vary(STONE[pid % 4], h)
        col = tuple(a * 0.45 + b * 0.55 for a, b in zip(base, MOSS))
    elif kind == DIRT:
        col = vary(DIRT_C, h)
    elif kind == K_METAL:
        col = vary(METAL, 0.5)
    elif kind == K_GLOW:
        return GLOW
    elif kind == K_SOOT:
        col = vary(SOOT, h)
    elif kind == BED:
        return MORTAR if up else DARK
    elif kind == CORE:
        col = MORTAR
    else:
        col = DARK
    if kind in (SLAB, K_MOSS, DIRT, K_SOOT) and not up:
        col = tuple(x * 0.72 for x in col[:3])
    if soot_above is not None and kind in (BRICK, K_TRIM) and c.z > soot_above:
        t = min(1.0, (c.z - soot_above) / 0.6)
        col = tuple(a * (1 - t * 0.75) + b * t * 0.75 for a, b in zip(col[:3], SOOT))
    return tuple(col[:3]) + (1.0,)


# ---------------------------------------------------------------- tiles
def hex_poly(r):
    return [(r * math.cos(math.radians(30 + 60 * k)), r * math.sin(math.radians(30 + 60 * k))) for k in range(6)]


TILE_SPECS = {
    "plain": dict(rows=(0.34, 0.48), widths=(0.3, 0.62)),
    "cracked": dict(rows=(0.34, 0.5), widths=(0.32, 0.66)),
    "slab": dict(rows=(0.62, 0.9), widths=(0.6, 1.0)),
    "moss": dict(rows=(0.32, 0.46), widths=(0.28, 0.58)),
    "rough": dict(rows=(0.3, 0.44), widths=(0.26, 0.5)),
    "rubble": dict(rows=(0.34, 0.48), widths=(0.3, 0.62)),
    "scorched": dict(rows=(0.34, 0.48), widths=(0.3, 0.62)),
}


def tile(name, variant, seed):
    rng = random.Random(seed)
    m = TaggedMesh()
    bed_kind = DIRT if variant == "rough" else (K_SOOT if variant == "scorched" else BED)
    m.prism(hex_poly(TILE_R), -TILE_DEPTH, 0.0, chamfer=0.025, kind=bed_kind)
    if variant == "plate":
        # a riveted steel plate with a raised rim, like the grey hex in the concept art
        m.prism(hex_poly(TILE_R - 0.06), 0.0, 0.05, chamfer=0.02, kind=K_METAL)
        m.prism(hex_poly(TILE_R - 0.2), 0.05, 0.065, chamfer=0.01, kind=K_METAL)
        for k in range(6):
            a = math.radians(30 + 60 * k)
            for rr in (0.74,):
                ring = [(rr * math.cos(a) + 0.03 * math.cos(t), rr * math.sin(a) + 0.03 * math.sin(t)) for t in (i * math.tau / 6 for i in range(6))]
                m.prism(ring, 0.05, 0.075, chamfer=0.008, kind=K_METAL)
    else:
        spec = TILE_SPECS[variant]
        stones = flagstones(rng, TILE_R - 0.04, angle=rng.choice([0.0, math.pi / 6, math.pi / 2, -math.pi / 6]), **spec)
        for poly in stones:
            if variant == "rough" and rng.random() < 0.35:
                continue  # missing stones leave bare earth
            pieces = crack(poly, rng) if (variant == "cracked" and rng.random() < 0.45) or (variant in ("rough", "rubble") and rng.random() < 0.2) else [poly]
            kind = {"moss": K_MOSS if rng.random() < 0.5 else SLAB, "scorched": K_SOOT}.get(variant, SLAB)
            for piece in pieces:
                top = rng.uniform(0.035, 0.055) - (rng.uniform(0.0, 0.02) if variant == "rough" else 0.0)
                m.prism(piece, -0.01, top, chamfer=0.012, kind=kind)
        if variant in ("moss", "rough"):
            for _ in range(10 if variant == "moss" else 5):  # tufts of moss and weeds in the seams
                ang, d = rng.uniform(0, math.tau), rng.uniform(0, 0.75)
                x, y = d * math.cos(ang), d * math.sin(ang)
                s2 = rng.uniform(0.03, 0.06)
                m.prism([(x - s2, y - s2 * 0.6), (x + s2, y - s2 * 0.6), (x + s2 * 0.7, y + s2), (x - s2 * 0.7, y + s2)], 0.0, 0.03, kind=K_MOSS)
        if variant in ("rough", "rubble"):
            for _ in range(6 if variant == "rough" else 9):
                ang, d = rng.uniform(0, math.tau), rng.uniform(0.05, 0.7)
                sz = rng.uniform(0.06, 0.16) if variant == "rubble" else rng.uniform(0.03, 0.06)
                m.box((sz * 1.3, sz, sz * 0.8), Vector((d * math.cos(ang), d * math.sin(ang), sz * 0.35 + 0.02)), Matrix.Rotation(rng.uniform(0, 3), 3, "Z"), BRICK)
    obj = new_obj(name, m.bm)
    colourise(obj, lambda f, k, tag: kind_colour(f, tag), seed, ao_len=0.3, ao_strength=0.4)
    export([obj], name)


# ---------------------------------------------------------------- towers and walls
def square_faces(width, depth):
    """The four outward faces of a square core of the given width centred on the origin."""
    faces = []
    for n in (Vector((0, 1, 0)), Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((-1, 0, 0))):
        wide = abs(n.y) > 0.5  # the Y faces run long so their stones cover the corners
        faces.append(Face(n * (width / 2), n.cross(Vector((0, 0, 1))), n, width + (2 * depth if wide else 0)))
    return faces


def shaft(m, rng, width, z0, z1, tiers, depth=0.045, top=None, win=(0.2, 0.42), mullion=True, quoins=True):
    """A square masonry shaft with a lancet per face on each tier and a string course above it."""
    zc = z1 if top is None else min(top(x / 10) for x in range(-5, 6)) - 0.05  # keep the core under a ragged top
    m.box((width, width, zc - z0), Vector((0, 0, (z0 + zc) / 2)), kind=CORE)
    for face in square_faces(width, depth):
        holes = [lancet_hole(0.0, tz - 0.05, win[0] + 0.09, win[1] + 0.06) for tz in tiers]
        coursed(m, face, z1, rng, depth=depth, holes=holes, top=top, z0=z0, quoins=quoins, brick=(0.14, 0.24))
        for tz in tiers:
            if top is None or top(0.0) > tz + win[1] + win[0] * 0.7:
                lancet(m, face, 0.0, tz, win[0], win[1], depth, mullion=mullion)
                string_course(m, face, tz + win[1] + win[0] * 0.62 + 0.13, depth)
        string_course(m, face, z0 + 0.02, depth + 0.02)


def tower(name, kind, seed):
    rng = random.Random(seed)
    m = TaggedMesh()
    W = 0.84
    # stepped plinth
    m.box((1.22, 1.22, 0.16), Vector((0, 0, 0.08)), kind=K_TRIM)
    m.box((1.08, 1.08, 0.14), Vector((0, 0, 0.23)), kind=BRICK)
    base = 0.3
    soot = None
    anchor = None
    if kind == "chimney":
        # a squat furnace house carrying a tall soot-blackened stack, like the stacks in the concept art
        bh = base + 0.95
        shaft(m, rng, 0.9, base, bh, tiers=[base + 0.25], win=(0.22, 0.34))
        for face in square_faces(0.9, 0.045):
            string_course(m, face, bh, 0.06)
        sw, top = 0.46, bh + 2.2
        shaft(m, rng, sw, bh, top, tiers=[bh + 0.6, bh + 1.4], win=(0.07, 0.24), mullion=False, quoins=False)
        for face in square_faces(sw, 0.04):
            string_course(m, face, top - 0.02, 0.08, extra=0.08)
        m.box((sw + 0.18, sw + 0.18, 0.09), Vector((0, 0, top + 0.07)), kind=K_SOOT)
        m.box((sw - 0.06, sw - 0.06, 0.03), Vector((0, 0, top + 0.115)), kind=K_GLOW)
        soot = top - 0.9
        anchor = (0.0, 0.0, top + 0.14)
    else:
        h = rng.uniform(2.0, 2.3)
        top_z = base + h
        ragged = None
        if kind == "ruined":
            # a collapsed crown: the courses stop along a jagged line
            notch = rng.uniform(-0.2, 0.2)
            ragged = lambda x: top_z - 0.25 - 0.55 * max(0.0, 1 - abs(x - notch) / 0.3) - 0.08 * math.sin(x * 23 + seed)  # noqa: E731
        shaft(m, rng, W, base, top_z, tiers=[base + 0.45, base + 1.3], top=ragged)
        if kind == "spire":
            for face in square_faces(W, 0.045):
                string_course(m, face, top_z - 0.06, 0.1, extra=0.14)  # cornice
            for sx in (-1, 1):
                for sy in (-1, 1):
                    m.box((0.15, 0.15, 0.34), Vector((sx * 0.45, sy * 0.45, top_z + 0.17)), kind=K_TRIM)
                    m.pyramid(0.17, 0.32, (sx * 0.45, sy * 0.45, top_z + 0.34), kind=K_ROOF)
            bw = 0.56  # belfry with a small lancet on each face
            shaft(m, rng, bw, top_z, top_z + 0.55, tiers=[top_z + 0.1], win=(0.12, 0.24), quoins=False)
            for face in square_faces(bw, 0.04):
                string_course(m, face, top_z + 0.53, 0.07, extra=0.08)
            m.pyramid(bw + 0.14, 1.35, (0, 0, top_z + 0.58), kind=K_ROOF)
            for sx in (-1, 1):  # gablets at the foot of the spire
                for axis in ("x", "y"):
                    pos = (sx * (bw / 2 + 0.02), 0, top_z + 0.6) if axis == "x" else (0, sx * (bw / 2 + 0.02), top_z + 0.6)
                    m.pyramid(0.16, 0.3, pos, kind=K_ROOF)
            m.box((0.035, 0.035, 0.36), Vector((0, 0, top_z + 2.05)), kind=K_SOOT)
            m.box((0.16, 0.035, 0.035), Vector((0, 0, top_z + 2.12)), kind=K_SOOT)
        else:
            for _ in range(7):  # fallen masonry round the foot and on the broken top
                sz = rng.uniform(0.1, 0.2)
                ang = rng.uniform(0, math.tau)
                d = rng.uniform(0.62, 0.85)
                m.box((sz * 1.4, sz, sz * 0.8), Vector((d * math.cos(ang), d * math.sin(ang), sz * 0.4)), Matrix.Rotation(rng.uniform(0, 3), 3, "Z"), BRICK)
    obj = new_obj(name, m.bm)
    objs = [obj]
    if anchor:
        bpy.ops.object.empty_add(location=anchor)
        empty = bpy.context.object
        empty.name = "smoke"
        empty.parent = obj
        objs.append(empty)
    colourise(obj, lambda f, k, tag: kind_colour(f, tag, soot), seed, ao_len=0.35, ao_strength=0.5)
    export(objs, name)


def wall(name, length, seed, kind="arched"):
    """A free-standing ruined wall: two leaves of coursed stone, buttresses between bays, lancets right through it."""
    rng = random.Random(seed)
    m = TaggedMesh()
    T = 0.24
    bays = max(2, round(length / 0.75))
    bay = length / bays
    heights = [rng.uniform(1.15, 1.75) if kind != "low" else rng.uniform(0.35, 0.65) for _ in range(bays)]
    heights[rng.randrange(bays)] *= 0.62 if kind != "low" else 1.0  # one bay has fallen further

    def top_world(x):
        i = min(bays - 1, max(0, int((x + length / 2) / bay)))
        return 0.12 + heights[i] - 0.1 * abs(math.sin(x * 17 + seed)) - 0.06 * math.sin(x * 41)

    m.box((length + 0.12, T + 0.14, 0.12), Vector((0, 0, 0.06)), kind=K_TRIM)
    centres = [-length / 2 + bay * (i + 0.5) for i in range(bays)]
    windows = [(x, 0.42) for x, hgt in zip(centres, heights) if kind != "low" and hgt > 1.05]
    for side in (1, -1):
        n = Vector((0, side, 0))
        face = Face(Vector((0, 0, 0)), n.cross(Vector((0, 0, 1))), n, length)
        sx = face.u.x  # +1 or -1: local x runs along world x or against it
        holes = [lancet_hole(wx * sx, wz - 0.05, 0.33, 0.61) for wx, wz in windows]
        coursed(m, face, 2.2, rng, depth=T / 2, holes=holes, top=lambda x: top_world(x * sx), z0=0.12, brick=(0.16, 0.3))
        if side == 1:
            for wx, wz in windows:
                lancet(m, face, wx * sx, wz, 0.24, 0.55, T / 2, through=T / 2)
        # stepped buttresses between the bays and at the ends
        for i in range(bays + 1):
            x = -length / 2 + bay * i
            hb = min(top_world(x - 0.05), top_world(x + 0.05)) - 0.12
            if hb < 0.3:
                continue
            fb = face_basis_world(n)
            m.box((0.17, 0.2, hb * 0.6), Vector((x, side * (T / 2 + 0.1), 0.12 + hb * 0.3)), fb, BRICK)
            m.box((0.13, 0.12, hb * 0.38), Vector((x, side * (T / 2 + 0.06), 0.12 + hb * 0.6 + hb * 0.19)), fb, BRICK)
            m.box((0.19, 0.24, 0.05), Vector((x, side * (T / 2 + 0.11), 0.12 + hb * 0.6 + 0.02)), fb, K_TRIM)
    for _ in range(5 if kind != "low" else 3):  # fallen blocks at the foot
        sz = rng.uniform(0.08, 0.18)
        m.box((sz * 1.5, sz, sz * 0.8), Vector((rng.uniform(-length / 2, length / 2), rng.choice((-1, 1)) * rng.uniform(0.25, 0.5), sz * 0.4)), Matrix.Rotation(rng.uniform(0, 3), 3, "Z"), BRICK)
    obj = new_obj(name, m.bm)
    colourise(obj, lambda f, k, tag: kind_colour(f, tag), seed, ao_len=0.35, ao_strength=0.5)
    export([obj], name)


def face_basis_world(n):
    return Matrix.Identity(3)


def crate(name, seed):
    bm = bmesh.new()
    box(bm, (0.5, 0.5, 0.5), (0, 0, 0.25), bevel=0.02)
    for s in (-1, 1):
        box(bm, (0.54, 0.07, 0.54), (0, s * 0.22, 0.25), bevel=0.01)
        box(bm, (0.07, 0.54, 0.54), (s * 0.22, 0, 0.25), bevel=0.01)
    obj = new_obj(name, bm)

    def classify(f, k, tag):
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
    colourise(obj, lambda f, k, tag: vary(WALL[int(k * 3) % 3], k), seed, ao_len=0.3)
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
