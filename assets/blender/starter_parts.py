"""Generate a starter parts.blend: blocky chassis with mount empties and a
simple stand-in for every item, laid out in a row so you can replace them.

    blender --background --python assets/blender/starter_parts.py -- [out.blend]
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from common import LOCATIONS, PART_SCALE, chassis_defs, equipment_defs, script_args  # noqa: E402

BASE_MM = {"scout": 25, "striker": 32, "bulwark": 40, "titan": 50}


def material(name, rgb, metal=0.6, rough=0.45, emit=None):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1)
        bsdf.inputs["Emission Strength"].default_value = 2.0
    return mat


HULL = BRASS = IRON = GLOW = None  # created in main(), after the scene is reset


def mesh(kind, size, loc, mat, parent, name=None):
    if kind == "box":
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        bpy.context.object.scale = size
    else:  # cylinder, size = (radius, length): "cyl" points forward (-Y), "vcyl" stands up
        r, length = size
        rotation = (1.5708, 0, 0) if kind == "cyl" else (0, 0, 0)
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=length, location=loc, rotation=rotation)
    obj = bpy.context.object
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    obj.data.materials.append(mat)
    obj.parent = parent
    if name:
        obj.name = name
    return obj


def empty(name, loc=(0, 0, 0), parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 2
    obj.location = loc
    obj.parent = parent
    bpy.context.scene.collection.objects.link(obj)
    return obj


def make_chassis(c, x):
    frame = c.get("frame", c["id"])
    k = PART_SCALE[frame]
    root = empty(f"chassis_{c['id']}", (x, 0, 0))
    base_r = BASE_MM[frame] / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=base_r, depth=3, location=(0, 0, 1.5))
    base = bpy.context.object
    base.data.materials.append(IRON)
    base.parent = root
    hip = 12 * k
    for side in (-1, 1):
        mesh("box", (3 * k, 4 * k, hip), (side * 4 * k, 0, 3 + hip / 2), HULL, root)
    mesh("box", (11 * k, 6 * k, 3 * k), (0, 0, 3 + hip), IRON, root)
    torso_z = 3 + hip + 7 * k
    mesh("vcyl", (5.5 * k, 10 * k), (0, 0, torso_z), HULL, root)
    mesh("box", (5 * k, 4 * k, 3 * k), (0, -4 * k, torso_z + 5 * k), BRASS, root)
    mesh("cyl", (1.2 * k, 0.6 * k), (0, -6.2 * k, torso_z + 5 * k), GLOW, root)
    slots = c["slots"]
    for side, loc in ((1, "armRight"), (-1, "armLeft")):
        arm_x = side * 8.5 * k
        mesh("box", (3 * k, 4 * k, 9 * k), (arm_x, 0, torso_z), HULL, root)
        for i in range(slots[loc]):
            empty(f"mount_{loc}_{i}", (arm_x + side * 2.5 * k, -1 * k, torso_z + (2 - 4 * i) * k), root)
    for i in range(slots["core"]):
        empty(f"mount_core_{i}", ((i - (slots["core"] - 1) / 2) * 4 * k, 4 * k, torso_z + 6 * k), root)
    for i in range(slots["legs"]):
        side = 1 if i % 2 == 0 else -1
        empty(f"mount_legs_{i}", (side * 6 * k, 0, 3 + hip * 0.4), root)
    return root


def make_item(e, x):
    root = empty(f"item_{e['id']}", (x, -60, 0))
    weapon = e.get("weapon")
    if weapon:
        length = 4 + 1.5 * e["slots"] + {"melee": -1, "short": 0, "medium": 1, "long": 3}.get(weapon["range"], 0)
        mesh("box", (2.5, 3, 2.5), (0, 0, 0), IRON, root)
        mesh("cyl", (0.7, length), (0, -length / 2, 0), BRASS, root)
    else:
        mesh("box", (2.5 * e["slots"], 2, 2.5), (0, 0, 0), BRASS if e["category"] != "defence" else HULL, root)
    return root


def main():
    out = Path(script_args()[0]) if script_args() else Path(__file__).parent / "parts.blend"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"
    global HULL, BRASS, IRON, GLOW
    HULL = material("hull", (0.35, 0.12, 0.08), metal=0.3, rough=0.6)
    BRASS = material("brass", (0.71, 0.53, 0.22), metal=0.9, rough=0.35)
    IRON = material("iron", (0.15, 0.15, 0.16), metal=0.8, rough=0.55)
    GLOW = material("aether", (0.4, 0.9, 1.0), emit=(0.4, 0.9, 1.0))
    for i, c in enumerate(chassis_defs().values()):
        make_chassis(c, i * 70)
    for i, e in enumerate(equipment_defs().values()):
        make_item(e, i * 12)
    bpy.ops.wm.save_as_mainfile(filepath=str(out.resolve()))
    print(f"Saved {out}")


main()
