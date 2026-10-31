"""Assemble one war-walker from a lance file using the exported part GLBs,
then save an STL for printing (and optionally a .blend for posing).

    blender --background --python assets/blender/build_walker.py -- \
        lance.json [walker-name-or-index] [out.stl] [--blend out.blend] [--kit]
    bvenv/bin/python assets/blender/build_walker.py lance.json ...

The lance file is the JSON the Lance Ledger exports (or data/lances/examples.json,
whose lances are under "lances"). The body comes from, in order:

1. the faction kit: `<faction>_frame_<frame>` with a part on every joint,
   each `<faction>_<component>_<class>` or else `<faction>_<component>_<frame>`.
   It is used once every required component has a part, or always with --kit
   (stand-ins fill the gaps);
2. a whole-body `chassis_<class>` GLB.

Missing parts are reported and skipped. Items use `item_<id>@<faction>`, else `item_<id>`.
"""
import json
import re
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from common import LOCATIONS, PART_SCALE, PARTS_DIR, chassis_defs, equipment_defs, script_args  # noqa: E402
from kit.skeleton import COMPONENTS, joint_name  # noqa: E402


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


def find_walker(data, key):
    lances = data.get("lances", [data])
    walkers = [w for lance in lances for w in lance["walkers"]]
    if key is None:
        return walkers[0]
    if key.isdigit():
        return walkers[int(key)]
    for w in walkers:
        if w["name"].lower() == key.lower():
            return w
    sys.exit(f"No walker named {key!r}; have: {', '.join(w['name'] for w in walkers)}")


def resolve(kit, faction, component, cls, frame, right=False):
    """The kit part name for a component: class first, then frame."""
    comps = ([f"{component}-right"] if right else []) + [component]
    for comp in comps:
        for variant in (cls, frame):
            name = f"{faction}_{comp}_{variant}"
            if name in kit:
                return name, comp.endswith("-right")
    return None, False


def kit_body(manifest, faction, cls, frame, force):
    """Import the frame and hang kit parts on it. Returns (root, objects) or None."""
    kit = manifest.get("kit", {})
    frame_file = kit.get(f"{faction}_frame_{frame}")
    if not frame_file:
        return None
    plan = []
    missing = []
    for comp in COMPONENTS.values():
        for side in (("L", "R") if comp.get("sided") else (None,)):
            name, own_right = resolve(kit, faction, comp["id"], cls, frame, right=side == "R")
            if name is None:
                if comp["required"]:
                    missing.append(comp["id"])
                continue
            plan.append((comp, side, name, side == "R" and not own_right))
    if missing and not force:
        print(f"kit for {faction} {cls} is missing {', '.join(sorted(set(missing)))}; pass --kit to use stand-ins")
        return None
    root, objects = import_glb(PARTS_DIR / frame_file)
    joints = {true_name(o): o for o in objects if true_name(o).startswith("joint_")}
    standins = {true_name(o): o for o in objects if true_name(o).startswith("standin_")}
    for comp, side, name, mirror in plan:
        joint = joints[joint_name(comp["joint"], side)]
        part, new = import_glb(PARTS_DIR / kit[name])
        objects += new
        part.parent = joint
        part.matrix_parent_inverse.identity()
        part.location = (0, 0, 0)
        part.scale = (-1 if mirror else 1, 1, 1)
        stand = standins.get(f"standin_{comp['id']}" + (f"_{side}" if side else ""))
        if stand is not None:
            for o in [stand, *stand.children_recursive]:
                bpy.data.objects.remove(o)
    return root, [root, *root.children_recursive]


def main():
    args = script_args()
    blend_out = None
    if "--blend" in args:
        i = args.index("--blend")
        blend_out = Path(args[i + 1])
        args = args[:i] + args[i + 2:]
    force = "--kit" in args
    args = [a for a in args if a != "--kit"]
    if not args:
        sys.exit(__doc__)
    walker = find_walker(json.loads(Path(args[0]).read_text()), args[1] if len(args) > 1 else None)
    slug = re.sub(r"[^a-z0-9]+", "-", walker["name"].lower()).strip("-") or "walker"
    out = Path(args[2]) if len(args) > 2 else Path(f"{slug}.stl")

    manifest = json.loads((PARTS_DIR / "manifest.json").read_text())
    equipment = equipment_defs()
    cls = walker["chassis"]
    cdef = chassis_defs().get(cls, {})
    frame = cdef.get("frame", cls)
    faction = cdef.get("faction")
    bpy.ops.wm.read_factory_settings(use_empty=True)

    body = kit_body(manifest, faction, cls, frame, force) if faction else None
    if body is None:
        chassis_file = manifest.get("chassis", {}).get(cls)
        if not chassis_file:
            sys.exit(f"No exported kit or chassis part for {cls!r}; run the part scripts or export_parts.py first")
        body = import_glb(PARTS_DIR / chassis_file)
    root, objects = body
    root.name = walker["name"]
    mounts = {true_name(o): o for o in objects if true_name(o).startswith("mount_")}
    scale = PART_SCALE.get(frame, 1.0)

    for loc in LOCATIONS:
        slot = 0
        for item_id in walker["loadout"].get(loc, []):
            anchor = mounts.get(f"mount_{loc}_{slot}")
            slot += equipment[item_id]["slots"]
            items = manifest.get("items", {})
            file = items.get(f"{item_id}@{cls}") or items.get(f"{item_id}@{faction}") or items.get(item_id)
            if anchor is None or file is None:
                print(f"skip {item_id} in {loc}: {'no mount' if anchor is None else 'no exported part'}")
                continue
            part, _ = import_glb(PARTS_DIR / file)
            part.parent = anchor
            part.matrix_parent_inverse.identity()
            part.location = (0, 0, 0)
            part.rotation_mode = "XYZ"
            part.rotation_euler = (0, 0, 0)
            part.scale = (scale, scale, scale)

    bpy.context.view_layer.update()
    # Bake every transform into the meshes (mirrored parts get their faces
    # turned back outwards by Blender as it applies the negative scale).
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    if meshes:
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.wm.stl_export(filepath=str(out.resolve()), export_selected_objects=True, apply_modifiers=True)
    print(f"Saved {out}")
    if blend_out:
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out.resolve()))
        print(f"Saved {blend_out}")


main()
