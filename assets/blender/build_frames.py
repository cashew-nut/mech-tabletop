"""Build the twelve frame skeletons (three factions x four frames), save
them to assets/blender/frames.blend and export each to
apps/web/public/parts/kit/<faction>_frame_<frame>.glb.

    bvenv/bin/python assets/blender/build_frames.py [faction ...] [--frames titan striker] [--no-export] [--render DIR]

Frames carry joints, spare mounts and plain-colour stand-ins, no baked
textures, so they stay a few tens of KB each. `--render` saves a lineup.
"""
import sys
from pathlib import Path

import bpy  # noqa: F401

sys.path.insert(0, str(Path(__file__).parent))
import kit  # noqa: E402
from common import script_args  # noqa: E402
from kit.skeleton import FRAMES, build_frame  # noqa: E402

HERE = Path(__file__).parent


def main():
    args = script_args()
    frames = list(FRAMES)
    if "--frames" in args:
        i = args.index("--frames")
        frames = [a for a in args[i + 1:] if not a.startswith("--")]
    render_dir = Path(args[args.index("--render") + 1]) if "--render" in args else None
    skip = {a for i, a in enumerate(args) if i > 0 and args[i - 1] in {"--render"}} | set(frames)
    factions = [a for a in args if not a.startswith("--") and a not in skip] or list(kit.materials.FACTIONS)
    kit.reset_scene()
    roots = []
    for row, faction in enumerate(factions):
        for col, frame in enumerate(frames):
            roots.append(build_frame(faction, frame, location=(col * 70, row * 70, 0)))
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "frames.blend"))
    if "--no-export" not in args:
        for root in roots:
            kit.publish(root, bake=False)
    if render_dir:
        kit.render.studio()
        objs = [o for r in roots for o in kit.meshes(r)]
        out = kit.render.shot(objs, render_dir / "frames-lineup.png", az=20, el=8, samples=32, res=(1600, 1000))
        kit.render.post(out)


main()
