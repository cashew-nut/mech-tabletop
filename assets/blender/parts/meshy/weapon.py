"""Meshy image-to-3D GLB -> one baked item_<id> equipment part.

    python3 -I cut.py extract MESHY.glb WORK                     # mesh.npz + tex_*.jpg
    ~/bvenv/bin/python -I weapon.py WORK ITEM_ID [--length L] [--rear Y] [--zc Z] [--muzzle -x|+x]
        [--tris N] [--size 1024,512,128] [--no-export] [--livery]

The weapon's long axis (the longest side) is laid along -Y, muzzle towards -Y, rear at --rear, centred on x=0 and --zc,
and scaled to --length (kit units, the same as the procedural item it replaces). High mesh is welded, decimated, unwrapped
with xatlas and baked (colour, roughness, metal, normal) from the Meshy textures. --livery names the material hull*_livery
so the web repaints red texels in the owner's colour.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def opt(args, k, d, cast=str):
    return cast(args[args.index(k) + 1]) if k in args else d


def main(args):
    import bpy
    sys.path.insert(0, str(REPO / "assets" / "blender"))
    import kit
    from kit import bake as kb
    work, item = Path(args[0]), args[1]
    length = opt(args, "--length", 17.2, float)
    rear = opt(args, "--rear", 1.2, float)
    zc = opt(args, "--zc", 0.6, float)
    muzzle = opt(args, "--muzzle", "-x")
    tris = opt(args, "--tris", 6000, int)
    sizes = [int(s) for s in opt(args, "--size", "1024,512,128").split(",")]
    d = np.load(work / "mesh.npz")
    V, F, UV = d["V"].copy(), d["F"], d["UV"]
    if "--keep-x" in args:  # drop faces outside this fraction of the x extent (Meshy sometimes adds a holder, e.g. a gauntlet)
        lo_f, hi_f = [float(v) for v in opt(args, "--keep-x", "0,1").split(",")]
        x0, x1 = V[:, 0].min(), V[:, 0].max()
        keep = (V[F, 0] >= x0 + lo_f * (x1 - x0)).all(1) & (V[F, 0] <= x0 + hi_f * (x1 - x0)).all(1)
        F = F[keep]
        used = np.unique(F)
        V = V[used]
        remap = np.zeros(len(used) + 1, np.int64)
        remap = np.full(used.max() + 1, -1, np.int64)
        remap[used] = np.arange(len(used))
        F, UV = remap[F], UV[used]
    ext = V.max(0) - V.min(0)
    ax = int(np.argmax(ext))
    # Long axis -> -Y (muzzle at y = rear - length), the side axis -> X, Z stays up. The side axis flips with the muzzle
    # end so the swap is a rotation, not a mirror.
    c = (V.max(0) + V.min(0)) / 2
    s = length / ext[ax]
    plus = muzzle.startswith("+")
    u = ((V[:, ax].max() - V[:, ax]) if plus else (V[:, ax] - V[:, ax].min())) * s   # distance back from the muzzle
    side, up = [i for i in range(3) if i != ax and i != 2][0], 2
    sg = 1.0 if plus else -1.0
    if "--fit" in args:  # equipment: keep the Meshy pose (front -Y, Z up), scale to fit a W,D,H box centred on --centre x,y,z
        W_, D_, H_ = [float(v) for v in opt(args, "--fit", "1,1,1").split(",")]
        cx, cy, cz = [float(v) for v in opt(args, "--centre", "0,0,0").split(",")]
        ss = min(W_ / ext[0], D_ / ext[1], H_ / ext[2])
        P = ((V - c) * ss + np.array([cx, cy, cz])).astype(np.float32)
    elif "--upright" in args:  # stands up from a mount (core items): z from 0 to --length, centred on x/y
        ss = length / ext[2]
        P = np.stack([(V[:, 0] - c[0]) * ss, (V[:, 1] - c[1]) * ss, (V[:, 2] - V[:, 2].min()) * ss], 1).astype(np.float32)
    else:
        P = np.stack([sg * (V[:, side] - c[side]) * s, (rear - length) + u, (V[:, up] - c[up]) * s + zc], 1).astype(np.float32)
    scene = kit.reset_scene()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.render.bake.margin = 6

    imgs = {}
    for k, nm, cs in ((0, "base", "sRGB"), (1, "mr", "Non-Color"), (2, "nrm", "Non-Color")):
        im = bpy.data.images.load(str(work / f"tex_{k}.jpg"))
        im.colorspace_settings.name = cs
        imgs[nm] = im

    def high_materials():
        mats = {}
        for mode in ("color", "rough", "metal", "normal"):
            m = bpy.data.materials.new(f"high_{mode}")
            m.use_nodes = True
            N, L = m.node_tree.nodes, m.node_tree.links
            N.clear()
            uv = N.new("ShaderNodeUVMap")
            uv.uv_map = "UVHigh"

            def tex(img):
                t = N.new("ShaderNodeTexImage")
                t.image = img
                L.new(uv.outputs["UV"], t.inputs["Vector"])
                return t
            out = N.new("ShaderNodeOutputMaterial")
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
            mats[mode] = m
        return mats
    hm = high_materials()

    # High mesh, welded by position (Meshy splits vertices along UV seams).
    key = np.round(P[F.ravel()] * opt(args, "--weld", 400, float)).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    wv = P[F.ravel()][first]
    f2 = inv.reshape(-1, 3)
    ok = (f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 0] != f2[:, 2])
    me = bpy.data.meshes.new("hi")
    me.from_pydata(wv.tolist(), [], f2[ok].tolist())
    uvl = me.uv_layers.new(name="UVHigh")
    uv = UV[F[ok].ravel()].copy()
    uv[:, 1] = 1 - uv[:, 1]
    uvl.data.foreach_set("uv", uv.ravel())
    for p in me.polygons:
        p.use_smooth = True
    hi = bpy.data.objects.new("hi", me)
    bpy.context.scene.collection.objects.link(hi)
    # The handedness of the axis swap may mirror the mesh; flip faces if so.
    lo = hi.copy()
    lo.data = hi.data.copy()
    lo.name = f"lo_{item}"
    bpy.context.scene.collection.objects.link(lo)
    bpy.ops.object.select_all(action="DESELECT")
    lo.select_set(True)
    bpy.context.view_layer.objects.active = lo
    for kind in ("TRIANGULATE", "DECIMATE"):
        m = lo.modifiers.new(kind.lower(), kind)
        if kind == "DECIMATE":
            m.ratio = min(1.0, tris / max(1, len(lo.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons)))
        bpy.ops.object.modifier_apply(modifier=m.name)
    import xatlas
    me = lo.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    vn = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("normal", vn)
    co, vn = co.reshape(-1, 3), vn.reshape(-1, 3)
    idx = np.empty(len(me.polygons) * 3, np.int32)
    me.polygons.foreach_get("vertices", idx)
    faces = idx.reshape(-1, 3).astype(np.uint32)
    atlas = xatlas.Atlas()
    atlas.add_mesh(co, faces)
    co_opt = xatlas.ChartOptions()
    co_opt.max_cost = 4.0
    po = xatlas.PackOptions()
    po.resolution = sizes[0]
    po.padding = 6
    po.bilinear = True
    atlas.generate(co_opt, po)
    vmap, nf, uvx = atlas[0]
    me.clear_geometry()
    me.from_pydata(co[vmap].tolist(), [], nf.astype(np.int64).tolist())
    for l in list(me.uv_layers):
        me.uv_layers.remove(l)
    layer = me.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", uvx[nf.ravel().astype(np.int64)].astype(np.float32).ravel())
    for p in me.polygons:
        p.use_smooth = True
    me.normals_split_custom_set_from_vertices(vn[vmap].tolist())

    size = sizes[0]

    def bake_one(mode):
        hi.data.materials.clear()
        hi.data.materials.append(hm[mode])
        img = kb._image(f"{item}_{mode}", size, mode in ("rough", "metal", "normal"))
        lo.data.materials.clear()
        m = bpy.data.materials.new(f"lo_{item}_{mode}")
        m.use_nodes = True
        t = m.node_tree.nodes.new("ShaderNodeTexImage")
        t.image = img
        m.node_tree.nodes.active = t
        lo.data.materials.append(m)
        bpy.ops.object.select_all(action="DESELECT")
        hi.select_set(True)
        lo.select_set(True)
        bpy.context.view_layer.objects.active = lo
        kw = dict(type="NORMAL" if mode == "normal" else "EMIT", use_selected_to_active=True, cage_extrusion=0.03 * length / 17,
                  max_ray_distance=0.06 * length / 17, margin=6, use_clear=True)
        if mode == "normal":
            kw["normal_space"] = "TANGENT"
        bpy.ops.object.bake(**kw)
        return img
    b = {m: bake_one(m) for m in ("color", "rough", "metal", "normal")}

    def chan(img):
        a = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(size, size, 4)[..., 0]
    orm = np.stack([np.ones((size, size), np.float32), chan(b["rough"]), chan(b["metal"]), np.ones((size, size), np.float32)], -1)
    io = kb._image(f"{item}_orm", size, False)
    io.colorspace_settings.name = "Non-Color"
    io.pixels.foreach_set(orm.ravel())
    cache = kit.export.BAKE_DIR / f"item_{item}"
    cache.mkdir(parents=True, exist_ok=True)
    paths = {}
    for k, img in (("basecolor", b["color"]), ("orm", io), ("normal", b["normal"])):
        p = cache / f"{item}_{k}.png"
        kb._save(img, p)
        paths[k] = p
    from PIL import Image
    for k, sz in (("normal", sizes[1]), ("orm", sizes[2])):
        if sz < size:
            Image.open(paths[k]).convert("RGB").resize((sz, sz), Image.LANCZOS).save(paths[k])
    tex = {}
    for k, p in paths.items():
        im = bpy.data.images.load(str(p), check_existing=False)
        im.name = p.stem + "_f"
        im.colorspace_settings.name = "sRGB" if k == "basecolor" else "Non-Color"
        tex[k] = im
    mat = kb.baked_material(f"hull_{item}_livery" if "--livery" in args else f"meshy_{item}", tex["basecolor"], tex["orm"], tex["normal"])
    lo.data.materials.clear()
    lo.data.materials.append(mat)
    bpy.data.objects.remove(hi)
    root = kit.empty(f"item_{item}")
    lo.parent = root
    lo.name = f"{item}_body"
    print(f"== item_{item}: {len(lo.data.polygons)} tris, {size}px")
    if "--no-export" not in args:
        kit.publish(root, bake=False)
    if "--save" in args:
        bpy.ops.wm.save_as_mainfile(filepath=opt(args, "--save", "/tmp/w/last.blend"), copy=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
