"""Shared helpers for the Brass Charter Blender scripts.

Conventions (match apps/web/src/model/parts.ts):
- 1 Blender unit = 1 mm. Models are built at tabletop scale.
- Blender is Z-up; the walker faces -Y (Blender's "Front" view looks at it).
  The glTF exporter converts this to the web's Y-up, +Z-forward.
- Each chassis is a root object named `chassis_<id>` with child empties
  named `mount_<location>_<slot>` (location: armLeft, armRight, core, legs).
- Each item is a root object named `item_<id>`, modelled at Scout scale with
  its origin at the attachment point and its barrel pointing -Y.
- Materials whose name starts with "hull" are recoloured by the web builder.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
PARTS_DIR = REPO / "apps" / "web" / "public" / "parts"
LOCATIONS = ("armLeft", "armRight", "core", "legs")
# Items are modelled at Scout scale and grow with the chassis, as in the web view.
PART_SCALE = {"scout": 1.0, "striker": 1.2, "bulwark": 1.4, "titan": 1.7}


def load(name):
    return json.loads((DATA / name).read_text())


def chassis_defs():
    return {c["id"]: c for c in load("chassis.json")["chassis"]}


def equipment_defs():
    return {e["id"]: e for e in load("equipment.json")["equipment"]}


def script_args():
    """Arguments after `--` on the Blender command line, or after the script
    name when run with the pip `bpy` module (`python script.py args`)."""
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    if sys.argv and sys.argv[0].endswith(".py"):
        return sys.argv[1:]
    return []


def chassis_frames():
    """{class id: frame id} from chassis.json (each class names its frame)."""
    return {c["id"]: c.get("frame", c["id"]) for c in load("chassis.json")["chassis"]}
