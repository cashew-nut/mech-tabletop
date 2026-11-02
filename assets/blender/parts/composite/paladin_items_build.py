"""Bake the Paladin's three items, put them on the walker in Blender and render the review shots (needs bpy).

    ~/bvenv/bin/python -I paladin_items_build.py PARTS ITEMS [--samples 32] [--size 1024] [--no-render] [--only items|loadouts|sockets]

PARTS  models/paladin-composite-1.5x (needs paladin_composite.blend: the assembled walker)
ITEMS  paladin_items.py's output folder (work/<item>/kit/<item>.npz and the Meshy textures; hosts/*.npz). Writes into it:

  glb/<item>.glb       the game part: kit mm (print mm / 1.5), origin on its joint like the other composite parts
  stl/<item>.stl       the print copy (closed, peg and magnet pocket in place)
  textures/            the baked colour, orm and normal maps
  paladin_items.blend  the walker with the hardpoints, the carapace gun on both shoulders and the shield on the left forearm
                       (the racks are hidden spares on both shoulders; the old pods are hidden)
  renders/items.png    each item on its own, three views
  renders/loadouts.png the walker with the items fitted
  renders/sockets.png  each item lifted out of its hardpoint: the peg and the magnet pocket, and the empty socket

build.py does the baking (the same code as every other composite part): the Meshy surface is the bake source, the
collar, peg and hardpoint bake as gunmetal and gold.
"""
import json
import math
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
from kit.render import studio, shot, post  # noqa: E402
from layout import joint, PS  # noqa: E402

# item: (budget triangles, texture size, joint its origin sits on, host part, hardpoint)
ITEMS = {
    "carapace-gun": (4500, 768, "chest", "torso", "shoulder"),
    "missile-rack": (7000, 1024, "chest", "torso", "shoulder"),
    "kinetic-shield": (7000, 1024, "elbow", "forearm", "bracer"),
}
GUNMETAL = ((0.035, 0.035, 0.04, 1.0), 0.42, 1.0)


def gunmetal():
    m = bpy.data.materials.new("hardpoint_gunmetal")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = GUNMETAL[0]
    b.inputs["Roughness"].default_value = GUNMETAL[1]
    b.inputs["Metallic"].default_value = GUNMETAL[2]
    return m


def load_host(path, name, mat):
    d = np.load(path)
    me = bpy.data.meshes.new(name)
    me.from_pydata(d["P"].tolist(), [], d["T"].tolist())
    me.update()
    for p in me.polygons:
        p.use_smooth = False
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def parent_keep(ob, parent):
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    ob.parent = parent
    ob.matrix_parent_inverse = parent.matrix_world.inverted()
    ob.matrix_world = mw


def bake_item(name, items, size_override):
    budget, size, joint_name, _, _ = ITEMS[name]
    build.TREE[name] = (None, joint_name, None)
    build.BUDGET[name] = (budget, size_override or size)
    work = items / "work" / name
    imgs = {}
    for k, nm, cs in ((0, "base", "sRGB"), (1, "mr", "Non-Color"), (2, "nrm", "Non-Color")):
        im = bpy.data.images.load(str(work / f"tex_{k}.jpg"))
        im.colorspace_settings.name = cs
        imgs[nm] = im
    mats = build.high_materials(imgs)
    ob, info = build.build_part(name, work, items, mats, size_override, True)
    for m in [m for m in bpy.data.materials if m.name.startswith(("high_", "lo_"))]:
        bpy.data.materials.remove(m)
    # the game copy alone, at kit size, origin on its joint
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    saved = ob.location.copy()
    ob.location = (0, 0, 0)
    ob.data.transform(Matrix.Scale(1 / PS, 4))
    (items / "glb").mkdir(exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(items / "glb" / f"{name}.glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_apply=True)
    ob.location = saved
    ob.data.transform(Matrix.Scale(PS, 4))
    return ob, info


def main(a):
    parts, items = Path(a[0]), Path(a[1])
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 32
    size = int(a[a.index("--size") + 1]) if "--size" in a else None
    bpy.ops.wm.open_mainfile(filepath=str(parts / "paladin_composite.blend"))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    info = {}
    base = {}
    for name in ITEMS:
        base[name], info[name] = bake_item(name, items, size)
    json.dump(info, open(items / "build_report.json", "w"), indent=1)

    # the walker: hide the old pods, add the hardpoints, hang each item from its host
    obj = bpy.data.objects
    for n in ("pod_L", "pod_R"):
        obj[n].hide_render = True
        obj[n].hide_set(True)
        obj[n]["retired"] = "replaced by item carapace-gun"
    mat = gunmetal()
    hosts = {"shoulder_L": ("torso", None), "shoulder_R": ("torso", None), "bracer_L": ("forearm_L", None)}
    hp = {}
    for k, (parent, _) in hosts.items():
        hp[k] = load_host(items / "hosts" / f"{k}.npz", f"hardpoint_{k}", mat)
        parent_keep(hp[k], obj[parent])
    # right bracer: the mirrored left one, on the right forearm (the forearm's own joint is its origin)
    r = bpy.data.objects.new("hardpoint_bracer_R", hp["bracer_L"].data)
    bpy.context.scene.collection.objects.link(r)
    r.location = Vector(joint("elbow", "R"))
    r.scale = (-1, 1, 1)
    parent_keep(r, obj["forearm_R"])
    hp["bracer_R"] = r

    placed = {}
    for name, (_, _, jname, host, _) in ITEMS.items():
        ob = base[name]
        ob.name = f"{name}_L"
        right = bpy.data.objects.new(f"{name}_R", ob.data)
        bpy.context.scene.collection.objects.link(right)
        right.location = Vector(joint(jname, "R"))
        right.scale = (-1, 1, 1)
        for side, o in (("L", ob), ("R", right)):
            parent_keep(o, obj[host if host == "torso" else f"{host}_{side}"])
        placed[name] = {"L": ob, "R": right}
    # loadout: carapace gun on both shoulders, shield on the left forearm; the rest are hidden spares
    spare = [placed["missile-rack"]["L"], placed["missile-rack"]["R"], placed["kinetic-shield"]["R"]]
    for o in spare:
        o["spare"] = True
    for o in [hp["bracer_R"]]:
        o["spare"] = True
    for o in spare + [hp["bracer_R"]]:
        o.hide_render = True
        o.hide_set(True)
    bpy.context.view_layer.update()
    for im in bpy.data.images:
        if im.filepath and not im.packed_file and im.source == "FILE":
            try:
                im.pack()
            except RuntimeError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=str((items / "paladin_items.blend").resolve()))
    if "--no-render" in a:
        return

    kit.render.studio()
    rd = items / "renders"
    rd.mkdir(exist_ok=True)
    allm = [o for o in bpy.data.objects if o.type == "MESH"]
    body = [o for o in allm if not o.get("spare") and not o.get("retired")]
    item_obs = {o for n in placed.values() for o in n.values()}
    host_obs = {*hp.values()}

    def show(names):
        for o in allm:
            on = (o in body and o not in item_obs and o not in host_obs) or o in names or (o in host_obs and o in names)
            o.hide_render = not on

    def sheet(paths, out, cols, labels):
        from render import sheet as _sheet
        _sheet(paths, out, cols, labels)

    only = a[a.index("--only") + 1] if "--only" in a else None
    # 1. items alone
    paths, labels = [], []
    for name in ITEMS if only in (None, "items") else ():
        for o in allm:
            o.hide_render = True
        ob = placed[name]["L"]
        ob.hide_render = False
        for az, el in ((30, 16), (120, 12), (210, 22)):
            p = rd / f"_alone_{name}_{az}.png"
            shot([ob], p, az=az, el=el, samples=samples, res=(600, 640), margin=0.8)
            post(p)
            paths.append(p)
            labels.append(f"{name} {az}")
    if paths:
        sheet(paths, rd / "items.png", 3, labels)

    # 2. the walker with the items fitted
    def fitted(spec):
        names = []
        for n, sides in spec.items():
            names += [placed[n][s] for s in sides]
            if n == "kinetic-shield":
                names += [hp["bracer_L"]]
        names += [hp["shoulder_L"], hp["shoulder_R"]]
        return names
    paths, labels = [], []
    plans = [
        ("carapace guns + shield", {"carapace-gun": "LR", "kinetic-shield": "L"}, (25, 8), (205, 10)),
        ("missile racks + shield", {"missile-rack": "LR", "kinetic-shield": "L"}, (25, 8), (205, 10)),
    ]
    for label, spec, v1, v2 in plans if only in (None, "loadouts") else ():
        show(fitted(spec))
        for az, el in (v1, v2):
            p = rd / f"_load_{label[:4]}_{az}.png"
            shot([o for o in allm if not o.hide_render], p, az=az, el=el, samples=samples, res=(800, 1000), margin=0.8)
            post(p)
            paths.append(p)
            labels.append(f"{label} ({'front' if az < 90 else 'back'})")
    if paths:
        sheet(paths, rd / "loadouts.png", 4, labels)

    # 3. sockets: each item lifted out of its hardpoint along the socket axis, and the empty socket
    rep = json.loads((items / "fit.json").read_text())
    lift = {"carapace-gun": np.array(rep["shoulder_hardpoint"]["axis_out"]), "missile-rack": np.array(rep["shoulder_hardpoint"]["axis_out"]),
            "kinetic-shield": np.array(rep["bracer_hardpoint"]["axis_out"])}
    paths, labels = [], []
    paths, labels = [], []
    nearby = [bpy.data.objects[n] for n in ("torso", "back", "helm", "pauldron_L", "arm_L", "forearm_L", "hand_L", "blade_L")]
    for name in ITEMS if only in (None, "sockets") else ():
        ob = placed[name]["L"]
        shown = nearby + [ob] + ([hp["bracer_L"]] if name == "kinetic-shield" else [hp["shoulder_L"], hp["shoulder_R"]])
        for o in allm:
            o.hide_render = o not in shown
        ob_loc = ob.location.copy()
        for gap, tag in ((9.0, "lifted"), (0.0, "seated")):
            ob.location = ob_loc + Vector(lift[name] * gap)
            bpy.context.view_layer.update()
            p = rd / f"_sock_{name}_{tag}.png"
            az, el = (35, 16) if name != "kinetic-shield" else (70, 12)
            shot([ob, hp["bracer_L"], bpy.data.objects["forearm_L"]] if name == "kinetic-shield" else [ob, hp["shoulder_L"]], p, az=az, el=el, samples=samples, res=(700, 800), margin=1.0)
            post(p)
            paths.append(p)
            labels.append(f"{name} {tag}")
        ob.location = ob_loc
    if paths:
        sheet(paths, rd / "sockets.png", 2, labels)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
