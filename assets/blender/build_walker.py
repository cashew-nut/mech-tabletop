"""Assemble one war-walker from a lance file using the exported part GLBs,
then save an STL for printing (and optionally a .blend for posing).

    blender --background --python assets/blender/build_walker.py -- \
        lance.json [walker-name-or-index] [out.stl] [--blend out.blend]

The lance file is the JSON the Lance Ledger exports (or data/lances/examples.json,
whose lances are under "lances"). Missing parts are reported and skipped.
"""
import json
import re
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from common import LOCATIONS, PART_SCALE, PARTS_DIR, equipment_defs, script_args  # noqa: E402


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    return roots[0], new


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


def main():
    args = script_args()
    blend_out = None
    if "--blend" in args:
        i = args.index("--blend")
        blend_out = Path(args[i + 1])
        args = args[:i] + args[i + 2:]
    if not args:
        sys.exit(__doc__)
    walker = find_walker(json.loads(Path(args[0]).read_text()), args[1] if len(args) > 1 else None)
    slug = re.sub(r"[^a-z0-9]+", "-", walker["name"].lower()).strip("-") or "walker"
    out = Path(args[2]) if len(args) > 2 else Path(f"{slug}.stl")

    manifest = json.loads((PARTS_DIR / "manifest.json").read_text())
    equipment = equipment_defs()
    bpy.ops.wm.read_factory_settings(use_empty=True)

    chassis_file = manifest.get("chassis", {}).get(walker["chassis"])
    if not chassis_file:
        sys.exit(f"No exported chassis part for {walker['chassis']!r}; run export_parts.py first")
    root, objects = import_glb(PARTS_DIR / chassis_file)
    root.name = walker["name"]
    mounts = {o.name.split(".")[0]: o for o in objects if o.name.startswith("mount_")}
    scale = PART_SCALE.get(walker["chassis"], 1.0)

    for loc in LOCATIONS:
        slot = 0
        for item_id in walker["loadout"].get(loc, []):
            anchor = mounts.get(f"mount_{loc}_{slot}")
            slot += equipment[item_id]["slots"]
            file = manifest.get("items", {}).get(item_id)
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
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.wm.stl_export(filepath=str(out.resolve()), export_selected_objects=True, apply_modifiers=True)
    print(f"Saved {out}")
    if blend_out:
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_out.resolve()))
        print(f"Saved {blend_out}")


main()
