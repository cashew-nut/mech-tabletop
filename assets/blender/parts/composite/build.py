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
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))           # assets/blender, for kit
from layout import M, NAME, PS, TREE, SIDED, LOADOUT, joint  # noqa: E402

BUDGET = M.BUDGET         # part: (game triangles, texture size)
GAME_SCALE = PS           # print size / kit size: the .blend and STLs are print size, the game GLBs kit size
RAY = getattr(M, "RAY", PS)   # bake ray reach, relative to the Paladin's (the decimated copy strays further on bigger parts)
PRINT_TOL = 0.015       # mm, manifold simplify tolerance for the print copies
GUNMETAL = ((0.035, 0.035, 0.04), 0.42, 1.0)        # colour, roughness, metallic of cut faces, pegs and holes
GOLD = getattr(M, "KNUCKLE_FINISH", ((0.56, 0.40, 0.18), 0.30, 1.0))   # designed knuckles and struts


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
    uv[:, 1] = 1 - uv[:, 1]
    me.uv_layers.new(name="UVHigh").data.foreach_set("uv", uv.ravel())
    me.polygons.foreach_set("material_index", (cap * 1 + knuckle * 2).astype(np.int32))
    me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob, cap


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


def high_materials(imgs):
    """Bake-source materials per channel: Meshy's textures on the surface (slot 0), gunmetal on cuts (slot 1)."""
    mats = {}
    for mode in ("color", "rough", "metal", "normal"):
        pair = []
        for slot in ("meshy", "cut", "knuckle"):
            m = bpy.data.materials.new(f"high_{mode}_{slot}")
            m.use_nodes = True
            N, L = m.node_tree.nodes, m.node_tree.links
            N.clear()
            out = N.new("ShaderNodeOutputMaterial")
            if slot in ("cut", "knuckle"):
                if mode == "normal":
                    L.new(N.new("ShaderNodeBsdfPrincipled").outputs["BSDF"], out.inputs["Surface"])
                else:
                    em = N.new("ShaderNodeEmission")
                    col, rough, metal = GUNMETAL if slot == "cut" else GOLD
                    v = {"color": (*col, 1), "rough": (rough,) * 3 + (1,), "metal": (metal,) * 3 + (1,)}[mode]
                    em.inputs["Color"].default_value = v
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
    while len(hi.data.materials) < 3:
        hi.data.materials.append(None)
    hi.data.materials[0], hi.data.materials[1], hi.data.materials[2] = mats[mode]
    img = kb._image(f"{name}_{mode}", size, mode != "color")
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
    decimate(lo, target)
    unwrap(lo, size)
    if do_bake:
        imgs = {mode: bake(hi, lo, mats, mode, size, k) for mode in ("color", "rough", "metal", "normal")}

        def chan(img):
            a = np.empty(size * size * 4, np.float32)
            img.pixels.foreach_get(a)
            return a.reshape(size, size, 4)[..., 0]
        orm = np.stack([np.ones((size, size), np.float32), chan(imgs["rough"]), chan(imgs["metal"]),
                        np.ones((size, size), np.float32)], -1)
        io = kb._image(f"{k}_orm", size, True)
        io.pixels.foreach_set(orm.ravel())
        tdir = out / "textures"
        tdir.mkdir(parents=True, exist_ok=True)
        paths = {}
        for key, img in (("basecolor", imgs["color"]), ("orm", io), ("normal", imgs["normal"])):
            p = tdir / f"{k}_{key}.png"
            kb._save(img, p)
            paths[key] = p
        for key, sz in (("normal", min(size, 512)), ("orm", 256)):
            Image.open(paths[key]).convert("RGB").resize((sz, sz), Image.LANCZOS).save(paths[key])
        tex = {}
        for key, p in paths.items():
            im = bpy.data.images.load(str(p), check_existing=False)
            im.colorspace_settings.name = "sRGB" if key == "basecolor" else "Non-Color"
            tex[key] = im
        mat = kb.baked_material(f"hull_{k}_livery", tex["basecolor"], tex["orm"], tex["normal"])
    else:
        mat = bpy.data.materials.new(f"plain_{k}")
    lo.data.materials.clear()
    lo.data.materials.append(mat)
    bpy.data.objects.remove(hi)
    # origin at the joint
    j = Vector(joint(TREE[k][1]))
    lo.data.transform(Matrix.Translation(-j))
    lo.location = j
    print(f"== {k}: game {len(lo.data.polygons)} tris {size}px, print {len(F)} tris, {time.time() - t0:.0f}s", flush=True)
    return lo, stl_info


def assemble(objs):
    """Duplicate sided parts as mirrored right-hand copies and parent everything joint to joint."""
    placed = {}
    for k, ob in objs.items():
        if k in SIDED:
            ob.name = f"{k}_L"
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
    for k, nm, cs in ((0, "base", "sRGB"), (1, "mr", "Non-Color"), (2, "nrm", "Non-Color")):
        im = bpy.data.images.load(str(work / f"tex_{k}.jpg"))
        im.colorspace_settings.name = cs
        imgs[nm] = im
    mats = high_materials(imgs)
    objs, info = {}, {}
    for k in TREE:
        if only and k not in only:
            continue
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
