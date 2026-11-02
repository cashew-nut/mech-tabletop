"""Bake the Seer's Hellfire Missiles, put the launcher on the walker in Blender and render the review shots (needs bpy).

    MODEL=seer ~/bvenv/bin/python -I seer_items_build.py PARTS ITEMS [--samples 32] [--size 1024] [--no-render]

PARTS  models/seer-composite-v2 (needs seer_composite.blend: the assembled walker)
ITEMS  seer_items.py's output folder (work/<item>/kit/<item>.npz and the Meshy textures; hosts/*.npz; fit.json). Writes into it:

  glb/hellfire-missiles.glb  the game part: kit mm (print mm / 1.5), origin on the socket seat, +Z up out of the socket, -Y forward
  stl/hellfire-missiles.stl  the print copy (closed, peg and magnet pocket in place)
  textures/                  the baked colour, orm and normal maps
  seer_items.blend           the walker with the shoulder hardpoint and the launcher on it; on a Seer whose right arm is the
                             mirror of the left (seer-composite-v2) the right shoulder gets the mirrored copy too
  renders/items.png          the launcher on its own, three views
  renders/loadout.png        the walker with the launcher fitted, front, three-quarter, side and back
  renders/socket.png         the launcher lifted out of its hardpoint (peg and magnet pocket) and seated

build.py does the baking (the same code as every other composite part): the Meshy surface is the bake source, the collar,
peg and hardpoint bake as gunmetal and gold.
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import kit  # noqa: E402
import build  # noqa: E402
from kit.render import shot, post  # noqa: E402
from layout import PS  # noqa: E402
from paladin_items_build import load_host, parent_keep  # noqa: E402

ITEM = "hellfire-missiles"
BUDGET = (9000, 1024)     # triangles, texture px: the serrated fins need more triangles than the Paladin's rack


def gold():
    """The hardpoint sleeve's finish: the Seer's knuckle gold (build.GOLD), like its joint housings."""
    m = bpy.data.materials.new("hardpoint_gold")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*build.GOLD[0], 1.0)
    b.inputs["Roughness"].default_value = build.GOLD[1]
    b.inputs["Metallic"].default_value = build.GOLD[2]
    return m


def bake_item(items, sock_c, size_override):
    build.TREE[ITEM] = (None, "chest", None)
    build.BUDGET[ITEM] = (BUDGET[0], size_override or BUDGET[1])
    work = items / "work" / ITEM
    imgs = {}
    for k, nm, cs in ((0, "base", "sRGB"), (1, "mr", "Non-Color"), (2, "nrm", "Non-Color")):
        im = bpy.data.images.load(str(work / f"tex_{k}.jpg"))
        im.colorspace_settings.name = cs
        imgs[nm] = im
    mats = build.high_materials(imgs)
    ob, info = build.build_part(ITEM, work, items, mats, size_override, True)
    for m in [m for m in bpy.data.materials if m.name.startswith(("high_", "lo_"))]:
        bpy.data.materials.remove(m)
    # origin on the socket seat instead of the chest joint build.py used
    c = Vector(sock_c)
    ob.data.transform(Matrix.Translation(ob.location - c))
    ob.location = c
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    ob.location = (0, 0, 0)
    ob.data.transform(Matrix.Scale(1 / PS, 4))
    (items / "glb").mkdir(exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(items / "glb" / f"{ITEM}.glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_apply=True)
    ob.data.transform(Matrix.Scale(PS, 4))
    ob.location = c
    return ob, info


def main(a):
    parts, items = Path(a[0]), Path(a[1])
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 32
    size = int(a[a.index("--size") + 1]) if "--size" in a else None
    fit = json.loads((items / "fit.json").read_text())
    hp = fit["shoulder_hardpoint"]
    sock_c = hp["centre"]
    bpy.ops.wm.open_mainfile(filepath=str(parts / "seer_composite.blend"))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    ob, info = bake_item(items, sock_c, size)
    json.dump({ITEM: info}, open(items / "build_report.json", "w"), indent=1)

    obj = bpy.data.objects
    arm_l = obj.get("arm") or obj["arm_L"]      # v1 names the left arm `arm`, v2 `arm_L`
    mat = gold()
    boss_l = load_host(items / "hosts" / "shoulder_L.npz", "hardpoint_shoulder_L", mat)
    parent_keep(boss_l, arm_l)
    ob.name = f"{ITEM}_L"
    parent_keep(ob, arm_l)
    placed = [ob]
    hosts = [boss_l]
    # the right shoulder, when the right arm is the mirror of the left (no native arm_r)
    if "arm_r" not in obj:
        arm_r = obj.get("arm_R")
        if arm_r is not None:
            for src, nm in ((boss_l, "hardpoint_shoulder_R"), (ob, f"{ITEM}_R")):
                r = bpy.data.objects.new(nm, src.data)
                bpy.context.scene.collection.objects.link(r)
                r.matrix_world = Matrix.Scale(-1, 4, (1, 0, 0)) @ src.matrix_world
                parent_keep(r, arm_r)
                (placed if nm.startswith(ITEM) else hosts).append(r)
    # the right pauldron plate lies over the right shoulder drum: cut it clear of the sleeve and collar (seer_items.py's cutter;
    # a modifier, so the baked pauldron keeps its UVs and textures)
    cut_path = items / "hosts" / "pauldron_r_cut.npz"
    if cut_path.exists() and "pauldron_r" in obj:
        d = np.load(cut_path)
        me = bpy.data.meshes.new("pauldron_r_cutter")
        me.from_pydata(d["P"].tolist(), [], d["T"].tolist())
        me.update()
        cutter = bpy.data.objects.new("pauldron_r_cutter", me)
        bpy.context.scene.collection.objects.link(cutter)
        cutter.hide_render = True
        cutter.hide_set(True)
        cutter["retired"] = "boolean cutter"
        mod = obj["pauldron_r"].modifiers.new("hellfire_clearance", "BOOLEAN")
        mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", cutter
    bpy.context.view_layer.update()
    for im in bpy.data.images:
        if im.filepath and not im.packed_file and im.source == "FILE":
            try:
                im.pack()
            except RuntimeError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=str((items / "seer_items.blend").resolve()))
    if "--no-render" in a:
        return

    kit.render.studio()
    rd = items / "renders"
    rd.mkdir(exist_ok=True)
    allm = [o for o in bpy.data.objects if o.type == "MESH" and not o.get("retired")]
    from render import sheet

    # 1. the launcher alone
    paths, labels = [], []
    for o in allm:
        o.hide_render = o is not ob
    for az, el, tag in ((300, 14, "left front"), (90, 6, "side"), (150, 24, "rear")):
        p = rd / f"_alone_{az}.png"
        shot([ob], p, az=az, el=el, samples=samples, res=(600, 640), margin=0.8)
        post(p)
        paths.append(p)
        labels.append(f"{ITEM} {tag}")
    sheet(paths, rd / "items.png", 3, labels)

    # 2. the walker with the launcher fitted
    for o in allm:
        o.hide_render = False
    paths, labels = [], []
    for az, el, tag in ((0, 6, "front"), (35, 12, "three-quarter"), (90, 6, "side"), (200, 12, "back")):
        p = rd / f"_load_{az}.png"
        shot(allm, p, az=az, el=el, samples=samples, res=(800, 1000), margin=0.8)
        post(p)
        paths.append(p)
        labels.append(tag)
    sheet(paths, rd / "loadout.png", 4, labels)

    # 3. the socket: the launcher lifted out of its hardpoint, and seated
    near = [obj[n] for n in ("torso", "arm", "arm_L", "pauldron", "helm", "crown") if n in obj]
    for o in allm:
        o.hide_render = o not in near + [ob, boss_l]
    loc = ob.location.copy()
    paths, labels = [], []
    for gap, tag in ((8.0, "lifted"), (0.0, "seated")):
        ob.location = loc + Vector((0, 0, gap))
        bpy.context.view_layer.update()
        p = rd / f"_sock_{tag}.png"
        shot([ob, boss_l], p, az=60, el=18, samples=samples, res=(700, 800), margin=1.0)
        post(p)
        paths.append(p)
        labels.append(f"{ITEM} {tag}")
    ob.location = loc
    # the right shoulder (mirrored arm, launcher and sleeve through the cleared right pauldron), when there is one
    if len(placed) > 1:
        rob, rboss = placed[1], hosts[1]
        near_r = [obj[n] for n in ("torso", "arm_R", "pauldron_r", "helm", "crown", "back") if n in obj]
        for o in allm:
            o.hide_render = o not in near_r + [rob, rboss]
        p = rd / "_sock_right.png"
        shot([rob, rboss], p, az=300, el=18, samples=samples, res=(700, 800), margin=1.0)
        post(p)
        paths.append(p)
        labels.append(f"{ITEM} right shoulder")
    sheet(paths, rd / "socket.png", len(paths), labels)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
