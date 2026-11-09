"""Turn a model's closed parts into finished Blender parts, and assemble them (step 3 of 3; needs bpy).

    ~/bvenv/bin/python -I build.py WORK OUT [part ...] [--size 1024] [--no-bake]

Reads WORK/kit/*.npz (joints.py) and the Meshy textures in WORK (tex_0..2.jpg). For every part:

  * the full-resolution solid (Meshy's surface plus the cut caps, pegs and holes) is the bake source;
  * a print copy is simplified with manifold (still closed) and written as OUT/stl/<part>.stl;
  * a game copy is decimated, unwrapped with xatlas, and Cycles bakes colour, roughness, metallic and normals onto it
    from the source. Cut caps, pegs and holes bake as dark gunmetal, so a part on its own reads as finished;
  * its origin is moved to its joint (the kit convention), and it is written as OUT/glb/<part>.glb.

Then OUT/<model>_composite.blend holds every part, the right side mirrored from the left, parented joint to joint
(pelvis > torso > pauldron > arm > forearm > hand > blade, and so on), so rotating a part in Blender swings
everything below it. `render.py` makes the review renders from that file.
"""
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))           # assets/blender, for kit
from layout import M, NAME, PS, TREE, SIDED, LOADOUT, NATIVE_RIGHT, SIDE_OF, joint  # noqa: E402

BUDGET = M.BUDGET         # part: (game triangles, texture size)
GAME_SCALE = PS           # print size / kit size: the .blend and STLs are print size, the game GLBs kit size
RAY = getattr(M, "RAY", PS)   # bake ray reach, relative to the Paladin's (the decimated copy strays further on bigger parts)
PRINT_TOL = 0.015       # mm, manifold simplify tolerance for the print copies
GUNMETAL = ((0.035, 0.035, 0.04), 0.42, 1.0)        # colour, roughness, metallic of cut faces, pegs and holes
GOLD = getattr(M, "KNUCKLE_FINISH", ((0.56, 0.40, 0.18), 0.30, 1.0))   # designed knuckles and struts
NORMAL_PX = getattr(M, "NORMAL_SIZE", 512)    # game normal map size cap (the base colour is BUDGET's size)
ORM_PX = getattr(M, "ORM_SIZE", 256)          # game occlusion/roughness/metal map size
# A model may bake an emissive map (brute_polish.py): M.glow_weight(P) marks where, imgs["glow"] says what colour.
GLOW_STRENGTH = getattr(M, "GLOW_STRENGTH", 1.0)
FRAME = getattr(M, "FRAME_FINISH", GUNMETAL)       # designed frame metal (the Seer's bronze knuckle housings): UV (-3, -3)
# Designed surfaces (cuts, knuckles, frame) are flat colours. With DESIGNED_WEAR they get what Meshy's own texture has:
# darker crevices (ambient occlusion over the part's own geometry, within WEAR_AO mm) and a faint mottle, so a gold band
# next to Meshy's gilding does not read as new plastic.
WEAR = getattr(M, "DESIGNED_WEAR", False)
WEAR_AO = getattr(M, "WEAR_AO", 0.6)
# With SHARP_DESIGNED (degrees), the bake source gets sharp edges where a designed face meets another face at more than
# that angle. A designed solid (knuckle housing, band, cut face) is a few long side triangles between hard rims: smooth
# shading averaged the rims' normals down those triangles and baked bright streaks into the normal map. Meshy's own
# surface keeps its smooth shading, and the game mesh is unchanged (the normal map carries the crisp rims).
SHARP = getattr(M, "SHARP_DESIGNED", None)
# ROUGH_FLOOR: the baked roughness never goes below this. Meshy's maps can be near mirror-smooth (the Seer's chest plate:
# median 0.29, a quarter under 0.1), which the game's bloom turned into white glare.
ROUGH_FLOOR = getattr(M, "ROUGH_FLOOR", None)


def load_solid(path):
    d = np.load(path)
    P, T = d["P"], d["T"]
    idx = np.arange(len(P))
    idx[d["mf"]] = d["mt"]
    used, inv = np.unique(idx[T], return_inverse=True)
    return P, T, used, inv.reshape(-1, 3)


def make_mesh(name, P, T, used, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata(P[used, :3].tolist(), [], faces.tolist())
    uv = P[T.ravel(), 3:5].astype(np.float32).copy()
    cap = (np.abs(P[T, 3] + 1) < 0.5).all(1)       # cut faces, pegs and holes: UV (-1, -1)
    knuckle = (np.abs(P[T, 3] + 2) < 0.5).all(1)   # designed knuckles and struts (seer.py): UV (-2, -2)
    frame = (np.abs(P[T, 3] + 3) < 0.5).all(1)     # designed frame metal (seer.py's knuckle housings): UV (-3, -3)
    uv[:, 1] = 1 - uv[:, 1]
    me.uv_layers.new(name="UVHigh").data.foreach_set("uv", uv.ravel())
    me.polygons.foreach_set("material_index", (cap * 1 + knuckle * 2 + frame * 3).astype(np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
    if hasattr(M, "glow_weight"):       # where the emissive bake shows the glow texture (0 to 1 per vertex)
        w = np.asarray(M.glow_weight(P[used, :3]), np.float32)
        me.attributes.new("glow", "FLOAT", "POINT").data.foreach_set("value", w)
        me["glow_max"] = float(w.max()) if len(w) else 0.0
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, cap


def sharpen(ob):
    """Sharp edges (SHARP) on the bake source where a designed face meets another at more than SHARP degrees."""
    if not SHARP:
        return
    me = ob.data
    me.set_sharp_from_angle(angle=math.radians(SHARP))
    n = len(me.polygons)
    mat, total = np.empty(n, np.int32), np.empty(n, np.int32)
    me.polygons.foreach_get("material_index", mat)
    me.polygons.foreach_get("loop_total", total)
    edge = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("edge_index", edge)
    designed = np.zeros(len(me.edges), bool)
    np.logical_or.at(designed, edge, np.repeat(mat > 0, total))      # loops run polygon by polygon
    attr = me.attributes.get("sharp_edge")
    sharp = np.zeros(len(me.edges), bool)
    if attr is not None:
        attr.data.foreach_get("value", sharp)
    else:
        attr = me.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    attr.data.foreach_set("value", sharp & designed)


def write_stl(path, P, T):
    """Simplify the closed solid with manifold (it stays closed) and write a binary STL."""
    import manifold3d as mf
    d = np.load(path)
    m = mf.Manifold(mf.Mesh(vert_properties=d["P"][:, :3].astype(np.float32), tri_verts=d["T"].astype(np.uint32),
                            merge_from_vert=d["mf"].astype(np.uint32), merge_to_vert=d["mt"].astype(np.uint32)))
    m = m.simplify(PRINT_TOL)
    keep = [p for p in m.decompose() if p.volume() > 0.2]     # slivers the simplify split off
    m = mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]
    mm = m.to_mesh()
    V, F = np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts)
    return V, F, m


def stl_bytes(V, F):
    tri = V[F].astype(np.float32)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    rec = np.zeros(len(F), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    return f"composite {NAME} part, mm".encode().ljust(80, b" ") + np.uint32(len(F)).tobytes() + rec.tobytes()


def wear(N, L, value, mode):
    """A designed surface's flat value with wear (WEAR): cavities darkened and a faint mottle in colour, a little roughness
    noise. Returns the socket to emit."""
    if not WEAR or mode in ("metal", "emit"):
        return None
    tc = N.new("ShaderNodeTexCoord")
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.9            # print mm: blotches about a millimetre across
    noise.inputs["Detail"].default_value = 6.0
    L.new(tc.outputs["Object"], noise.inputs["Vector"])
    mot = N.new("ShaderNodeMapRange")                     # noise 0.3..0.7 -> 0.86..1.10
    mot.inputs["From Min"].default_value, mot.inputs["From Max"].default_value = 0.3, 0.7
    mot.inputs["To Min"].default_value, mot.inputs["To Max"].default_value = (0.86, 1.10) if mode == "color" else (0.85, 1.2)
    L.new(noise.outputs["Fac"], mot.inputs["Value"])
    mul = N.new("ShaderNodeMix")
    mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    mul.inputs[6].default_value = value
    L.new(mot.outputs["Result"], mul.inputs[7])
    if mode != "color":
        return mul.outputs[2]
    ao = N.new("ShaderNodeAmbientOcclusion")
    ao.only_local = True                                  # the part's own geometry, not the game copy it is baked onto
    ao.samples = 32
    ao.inputs["Distance"].default_value = WEAR_AO
    cav = N.new("ShaderNodeMapRange")                     # fully open 1.0, a closed crevice 0.35
    cav.inputs["To Min"].default_value, cav.inputs["To Max"].default_value = 0.35, 1.0
    L.new(ao.outputs["AO"], cav.inputs["Value"])
    mul2 = N.new("ShaderNodeMix")
    mul2.data_type, mul2.blend_type = "RGBA", "MULTIPLY"
    mul2.inputs[0].default_value = 1.0
    L.new(mul.outputs[2], mul2.inputs[6])
    L.new(cav.outputs["Result"], mul2.inputs[7])
    return mul2.outputs[2]


def high_materials(imgs):
    """Bake-source materials per channel: Meshy's textures on the surface (slot 0), gunmetal on cuts (slot 1), the designed
    knuckles' gold (slot 2) and frame metal (slot 3)."""
    finish = {"cut": GUNMETAL, "knuckle": GOLD, "frame": FRAME}
    mats = {}
    for mode in ("color", "rough", "metal", "normal") + (("emit",) if "glow" in imgs else ()):
        pair = []
        for slot in ("meshy", "cut", "knuckle", "frame"):
            m = bpy.data.materials.new(f"high_{mode}_{slot}")
            m.use_nodes = True
            N, L = m.node_tree.nodes, m.node_tree.links
            N.clear()
            out = N.new("ShaderNodeOutputMaterial")
            if slot in finish:
                if mode == "normal":
                    L.new(N.new("ShaderNodeBsdfPrincipled").outputs["BSDF"], out.inputs["Surface"])
                else:
                    em = N.new("ShaderNodeEmission")
                    col, rough, metal = finish[slot]
                    v = {"color": (*col, 1), "rough": (rough,) * 3 + (1,), "metal": (metal,) * 3 + (1,),
                         "emit": (0, 0, 0, 1)}[mode]
                    em.inputs["Color"].default_value = v
                    worn = wear(N, L, v, mode)
                    if worn is not None:
                        L.new(worn, em.inputs["Color"])
                    L.new(em.outputs["Emission"], out.inputs["Surface"])
                pair.append(m)
                continue
            uv = N.new("ShaderNodeUVMap")
            uv.uv_map = "UVHigh"

            def tex(img):
                t = N.new("ShaderNodeTexImage")
                t.image = img
                L.new(uv.outputs["UV"], t.inputs["Vector"])
                return t
            if mode == "normal":
                b = N.new("ShaderNodeBsdfPrincipled")
                nm = N.new("ShaderNodeNormalMap")
                nm.uv_map = "UVHigh"
                L.new(tex(imgs["nrm"]).outputs["Color"], nm.inputs["Color"])
                L.new(nm.outputs["Normal"], b.inputs["Normal"])
                L.new(b.outputs["BSDF"], out.inputs["Surface"])
            else:
                em = N.new("ShaderNodeEmission")
                if mode == "color":
                    L.new(tex(imgs["base"]).outputs["Color"], em.inputs["Color"])
                elif mode == "emit":        # the glow texture where the model's glow_weight says so, black elsewhere
                    at = N.new("ShaderNodeAttribute")
                    at.attribute_name = "glow"
                    mix = N.new("ShaderNodeMix")
                    mix.data_type = "RGBA"
                    mix.blend_type = "MULTIPLY"
                    mix.inputs[0].default_value = 1.0
                    L.new(tex(imgs["glow"]).outputs["Color"], mix.inputs[6])
                    L.new(at.outputs["Fac"], mix.inputs[7])
                    L.new(mix.outputs[2], em.inputs["Color"])
                else:
                    sep = N.new("ShaderNodeSeparateColor")
                    L.new(tex(imgs["mr"]).outputs["Color"], sep.inputs["Color"])
                    L.new(sep.outputs["Green" if mode == "rough" else "Blue"], em.inputs["Color"])
                L.new(em.outputs["Emission"], out.inputs["Surface"])
            pair.append(m)
        mats[mode] = pair
    return mats


def decimate(ob, target):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    m = ob.modifiers.new("tri", "TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=m.name)
    m = ob.modifiers.new("dec", "DECIMATE")
    m.ratio = min(1.0, target / max(1, len(ob.data.polygons)))
    m.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=m.name)


def unwrap(ob, size):
    """xatlas charts and packing; split seam vertices but keep the smooth normals."""
    import xatlas
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    vn = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("normal", vn)
    vn = vn.reshape(-1, 3)
    idx = np.empty(len(me.polygons) * 3, np.int32)
    me.polygons.foreach_get("vertices", idx)
    atlas = xatlas.Atlas()
    atlas.add_mesh(co, idx.reshape(-1, 3).astype(np.uint32))
    co_opt = xatlas.ChartOptions()
    co_opt.max_cost = 4.0
    po = xatlas.PackOptions()
    po.resolution = size
    po.padding = 6
    po.bilinear = True
    atlas.generate(co_opt, po)
    vmap, nf, uv = atlas[0]
    me.clear_geometry()
    me.from_pydata(co[vmap].tolist(), [], nf.astype(np.int64).tolist())
    for l in list(me.uv_layers):
        me.uv_layers.remove(l)
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", uv[nf.ravel().astype(np.int64)].astype(np.float32).ravel())
    me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    me.normals_split_custom_set_from_vertices(vn[vmap].tolist())


def bake(hi, lo, mats, mode, size, name):
    from kit import bake as kb
    # swap the slots in place: materials.clear() would reset every face's slot to 0
    while len(hi.data.materials) < 4:
        hi.data.materials.append(None)
    for i, m in enumerate(mats[mode]):
        hi.data.materials[i] = m
    img = kb._image(f"{name}_{mode}", size, mode not in ("color", "emit"))
    lo.data.materials.clear()
    m = bpy.data.materials.new(f"lo_{name}_{mode}")
    m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = img
    m.node_tree.nodes.active = t
    lo.data.materials.append(m)
    bpy.ops.object.select_all(action="DESELECT")
    hi.select_set(True)
    lo.select_set(True)
    bpy.context.view_layer.objects.active = lo
    kw = dict(type="NORMAL" if mode == "normal" else "EMIT", use_selected_to_active=True, cage_extrusion=0.5 * RAY,
              max_ray_distance=1.0 * RAY, margin=6, use_clear=True)
    if mode == "normal":
        kw["normal_space"] = "TANGENT"
    bpy.ops.object.bake(**kw)
    return img


def build_part(k, work, out, mats, size_override, do_bake):
    import kit
    from kit import bake as kb
    from PIL import Image
    t0 = time.time()
    src = work / "kit" / f"{k}.npz"
    target, size = BUDGET[k]
    size = size_override or size
    # print copy
    V, F, m = write_stl(src, None, None)
    (out / "stl").mkdir(parents=True, exist_ok=True)
    (out / "stl" / f"{k}.stl").write_bytes(stl_bytes(V, F))
    stl_info = {"tris": int(len(F)), "volume_mm3": round(m.volume(), 1), "closed": m.status().name == "NoError",
                "pieces": len(m.decompose()), "size_mm": [round(float(v), 1) for v in (V.max(0) - V.min(0))]}
    # bake source and game copy
    P, T, used, faces = load_solid(src)
    hi, cap = make_mesh(f"{k}_hi", P, T, used, faces)
    lo = bpy.data.objects.new(k, hi.data.copy())
    bpy.context.scene.collection.objects.link(lo)
    sharpen(hi)
    decimate(lo, target)
    unwrap(lo, size)
    if do_bake:
        imgs = {mode: bake(hi, lo, mats, mode, size, k) for mode in ("color", "rough", "metal", "normal")}
        glows = "emit" in mats and hi.data.get("glow_max", 0.0) > 0.01
        if glows:       # only parts that carry some of the glow regions get an emissive map
            imgs["emit"] = bake(hi, lo, mats, "emit", size, k)
            px = np.empty(size * size * 4, np.float32)
            imgs["emit"].pixels.foreach_get(px)
            if px.reshape(-1, 4)[:, :3].max() < 1 / 255:     # in a glow region but nothing there is lit
                del imgs["emit"]

        def chan(img):
            a = np.empty(size * size * 4, np.float32)
            img.pixels.foreach_get(a)
            return a.reshape(size, size, 4)[..., 0]
        rough = chan(imgs["rough"])
        if ROUGH_FLOOR:
            rough = np.maximum(rough, ROUGH_FLOOR)
        orm = np.stack([np.ones((size, size), np.float32), rough, chan(imgs["metal"]), np.ones((size, size), np.float32)], -1)
        io = kb._image(f"{k}_orm", size, True)
        io.pixels.foreach_set(orm.ravel())
        tdir = out / "textures"
        tdir.mkdir(parents=True, exist_ok=True)
        paths = {}
        for key, img in (("basecolor", imgs["color"]), ("orm", io), ("normal", imgs["normal"]),
                         ("emissive", imgs.get("emit"))):
            if img is None:
                continue
            p = tdir / f"{k}_{key}.png"
            kb._save(img, p)
            paths[key] = p
        for key, sz in (("normal", min(size, NORMAL_PX)), ("orm", min(size, ORM_PX)), ("emissive", min(size, 512))):
            if key in paths:
                Image.open(paths[key]).convert("RGB").resize((sz, sz), Image.LANCZOS).save(paths[key])
        tex = {}
        for key, p in paths.items():
            im = bpy.data.images.load(str(p), check_existing=False)
            im.colorspace_settings.name = "sRGB" if key in ("basecolor", "emissive") else "Non-Color"
            tex[key] = im
        mat = kb.baked_material(f"hull_{k}_livery", tex["basecolor"], tex["orm"], tex["normal"])
        if "emissive" in tex:       # the glTF exporter writes emissiveTexture and KHR_materials_emissive_strength
            N, L = mat.node_tree.nodes, mat.node_tree.links
            te = N.new("ShaderNodeTexImage")
            te.image = tex["emissive"]
            uvn = next(n for n in N if n.bl_idname == "ShaderNodeUVMap")
            L.new(uvn.outputs["UV"], te.inputs["Vector"])
            bsdf = N["Principled BSDF"]
            L.new(te.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = GLOW_STRENGTH
    else:
        mat = bpy.data.materials.new(f"plain_{k}")
    lo.data.materials.clear()
    lo.data.materials.append(mat)
    bpy.data.objects.remove(hi)
    # origin at the joint (a native right-hand part's is on the right)
    j = Vector(joint(TREE[k][1], SIDE_OF.get(k, "L")))
    lo.data.transform(Matrix.Translation(-j))
    lo.location = j
    print(f"== {k}: game {len(lo.data.polygons)} tris {size}px, print {len(F)} tris, {time.time() - t0:.0f}s", flush=True)
    return lo, stl_info


def assemble(objs):
    """Duplicate sided parts as mirrored right-hand copies and parent everything joint to joint."""
    placed = {}
    native_for = {like: k for k, like in NATIVE_RIGHT.items() if k in objs}
    for k, ob in objs.items():
        if k in NATIVE_RIGHT:
            continue        # placed as its left part's right-hand copy, below
        if k in SIDED:
            ob.name = f"{k}_L"
            if k in native_for:     # the right side has its own part (the Paladin's pauldron with the long cape)
                r = objs[native_for[k]]
            else:
                r = bpy.data.objects.new(f"{k}_R", ob.data)
                bpy.context.scene.collection.objects.link(r)
                r.location = Vector(joint(TREE[k][1], "R"))
                r.scale = (-1, 1, 1)
            placed[(k, "L")], placed[(k, "R")] = ob, r
            side = LOADOUT.get(k)
            if side:        # the other side's copy is a spare: in the file, hidden, for swapping guns over
                spare = r if side == "L" else ob
                spare["spare"] = True
                spare.hide_render = True
                spare.hide_set(True)
        else:
            placed[(k, None)] = ob
    bpy.context.view_layer.update()
    for (k, side), ob in placed.items():
        parent = TREE[k][2]
        if isinstance(parent, tuple):
            parent = parent[0]
        if parent is None:
            continue
        p = placed.get((parent, side if parent in SIDED else None))
        if p is None:
            continue
        mw = ob.matrix_world.copy()
        ob.parent = p
        ob.matrix_parent_inverse = p.matrix_world.inverted()
        ob.matrix_world = mw
    return placed


def main(a):
    import kit
    work, out = Path(a[0]), Path(a[1])
    out.mkdir(parents=True, exist_ok=True)
    size_override = int(a[a.index("--size") + 1]) if "--size" in a else None
    only = [x for x in a[2:] if not x.startswith("--") and not x.isdigit()]
    do_bake = "--no-bake" not in a
    scene = kit.reset_scene()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    imgs = {}
    src = {"base": work / "tex_0.jpg", "mr": work / "tex_1.jpg", "nrm": work / "tex_2.jpg"}
    if hasattr(M, "surface_textures"):     # the model's own finish map and glow texture (brute_polish.py)
        src.update(M.surface_textures(work))
    for nm, path in src.items():
        im = bpy.data.images.load(str(path))
        im.colorspace_settings.name = "sRGB" if nm in ("base", "glow") else "Non-Color"
        imgs[nm] = im
    mats = high_materials(imgs)
    objs, info = {}, {}
    for k in TREE:
        if (only and k not in only) or not (work / "kit" / f"{k}.npz").exists():
            continue        # (the Brute's claw and rail come from their own builds, item_cut.py)
        objs[k], info[k] = build_part(k, work, out, mats, size_override, do_bake)
        # the game copy, alone, origin at its joint
        sel = objs[k]
        bpy.ops.object.select_all(action="DESELECT")
        sel.select_set(True)
        saved = sel.location.copy()
        sel.location = (0, 0, 0)
        sel.data.transform(Matrix.Scale(1 / GAME_SCALE, 4))     # game copy at kit size (origin is the joint)
        (out / "glb").mkdir(exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(out / "glb" / f"{k}.glb"), export_format="GLB", use_selection=True,
                                  export_yup=True, export_apply=True)
        sel.location = saved
        sel.data.transform(Matrix.Scale(GAME_SCALE, 4))
    for m in [m for m in bpy.data.materials if m.name.startswith(("high_", "lo_"))]:
        bpy.data.materials.remove(m)
    if not only:
        assemble(objs)
        for im in bpy.data.images:
            if im.filepath and not im.packed_file and im.source == "FILE":
                try:
                    im.pack()
                except RuntimeError:
                    pass
        bpy.ops.wm.save_as_mainfile(filepath=str((out / f"{NAME}_composite.blend").resolve()))
    elif only:      # a part built on its own (the Brute's claw and rail): keep it as a .blend to put on the walker
        for im in bpy.data.images:
            if im.filepath and not im.packed_file and im.source == "FILE":
                try:
                    im.pack()
                except RuntimeError:
                    pass
        bpy.ops.wm.save_as_mainfile(filepath=str((out / f"{'_'.join(only)}_part.blend").resolve()))
    joints = json.loads((work / "joints.json").read_text())
    report = {"parts": info, "joints": joints}
    prev = out / "report.json"
    if only and prev.exists():
        old = json.loads(prev.read_text())
        old["parts"].update(info)
        report = {"parts": old["parts"], "joints": joints}
    prev.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
