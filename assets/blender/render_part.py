"""Render a part in Cycles from a few angles and lay the renders beside a crop
of the concept art, for review.

    bvenv/bin/python assets/blender/render_part.py PART [--art CROP] [--angles 0,35,90]
        [--samples 48] [--out DIR] [--turntable 8]

PART is a manifest name (covenant_helm_titan, covenant_frame_titan, item_lance),
a .glb path, or a .blend path with an optional :object suffix
(assets/blender/parts/helm/helm.blend:covenant_helm_titan).
CROP is a name from assets/art/crops.json (`--art list` prints them).
`--turntable N` also writes N evenly spaced frames. Output goes to --out,
else $RENDERS, else renders/ in the repo; the comparison is <part>-compare.png.
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import kit  # noqa: E402
from common import PARTS_DIR, REPO, script_args  # noqa: E402


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def load_part(spec):
    """Bring the part into an empty scene; returns its mesh objects and a label."""
    if ".blend" in spec:
        path, _, obj = spec.partition(":")
        bpy.ops.wm.open_mainfile(filepath=path)
        for o in list(bpy.data.objects):
            if o.type in {"CAMERA", "LIGHT"}:
                bpy.data.objects.remove(o)
        if obj:
            root = bpy.data.objects[obj]
            return kit.meshes(root), obj
        return [o for o in bpy.data.objects if o.type in {"MESH", "CURVE"} and not o.get("kit_cutter")], Path(path).stem
    kit.reset_scene()
    if spec.endswith(".glb"):
        path, label = Path(spec), Path(spec).stem
    else:
        manifest = json.loads((PARTS_DIR / "manifest.json").read_text())
        entries = {**manifest.get("kit", {}), **{f"item_{k}": v for k, v in manifest.get("items", {}).items()},
                   **{f"chassis_{k}": v for k, v in manifest.get("chassis", {}).items()}}
        if spec not in entries:
            sys.exit(f"{spec!r} is not in the manifest; have {', '.join(sorted(entries))}")
        path, label = PARTS_DIR / entries[spec], spec
    bpy.ops.import_scene.gltf(filepath=str(path))
    return [o for o in bpy.data.objects if o.type == "MESH"], label


def main():
    args = script_args()
    if not args:
        sys.exit(__doc__)
    if opt(args, "--art") == "list":
        print("\n".join(sorted(kit.render.crops())))
        return
    spec = args[0]
    art = opt(args, "--art")
    angles = [float(a) for a in opt(args, "--angles", "0,35,90").split(",")]
    samples = int(opt(args, "--samples", 48))
    out = Path(opt(args, "--out") or __import__("os").environ.get("RENDERS") or REPO / "renders")
    objs, label = load_part(spec)
    if not objs:
        sys.exit(f"nothing to render in {spec}")
    kit.render.studio()
    shots = []
    for az in angles:
        p = kit.render.shot(objs, out / f"{label}-{int(az)}.png", az=az, el=10, samples=samples, res=(720, 900))
        kit.render.post(p)
        shots.append(p)
    n = int(opt(args, "--turntable", 0))
    for k in range(n):
        p = kit.render.shot(objs, out / "turntable" / f"{label}-{k:02d}.png", az=360 * k / n, el=10, samples=max(16, samples // 2), res=(540, 680))
        kit.render.post(p)
    cmp_path = kit.render.compare(shots, art, out / f"{label}-compare.png", labels=[f"{int(a)}°" for a in angles], title=label)
    print("wrote", cmp_path)


main()
