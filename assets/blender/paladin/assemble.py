"""Assemble the Iron Covenant Paladin from the published kit GLBs in Blender
and render it beside the north-star render.

    ~/bvenv/bin/python assets/blender/paladin/assemble.py OUT_DIR [--az 35 --el 8 --samples 48] [--blend f.blend]

The kit joints come from covenant_frame_titan; sided parts are mirrored on the
right as in the web. Items hang on the frame's mounts at the titan scale.
"""
import json, math, sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))
import kit  # noqa: E402
from kit.skeleton import COMPONENTS, joint_name  # noqa: E402
from common import PARTS_DIR, PART_SCALE  # noqa: E402

FACTION, CLS, FRAME = "covenant", "paladin", "titan"
LOADOUT = {"armLeft": ["lance"], "armRight": ["lance"], "core": []}


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return roots[0], new


def true_name(o):
    for key in ("mount", "joint", "standin_name"):
        if key in o:
            return o[key]
    return o.name.split(".")[0]


def resolve(names, comp, right):
    for c in ([f"{comp}-right"] if right else []) + [comp]:
        for v in (CLS, FRAME):
            n = f"{FACTION}_{c}_{v}"
            if n in names:
                return n, c.endswith("-right")
    return None, False


def build(loadout=LOADOUT):
    manifest = json.loads((PARTS_DIR / "manifest.json").read_text())
    names = manifest["kit"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    root, objects = import_glb(PARTS_DIR / names[f"{FACTION}_frame_{FRAME}"])
    joints = {true_name(o): o for o in objects if true_name(o).startswith("joint_")}
    standins = {true_name(o): o for o in objects if true_name(o).startswith("standin_")}
    for comp in COMPONENTS.values():
        for side in (("L", "R") if comp.get("sided") else (None,)):
            name, own = resolve(names, comp["id"], side == "R")
            if name is None:
                continue
            part, new = import_glb(PARTS_DIR / names[name])
            objects += new
            part.parent = joints[joint_name(comp["joint"], side)]
            part.matrix_parent_inverse.identity()
            part.location = (0, 0, 0)
            part.scale = (-1 if side == "R" and not own else 1, 1, 1)
            st = standins.get(f"standin_{comp['id']}" + (f"_{side}" if side else ""))
            if st is not None:
                for o in [st, *st.children_recursive]:
                    bpy.data.objects.remove(o)
    mounts = {true_name(o): o for o in objects if true_name(o).startswith("mount_")}
    s = PART_SCALE[FRAME]
    for loc, items in loadout.items():
        for slot, item in enumerate(items):
            anchor = mounts.get(f"mount_{loc}_{slot}")
            f = manifest["items"].get(f"{item}@{FACTION}") or manifest["items"][item]
            part, _ = import_glb(PARTS_DIR / f)
            part.parent = anchor
            part.matrix_parent_inverse.identity()
            part.location, part.rotation_euler, part.scale = (0, 0, 0), (0, 0, 0), (s, s, s)
    bpy.context.view_layer.update()
    # drop any leftover stand-ins
    for o in list(bpy.data.objects):
        if true_name(o).startswith("standin_") and o.name in bpy.data.objects:
            bpy.data.objects.remove(o)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    return root, meshes


def main():
    a = sys.argv[1:]
    out = Path(a[0])
    opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
    root, meshes = build()
    kit.render.studio(floor=True)
    p = kit.render.shot(meshes, out / "paladin-current.png", az=opt("--az", 30.0), el=opt("--el", 6.0),
                        samples=opt("--samples", 32), res=(720, 900), margin=opt("--margin", 0.75))
    kit.render.post(p)
    if "--blend" in a:
        bpy.ops.wm.save_as_mainfile(filepath=a[a.index("--blend") + 1])


main()
