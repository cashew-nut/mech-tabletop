"""Meshy image-to-3D GLB -> one hero scenery piece for the 3D board (public/board/hero_<name>.glb).

    python3 -I assets/blender/parts/meshy/cut.py extract MESHY.glb WORK        # mesh.npz + tex_*.jpg
    ~/bvenv/bin/python -I assets/blender/board/hero.py WORK NAME --height H [--max-width W] [--crop-base F] [--tris N]
        [--size 1024] [--stretch F] [--cage F] [--smoke]

Scales the piece so it is H board units tall (one hex has circumradius 1) and at most W wide, stands it on z = 0 centred on
x = y = 0, and cuts away the plinth Meshy invents under it (--crop-base F removes the lowest fraction F of the height, so the
piece sits on the board's own flagstone). The high mesh is welded, a decimated copy is unwrapped with xatlas, and colour and
a tangent-space normal map are baked from the Meshy textures. --smoke adds an empty named `smoke` at the top for the board's
chimney smoke. Output is a plain GLB with JPEG textures: the board loader keeps its own material for hero pieces.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUT = REPO / "apps" / "web" / "public" / "board"


def opt(args, k, d, cast=str):
    return cast(args[args.index(k) + 1]) if k in args else d


def main(args):
    import bpy
    sys.path.insert(0, str(REPO / "assets" / "blender"))
    import kit
    from kit import bake as kb
    work, name = Path(args[0]), args[1]
    height = opt(args, "--height", 4.0, float)
    max_w = opt(args, "--max-width", 1.5, float)
    crop = opt(args, "--crop-base", 0.0, float)
    tris = opt(args, "--tris", 12000, int)
    size = opt(args, "--size", 1024, int)
    cage = opt(args, "--cage", 1.0, float)  # a coarsely clustered low mesh strays further from the high one: widen the bake rays
    d = np.load(work / "mesh.npz")
    V, F, UV = d["V"].copy(), d["F"], d["UV"]

    # Drop the invented plinth: faces whose vertices all sit in the lowest fraction of the height.
    z0, z1 = V[:, 2].min(), V[:, 2].max()
    if crop > 0:
        keep = (V[F, 2] >= z0 + crop * (z1 - z0)).any(1)
        F = F[keep]
        used = np.unique(F)
        remap = np.full(used.max() + 1, -1, np.int64)
        remap[used] = np.arange(len(used))
        V, UV, F = V[used], UV[used], remap[F]
    z0, z1 = V[:, 2].min(), V[:, 2].max()
    ext = V.max(0) - V.min(0)
    stretch = opt(args, "--stretch", 1.0, float)  # >1 makes a squat piece taller than Meshy drew it
    s = min(height / ((z1 - z0) * stretch), max_w / max(ext[0], ext[1]))
    c = (V.max(0) + V.min(0)) / 2
    P = np.stack([(V[:, 0] - c[0]) * s, (V[:, 1] - c[1]) * s, (V[:, 2] - z0) * s * stretch], 1).astype(np.float32)
    top = float(P[:, 2].max())

    scene = kit.reset_scene()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    scene.render.bake.margin = 6

    imgs = {}
    for k, nm, cs in ((0, "base", "sRGB"), (2, "nrm", "Non-Color")):
        im = bpy.data.images.load(str(work / f"tex_{k}.jpg"))
        im.colorspace_settings.name = cs
        imgs[nm] = im

    def high_material(mode):
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
            L.new(tex(imgs["base"]).outputs["Color"], em.inputs["Color"])
            L.new(em.outputs["Emission"], out.inputs["Surface"])
        return m
    hm = {mode: high_material(mode) for mode in ("color", "normal")}

    key = np.round(P[F.ravel()] * opt(args, "--weld", 300, float)).astype(np.int64)
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
    print("T hi", len(hi.data.polygons), flush=True)

    lo = hi.copy()
    lo.data = hi.data.copy()
    lo.name = f"hero_{name}"
    if "--lo-weld" in args:  # Noisy Meshy meshes stall the decimator: cluster the low mesh's vertices on a coarse grid first,
        # coarsening the grid until the triangle count is near the target (the baked normal map carries the detail).
        w = opt(args, "--lo-weld", 40, float)
        Pf = P[F[ok].ravel()]
        while True:
            kk = np.round(Pf * w).astype(np.int64)
            _, fi, iv = np.unique(kk, axis=0, return_index=True, return_inverse=True)
            iv = iv.ravel()
            ff = iv.reshape(-1, 3)
            good = (ff[:, 0] != ff[:, 1]) & (ff[:, 1] != ff[:, 2]) & (ff[:, 0] != ff[:, 2])
            print(f"T weld {w:.1f}: {int(good.sum())} tris", flush=True)
            if good.sum() <= tris * 1.6 or w < 4:
                break
            w *= 0.85
        lm = bpy.data.meshes.new("lo")
        lm.from_pydata(Pf[fi].tolist(), [], ff[good].tolist())
        lo.data = lm
    bpy.context.scene.collection.objects.link(lo)
    bpy.ops.object.select_all(action="DESELECT")
    lo.select_set(True)
    bpy.context.view_layer.objects.active = lo
    for kind in ("TRIANGULATE", "DECIMATE", "DECIMATE", "DECIMATE"):
        if kind == "DECIMATE" and len(lo.data.polygons) <= tris * 1.15:
            break
        m = lo.modifiers.new(kind.lower(), kind)
        if kind == "DECIMATE":
            m.ratio = min(1.0, tris / max(1, len(lo.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons)))
        bpy.ops.object.modifier_apply(modifier=m.name)
    print("T dec", len(lo.data.polygons), flush=True)

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
    copt = xatlas.ChartOptions()
    copt.max_cost = 4.0
    po = xatlas.PackOptions()
    po.resolution = size
    po.padding = 6
    po.bilinear = True
    atlas.generate(copt, po)
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
    print("T unwrap", flush=True)

    def bake_one(mode):
        hi.data.materials.clear()
        hi.data.materials.append(hm[mode])
        img = kb._image(f"{name}_{mode}", size, mode == "normal")
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
        kw = dict(type="NORMAL" if mode == "normal" else "EMIT", use_selected_to_active=True, cage_extrusion=0.02 * height / 4 * cage,
                  max_ray_distance=0.05 * height / 4 * cage, margin=6, use_clear=True)
        if mode == "normal":
            kw["normal_space"] = "TANGENT"
        bpy.ops.object.bake(**kw)
        return img
    colour, normal = bake_one("color"), bake_one("normal")

    # One Principled material: baked colour and normal, fixed roughness.
    mat = bpy.data.materials.new(f"hero_{name}")
    mat.use_nodes = True
    N, L = mat.node_tree.nodes, mat.node_tree.links
    b = N["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.9
    b.inputs["Metallic"].default_value = 0.0
    tc = N.new("ShaderNodeTexImage")
    tc.image = colour
    L.new(tc.outputs["Color"], b.inputs["Base Color"])
    tn = N.new("ShaderNodeTexImage")
    tn.image = normal
    nm = N.new("ShaderNodeNormalMap")
    L.new(tn.outputs["Color"], nm.inputs["Color"])
    L.new(nm.outputs["Normal"], b.inputs["Normal"])
    lo.data.materials.clear()
    lo.data.materials.append(mat)
    bpy.data.objects.remove(hi)
    colour.pack()
    normal.pack()

    if "--smoke" in args:
        e = bpy.data.objects.new("smoke", None)
        e.location = (0.0, 0.0, top)
        bpy.context.scene.collection.objects.link(e)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"hero_{name}.glb"
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=str(out), export_format="GLB", use_selection=True, export_yup=True,
                              export_image_format="JPEG", export_jpeg_quality=85, export_apply=True)
    print(f"== {out.name}: {len(lo.data.polygons)} tris, {out.stat().st_size // 1024} KiB, {height} tall")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
