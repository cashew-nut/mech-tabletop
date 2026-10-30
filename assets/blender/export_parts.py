"""Export every `chassis_<id>` and `item_<id>` root in the open .blend as a
GLB into apps/web/public/parts/ and rewrite manifest.json, so the web
builder picks them up in place of its placeholders.

    blender parts.blend --background --python assets/blender/export_parts.py -- [--only id ...]
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
from common import PARTS_DIR, chassis_defs, equipment_defs, script_args  # noqa: E402


def subtree(obj):
    return [obj, *obj.children_recursive]


def export_root(root, path):
    # Blender makes names unique (mount_core_0.001 when several chassis share a
    # file), so record each mount's true name as a custom property for the web.
    for o in root.children_recursive:
        if o.name.startswith("mount_"):
            o["mount"] = o.name.split(".")[0]
    saved = root.location.copy()
    root.location = (0, 0, 0)  # parts are laid out in a row; export each at the origin
    bpy.ops.object.select_all(action="DESELECT")
    for o in subtree(root):
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_extras=True,
    )
    root.location = saved


def main():
    args = script_args()
    only = set(args[args.index("--only") + 1:]) if "--only" in args else None
    known = {"chassis": set(chassis_defs()), "items": set(equipment_defs())}
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = PARTS_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.setdefault("chassis", {})
    manifest.setdefault("items", {})

    for obj in bpy.data.objects:
        if obj.parent is not None:
            continue
        for prefix, kind in (("chassis_", "chassis"), ("item_", "items")):
            if not obj.name.startswith(prefix):
                continue
            part_id = obj.name[len(prefix):]
            if part_id not in known[kind]:
                print(f"skip {obj.name}: no {kind} with id {part_id!r} in data/")
                continue
            if only and part_id not in only:
                continue
            if kind == "chassis":
                mounts = [o.name.split(".")[0] for o in obj.children_recursive if o.name.startswith("mount_")]
                slots = chassis_defs()[part_id]["slots"]
                missing = [f"mount_{loc}_{i}" for loc, n in slots.items() for i in range(n)
                           if f"mount_{loc}_{i}" not in mounts]
                if missing:
                    print(f"warning {obj.name}: missing {', '.join(missing)}")
            file = f"{prefix}{part_id}.glb"
            export_root(obj, PARTS_DIR / file)
            manifest[kind][part_id] = file
            print(f"exported {file}")

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {manifest_path}")


main()
