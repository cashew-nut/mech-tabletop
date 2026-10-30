"""Export every part root in the open .blend as a GLB into
apps/web/public/parts/ and update manifest.json, so the web builder picks
them up in place of its placeholders.

    blender parts.blend --background --python assets/blender/export_parts.py -- [--only name ...] [--bake]
    bvenv/bin/python assets/blender/export_parts.py --blend parts.blend [--only name ...] [--bake]

Part roots are top-level objects named:

    chassis_<class>                   a whole walker body (the old single-piece route)
    item_<id> or item_<id>@<faction>  equipment, optionally in a faction's style
    <faction>_frame_<frame>           a kit skeleton (see kit/skeleton.py)
    <faction>_<component>_<variant>   a kit part for a class or a frame

`--bake` bakes node materials to textures first (kit.publish does the same
for part scripts). Then run `node scripts/compress-parts.mjs` for KTX2.
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import kit  # noqa: E402
from common import chassis_defs, equipment_defs, script_args  # noqa: E402
from kit.export import kind_of  # noqa: E402


def check(root, kind, key):
    """Warn about names the data doesn't know and chassis missing mounts."""
    if kind == "items" and key.split("@")[0] not in equipment_defs():
        print(f"warning {root.name}: no equipment with id {key.split('@')[0]!r} in data/equipment.json")
    if kind == "chassis":
        defs = chassis_defs()
        if key not in defs:
            print(f"skip {root.name}: no class with id {key!r} in data/chassis.json")
            return False
        mounts = [o.name.split(".")[0] for o in root.children_recursive if o.name.startswith("mount_")]
        missing = [f"mount_{loc}_{i}" for loc, n in defs[key]["slots"].items() for i in range(n) if f"mount_{loc}_{i}" not in mounts]
        if missing:
            print(f"warning {root.name}: missing {', '.join(missing)}")
    return True


def main():
    args = script_args()
    if "--blend" in args:
        bpy.ops.wm.open_mainfile(filepath=args[args.index("--blend") + 1])
    only = None
    if "--only" in args:
        only = {a for a in args[args.index("--only") + 1:] if not a.startswith("--")}
    for obj in list(bpy.data.objects):
        if obj.parent is not None:
            continue
        found = kind_of(obj.name)
        if not found:
            continue
        kind, key, _ = found
        if only and key not in only and obj.name not in only:
            continue
        if check(obj, kind, key):
            kit.publish(obj, bake="--bake" in args)


main()
