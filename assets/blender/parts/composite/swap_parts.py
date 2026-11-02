"""Swap re-cut parts into an assembled composite walker, without rebaking the rest (needs bpy).

    MODEL=seer ~/bvenv/bin/python -I swap_parts.py OLD.blend PART.blend NEW.blend [--drop name,name]

OLD.blend   build.py's assembled walker (e.g. models/seer-composite-v2/seer_composite.blend)
PART.blend  build.py's output for a few parts built on their own (`build.py WORK OUT torso pauldron` writes
            OUT/torso_pauldron_part.blend); each object there replaces the object of the same name in OLD.blend, a sided
            part (layout.SIDED) both its `_L` copy and a mirrored `_R` copy, keeping the old object's parent and children
--drop      objects of OLD.blend to delete (the Seer's native right pauldron, `pauldron_r`, when the pauldron became sided)

Written for the Seer's mirrored pauldron (2026-11-02): only the torso (new hole, trimmed for the mirrored pauldron) and the
pauldron changed, so only those two are baked again.
"""
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from layout import SIDED, TREE, joint  # noqa: E402


def main(a):
    old, part, new = Path(a[0]), Path(a[1]), Path(a[2])
    drop = a[a.index("--drop") + 1].split(",") if "--drop" in a else []
    bpy.ops.wm.open_mainfile(filepath=str(old))
    obj = bpy.data.objects
    for n in drop:
        if n in obj:
            for ch in list(obj[n].children):      # keep anything hung on it (re-parented to its parent)
                mw = ch.matrix_world.copy()
                ch.parent = obj[n].parent
                ch.matrix_world = mw
            bpy.data.objects.remove(obj[n])
            print("dropped", n)
    with bpy.data.libraries.load(str(part), link=False) as (src, dst):
        dst.objects = [n for n in src.objects]
    scene = bpy.context.scene
    for ob in dst.objects:
        if ob is None or ob.type != "MESH":
            continue
        k = ob.name.split(".")[0]          # loaded beside the old one, so Blender numbered it (torso.001)
        sides = ("L", "R") if k in SIDED else (None,)
        for side in sides:
            name = f"{k}_{side}" if side else k
            prev = obj.get(name) or (obj.get(k) if side == "L" else None)
            me = ob.data
            new_ob = bpy.data.objects.new(name + "__new", me)
            scene.collection.objects.link(new_ob)
            j = Vector(joint(TREE[k][1], side or "L"))
            new_ob.location = j
            if side == "R":
                new_ob.scale = (-1, 1, 1)
            parent = prev.parent if prev else None
            children = list(prev.children) if prev else []
            if prev is None:            # a newly sided part: hang it where the left one hangs
                left = obj.get(f"{k}_L") or obj.get(k)
                parent = left.parent if left else None
                if parent is not None and side == "R" and parent.name.endswith("_L"):
                    parent = obj.get(parent.name[:-2] + "_R") or parent
            bpy.context.view_layer.update()
            for ch in children:
                mw = ch.matrix_world.copy()
                ch.parent = new_ob
                ch.matrix_parent_inverse = new_ob.matrix_world.inverted()
                ch.matrix_world = mw
            if parent is not None:
                mw = new_ob.matrix_world.copy()
                new_ob.parent = parent
                new_ob.matrix_parent_inverse = parent.matrix_world.inverted()
                new_ob.matrix_world = mw
            if prev is not None:
                bpy.data.objects.remove(prev)
            new_ob.name = name
            print("swapped", name)
        bpy.data.objects.remove(ob)        # the loaded copy was never linked; its mesh lives on in the new objects
    for im in bpy.data.images:
        if im.filepath and not im.packed_file and im.source == "FILE":
            try:
                im.pack()
            except RuntimeError:
                pass
    new.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(new.resolve()))


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
