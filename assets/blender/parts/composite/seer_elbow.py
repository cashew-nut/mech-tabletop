"""Bend the Seer's elbow forward: the forearm, hand and anything on the wrist swing about the elbow knuckle, and the elbow
joint is cut again for the new pose (numpy + manifold3d, no Blender).

    MODEL=seer python3 -I seer_elbow.py WORK BENT [--deg 25]

WORK  the Seer's work folder after split.py and joints.py (kit/*.npz, joints.json, the textures)
BENT  a copy of WORK with kit/arm.npz, kit/forearm.npz and kit/hand.npz replaced, joints.json updated (the forearm's
      new peg, the hand's moved socket) and bend.json (the turn: centre, axis, degrees, the 3 x 3 matrix, the new wrist).

Luke (2026-11-02): with the wrist weapons straight on, the arms looked too long and the joint awkward; he asked for the
weapons to join straight on with the arm turned forward at the elbow (the gold knuckle under the upper arm), and approved
a 25 degree sketch.

The elbow is a gilded ball knuckle (seer.py): a ball at the joint with a housing up the upper arm's bone, cut through its
centre square to the bone. The ball is round about its own centre, so the forearm can swing about that centre and the ball
still closes; only the cut moves. Here:

  * the forearm loses its old peg (everything above its old cut plane), then it and the hand turn by --deg about the
    lateral axis through the ball's centre, towards the front;
  * the new cut is the plane through the centre half way between the two bones (normal: the sum of the two bone axes),
    so each side keeps a half ball; the arm is filled back with its knuckle (which also fills the old hole) and both
    are trimmed to the new plane, and anything of either side across it goes to the other. The knuckle's seam band
    moves onto the new cut and the forearm's collar turns with the forearm (seer.knuckle_solid's seam and child axes);
  * a new D peg (the forearm's own size from joints.json, r 1.3 mm with a 2 x 1 mm magnet) goes on the forearm along the
    upper arm's bone, so its hole and magnet pocket run straight up the arm's housing as before (along the cut's normal the
    hole's 0.4 mm wall broke out of the housing's side); the wall must lie in the arm, and the forearm pulls off straight
    along the peg (checked).

The hand turns with the forearm unchanged, so its socket still fits; joints.json gets its new centre and axis, and every
later step (seer_wrist.py, the web's wrist joint) reads the bent wrist from bend.json.
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifold3d as mf  # noqa: E402
import layout  # noqa: E402
from joints import load, save, peg_shapes, CLEAR, WALL  # noqa: E402

M = layout.M


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rot(axis, deg):
    a = unit(axis)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


def align(u, v):
    w = np.cross(u, v)
    s, c = np.linalg.norm(w), u @ v
    if s < 1e-8:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    K = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - c) / s ** 2)


def about(m, R, c):
    """Turn a solid by R about the point c."""
    c = np.asarray(c, float)
    return m.transform(np.concatenate([R, (c - R @ c)[:, None]], 1).tolist())


def half(c, n, keep_above, size=200.0):
    """The half space on one side of the plane through c with normal n."""
    box = mf.Manifold.cube((size, size, size), True).translate((0, 0, size / 2 if keep_above else -size / 2))
    return box.transform(np.concatenate([align(np.array([0, 0, 1.0]), unit(n)), np.asarray(c, float)[:, None]], 1).tolist())


def along_axis(c, a, z0, z1, r, n=64):
    """A cylinder of radius r along the axis a through c, from z0 to z1 (mm along a)."""
    cyl = mf.Manifold.cylinder(z1 - z0, r, r, n).translate((0, 0, z0))
    return cyl.transform(np.concatenate([align(np.array([0, 0, 1.0]), unit(a)), np.asarray(c, float)[:, None]], 1).tolist())


def one(m, crumb=0.3):
    keep = [p for p in m.decompose() if p.volume() > crumb]
    return mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]


def main(work, bent, deg):
    work, bent = Path(work), Path(bent)
    if bent.exists():
        shutil.rmtree(bent)
    shutil.copytree(work, bent, ignore=shutil.ignore_patterns("parts", "*.npy"))
    J = json.loads((work / "joints.json").read_text())
    arm, fore, hand = (load(work / "kit" / f"{k}.npz") for k in ("arm", "forearm", "hand"))
    jn, ax, r = M.KNUCKLES["forearm"]
    c = np.array(layout.joint(jn), float)                 # the elbow ball's centre, print mm
    a_up = unit(ax)                                       # the upper arm's bone axis, from the elbow up
    R_k = r * layout.MM
    # forward is -y; turn about the lateral axis (x), as in the approved sketch
    R = rot((1.0, 0.0, 0.0), -deg)
    a_low = R @ a_up                                      # the forearm's bone axis (into the arm) after the turn
    n = unit(a_up + a_low)                                # the new cut: half way between the bones

    # forearm: drop the old peg (everything above its old cut, near the ball), then turn
    old_peg_zone = half(c, a_up, True) ^ mf.Manifold.sphere(R_k * 3.0, 48).translate(tuple(c))
    fore0 = fore - old_peg_zone
    fore1 = about(fore0, R, c)
    hand1 = about(hand, R, c)
    # The straight cut's seam band (seer.py's knuckle: a gold ring split by the cut) sits square to the upper arm's bone on
    # the arm and, turned with the forearm, square to the forearm's on the other side. The joint is cut again on the
    # bisector, so both old halves come off (outside the ball) and the knuckle is put back with its band on the new cut.
    sh, sr = M.HOUSING["seam"]
    ball = mf.Manifold.sphere(R_k * 0.999, 64).translate(tuple(c))
    arm = arm - (along_axis(c, a_up, -(sh + 0.02) * R_k, (sh + 0.02) * R_k, (sr + 0.06) * R_k) - ball)
    fore1 = fore1 - (along_axis(c, a_low, -(sh + 0.02) * R_k, (sh + 0.02) * R_k, (sr + 0.06) * R_k) - ball)
    # the knuckle, both halves, about the same centre: the housing up the upper arm, the collar on the turned forearm
    kn = M.knuckle_solid(mf, c, a_up, R_k, seam_axis=n, child_axis=a_low)
    k_arm = kn ^ half(c, n, True)
    ball_low = kn ^ half(c, n, False)
    near = mf.Manifold.sphere(R_k * 1.6, 48).translate(tuple(c))
    above, below = half(c, n, True), half(c, n, False)
    # sliver exchange across the new plane, close to the ball only
    arm_across = arm ^ below ^ near
    fore_across = fore1 ^ above ^ near
    arm1 = ((arm - (below ^ near)) + k_arm + fore_across)
    fore2 = ((fore1 - (above ^ near)) + ball_low + arm_across)
    # the new peg, on the forearm, up the upper arm's bone (into the arm)
    pr, pl = J["forearm"]["peg_radius"], J["forearm"]["peg_length"]
    mag = (1.0, 1.0) if J["forearm"]["magnet"] == "2 x 1 mm" else ((0.5, 1.0) if J["forearm"]["magnet"] == "1 x 1 mm" else None)
    # where joints.py put it (on the bone, a hair off the ball's centre), so the hole keeps the wall it had
    pc, pa = np.array(J["forearm"]["centre"], float), unit(J["forearm"]["axis"])
    add, hole = peg_shapes(pr, pl, mag, pa, pc)
    arm2 = one(arm1 - hole)
    fore3 = one(fore2 + add)
    # checks: the peg is clear of the arm; the hole and its wall lie in the arm; the turned forearm, hand and the arm do not
    # overlap; the forearm comes off straight along the peg
    depth = pl + 0.15 + (mag[1] + 0.1 if mag else 0)
    # from 0.6 mm in: at the mouth the front of the wall is the forearm's half ball (the cut is tilted half the bend)
    lip = 0.6
    ring = mf.Manifold.cylinder(depth - lip, pr + CLEAR + WALL, -1.0, 48).translate((0, 0, lip))
    ring = ring.transform(np.concatenate([align(np.array([0, 0, 1.0]), pa), pc[:, None]], 1).tolist())
    wall_missing = (ring - arm2 - hole).volume()
    # the same measure on the joint joints.py fitted before the bend (the deep end of the hole runs close to the arm's
    # inner side there too): the bent joint may not be thinner than that
    j0c, j0a = np.array(J["forearm"]["centre"], float), unit(J["forearm"]["axis"])
    ring0 = mf.Manifold.cylinder(depth - lip, pr + CLEAR + WALL, -1.0, 48).translate((0, 0, lip))
    ring0 = ring0.transform(np.concatenate([align(np.array([0, 0, 1.0]), j0a), j0c[:, None]], 1).tolist())
    wall_before = (ring0 - arm - peg_shapes(pr, pl, mag, j0a, j0c)[1]).volume()
    pull = max((fore3.translate(tuple(-pa * d)) ^ arm2).volume() for d in np.arange(0.0, 6.01, 0.5))
    others = {k.stem: load(k) for k in (work / "kit").glob("*.npz") if k.stem not in ("arm", "forearm", "hand", "spear")}
    clashes = {}
    for k, o in others.items():
        for nm, m in (("forearm", fore3), ("hand", hand1)):
            v = (m ^ o).volume()
            if v > 1e-3:
                clashes[f"{nm}/{k}"] = round(v, 3)
    wrist0 = np.array(layout.joint("wrist"), float)
    wrist1 = c + R @ (wrist0 - c)
    info = {"deg": deg, "centre": [round(float(v), 4) for v in c], "axis": [1.0, 0.0, 0.0], "R": np.round(R, 6).tolist(),
            "cut_normal": [round(float(v), 4) for v in n], "ball_r_mm": round(R_k, 3),
            "wrist_print_mm": [round(float(v), 4) for v in wrist1],
            "wrist_kit_mm": [round(float(v) / layout.PS, 3) for v in wrist1],
            "peg": f"r {pr} x {pl} mm D, magnet {J['forearm']['magnet']}",
            "wall_missing_mm3": round(wall_missing, 4), "wall_missing_before_bend_mm3": round(wall_before, 4), "peg_in_arm_mm3": round((add ^ arm2).volume(), 4),
            "pull_off_overlap_mm3": round(pull, 4), "forearm_arm_overlap_mm3": round((fore3 ^ arm2).volume(), 4),
            "clashes_mm3": clashes, "pieces": {"arm": len(arm2.decompose()), "forearm": len(fore3.decompose())},
            "closed": {"arm": arm2.status().name == "NoError", "forearm": fore3.status().name == "NoError"}}
    info["pass"] = bool(wall_missing < wall_before + 0.02 and info["peg_in_arm_mm3"] < 0.01 and pull < 0.01
                        and info["forearm_arm_overlap_mm3"] < 0.01 and not clashes
                        and info["pieces"] == {"arm": 1, "forearm": 1} and all(info["closed"].values()))
    for k, m in (("arm", arm2), ("forearm", fore3), ("hand", hand1)):
        save(m, bent / "kit" / f"{k}.npz")
    J["forearm"].update(cut_normal=
                        [round(float(v), 4) for v in n], bent_deg=deg)
    J["hand"].update(centre=[round(float(v), 3) for v in c + R @ (np.array(J["hand"]["centre"]) - c)],
                     axis=[round(float(v), 4) for v in R @ np.array(J["hand"]["axis"])])
    (bent / "joints.json").write_text(json.dumps(J, indent=1))
    (bent / "bend.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))
    sys.exit(0 if info["pass"] else 1)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], float(a[a.index("--deg") + 1]) if "--deg" in a else 25.0)
