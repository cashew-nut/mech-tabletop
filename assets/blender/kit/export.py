"""GLB export and the parts manifest the web game reads.

    kit.publish(root)        # bake (if needed), export, add to the manifest

Where things go, by root name:

    chassis_<id>                     parts/chassis_<id>.glb       manifest "chassis"
    item_<id>, item_<id>@<faction>   parts/item_<id>[@f].glb      manifest "items"
    <faction>_frame_<frame>          parts/kit/<name>.glb         manifest "kit"
    <faction>_<component>_<variant>  parts/kit/<name>.glb         manifest "kit"

The web loads KTX2 textures; run `node scripts/compress-parts.mjs` after
exporting to convert the PNGs packed in each GLB (publish prints a reminder).
"""
import json
import sys
from pathlib import Path

import bpy

from .core import parse_name, subtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import PARTS_DIR  # noqa: E402

BAKE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "bake"


def kind_of(name):
    """("chassis" | "items" | "kit", manifest key, file name) for a root name, or None."""
    base = name.split(".")[0]
    if base.startswith("chassis_"):
        return "chassis", base[len("chassis_"):], f"{base}.glb"
    if base.startswith("item_"):
        return "items", base[len("item_"):], f"{base}.glb"
    if parse_name(base):
        return "kit", base, f"kit/{base}.glb"
    return None


def export_glb(root, path):
    """Export `root` and everything under it, at the origin, as a GLB."""
    # Blender makes names unique (mount_core_0.001 when several parts share a
    # file), so record the true names as custom properties for the web.
    for o in root.children_recursive:
        for prefix, key in (("mount_", "mount"), ("joint_", "joint"), ("standin_", "standin_name")):
            if o.name.startswith(prefix):
                o[key] = o.get(key, o.name.split(".")[0])
    saved = root.location.copy()
    root.location = (0, 0, 0)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for o in subtree(root):
        if not o.get("kit_cutter"):
            o.hide_set(False)
            o.select_set(True)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_extras=True,
        export_image_format="AUTO",
    )
    root.location = saved
    return path


def update_manifest(kind, key, file):
    path = PARTS_DIR / "manifest.json"
    manifest = json.loads(path.read_text()) if path.exists() else {}
    for k in ("chassis", "items", "kit"):
        manifest.setdefault(k, {})
    manifest[kind][key] = file
    manifest[kind] = dict(sorted(manifest[kind].items()))
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def needs_bake(root):
    from .bake import _bakeable
    return any(_bakeable(s.material) for o in subtree(root) if o.type in {"MESH", "CURVE"} for s in o.material_slots)


def publish(root, size=1024, samples=None, bake=True, source=None):
    """Bake `root` if any of its materials are node materials, export it into
    apps/web/public/parts/ and list it in the manifest. `source` saves the
    editable .blend first (before baking flattens the materials)."""
    from . import bake as baker
    found = kind_of(root.name)
    if not found:
        raise ValueError(f"{root.name!r} is not a part name; see kit/README.md")
    kind, key, file = found
    if source:
        Path(source).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(source).resolve()), copy=True)
    if bake and needs_bake(root):
        baker.bake_part(root, size=size, samples=samples, out_dir=BAKE_DIR / key)
    path = export_glb(root, PARTS_DIR / file)
    update_manifest(kind, key, file)
    print(f"exported {path.relative_to(PARTS_DIR.parents[3])} ({path.stat().st_size / 1024:.0f} KB); "
          "run `node scripts/compress-parts.mjs` to convert its textures to KTX2")
    return path
