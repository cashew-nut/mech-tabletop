"""Finish the Brute's designed items: game GLBs, a .blend with the items on the walker, and review renders (needs bpy).

    MODEL=brute ~/bvenv/bin/python -I brute_items_build.py PARTS ITEMS [--samples 32] [--no-render]

PARTS is the Brute composite build (needs brute_composite.blend); ITEMS is brute_items.py's output folder. Writes into ITEMS:

  glb/<item>.glb            the game part: kit mm (print mm / GAME_SCALE), origin on the elbow joint, like the gun forearms
  textures/palette_*.png    a 128 px palette atlas: one 64 px swatch per paint (livery red, iron, steel, brass)
  brute_items.blend         the Brute composite with the claw and rail cannon added as hidden spares on both elbows
  renders/items.png         each item on its own, three views
  renders/loadouts.png      the walker with the claw and rail cannon fitted (left and right) and the guns swapped out
  renders/fit.png           the claw and the rail cannon on the elbow, close up, beside the cannon arm

The items are not baked from a sculpt: every face takes the middle of its paint's swatch, so the textures are tiny and the
livery red is tinted by the web exactly like the Brute's own baked parts (`hull_*_livery`).
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import kit  # noqa: E402
from kit import bake as kb  # noqa: E402
from kit.render import studio, shot, post  # noqa: E402
from layout import PS, joint  # noqa: E402
from brute_items import ITEMS, NAMES, PAINT  # noqa: E402

SW = 64            # swatch size, px; the atlas is 2 x 2 swatches


def swatch_uv(i):
    """The middle of paint i's swatch (glTF UV origin top-left: Blender's is bottom-left, so flip v)."""
    cx, cy = (i % 2 + 0.5) / 2, (i // 2 + 0.5) / 2
    return cx, 1 - cy


def palette_textures(out):
    from PIL import Image
    tdir = out / "textures"
    tdir.mkdir(parents=True, exist_ok=True)
    base = Image.new("RGB", (2 * SW, 2 * SW), (0, 0, 0))
    orm = Image.new("RGB", (2 * SW, 2 * SW), (255, 0, 0))
    for i, name in enumerate(NAMES):
        col, rough, metal = PAINT[name]
        box = (i % 2 * SW, i // 2 * SW, (i % 2 + 1) * SW, (i // 2 + 1) * SW)
        lin = tuple(int(round(255 * c)) for c in col)
        base.paste(lin, box)
        orm.paste((255, int(round(255 * rough)), int(round(255 * metal))), box)
    nrm = Image.new("RGB", (2 * SW, 2 * SW), (128, 128, 255))
    paths = {}
    for key, im in (("basecolor", base), ("orm", orm), ("normal", nrm)):
        p = tdir / f"palette_{key}.png"
        im.save(p)
        paths[key] = p
    return paths


def make_material(paths, name):
    tex = {}
    for key, p in paths.items():
        im = bpy.data.images.load(str(p), check_existing=False)
        im.colorspace_settings.name = "sRGB" if key == "basecolor" else "Non-Color"
        tex[key] = im
    return kb.baked_material(name, tex["basecolor"], tex["orm"], tex["normal"])


def load_item(key, solids, mat):
    z = np.load(solids / f"{key}.npz")
    P, T, paint = z["P"], z["T"], z["paint"]
    me = bpy.data.meshes.new(key)
    me.from_pydata(P.tolist(), [], T.tolist())
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    uvs = np.array([swatch_uv(int(i)) for i in paint], np.float32)
    uv.data.foreach_set("uv", np.repeat(uvs, 3, axis=0).ravel())
    me.polygons.foreach_set("use_smooth", np.zeros(len(T), bool))
    me.materials.append(mat)
    ob = bpy.data.objects.new(key, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def export_glb(ob, path):
    """Origin on the elbow joint, kit size (the same convention as the gun forearms), then export alone."""
    j = Vector(joint("elbow"))
    saved = ob.data.copy()
    ob.data.transform(Matrix.Scale(1 / PS, 4) @ Matrix.Translation(-j))
    ob.location = (0, 0, 0)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_yup=True, export_apply=True)
    ob.data = saved


def main(a):
    parts, items = Path(a[0]), Path(a[1])
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 32
    paths = palette_textures(items)
    # 1. game GLBs (a scratch scene: nothing else is in it)
    kit.reset_scene()
    mat = make_material(paths, "hull_brute_item_livery")
    for key in ITEMS:
        ob = load_item(key, items / "solids", mat)
        export_glb(ob, items / "glb" / f"{key}.glb")
        bpy.data.objects.remove(ob)
    # 2. the Brute with the items on the elbows
    bpy.ops.wm.open_mainfile(filepath=str(parts / "brute_composite.blend"))
    kit.render.studio()
    scene = bpy.context.scene
    mat = make_material(paths, "items_palette")
    pauldron = {"L": bpy.data.objects["pauldron_L"], "R": bpy.data.objects["pauldron_R"]}
    placed = {}
    for key in ITEMS:
        for side in ("L", "R"):
            ob = load_item(key, items / "solids", mat)
            j = Vector(joint("elbow", "L"))
            ob.data.transform(Matrix.Translation(-j))        # origin on the elbow joint, like the guns
            if side == "L":
                ob.location = j
            else:       # the right copy is the left one mirrored, like every sided part
                ob.location = Vector(joint("elbow", "R"))
                ob.scale = (-1, 1, 1)
            ob.name = f"{key}_{side}"
            bpy.context.view_layer.update()
            mw = ob.matrix_world.copy()
            ob.parent = pauldron[side]
            ob.matrix_parent_inverse = pauldron[side].matrix_world.inverted()
            ob.matrix_world = mw
            ob["spare"] = True
            ob.hide_render = True
            ob.hide_set(True)
            placed[ob.name] = ob
    bpy.context.view_layer.update()
    for im in bpy.data.images:
        if im.filepath and not im.packed_file and im.source == "FILE":
            try:
                im.pack()
            except RuntimeError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=str((items / "brute_items.blend").resolve()))
    if "--no-render" in a:
        return
    rd = items / "renders"
    rd.mkdir(exist_ok=True)
    allm = [o for o in bpy.data.objects if o.type == "MESH"]
    body = [o for o in allm if not o.get("spare")]
    guns = {n for n in ("rockets_L", "gatling_R", "rockets_R", "gatling_L")}

    def show(names):
        for o in allm:
            on = (o in body and o.name not in guns) or o.name in names
            o.hide_render = not on

    def sheet(paths_, out_, cols, labels):
        from render import sheet as _sheet
        _sheet(paths_, out_, cols, labels)

    # items alone, three views
    paths_, labels = [], []
    for key in ITEMS:
        show([f"{key}_L"])
        for o in allm:
            if o.name != f"{key}_L":
                o.hide_render = True
        for az, el in ((35, 14), (125, 10), (215, 20)):
            p = rd / f"_item_{key}_{az}.png"
            shot([placed[f"{key}_L"]], p, az=az, el=el, samples=samples, res=(600, 640), margin=0.75)
            post(p)
            paths_.append(p)
            labels.append(f"{key} {az}")
    sheet(paths_, rd / "items.png", 3, labels)
    # the walker with the claw on the left and the rail cannon on the right, and the other way round
    paths_ = []
    for left, right in (("claw", "rail"), ("rail", "claw")):
        show([f"{left}_L", f"{right}_R"])
        for az in (25, 335):
            p = rd / f"_load_{left}_{az}.png"
            shot([o for o in allm if not o.hide_render], p, az=az, el=8, samples=samples, res=(800, 1000), margin=0.75)
            post(p)
            paths_.append(p)
    sheet(paths_, rd / "loadouts.png", 4, ["claw left, rail right", "claw left, other side", "rail left, claw right", "rail left, other side"])
    # the elbow, close up: cannon arm, claw, rail cannon on the same socket
    paths_, labels = [], []
    for name, label in (("rockets_L", "cannon arm"), ("claw_L", "industrial claw"), ("rail_L", "rail cannon")):
        show([name])
        p = rd / f"_fit_{name}.png"
        shot([o for o in allm if o.name in (name, "pauldron_L", "torso", "thigh_L")], p, az=60, el=8, samples=samples, res=(700, 800), margin=1.0)
        post(p)
        paths_.append(p)
        labels.append(label)
    sheet(paths_, rd / "fit.png", 3, labels)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
