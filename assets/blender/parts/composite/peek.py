"""Quick Workbench views of the split parts, each solid piece in its own colour (review aid, seconds per image).

    ~/bvenv/bin/python -I peek.py WORK OUT.png [--explode 1.0] [--parts a,b] [--dir parts]
"""
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from layout import JOINT_OF, joint, load_npz, SIDED  # noqa: E402


def pieces(nv, T):
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]]])
    n, lab = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nv, nv)), directed=False)
    fl = lab[T[:, 0]]
    out = [T[fl == i] for i in np.unique(fl)]
    return sorted(out, key=len, reverse=True)


def main(a):
    work, out = Path(a[0]), a[1]
    ex = float(a[a.index("--explode") + 1]) if "--explode" in a else 0.0
    sub = a[a.index("--dir") + 1] if "--dir" in a else "parts"
    only = a[a.index("--parts") + 1].split(",") if "--parts" in a else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    objs = []
    for f in sorted((work / sub).glob("*.npz")):
        k = f.stem
        if only and k not in only:
            continue
        P, T = load_npz(f)
        for side in (("L", "R") if k in SIDED else ("L",)):
            me = bpy.data.meshes.new(k)
            # manifold splits vertices where UVs differ: weld by position so loose pieces are real pieces
            _, first, inv = np.unique(np.round(P[:, :3] * 1e4).astype(np.int64), axis=0, return_index=True, return_inverse=True)
            v = P[first, :3].copy()
            tt = inv.ravel()[T]
            if side == "R":
                v[:, 0] *= -1
                tt = tt[:, ::-1]
            j = Vector(joint(JOINT_OF.get(k, "chest"), side))
            c = Vector((0, 0, joint("chest")[2] - 6))
            # one object per loose piece, so each gets its own colour
            for pc, tp in enumerate(pieces(len(v), tt)):
                me = bpy.data.meshes.new(k)
                me.from_pydata(v.tolist(), [], tp.tolist())
                me.validate()
                ob = bpy.data.objects.new(f"{k}_{side}_{pc}", me)
                sc.collection.objects.link(ob)
                ob.location = (j - c) * ex * 0.6 if ex else (0, 0, 0)
                objs.append(ob)
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "RANDOM"
    sh.show_cavity = True
    sh.show_shadows = False
    sc.display.shading.background_type = "VIEWPORT" if hasattr(sh, "background_type") else None
    sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.15, 0.15, 0.17)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam.data.type = "ORTHO"
    pts = np.array([o.matrix_world @ Vector(c) for o in sc.objects if o.type == "MESH" for c in o.bound_box])
    lo, hi = pts.min(0), pts.max(0)
    ctr = Vector(((lo + hi) / 2).tolist())
    span = max(hi[0] - lo[0], (hi[2] - lo[2]) * 1.1) * 1.06
    cam.data.ortho_scale = span
    sc.render.resolution_x, sc.render.resolution_y = 1100, 1000
    import math
    tiles = []
    for name, az in (("front", 0), ("side", 90), ("back", 180), ("q", 35)):
        d = Vector((math.sin(math.radians(az)), -math.cos(math.radians(az)), 0.15 if name == "q" else 0)).normalized()
        cam.location = ctr + d * 400
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam.data.clip_end = 2000
        p = f"{out}.{name}.png"
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        tiles.append(p)
    from PIL import Image
    ims = [Image.open(t) for t in tiles]
    w = sum(i.width for i in ims)
    sheet = Image.new("RGB", (w, ims[0].height))
    x = 0
    for i in ims:
        sheet.paste(i, (x, 0))
        x += i.width
    sheet.save(out)
    for t in tiles:
        Path(t).unlink()


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
