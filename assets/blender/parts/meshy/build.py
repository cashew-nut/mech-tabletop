"""Build the Paladin's kit parts from the cut Meshy mesh (step 2 of 2; needs Blender via bpy).

    ~/bvenv/bin/python build.py tunes                         # write frameTunes into data/model-kit.json (no bpy)
    ~/bvenv/bin/python build.py WORKDIR [part ...] [--size 1024] [--no-export]

WORKDIR holds the files made by cut.py (mesh.npz, lab.npy, names.json, tex_0..2.jpg). For every part:
the labelled triangles become the high-poly source (with Meshy's colour, metal/rough and normal maps),
a decimated copy gets fresh UVs, and Cycles bakes colour, roughness, metallic and normals onto it.
The part is moved so its origin is its joint (or mount, for equipment) and published into
apps/web/public/parts/ under the kit names:  covenant_<component>_paladin, covenant_<component>-right_paladin,
item_lance@paladin (the siege blade) and item_carapace-gun@paladin (the shoulder pod).
Meshy units are scaled by S so the figure's helm top sits at the titan frame's nominal height.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cut import CX, JOINTS  # noqa: E402

REPO = HERE.parents[3]
S = 50 / 1.5          # mm per Meshy unit (standing height to the helm top = 50 mm, the titan frame's H)
FOOT_Z, BASE = -0.90, 3.0


def to_mm(p):
    """Meshy unit position (x already centred on CX) to kit mm."""
    return np.array([p[0] * S, p[1] * S, (p[2] - FOOT_Z) * S + BASE])


# component: (joint, triangles, texture size)
PARTS = {
    "helm": ("head", 5000, 1024), "collar": ("neck", 3000, 512), "torso": ("spine", 12000, 1024),
    "pelvis": ("pelvis", 6000, 1024), "back": ("chest", 8000, 1024), "cloth": ("chest", 5000, 1024),
    "pauldron": ("shoulder", 6000, 1024), "arm": ("shoulder", 2500, 512), "forearm": ("elbow", 4000, 1024),
    "hand": ("wrist", 3500, 512), "thigh": ("hip", 5000, 1024), "shin": ("knee", 6000, 1024),
    "foot": ("ankle", 3500, 512),
}
SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot"}
# Equipment: label, item file name, attach mount (world position in Meshy units, centred), triangles, size
ITEMS = {
    "lance": ("sword_L", "item_lance@paladin", (0.57, -0.30, -0.28), 4000, 1024),
    "carapace-gun": ("pod_L", "item_carapace-gun@paladin", (0.22, 0.10, 0.62), 6000, 1024),
}
DEBUG = False
import os
VOXELS = int(os.environ.get('VOXELS', 0)); SMOOTH = int(os.environ.get('SMOOTH', 0));         # voxel remesh resolution along a part's longest side
ITEM_SCALE = 1.7      # items are modelled at Scout scale and grown by the titan frame's factor in the web


def tunes():
    """Write the Meshy joint positions (mm, left side) as frameTunes in data/model-kit.json."""
    path = REPO / "data" / "model-kit.json"
    kit = json.loads(path.read_text())
    joints = {k: [round(float(v), 3) for v in to_mm(p)] for k, p in JOINTS.items()}
    mounts = {}
    # Mount offsets are local to their joint (see Skeleton.mounts): arm 0 at the sword grip, core 0/1 at the pods.
    grip, pod = to_mm(ITEMS["lance"][2]), to_mm(ITEMS["carapace-gun"][2])
    mounts["mount_armLeft_0"] = ["wrist", [round(float(v), 3) for v in grip - np.array(joints["wrist"])]]
    mounts["mount_core_0"] = ["chest", [round(float(v), 3) for v in pod - np.array(joints["chest"])]]
    mounts["mount_core_1"] = ["chest", [round(float(-pod[0] - joints["chest"][0]), 3), round(float(pod[1] - joints["chest"][1]), 3), round(float(pod[2] - joints["chest"][2]), 3)]]
    mounts["mount_armRight_0"] = ["wrist", [round(float(-grip[0] + joints["wrist"][0]), 3), round(float(grip[1] - joints["wrist"][1]), 3), round(float(grip[2] - joints["wrist"][2]), 3)]]
    kit.setdefault("frameTunes", {})["covenant/titan"] = {
        "$comment": "Joints (mm, left side) measured from the Meshy Paladin; see assets/blender/parts/meshy.",
        "joints": joints, "mounts": mounts,
    }
    path.write_text(json.dumps(kit, indent=2) + "\n")
    print("frameTunes written")


def main(args):
    import bpy  # noqa: E402
    sys.path.insert(0, str(REPO / "assets" / "blender"))
    import kit  # noqa: E402
    from kit import bake as kb  # noqa: E402
    from kit.skeleton import Skeleton  # noqa: E402
    from mathutils import Matrix, Vector  # noqa: E402

    work = Path(args[0])
    size_override = int(args[args.index("--size") + 1]) if "--size" in args else None
    only = [a for a in args[1:] if not a.startswith("--") and not a.isdigit()]
    export = "--no-export" not in args
    d = np.load(work / "mesh.npz")
    V, F, UV = d["V"].copy(), d["F"], d["UV"]
    lab = np.load(work / "lab.npy")
    names = json.loads((work / "names.json").read_text())
    V[:, 0] -= CX
    Vmm = ((V - np.array([0, 0, FOOT_Z], np.float32)) * S + np.array([0, 0, BASE], np.float32)).astype(np.float32)
    sk = Skeleton("covenant", "titan")

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
            nt = m.node_tree
            N, L = nt.nodes, nt.links
            N.clear()
            uv = N.new("ShaderNodeUVMap")
            uv.uv_map = "UVHigh"

            def tex(img):
                t = N.new("ShaderNodeTexImage")
                t.image = img
                t.interpolation = "Linear"
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

    def subset(name, mask):
        faces = F[mask]
        # Meshy splits vertices along its texture seams; weld by position so the part is one connected shell.
        key = np.round(Vmm[faces.ravel()] * 2000).astype(np.int64)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        inv = inv.ravel()
        wv = Vmm[faces.ravel()][first]
        f2 = inv.reshape(-1, 3)
        ok = (f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 0] != f2[:, 2])
        f2, faces = f2[ok], faces[ok]
        me = bpy.data.meshes.new(name)
        me.from_pydata(wv.tolist(), [], f2.tolist())
        uvl = me.uv_layers.new(name="UVHigh")
        uv = UV[faces.ravel()].copy()
        uv[:, 1] = 1 - uv[:, 1]
        uvl.data.foreach_set("uv", uv.ravel())
        for p in me.polygons:
            p.use_smooth = True
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob

    def drop_floaters(ob, min_tris=120):
        """Delete tiny disconnected shells left by the voxel remesh."""
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        seen, kill = set(), []
        for f in bm.faces:
            if f.index in seen:
                continue
            comp, stack = [f], [f]
            seen.add(f.index)
            while stack:
                g = stack.pop()
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen:
                            seen.add(h.index)
                            stack.append(h)
                            comp.append(h)
            if len(comp) < min_tris:
                kill += comp
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        bm.to_mesh(ob.data)
        bm.free()

    def decimate(ob, target):
        me = ob.data
        # Voxel remesh first: Meshy's surface is noisy and full of tiny relief; the remesh gives one clean watertight
        # shell (which also closes the cut). Smooth away the voxel steps, then decimate: the relief returns via the normal map.
        me.remesh_voxel_size = max(ob.dimensions) / (VOXELS or 100)
        me.remesh_voxel_adaptivity = 0.0
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        if VOXELS:
            bpy.ops.object.voxel_remesh()
        for kind, kw in (("TRIANGULATE", {}), ("SMOOTH", dict(factor=0.6, iterations=SMOOTH)), ("DECIMATE", dict(ratio=1.0))):
            if kind == "SMOOTH" and not SMOOTH:
                continue
            m = ob.modifiers.new(kind.lower(), kind)
            for k, v in kw.items():
                setattr(m, k, v)
            if kind == "DECIMATE":
                n = len(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons)
                m.ratio = min(1.0, target / max(1, n))
            bpy.ops.object.modifier_apply(modifier=m.name)
            if kind == "TRIANGULATE" and VOXELS:
                drop_floaters(ob)
        for p in me.polygons:
            p.use_smooth = True

    def unwrap(ob, size):
        """xatlas charts and packing (Blender's smart project shatters noisy low-poly shells), then rebuild the
        mesh with the seam vertices split, keeping the smooth vertex normals so seams don't show."""
        import xatlas
        me = ob.data
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
        po.resolution = size
        po.padding = 6
        po.bilinear = True
        po.texels_per_unit = 0
        atlas.generate(co_opt, po)
        vmap, nf, uv = atlas[0]
        me.clear_geometry()
        me.from_pydata(co[vmap].tolist(), [], nf.astype(np.int64).tolist())
        for l in list(me.uv_layers):
            me.uv_layers.remove(l)
        layer = me.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", uv[nf.ravel().astype(np.int64)].astype(np.float32).ravel())
        for p in me.polygons:
            p.use_smooth = True
        me.normals_split_custom_set_from_vertices(vn[vmap].tolist())
        if DEBUG:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            seen, comps = set(), 0
            for f in bm.faces:
                if f.index in seen:
                    continue
                comps += 1
                stack = [f]
                seen.add(f.index)
                while stack:
                    g = stack.pop()
                    for e in g.edges:
                        for h in e.link_faces:
                            if h.index not in seen:
                                seen.add(h.index)
                                stack.append(h)
            ang = np.array([e.calc_face_angle(0) for e in bm.edges if len(e.link_faces) == 2])
            uvl = bm.loops.layers.uv.active
            cut = sum(1 for e in bm.edges if len(e.link_faces) == 2 and {tuple(l[uvl].uv) for l in e.link_faces[0].loops if l.vert in e.verts} != {tuple(l[uvl].uv) for l in e.link_faces[1].loops if l.vert in e.verts})
            print(f"DEBUG tris={len(bm.faces)} comps={comps} edges={len(bm.edges)} uvcut={cut} dihedral>60deg={(ang > 1.05).sum()} median={np.median(ang):.2f}")
            bm.free()

    def bake_one(hi, lo, kind, mode, size, name):
        hi.data.materials.clear()
        hi.data.materials.append(hm[mode])
        img = kb._image(f"{name}_{mode}", size, kind != "color")
        lo.data.materials.clear()
        m = bpy.data.materials.new(f"lo_{name}_{mode}")
        m.use_nodes = True
        n = m.node_tree.nodes.new("ShaderNodeTexImage")
        n.image = img
        m.node_tree.nodes.active = n
        lo.data.materials.append(m)
        bpy.ops.object.select_all(action="DESELECT")
        hi.select_set(True)
        lo.select_set(True)
        bpy.context.view_layer.objects.active = lo
        kw = dict(type="NORMAL" if mode == "normal" else "EMIT", use_selected_to_active=True, cage_extrusion=0.8, max_ray_distance=1.6,
                  margin=6, use_clear=True)
        if mode == "normal":
            kw["normal_space"] = "TANGENT"
        bpy.ops.object.bake(**kw)
        return img

    def build(out_name, mask, comp_target, size, shift, is_item=False, scale=1.0):
        t0 = time.time()
        ntri = int(mask.sum())
        if not ntri:
            print("skip (empty)", out_name)
            return
        size = size_override or size
        hi = subset(out_name + "_hi", mask)
        lo = hi.copy()
        lo.data = hi.data.copy()
        lo.name = out_name
        bpy.context.scene.collection.objects.link(lo)
        decimate(lo, comp_target)
        unwrap(lo, size)
        imgs_b = {m: bake_one(hi, lo, "n" if m == "normal" else "color" if m == "color" else "data", m, size, out_name) for m in ("color", "rough", "metal", "normal")}

        def chan(img):
            a = np.empty(size * size * 4, np.float32)
            img.pixels.foreach_get(a)
            return a.reshape(size, size, 4)[..., 0]
        orm = np.stack([np.ones((size, size), np.float32), chan(imgs_b["rough"]), chan(imgs_b["metal"]), np.ones((size, size), np.float32)], -1)
        io = kb._image(f"{out_name}_orm", size, False)
        io.colorspace_settings.name = "Non-Color"
        io.pixels.foreach_set(orm.ravel())
        cache = kit.export.BAKE_DIR / out_name
        cache.mkdir(parents=True, exist_ok=True)
        paths = {}
        for key, img in (("basecolor", imgs_b["color"]), ("orm", io), ("normal", imgs_b["normal"])):
            p = cache / f"{out_name}_{key}.png"
            kb._save(img, p)
            paths[key] = p
        tex = {}
        for key, p in paths.items():
            im = bpy.data.images.load(str(p), check_existing=False)
            im.name = p.stem + "_f"
            im.colorspace_settings.name = "sRGB" if key == "basecolor" else "Non-Color"
            tex[key] = im
        mat = kb.baked_material(f"{out_name}_kit", tex["basecolor"], tex["orm"], tex["normal"])
        lo.data.materials.clear()
        lo.data.materials.append(mat)
        root = kit.empty(out_name)
        lo.parent = root
        # Move the part so its origin is its joint (or mount).
        lo.data.transform(Matrix.Scale(scale, 4) @ Matrix.Translation(-Vector(shift)))
        bpy.data.objects.remove(hi)
        tris = len(lo.data.polygons)
        if export:
            kit.publish(root, bake=False)
        print(f"== {out_name}: {ntri} -> {tris} tris, {size}px, {time.time() - t0:.0f}s", flush=True)

    for comp, (joint, target, size) in PARTS.items():
        sides = ("L", "R") if comp in SIDED else (None,)
        for side in sides:
            out = f"covenant_{comp}{'-right' if side == 'R' else ''}_paladin"
            if only and out not in only and comp not in only:
                continue
            key = f"{comp}_{side}" if side else comp
            mask = lab == names.index(key)
            sock = sk.joint(joint, side or "L")
            build(out, mask, target, size, sock)
    for iid, (label, out, mount, target, size) in ITEMS.items():
        if only and out not in only and iid not in only:
            continue
        mask = lab == names.index(label)
        # Items are modelled at Scout scale around the mount, then grown by ITEM_SCALE in the web.
        build(out, mask, target, size, to_mm(mount), is_item=True, scale=1 / ITEM_SCALE)


if __name__ == "__main__":
    if sys.argv[1] == "tunes":
        tunes()
    else:
        main(sys.argv[1:])
