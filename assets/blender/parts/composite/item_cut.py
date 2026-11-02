"""Cut a Meshy-sculpted Brute arm item into a closed part on the elbow socket (numpy, scipy, manifold3d; no Blender).

    MODEL=brute ~/bvenv/bin/python -I item_cut.py WORK ITEM PARTS --length L [--muzzle +|-] [--roll DEG] [--pitch DEG]
                                                   [--sink MM] [--flip-side] [--boss-at F] [--girth G]

WORK holds the item's `mesh.npz` and textures (`python3 -I ../meshy/cut.py extract ITEM.glb WORK`); ITEM is the part name
in brute.py (`claw`, `rail`); PARTS is the Brute composite build (stl/ and report.json). Writes WORK/kit/<ITEM>.npz in
the same format joints.py leaves (print mm, UV properties, cap faces UV (-1, -1)), ready for `build.py WORK OUT ITEM`,
and WORK/item.json with the placement and the checks.

The Meshy prop is a whole forearm: a housing with a flat mounting boss on its top, a business end in front. This turns it
onto the Brute's elbow socket the way the gatling was (joints.py `reseat`), with one difference: the gatling was a part
of a figure and was turned onto the cannon arm's barrel axis, a prop's boss is a face, so the boss is turned onto the
peg axis and the prop rolled about it until its barrel points where the cannon arm's does.

  1. orient: up is +z, the barrel is the long horizontal axis, the muzzle is the end away from the heavy housing;
  2. scale to --length mm and put the boss top on the peg's plane, centred on the peg;
  3. subtract every other part of the walker (nothing may overlap), add the collar and the cannon arm's exact peg.

Then the part is one closed piece (the biggest, anything cut loose is dropped and reported).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifold3d as mf  # noqa: E402
from brute_socket import BARREL, ELBOW, SOCKET_AXIS, SWING, check_socket, load_stl, socket  # noqa: E402
from joints import save  # noqa: E402


def arg(a, name, default=None, cast=float):
    return cast(a[a.index(name) + 1]) if name in a else default


def basis(roll_deg):
    """Columns x' (the item's barrel), y' (outward), z' (up, the peg axis) in the world, for the left arm."""
    a = SOCKET_AXIS
    b = BARREL - (BARREL @ a) * a
    b /= np.linalg.norm(b)
    th = np.radians(roll_deg)
    b = b * np.cos(th) + np.cross(a, b) * np.sin(th)
    return np.stack([b, np.cross(a, b), a], 1)


def orient(V, muzzle):
    """The prop's axes: forward (xy plane), side, up = +z. Returns the rotation (columns) and the forward sign used."""
    xy = V[:, :2] - V[:, :2].mean(0)
    w, v = np.linalg.eigh(np.cov(xy.T))
    f = np.array([*v[:, -1], 0.0])
    # the muzzle is the end away from the bulk of the part: the centroid sits on the housing side
    s = np.sign((V[:, :3].mean(0) - (V.min(0) + V.max(0)) / 2) @ f)
    f = -f * (s if s != 0 else 1.0)
    if muzzle == "+":
        pass
    elif muzzle == "-":
        f = -f
    up = np.array([0.0, 0, 1.0])
    side = np.cross(up, f)
    return np.stack([f, side, up], 1)


def main(a):
    work, item, parts_dir = Path(a[0]), a[1], Path(a[2])
    length = arg(a, "--length")
    check_socket(json.loads((parts_dir / "report.json").read_text())["joints"]["rockets"])
    d = np.load(work / "mesh.npz")
    V, F, UV = d["V"].astype(np.float64), d["F"], d["UV"]
    muzzle = a[a.index("--muzzle") + 1] if "--muzzle" in a else None
    Ro = orient(V, muzzle)
    Q = (V - V.mean(0)) @ Ro                           # item frame: x forward, y side, z up
    if "--flip-side" in a:      # mirror the prop across its own length (a drum or plate that sits on the walker's inboard side)
        Q[:, 1] *= -1
        F = F[:, ::-1]
    Q -= (Q.min(0) + Q.max(0)) / 2 * np.array([0, 1, 0])
    ext = Q.max(0) - Q.min(0)
    sc = length / ext[0]
    Q *= sc
    Q[:, 1:] *= arg(a, "--girth", 1.0)     # thicken a spindly prop across its length (the rail cannon: chunkier, sturdier print)
    xr = Q[:, 0].min()
    # the boss: the highest flat on top of the housing, in the rear half; or, for a prop with no boss (--boss-at F),
    # the top of the housing at F of the length from the rear, which the collar then seats on
    width = Q[:, 1].max() - Q[:, 1].min()
    at = arg(a, "--boss-at")
    if at is None:
        win = (Q[:, 0] < xr + 0.55 * length) & (np.abs(Q[:, 1]) < 0.3 * width)
    else:
        win = (np.abs(Q[:, 0] - (xr + at * length)) < 0.04 * length) & (np.abs(Q[:, 1]) < 0.15 * width)
    ztop = Q[win, 2].max()
    top = win & (Q[:, 2] > ztop - 0.05 * (Q[:, 2].max() - Q[:, 2].min()))
    bx, by = Q[top, 0].mean(), Q[top, 1].mean()
    sink = arg(a, "--sink", 0.15)
    boss = np.array([bx, by, ztop])
    Q -= boss
    # item frame -> world: x' along the barrel, z' on the peg axis, boss top just below the socket face
    Rw = basis(arg(a, "--roll", 0.0))
    pitch = np.radians(arg(a, "--pitch", 0.0))
    if pitch:
        c, s = np.cos(pitch), np.sin(pitch)
        Rw = Rw @ np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    W = Q @ Rw.T + ELBOW - sink * SOCKET_AXIS
    props = np.concatenate([W, UV], 1).astype(np.float32)
    mesh = mf.Mesh(vert_properties=props, tri_verts=F.astype(np.uint32))
    mesh.merge()
    fig = mf.Manifold(mesh)
    info = {"item": item, "length_mm": length, "scale": float(sc), "muzzle_world": (Rw[:, 0]).round(3).tolist(),
            "status": str(fig.status()), "tris": fig.num_tri(), "raw_volume": round(fig.volume(), 1)}
    print(info, flush=True)
    if fig.status() != mf.Error.NoError:
        sys.exit(f"the Meshy mesh is not a manifold ({fig.status()}): voxel-close it first")
    # the rest of the walker, with cap UVs so cut faces bake as gunmetal
    cap = lambda m: m.set_properties(2, lambda p, old: (-1.0, -1.0))   # noqa: E731
    names = ("pelvis", "torso", "helm", "back", "pauldron", "thigh", "shin", "foot")
    others = {k: cap(load_stl(parts_dir / "stl" / f"{k}.stl")) for k in names}
    add, _, collar = socket()
    swing_clash = {}
    for deg in SWING:
        if deg == 0:
            continue
        turned = to_world_manifold(fig, deg)
        for k, o in others.items():
            v = (turned ^ o).volume()
            if v > 0.05:
                swing_clash[f"{k}@{deg:+.0f}"] = round(v, 2)
    trimmed = {}
    body = fig
    for k, o in others.items():
        v = (body ^ o).volume()
        if v > 1e-3:
            trimmed[k] = round(v, 2)
            body = body - o
    body = body + (collar - others["pauldron"])
    body = body + add
    pieces = sorted(body.decompose(), key=lambda m: -m.volume())
    dropped = round(sum(p.volume() for p in pieces[1:]), 2)
    part = pieces[0]
    bb = part.bounding_box()
    info.update({"trimmed_mm3": trimmed, "swing_clash_mm3": swing_clash, "dropped_loose_mm3": dropped,
                 "pieces_before_keep": len(pieces), "volume_mm3": round(part.volume(), 1), "tris": part.num_tri(),
                 "closed": part.status().name == "NoError", "size_mm": [round(bb[3 + i] - bb[i], 1) for i in range(3)],
                 "peg_vs_arm_mm3": round(abs((part ^ add).volume() - add.volume()), 4)})
    (work / "kit").mkdir(exist_ok=True)
    save(part, work / "kit" / f"{item}.npz")
    (work / "item.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))


def to_world_manifold(m, deg):
    """The manifold swung about the elbow's x axis by deg."""
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    Rx = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return m.transform(np.concatenate([Rx, (ELBOW - Rx @ ELBOW)[:, None]], 1).tolist())


if __name__ == "__main__":
    main(sys.argv[1:])
