"""Bake a part's node materials into textures the web game can draw.

    from kit import bake
    bake.bake_part(root, size=1024)

The browser can't run Blender's shader nodes, so the look has to travel as
images. For every mesh under `root` this:

1. applies modifiers (curves become meshes) and lays out one shared atlas
   UV map ("UVMap") across all of them,
2. bakes base colour, roughness, metallic, a tangent-space normal map (with
   every bump and relief node in it) and ambient occlusion with Cycles,
3. swaps the materials for baked ones that share those textures:
   `<root>_kit` for everything, and `hull_<root>_<role>` for each paintable
   material (baked with the paint set to white, so the web multiplies the
   livery in), and keeps glow materials as plain emissive factors.

Textures are written next to the .blend (or to `out_dir`) as
`<root>_basecolor.png`, `<root>_orm.png` (occlusion, roughness, metallic in
R, G, B, as glTF wants) and `<root>_normal.png`. export_parts.py packs them
into the GLB and compress-parts.mjs turns them into KTX2.
"""
import time
from pathlib import Path

import bpy
import numpy as np

from .core import apply_all, meshes
from .shapes import decal_uv

CHANNELS = ("Base Color", "Roughness", "Metallic")


def _principled(mat):
    nt = mat.node_tree
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None) or \
        next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    return out, bsdf


def _is_hull(mat):
    return mat.name.lower().startswith("hull")


def _bakeable(mat):
    return mat is not None and mat.use_nodes and mat.get("bake", True) and _principled(mat)[1] is not None


def _image(name, size, data):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, size, size, alpha=False, float_buffer=data)
    img.colorspace_settings.name = "Non-Color" if data else "sRGB"
    return img


def _target(mats, img):
    """Point every material's bake target at `img`."""
    for m in mats:
        nt = m.node_tree
        n = nt.nodes.get("kit_bake_target") or nt.nodes.new("ShaderNodeTexImage")
        n.name = "kit_bake_target"
        n.image = img
        uv = nt.nodes.get("kit_bake_uv") or nt.nodes.new("ShaderNodeUVMap")
        uv.name = "kit_bake_uv"
        uv.uv_map = "UVMap"
        if not n.inputs["Vector"].links:
            nt.links.new(uv.outputs["UV"], n.inputs["Vector"])
        nt.nodes.active = n


# Samples per bake: emission and normals need few, occlusion needs more.
SAMPLES = {"EMIT": 8, "NORMAL": 8, "AO": 16}


def _bake(kind, objs, margin, samples=None):
    t = time.time()
    bpy.context.scene.cycles.samples = samples or SAMPLES[kind]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(type=kind, margin=margin, use_clear=True)
    if kind == "NORMAL":
        kw.update(normal_space="TANGENT")
    bpy.ops.object.bake(**kw)
    print(f"baked {kind} in {time.time() - t:.0f} s")


def _emit_channel(mats, channel):
    """Rewire each material so its emission is `channel` of its BSDF. Returns an undo list."""
    undo = []
    for m in mats:
        nt = m.node_tree
        out, bsdf = _principled(m)
        sock = bsdf.inputs[channel]
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 1.0
        if sock.links:
            nt.links.new(sock.links[0].from_socket, em.inputs["Color"])
        else:
            v = sock.default_value
            em.inputs["Color"].default_value = tuple(v) if hasattr(v, "__len__") else (v, v, v, 1.0)
        prev = out.inputs["Surface"].links[0].from_socket if out.inputs["Surface"].links else None
        nt.links.new(em.outputs[0], out.inputs["Surface"])
        undo.append((nt, out, prev, em))
    return undo


def _restore(undo):
    for nt, out, prev, em in undo:
        nt.nodes.remove(em)
        if prev is not None:
            nt.links.new(prev, out.inputs["Surface"])


def _paint_white(mats):
    saved = []
    for m in mats:
        n = m.node_tree.nodes.get("paint")
        if n is not None:
            saved.append((n, tuple(n.outputs[0].default_value)))
            n.outputs[0].default_value = (1, 1, 1, 1)
    return saved


def _gltf_output_group():
    """The node group the glTF exporter reads ambient occlusion from."""
    g = bpy.data.node_groups.get("glTF Material Output")
    if g is None:
        g = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        g.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        g.interface.new_socket("Thickness", in_out="INPUT", socket_type="NodeSocketFloat")
    return g


def baked_material(name, base, orm, normal, paint=None):
    """A Principled material on the baked textures. `paint` (linear RGB) is
    multiplied into the base colour and exported as the glTF baseColorFactor."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"

    def tex(img):
        t = N.new("ShaderNodeTexImage")
        t.image = img
        L.new(uv.outputs["UV"], t.inputs["Vector"])
        return t
    tb, to, tn = tex(base), tex(orm), tex(normal)
    if paint is not None:
        mul = N.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        L.new(tb.outputs["Color"], mul.inputs[6])
        mul.inputs[7].default_value = (*paint, 1.0)
        L.new(mul.outputs[2], bsdf.inputs["Base Color"])
    else:
        L.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
    sep = N.new("ShaderNodeSeparateColor")
    L.new(to.outputs["Color"], sep.inputs["Color"])
    L.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    L.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    nm = N.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    L.new(tn.outputs["Color"], nm.inputs["Color"])
    L.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    grp = N.new("ShaderNodeGroup")
    grp.node_tree = _gltf_output_group()
    L.new(sep.outputs["Red"], grp.inputs["Occlusion"])
    return m


def _save(img, path):
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()


def _atlas(objs, margin_frac):
    for o in objs:
        uvs = o.data.uv_layers
        layer = uvs.get("UVMap") or uvs.new(name="UVMap")
        uvs.active = layer
        layer.active_render = True
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=margin_frac, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=margin_frac, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake_part(root, size=1024, samples=None, margin=4, out_dir=None, name=None):
    """Bake every mesh under `root` into one texture set and swap in the baked
    materials. Returns the dict of written texture paths."""
    name = name or root.name.split(".")[0]
    out_dir = Path(out_dir or (Path(bpy.data.filepath).parent if bpy.data.filepath else Path.cwd()))
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.render.bake.margin = margin

    # Real geometry only: drop boolean cutters, apply every modifier.
    objs = []
    for o in meshes(root):
        if o.get("kit_cutter"):
            continue
        objs.append(o)
    objs = [apply_all(o) for o in objs]
    for o in list(objs):
        for c in o.children_recursive:
            if c.get("kit_cutter"):
                bpy.data.objects.remove(c)
    for o in [*meshes(root)]:
        if o.get("kit_cutter"):
            bpy.data.objects.remove(o)
    objs = [o for o in meshes(root) if o.type == "MESH" and len(o.data.polygons)]
    baked = [o for o in objs if any(_bakeable(s.material) for s in o.material_slots)]
    if not baked:
        return {}
    for o in baked:
        decal_uv(o)
    _atlas(baked, 2 * margin / size)

    mats = sorted({s.material for o in baked for s in o.material_slots if s.material is not None}, key=lambda m: m.name)
    bmats = [m for m in mats if _bakeable(m)]
    saved_paint = _paint_white(bmats)

    paths = {}
    # Normal and occlusion bake from the materials as they are.
    img_n = _image(f"{name}_normal", size, True)
    _target(mats, img_n)
    _bake("NORMAL", baked, margin)
    img_ao = _image(f"{name}_ao", size, True)
    _target(mats, img_ao)
    _bake("AO", baked, margin, samples)
    # Colour, roughness and metallic through emission.
    imgs = {}
    for ch in CHANNELS:
        img = _image(f"{name}_{ch.split()[0].lower()}", size, ch != "Base Color")
        _target(mats, img)
        undo = _emit_channel(bmats, ch)
        _bake("EMIT", baked, margin)
        _restore(undo)
        imgs[ch] = img
    for node, value in saved_paint:
        node.outputs[0].default_value = value

    # Pack occlusion, roughness and metallic into one image.
    def chan(img):
        a = np.empty(size * size * 4, dtype=np.float32)
        img.pixels.foreach_get(a)
        return a.reshape(size, size, 4)[..., 0]
    orm = np.stack([chan(img_ao), chan(imgs["Roughness"]), chan(imgs["Metallic"]), np.ones((size, size), np.float32)], axis=-1)
    img_orm = _image(f"{name}_orm", size, False)
    img_orm.colorspace_settings.name = "Non-Color"
    img_orm.pixels.foreach_set(orm.ravel())
    img_base = imgs["Base Color"]
    # Save the base colour through a byte image so the PNG is plain sRGB.
    img_n_out = img_n
    for key, img in (("basecolor", img_base), ("orm", img_orm), ("normal", img_n_out)):
        p = out_dir / f"{name}_{key}.png"
        _save(img, p)
        paths[key] = p
    for img in (img_ao, imgs["Roughness"], imgs["Metallic"]):
        bpy.data.images.remove(img)

    # Reload the saved PNGs so the materials (and the glTF export) use the files.
    tex = {}
    for key, p in paths.items():
        old = bpy.data.images.get(p.stem)
        img = bpy.data.images.load(str(p), check_existing=False)
        img.name = f"{p.stem}"
        img.colorspace_settings.name = "sRGB" if key == "basecolor" else "Non-Color"
        tex[key] = img
        if old is not None and old != img:
            bpy.data.images.remove(old)
    kit_mat = baked_material(f"{name}_kit", tex["basecolor"], tex["orm"], tex["normal"])
    # One baked hull material per paintable source material, each keeping its
    # default paint as the glTF colour factor (the web replaces it with the livery).
    hull_mats = {}
    for m in bmats:
        if _is_hull(m):
            node = m.node_tree.nodes.get("paint")
            paint = tuple(node.outputs[0].default_value)[:3] if node else (1, 1, 1)
            role = m.get("kit_role", m.name.split("_")[1] if "_" in m.name else "paint")
            hull_mats[m.name] = baked_material(f"hull_{name}_{role}", tex["basecolor"], tex["orm"], tex["normal"], paint=paint)
    for o in baked:
        for s in o.material_slots:
            if _bakeable(s.material):
                s.material = hull_mats[s.material.name] if _is_hull(s.material) else kit_mat
        if "Decal" in o.data.uv_layers:
            o.data.uv_layers.remove(o.data.uv_layers["Decal"])
    for m in mats:
        for nn in ("kit_bake_target", "kit_bake_uv"):
            n = m.node_tree.nodes.get(nn)
            if n is not None:
                m.node_tree.nodes.remove(n)
    return paths
