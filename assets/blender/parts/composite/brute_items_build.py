"""Put the Brute's cut arm items on the walker in the composite .blend and render them (needs bpy; Cycles on the CPU).

    MODEL=brute ~/bvenv/bin/python -I brute_items_build.py PARTS OUT claw=ITEM_OUT rail=ITEM_OUT [--samples 32] [--no-render]

PARTS is the Brute composite build (needs brute_composite.blend). Each `name=dir` is a `build.py WORK dir name` output:
dir/<name>_part.blend holds the baked part (print mm, origin on the elbow joint); dir/glb and dir/stl the game and print copies. Writes into OUT:

  brute_items.blend         the Brute with each item added as a hidden spare on both elbows (the right copy mirrored)
  renders/items.png         each item alone, three views
  renders/loadouts.png      the walker with claw and rail cannon fitted, and swapped
  renders/fit.png           the elbow close up: cannon arm, then each item on the same socket
"""
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import kit  # noqa: E402
from kit.render import studio, shot, post  # noqa: E402
from layout import PS, joint  # noqa: E402


def import_item(name, blend, part):
    """Append the part's object (with its baked material) from the .blend build.py wrote for it."""
    with bpy.data.libraries.load(str(blend), link=False) as (src, dst):
        dst.objects = [part]
    ob = dst.objects[0]
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    ob.name = name
    return ob


def main(a):
    parts, out = Path(a[0]), Path(a[1])
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 32
    items = dict(x.split("=", 1) for x in a[2:] if "=" in x)
    out.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(parts / "brute_composite.blend"))
    studio()
    pauldron = {"L": bpy.data.objects["pauldron_L"], "R": bpy.data.objects["pauldron_R"]}
    placed = {}
    for key, d in items.items():
        for side in ("L", "R"):
            ob = import_item(f"{key}_{side}", Path(d) / f"{key}_part.blend", key)
            ob.location = Vector(joint("elbow", side))
            if side == "R":     # the right copy is the left one mirrored, like every sided part
                ob.scale = (-1, 1, 1)
            bpy.context.view_layer.update()
            mw = ob.matrix_world.copy()
            ob.parent = pauldron[side]
            ob.matrix_parent_inverse = pauldron[side].matrix_world.inverted()
            ob.matrix_world = mw
            ob["spare"] = True
            ob.hide_render = True
            ob.hide_set(True)
            placed[ob.name] = ob
    bpy.context.view_layer.update()
    for im in bpy.data.images:
        if im.filepath and not im.packed_file and im.source == "FILE":
            try:
                im.pack()
            except RuntimeError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=str((out / "brute_items.blend").resolve()))
    if "--no-render" in a:
        return
    rd = out / "renders"
    rd.mkdir(exist_ok=True)
    allm = [o for o in bpy.data.objects if o.type == "MESH"]
    guns = {"rockets_L", "gatling_R", "rockets_R", "gatling_L"}

    def show(names):
        for o in allm:
            o.hide_render = not ((not o.get("spare") and o.name not in guns) or o.name in names)

    from render import sheet
    keys = list(items)
    paths_, labels = [], []
    for key in keys:
        for az, el in ((35, 14), (125, 10), (215, 20)):
            for o in allm:
                o.hide_render = o.name != f"{key}_L"
            p = rd / f"_item_{key}_{az}.png"
            shot([placed[f"{key}_L"]], p, az=az, el=el, samples=samples, res=(600, 640), margin=0.75)
            post(p)
            paths_.append(p)
            labels.append(f"{key} {az}")
    sheet(paths_, rd / "items.png", 3, labels)
    paths_ = []
    pairs = [(keys[0], keys[-1]), (keys[-1], keys[0])] if len(keys) > 1 else [(keys[0], keys[0])]
    for left, right in pairs:
        show([f"{left}_L", f"{right}_R"])
        for az in (25, 335):
            p = rd / f"_load_{left}_{az}.png"
            shot([o for o in allm if not o.hide_render], p, az=az, el=8, samples=samples, res=(800, 1000), margin=0.75)
            post(p)
            paths_.append(p)
    sheet(paths_, rd / "loadouts.png", len(paths_), [f"{l} left, {r} right" if i % 2 == 0 else "other side"
                                                    for (l, r) in pairs for i in range(2)])
    paths_, labels = [], []
    for name, label in [("rockets_L", "cannon arm")] + [(f"{k}_L", k) for k in keys]:
        show([name])
        p = rd / f"_fit_{name}.png"
        shot([o for o in allm if o.name in (name, "pauldron_L", "torso", "thigh_L")], p, az=60, el=8, samples=samples,
             res=(700, 800), margin=1.0)
        post(p)
        paths_.append(p)
        labels.append(label)
    sheet(paths_, rd / "fit.png", len(paths_), labels)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
