"""Review renders of the composite Paladin from OUT/paladin_composite.blend (needs bpy; Cycles on the CPU).

    ~/bvenv/bin/python -I render.py OUT [--samples 32] [--only parts|assembled|exploded|pose]

Writes into OUT/renders/:
  parts.png       every part on its own (three-quarter view), as a card would show it, with its name
  assembled.png   the full Paladin from the parts: front, three-quarter, side, back
  exploded.png    the parts pulled apart along the joint tree, pegs visible
  pose.png        the same parts posed by rotating joints (arm raised, blade forward, head turned), proving
                  that the hierarchy works
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import kit  # noqa: E402
from kit.render import studio, shot, post  # noqa: E402
from layout import TREE, SIDED, NAME, joint  # noqa: E402
import layout  # noqa: E402

LABEL = layout.LABEL or {
    "pelvis": "Pelvis + tabard", "torso": "Torso + collar + back banner", "helm": "Helm", "back": "Reliquary spire",
    "pauldron": "Pauldron + cape", "arm": "Upper arm", "forearm": "Forearm", "hand": "Gauntlet", "thigh": "Thigh",
    "shin": "Greave", "foot": "Sabaton", "blade": "Siege blade (equipment)", "pod": "Shoulder pod (equipment)",
}


def meshes(spares=False):
    """The walker's mesh objects. Spare loadout parts (the Brute's other gun on each arm) only when asked."""
    return [o for o in bpy.data.objects if o.type == "MESH" and (spares or not o.get("spare"))]


def hide_all_but(keep):
    for o in meshes(True):
        o.hide_render = o not in keep


def sheet(paths, out, cols, labels=None, cell=None):
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in paths]
    w, h = cell or ims[0].size
    rows = math.ceil(len(ims) / cols)
    S = Image.new("RGB", (w * cols, h * rows), (12, 12, 14))
    d = ImageDraw.Draw(S)
    font = kit.render._font(max(14, w // 26))
    for i, im in enumerate(ims):
        x, y = (i % cols) * w, (i // cols) * h
        S.paste(im.resize((w, h)), (x, y))
        if labels:
            d.text((x + 12, y + 10), labels[i], fill=(225, 210, 170), font=font)
    S.save(out)
    for p in paths:
        Path(p).unlink()
    return out


def brute_pose(o):
    """The Meshy Brute's own stance, rebuilt from symmetric parts: gatling raised to fire, left leg striding."""
    o["gatling_R"].rotation_euler = Euler((math.radians(-55), 0, 0))
    o["rockets_L"].rotation_euler = Euler((math.radians(-10), 0, 0))
    o["helm"].rotation_euler = Euler((0, 0, math.radians(15)))
    o["thigh_L"].rotation_euler = Euler((math.radians(-14), 0, 0))
    o["shin_L"].rotation_euler = Euler((math.radians(10), 0, 0))
    o["foot_L"].rotation_euler = Euler((math.radians(4), 0, 0))
    o["thigh_R"].rotation_euler = Euler((math.radians(12), 0, 0))
    o["shin_R"].rotation_euler = Euler((math.radians(6), 0, 0))
    o["foot_R"].rotation_euler = Euler((math.radians(-18), 0, 0))


def main(a):
    out = Path(a[0])
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 32
    only = a[a.index("--only") + 1] if "--only" in a else None
    bpy.ops.wm.open_mainfile(filepath=str(out / f"{NAME}_composite.blend"))
    rd = out / "renders"
    rd.mkdir(exist_ok=True)
    studio()
    obs = {o.name: o for o in meshes(True)}

    if only in (None, "parts"):
        paths, labels = [], []
        for k in TREE:
            o = obs.get(f"{k}_L") or obs.get(k)
            if o is None:
                continue
            hide_all_but([o])
            p = rd / f"_part_{k}.png"
            shot([o], p, az=35, el=14, samples=samples, res=(600, 720), margin=1.25)
            post(p)
            paths.append(p)
            labels.append(LABEL[k])
        sheet(paths, rd / "parts.png", 5, labels)

    if only in (None, "assembled"):
        hide_all_but(meshes())
        paths = []
        for az in (0, 35, 90, 180):
            p = rd / f"_asm_{az}.png"
            shot(meshes(), p, az=az, el=6, samples=samples, res=(760, 1000), margin=0.9)
            post(p)
            paths.append(p)
        sheet(paths, rd / "assembled.png", 4, ["front", "three-quarter", "side", "back"])

    if only in (None, "exploded"):
        hide_all_but(meshes())
        # pull each part away from its parent along the line between their joints (world space)
        saved = {o: o.matrix_world.copy() for o in meshes()}
        centre = Vector(joint("chest")) if NAME == "brute" else Vector((0, 0, 36))
        for o in meshes():
            if o.parent is None:
                continue
            k = o.name.rsplit("_", 1)[0] if o.name.endswith(("_L", "_R")) else o.name
            side = o.name[-1] if o.name.endswith(("_L", "_R")) else "L"
            d = Vector(joint(TREE[k][1], side)) - centre
            d.z *= 0.5
            if d.length < 1:
                d = Vector((0, 0, 1))
            o.matrix_world.translation += d.normalized() * (14.0 if NAME == "brute" else 7.0)
        bpy.context.view_layer.update()
        paths = []
        for az in (20, 160):
            p = rd / f"_exp_{az}.png"
            shot(meshes(), p, az=az, el=10, samples=samples, res=(900, 1000), margin=0.75)
            post(p)
            paths.append(p)
        sheet(paths, rd / "exploded.png", 2, ["exploded, front", "exploded, back"])
        for o, m in saved.items():
            o.matrix_world = m
        bpy.context.view_layer.update()

    if NAME == "brute" and only in (None, "swap"):
        # both guns share one elbow socket: swap them over (gatling on the left, cannon on the right)
        keep = [x for x in meshes(True) if not x.name.startswith(("rockets_L", "gatling_R"))]
        hide_all_but(keep)
        paths = []
        for az in (20, 330):
            p = rd / f"_swap_{az}.png"
            shot(keep, p, az=az, el=8, samples=samples, res=(800, 1000), margin=0.75)
            post(p)
            paths.append(p)
        sheet(paths, rd / "swap.png", 2, ["guns swapped over on the same sockets", "swapped, other side"])

    if only in (None, "pose"):
        hide_all_but(meshes())
        o = obs
        if NAME == "brute":
            brute_pose(o)
        else:   # rotations about each part's own origin (its joint)
            o["arm_L"].rotation_euler = Euler((math.radians(-30), 0, 0))
            o["forearm_L"].rotation_euler = Euler((math.radians(-45), 0, 0))
            o["arm_R"].rotation_euler = Euler((math.radians(20), 0, 0))
            o["helm"].rotation_euler = Euler((0, 0, math.radians(-25)))
            o["thigh_L"].rotation_euler = Euler((math.radians(-20), 0, 0))
            o["shin_L"].rotation_euler = Euler((math.radians(25), 0, 0))
            o["foot_L"].rotation_euler = Euler((math.radians(-5), 0, 0))
        bpy.context.view_layer.update()
        paths = []
        for az in (30, 300):
            p = rd / f"_pose_{az}.png"
            shot(meshes(), p, az=az, el=8, samples=samples, res=(800, 1000), margin=0.9 if NAME == "brute" else 0.75)
            post(p)
            paths.append(p)
        sheet(paths, rd / "pose.png", 2, ["posed by rotating joints", "posed, other side"])


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
