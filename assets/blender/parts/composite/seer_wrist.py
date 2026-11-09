"""The Seer's wrist weapons: the arc spear and the kinetic claws plug into the wrist socket in place of the hand
(numpy + manifold3d, no Blender).

    MODEL=seer python3 -I seer_wrist.py WORK OUT --claws CLAWS_WORK

WORK        the Seer's composite work folder after split.py and joints.py (kit/*.npz in print mm with Meshy's UVs, joints.json
            and the Seraphim textures tex_0..2.jpg).
OUT         gets work/<item>/kit/<item>.npz plus that item's textures (build.py's input, baked by seer_wrist_build.py),
            stl/<item>.stl (the print copy) and fit.json (the checks below). Exits 1 if a check fails.
CLAWS_WORK  a `../meshy/cut.py extract` folder of the original Meshy kinetic claws (image-to-3D task
            01a1938a-aa42-71d6-beb1-9ff035b5041d, made 2026-10-31 for the first weapons pass; the source GLB is in the project
            folder, meshy-sources/kinetic-claws/). Downloaded again from the account's Meshy history: no credits.

Luke (2026-11-02): the spear held through the fist and the claws hung at the grip did not fit the magnetic idea, since nothing
should be carried. Like the Paladin's blade, they now continue the arm: each is a part that takes the hand's place on the wrist.

  * The wrist socket is the one the hand already plugs into: a gilded ball knuckle cut through its centre, the hole and its
    magnet pocket in the forearm, the peg (r 1.15 mm D, 1 x 1 mm magnet) on the hand's half ball. Each weapon carries an exact
    copy of the hand's half ball, collar and peg (cut out of the hand itself), so it seats in the same hole and the forearm
    is not changed. Swap hand, spear or claws by pulling one off and pushing the other on.
  * Spear: the Seraphim's own spear. Its bulky rear housing (the part couched under the arm in the Meshy figure, which stuck
    up behind the arm when the fist held it) is cut off; the shaft and the blade stay. A ferrule in the knuckles' style
    (bronze, gold bands) runs from the half ball down onto the shaft, so the blade grows out of the wrist like the
    Paladin's siege blade. The
    angle off the forearm's line is searched (smallest first) so the tip stays clear of the base, the legs and the body.
  * Claws: the Meshy claws are a gauntlet with glowing rings round the wrist and four blades. The rear of the gauntlet is cut
    off and the half ball sits inside the big rings, so the claws go on like a glove over the wrist ball; the ring cuff
    is cleared round the forearm's half of the ball. The loose ring shells are fused to the body with short struts.
  * Every weapon must come off its peg in a straight pull along the socket axis without touching the forearm (checked).

Item frame: world print mm, the walker's left arm (the web and the blend mirror it for the right). The game GLB's origin is
the wrist joint.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifold3d as mf  # noqa: E402
import layout  # noqa: E402
from joints import load, save  # noqa: E402

M = layout.M
GOLD, CAP = (-2.0, -2.0), (-1.0, -1.0)
BASE_TOP = M.BASE * M.PRINT_SCALE          # top of the round base, print mm
TIP_CLEAR = 1.0                            # mm the lowest point keeps above the base
PULL = 6.0                                 # mm the straight pull-off check runs
BODY = ("torso", "pelvis", "thigh", "shin", "foot", "pauldron", "pauldron_r", "back", "crown", "helm", "arm")

# spear: where the rear housing is cut off, along the shaft from the grip (mm, towards the tip is +)
SPEAR_KEEP_FROM = -1.5
SLEEVE_LEN = 3.2                           # the ferrule from the knuckle centre down onto the shaft
SPEAR_FERRULE = 0.85                       # its radius over the knuckle housing's (it holds no hole)
# Luke (2026-11-02, second pass): straight on, no tilt at the wrist; the elbow is bent forward instead (seer_elbow.py), and
# the weapons are shorter so the arm does not look too long. Only if straight on fails do the turns below get tried.
TURNS = (0, 10, 20, 30, 40, 50, 60)        # degrees off the forearm's line, towards the front
SPEAR_SCALE = 0.8                          # the spear's size about its root in the sleeve (it was 19 mm, now about 15)
CLAW_SCALE = 0.9                           # the claws' size (the rings still clear the wrist ball)
ROLLS = (0, 45, 90, 135, 180, 225, 270, 315)

# claws: Meshy units (long axis x, blades at -x, rings at x 0.57..0.76 and 0.09..0.30)
CLAW_RING_R = 0.28                         # outer radius of the big rings
CLAW_KNUCKLE_X = 0.66                      # the wrist ball's centre sits here, inside the big rings
CLAW_CUT_X = 0.74                          # the gauntlet's rear end past this is cut off
CLAW_RING_OVER = 1.45                      # the big rings' radius over the knuckle ball's


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rot(axis, deg):
    a = unit(axis)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


def align(u, v):
    """Rotation taking unit vector u onto unit vector v."""
    w = np.cross(u, v)
    s, c = np.linalg.norm(w), u @ v
    if s < 1e-8:
        return np.eye(3) if c > 0 else rot(np.cross(u, [1.0, 0, 0]) if abs(u[0]) < 0.9 else np.cross(u, [0, 1.0, 0]), 180)
    K = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - c) / s ** 2)


def affine(m, R, t):
    return m.transform(np.concatenate([np.asarray(R, float), np.asarray(t, float)[:, None]], 1).tolist())


def along(r, z0, z1, centre, axis, n=48):
    """A cylinder of radius r along `axis` from z0 to z1 (mm from `centre`)."""
    c = mf.Manifold.cylinder(z1 - z0, r, r, n).translate((0, 0, z0))
    return affine(c, align(np.array([0, 0, 1.0]), unit(axis)), centre)


def mark(m, uv):
    return m.set_properties(2, lambda p, old: uv)


def keep_marks(m):
    """Cut faces stay gunmetal and frame metal stays frame metal; everything else on the knuckle copy bakes gold."""
    return m.set_properties(2, lambda p, old: (old[0], old[1]) if abs(old[0] + 1) < 0.5 or abs(old[0] + 3) < 0.5 else GOLD)


def plain(m):
    mm = m.to_mesh()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(mm.vert_properties)[:, :3].astype(np.float32),
                               tri_verts=np.asarray(mm.tri_verts, np.uint32)))


def stl_bytes(m):
    mm = m.to_mesh()
    P, T = np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts)
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    n = np.cross(B - A, C - A)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    rec = np.zeros(len(T), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, np.stack([A, B, C], 1)
    return b"composite seer wrist weapon, mm".ljust(80, b" ") + np.uint32(len(T)).tobytes() + rec.tobytes()


def one_piece(m, label):
    """Fuse loose pieces to the main body with short gold struts (seer.design's rule); drop crumbs."""
    from scipy.spatial import cKDTree
    ps = sorted(m.decompose(), key=lambda p: -p.volume())
    body = ps[0]
    for p in ps[1:]:
        if p.volume() < 0.05:
            continue
        A = np.asarray(body.to_mesh().vert_properties)[:, :3]
        B = np.asarray(p.to_mesh().vert_properties)[:, :3]
        d, i = cKDTree(A).query(B, k=1)
        j = int(d.argmin())
        a, b = A[i[j]], B[j]
        L = float(np.linalg.norm(b - a))
        if L > 3.0 and p.volume() < 1.0:
            print(f"  {label}: dropped a {p.volume():.2f} mm3 piece {L:.1f} mm away", flush=True)
            continue
        st = mark(along(0.35 if L < 1.5 else 0.45, -0.5, L + 0.5, a, b - a if L > 1e-6 else (0, 0, 1.0), 16), GOLD)
        body = body + p + st
        print(f"  {label}: strut {L:.2f} mm to a {p.volume():.2f} mm3 piece", flush=True)
    return body


def settle(item, wr):
    """Struts added to rejoin pieces the clearance cut split off may cross it again: cut once more, keep the cap whole and
    drop what is left loose."""
    item = (item - wr.keep_out) + wr.cap
    keep = [p for p in item.decompose() if p.volume() > 0.5]
    return mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]


class Wrist:
    """The hand's socket at the wrist: knuckle centre, axis (from the hand into the forearm), ball radius, and the cap: the
    hand's own half ball, sleeve and peg."""

    def __init__(self, work, parts):
        j = json.loads((Path(work) / "joints.json").read_text())["hand"]
        self.peg = j
        self.c = np.array(j["centre"], float)
        self.a = unit(j["axis"])
        jn, _, r = M.KNUCKLES["hand"]
        self.knuckle_c = np.array(layout.joint(jn), float)
        bend = Path(work) / "bend.json"         # seer_elbow.py turned the forearm and hand about the elbow
        if bend.exists():
            b = json.loads(bend.read_text())
            Rb, cb = np.array(b["R"], float), np.array(b["centre"], float)
            self.knuckle_c = cb + Rb @ (self.knuckle_c - cb)
        self.wrist = self.knuckle_c.copy()
        self.R = r * layout.MM
        sl_r, sl_up, sl_dn = M.SLEEVE
        R, kc = self.R, self.knuckle_c
        c_r = M.HOUSING["child_collar"][2]
        region = (mf.Manifold.sphere(R * 1.03, 64).translate(tuple(kc))
                  + along(R * sl_r * 1.14, -R * sl_dn * 1.05, 0.0, kc, self.a)          # the seam band's lower half
                  + along(R * c_r * 1.1, -R * 1.1, 0.0, kc, self.a)                     # the collar where the hand leaves the ball
                  + along(j["peg_radius"] + 0.3, -1.5, j["peg_length"] + 0.3, self.c, self.a))
        self.cap = keep_marks(parts["hand"] ^ region)
        # what the weapon may not fill: the forearm, and the forearm's half of the ball and its sleeve swept straight out
        # (swept along the pull-off path, so the weapon also comes off in a straight pull without catching on the forearm)
        low_end = parts["forearm"] ^ mf.Manifold.sphere(R * 8.0, 48).translate(tuple(kc))     # the wrist end, full detail
        fa = low_end + along(R * sl_r * 1.18, 0.0, R * (sl_up + 1.0), kc, self.a)
        self.keep_out = mf.Manifold.batch_boolean([parts["forearm"]] + [fa.translate(tuple(self.a * k))
                                                  for k in np.arange(0.0, PULL + 1e-6, 0.25)], mf.OpType.Add)

    def pull_clear(self, item, forearm):
        """Largest overlap with the forearm as the item is pulled straight off its peg (along -axis)."""
        worst = 0.0
        for d in np.arange(0.0, PULL + 1e-6, 0.5):
            moved = item.translate(tuple(-self.a * d))
            worst = max(worst, (moved ^ forearm).volume())
        return round(worst, 4)


def clashes(item, others):
    out = {}
    for k, o in others.items():
        v = (item ^ o).volume()
        if v > 1e-3:
            out[k] = round(v, 3)
    return out


def spear(work, parts, wr, others):
    """The Seraphim spear on the wrist knuckle, blade out along the forearm's line (turned forward as little as it needs)."""
    sp = parts["spear"]
    seat = json.loads((Path(work) / "spear_seat.json").read_text()) if (Path(work) / "spear_seat.json").exists() else None
    G = np.array(layout.joint("grip"), float)
    if seat:
        na = unit(seat["axis"])
    else:   # seer.seat_spear trued the shaft round through the grip: its two end rings sit about 5 mm either side of it
        P = np.asarray(sp.to_mesh().vert_properties)[:, :3]
        dist = np.linalg.norm(P - G, axis=1)
        ring = P[(dist > 4.6) & (dist < 5.6)]
        na = np.linalg.svd(ring - ring.mean(0), full_matrices=False)[2][0]
        Pc = P - G
        na = na if (Pc @ na).max() > -(Pc @ na).min() else -na      # towards the long end, the blade
    # cut off the rear housing: keep only what lies past SPEAR_KEEP_FROM along the shaft
    big = 200.0
    half = affine(mf.Manifold.cube((big, big, big), True).translate((0, 0, big / 2)), align(np.array([0, 0, 1.0]), na),
                  G + na * SPEAR_KEEP_FROM)
    blade = sp ^ half
    blade = sorted(blade.decompose(), key=lambda p: -p.volume())[0]     # the shaft and blade (one piece)
    root = G + na * SPEAR_KEEP_FROM
    blade = blade.translate(tuple(-root)).scale((SPEAR_SCALE,) * 3).translate(tuple(root))
    sl_r = wr.R * M.SLEEVE[0]
    best = None
    lite = blade.simplify(0.05)
    for turn in TURNS:
        for roll in ROLLS:
            d = unit(rot(np.cross(-wr.a, [0, -1.0, 0]), turn) @ -wr.a) if turn else -wr.a     # down the arm, turned forward
            Rm = rot(d, roll) @ align(na, d)
            # the cut end of the shaft goes up into the sleeve, 0.8 mm short of the knuckle centre
            t = wr.knuckle_c + d * (0.8 * wr.R) - Rm @ (G + na * SPEAR_KEEP_FROM)
            moved = affine(lite, Rm, t) - wr.keep_out
            low = moved.bounding_box()[2]
            hit = sum(clashes(moved, others).values())
            ok = low > BASE_TOP + TIP_CLEAR and hit == 0
            score = (0 if ok else 1, turn, hit, roll)
            if best is None or score < best[0]:
                best = (score, turn, roll, d, Rm, t, low, hit)
    _, turn, roll, d, Rm, t, low, hit = best
    body = affine(blade, Rm, t)
    # the ferrule from the ball down onto the shaft, in the knuckles' style (seer.housing: bronze, a gold collar at
    # the ball, a gold band and a short taper onto the shaft), slimmer than a knuckle's housing since it holds no hole; the
    # shaft's cut end runs up inside it, so the blade is rooted in metal
    kc, R = wr.knuckle_c, wr.R
    ferrule = mf.Manifold.batch_boolean(M.housing(mf, R, 0.42 * R, SLEEVE_LEN, rh=SPEAR_FERRULE * sl_r), mf.OpType.Add)
    gilt = M._orient(ferrule, d, kc)
    item = settle(one_piece(((gilt + body) - wr.keep_out) + wr.cap, "spear"), wr)
    return item, {"turned_forward_deg": turn, "roll_deg": roll, "lowest_mm": round(low, 2), "base_top_mm": BASE_TOP,
                  "blade_axis": [round(float(v), 4) for v in d], "kept_from_grip_mm": SPEAR_KEEP_FROM}


def claws(cwork, wr, others):
    """The Meshy claws as a glove on the wrist knuckle: blades down the arm's line, the big rings round the ball."""
    d = np.load(Path(cwork) / "mesh.npz")
    me = mf.Mesh(vert_properties=np.column_stack([d["V"], d["UV"]]).astype(np.float32), tri_verts=d["F"].astype(np.uint32))
    me.merge()
    m = mf.Manifold(me)
    m = m ^ mf.Manifold.cube((CLAW_CUT_X + 2.0, 2.0, 2.0), True).translate((CLAW_CUT_X - (CLAW_CUT_X + 2.0) / 2, 0, 0))
    s = wr.R * CLAW_RING_OVER / CLAW_RING_R * CLAW_SCALE      # print mm per Meshy unit
    m = m.scale((s, s, s)).translate((-CLAW_KNUCKLE_X * s, 0, 0))   # knuckle centre at the origin
    best = None
    lite = m.simplify(0.05)
    for turn in TURNS[:4]:
        for roll in ROLLS:
            dd = unit(rot(np.cross(-wr.a, [0, -1.0, 0]), turn) @ -wr.a) if turn else -wr.a
            # Meshy -x (the blades) onto dd; roll about it
            Rm = rot(dd, roll) @ align(np.array([-1.0, 0, 0]), dd)
            moved = affine(lite, Rm, wr.knuckle_c) - wr.keep_out
            low = moved.bounding_box()[2]
            hit = sum(clashes(moved, others).values())
            # prefer the claws' top (Meshy +z) facing out from the body (+x)
            outward = (Rm @ np.array([0, 0, 1.0]))[0]
            ok = low > BASE_TOP + TIP_CLEAR and hit == 0
            score = (0 if ok else 1, turn, hit, -outward)
            if best is None or score < best[0]:
                best = (score, turn, roll, dd, Rm, low, hit)
    _, turn, roll, dd, Rm, low, hit = best
    glove = affine(m, Rm, wr.knuckle_c)
    glove = one_piece(glove, "claws")          # struts to the loose rings first, so the clearance cut below trims them too
    item = settle(one_piece((glove - wr.keep_out) + wr.cap, "claws"), wr)
    return item, {"turned_forward_deg": turn, "roll_deg": roll, "lowest_mm": round(low, 2), "meshy_to_mm": round(s, 3),
                  "length_mm": round(s * (CLAW_CUT_X + 0.953), 1), "ring_radius_mm": round(CLAW_RING_R * s, 2)}


def main(work, out, cwork):
    work, out = Path(work), Path(out)
    parts = {k.stem: load(k) for k in sorted((work / "kit").glob("*.npz"))}
    wr = Wrist(work, parts)
    # the rest of the walker, both sides (the right arm and legs are the left mirrored)
    others = {k: parts[k] for k in BODY if k in parts}
    for k in ("thigh", "shin", "foot", "arm", "forearm", "hand"):
        if k in parts:
            others[k + "_R"] = parts[k].mirror((1, 0, 0))
    others["base"] = mf.Manifold.cylinder(BASE_TOP, 40.0, 40.0, 96)
    report = {"socket": {"knuckle_centre": [round(float(v), 3) for v in wr.knuckle_c], "axis_into_forearm":
                         [round(float(v), 4) for v in wr.a], "ball_r_mm": round(wr.R, 3), "peg": {k: wr.peg[k] for k in
                         ("peg_radius", "peg_length", "magnet")}, "cap_mm3": round(wr.cap.volume(), 2)}}
    ok = True
    made = {}
    made["arc-cannon"], report["arc-cannon"] = spear(work, parts, wr, others)
    made["kinetic-claws"], report["kinetic-claws"] = claws(cwork, wr, others)
    for item, m in made.items():
        info = report[item]
        bb = m.bounding_box()
        info.update(closed=m.status().name == "NoError", pieces=len(m.decompose()), volume_mm3=round(m.volume(), 1),
                    size_mm=[round(bb[3 + i] - bb[i], 1) for i in range(3)], clashes_mm3=clashes(m, others),
                    pull_off_overlap_mm3=wr.pull_clear(m, parts["forearm"]),
                    peg_matches_hand=round(abs((m ^ wr.cap).volume() - wr.cap.volume()), 4))
        info["pass"] = bool(info["closed"] and info["pieces"] == 1 and not info["clashes_mm3"]
                            and info["pull_off_overlap_mm3"] < 0.01 and info["peg_matches_hand"] < 0.01)
        ok &= info["pass"]
        wd = out / "work" / item
        (wd / "kit").mkdir(parents=True, exist_ok=True)
        save(m, wd / "kit" / f"{item}.npz")
        src = work if item == "arc-cannon" else Path(cwork)
        for i in range(3):
            (wd / f"tex_{i}.jpg").write_bytes((src / f"tex_{i}.jpg").read_bytes())
        (out / "stl").mkdir(parents=True, exist_ok=True)
        (out / "stl" / f"{item}.stl").write_bytes(stl_bytes(plain(m).simplify(0.015)))
        print(item, json.dumps(info), flush=True)
    report["origin"] = {"joint": "wrist", "print_mm": [round(float(v), 3) for v in wr.wrist]}
    (out / "fit.json").write_text(json.dumps(report, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[a.index("--claws") + 1])
