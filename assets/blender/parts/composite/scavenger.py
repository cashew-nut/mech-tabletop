"""The Ashen Foundries Scavenger's settings for the composite pipeline (MODEL=scavenger; numpy only). See README.md.

The last Foundries walker from the Meshy pipeline (docs/model-pipeline-plan.md): Luke's approved concept art
(docs/concept-art/scavenger/, hero roll 3) went to one multi-image-to-3D mesh and one retexture (project folder
meshy-sources/scavenger/model/), and this module cuts it into closed parts the way the Sentinel was cut. What is specific
to this figure:

* **Axes.** cut.py extract puts the figure z up, facing -Y, the walker's left +X. Meshy normalised the model to z -1..1
  (sole to the top of the bent exhaust). The centre line is x = -0.09 (canopy, lens, back and feet agree), so
  CX = -0.09 and every x below is centred.
* **Print scale.** The Scavenger is the scout frame (28 kit mm). Sole to the hull roof (z = 0.63) is that 28 mm, so
  S = 28 / 1.63 kit mm per unit; at Luke's 1.5x the hull roof stands about 45 mm and the exhaust top about 54 mm.
* **Digitigrade legs.** The thigh runs forward and down to the knee, the shin back up to a hock and then down to the
  ankle (two bone segments). The figure's right leg is splayed wider than its left; the left leg is cut and mirrored.
* **Head.** The low wide head is the red hull canopy over the chest with the single lens eye and the jaw tusks under
  it: one helm part on the torso's roof.
* **The gun arm.** The figure's right forearm is a short heavy autocannon held level and pointing forward. Like the
  Sentinel's Carapace Gun it is cut from the right, mirrored and re-seated on the left forearm's elbow socket (RESEAT),
  keeping the sculpted level pose (RESEAT_POSE). Meshy's two elbows are not mirror images (the gun's elbow sits about 3 mm
  further in), so RESEAT_SHIFT moves the mirrored gun from its own elbow onto the left one first.
* **The claw arm.** The figure's left arm (upper arm, forearm, salvage claw) is the plain arm, mirrored for the right
  when the gun is not fitted.
* **Chains.** The loose chains under the pelvis and the gun do not print and are dropped (label _chain), as planned
  at gate B.
"""
import numpy as np

NAME = "scavenger"
TUNE = "foundries/scavenger"    # not used: the joints are measured below (this model measures its own)
CX = -0.09
PRINT_SCALE = 1.5               # Luke, 2026-11-01: collector scale is 1.5x the game
FOOT_Z = -1.0                   # Meshy z of the sole
S = 28 / 1.63                   # kit mm per figure unit (sole to hull roof 28 mm, the scout frame)
BASE = 3.0
H = 0.25 / (S * PRINT_SCALE)    # voxel size in figure units (0.25 mm at print scale)
CLOTH_T = 0.02

MAGNETS = ((1.5, 2.0), (1.0, 1.0), (0.5, 1.0))
RADII = (3.0, 2.75, 2.5, 2.2, 2.0, 1.75, 1.5, 1.3, 1.15, 1.0, 0.85, 0.75, 0.65, 0.55)
LENGTHS = (3.5, 3.0, 2.6, 2.2, 1.8, 1.5, 1.2, 1.0)
PREFER_MAGNET = True
STRICT = True
CLEAR_MIRRORED = True
CRUMB = 1.0

# Bones, figure units, x centred. Sided bones are tested on |x|: labels are mirror images, and the walker's left is +X.
# A bone is one or more segments (A, B) with a radius.
BONES_C = {
    "torso": ([((0.0, 0.02, 0.12), (0.0, 0.02, 0.50))], 0.27),
    "pelvis": ([((0.0, 0.06, -0.22), (0.0, 0.06, 0.04))], 0.20),
}
BONES_S = {
    "arm": ([((0.43, 0.14, 0.33), (0.62, 0.15, 0.14))], 0.075),
    "forearm": ([((0.62, 0.15, 0.14), (0.71, -0.03, -0.15))], 0.09),
    "thigh": ([((0.36, 0.14, -0.10), (0.37, -0.13, -0.41))], 0.11),
    "shin": ([((0.37, -0.13, -0.41), (0.38, 0.21, -0.52)), ((0.38, 0.21, -0.52), (0.41, 0.08, -0.86))], 0.09),
}
FOOT_TOP = -0.875                                             # below this, everything on a side is its foot
HAND = (0.56, (-0.62, -0.135))                                # |x| above, z range: the claw and its wrist
GUN = ((-0.79, -0.465), (-0.62, 0.44), (-0.085, 0.165))      # x (the figure's right), y, z: the autocannon
GUN_CHAIN_Z = -0.085                                          # below the gun body: hanging chains
GUN_DRUM_Y, GUN_DRUM_Z = 0.235, -0.125                        # the ammunition drum behind the breech hangs lower
PELVIS_CHAIN = ((0.21, 0.21), -0.285)                        # |x| below (left, right), z below: chains from the belt
PAULDRON = ((0.35, 0.77), (-0.26, 0.34), 0.400)               # |x|, y ranges and the z it starts at
HELM_CANOPY = (0.37, -0.06, 0.33)                             # |x| below, y below, z above: the hull canopy
HELM_FACE = (0.16, -0.20, (0.07, 0.34))                      # |x| below, y below, z range: lens and jaw tusks
BACK = (0.48, 0.255, 0.10)                                    # |x| below, y above, z above: stacks, pack, exhaust
EXHAUST_Z = 0.64                                              # everything above the hull roof is the exhaust
WAIST = (0.25, 0.07, (-0.10, 0.12))                           # |x| below, the cut's z, the z range it applies in

PARTS = {
    "torso": ["torso"], "pelvis": ["pelvis"], "helm": ["helm"], "back": ["back"],
    "pauldron": ["pauldron_L"], "arm": ["arm_L"], "forearm": ["forearm_L"], "hand": ["hand_L"],
    "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"], "gun": ["gun"],
    "_pauldron_R": ["pauldron_R"], "_arm_R": ["arm_R"], "_forearm_R": ["forearm_R"], "_hand_R": ["hand_R"],
    "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"], "_foot_R": ["foot_R"], "_chain": ["chain"],
}

DROP = ("_chain",)              # split.py: chain pieces are not handed to the part they hang from

JOINTS = {
    "pelvis": (0.0, 0.06, -0.04), "spine": (0.0, 0.06, 0.06), "chest": (0.0, 0.10, 0.36),
    "neck": (0.0, -0.10, 0.40), "head": (0.0, -0.12, 0.42),
    "shoulder": (0.43, 0.14, 0.33), "elbow": (0.62, 0.15, 0.14), "wrist": (0.71, -0.03, -0.15),
    "hip": (0.36, 0.14, -0.10), "knee": (0.37, -0.13, -0.41), "ankle": (0.41, 0.08, -0.86),
}
GUN_ELBOW = (-0.51, 0.12, 0.155)        # where the figure's right upper arm meets the gun's breech
# print mm: moves the mirrored gun from its own elbow onto the left elbow (joints.reseat, with RESEAT_POSE "mirror")
RESEAT_SHIFT = {"gun": tuple(float(v) for v in (np.array(JOINTS["elbow"]) - np.array(GUN_ELBOW) * (-1, 1, 1))
                             * S * PRINT_SCALE)}

# part: (kit component it publishes as, joint its origin sits on, parent part it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "thigh": ("thigh", "hip", "pelvis"),       # before the torso: the hips get first pick of the pelvis for their holes
    "torso": ("torso", "spine", "pelvis"),
    "helm": ("helm", "head", "torso"),
    "back": ("back", "chest", "torso"),
    "arm": ("arm", "shoulder", "torso"),       # on a ball knuckle at the shoulder (below), before the pauldron's peg
    "pauldron": ("pauldron", "shoulder", ("arm", "torso")),   # the cap on the shoulder box, moves with the arm
    "forearm": ("forearm", "elbow", "arm"),
    "hand": ("hand", "wrist", "forearm"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
    "gun": ("forearm", "elbow", "arm"),        # equipment forearm: the autocannon, re-seated on the forearm's socket
}
SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot", "gun"}
RESEAT = {"gun": "forearm"}
RESEAT_POSE = {"gun": "mirror"}                # keep the sculpt's level pose: joints.py
LOADOUT = {"gun": "R"}                         # the figure's own pose; the left copy is a hidden spare
LOADOUT_HIDES = {"gun": ("forearm", "hand")}   # build.py: with the gun fitted, the right forearm and claw are spares

# part: (game triangles, texture size)
BUDGET = {
    "torso": (9000, 1024), "pelvis": (5000, 768), "helm": (5000, 1024), "back": (8000, 1024),
    "pauldron": (4000, 768), "arm": (2500, 512), "forearm": (3500, 768), "hand": (4500, 768),
    "thigh": (3500, 768), "shin": (5000, 768), "foot": (3500, 768), "gun": (5000, 1024),
}
LABEL = {
    "pelvis": "Pelvis", "torso": "Torso", "helm": "Hull canopy + lens", "back": "Stacks + exhaust",
    "pauldron": "Pauldron", "arm": "Upper arm", "forearm": "Forearm", "hand": "Salvage claw", "thigh": "Thigh",
    "shin": "Shin + hock", "foot": "Foot", "gun": "Autocannon (equipment)",
}
EXPLODE, EXPLODE_DROP = 8.0, 3.0
POSE = {
    "arm_L": (-20, 0, 0), "forearm_L": (-35, 0, 0), "helm": (0, 0, -15),
    "thigh_L": (-15, 0, 0), "shin_L": (18, 0, 0), "foot_L": (-3, 0, 0),
}


def seg_d(P, A, B):
    A, B = np.array(A, np.float32), np.array(B, np.float32)
    AB = B - A
    t = np.clip(((P - A) @ AB) / (AB @ AB), 0, 1)
    return np.linalg.norm(P - (A + t[:, None] * AB), axis=1)


def bone_d(P, bone):
    segs, r = bone
    return np.min([seg_d(P, A, B) for A, B in segs], axis=0) - r


def label_points(P, _cloth=None):
    """Label points P (figure units, x centred). Sided bones are tested on |x|, so labels are mirror images."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    a = np.abs(x)
    Pm = np.stack([a, y, z], 1)
    cn, sn = list(BONES_C), list(BONES_S)
    names = cn + [k + "_L" for k in sn] + [k + "_R" for k in sn]
    D = [bone_d(P, BONES_C[k]) for k in cn]
    D += [bone_d(Pm, BONES_S[k]) for k in sn]
    D = np.stack(D, 1)
    lab = D.argmin(1).astype(np.int16)
    del D
    right = (lab >= len(cn)) & (x < 0)
    lab[right] += len(sn)

    def setl(mask, name):
        if name not in names:
            names.append(name)
        lab[mask] = names.index(name)

    # the waist: a flat cut through the neck between hull and pelvis (the bones' round ends left a knob of pelvis up
    # the middle of the torso's ring, too narrow round its sides to hold the waist peg)
    wx, wz, (wz0, wz1) = WAIST
    ti, pi = names.index("torso"), names.index("pelvis")
    w = (a < wx) & (z > wz0) & (z < wz1) & ((lab == ti) | (lab == pi))
    lab[w & (z >= wz)] = ti
    lab[w & (z < wz)] = pi
    L = x >= 0
    # the shoulder plates and the shoulder housing under them
    (px0, px1), (py0, py1), pz0 = PAULDRON
    paul = (a >= px0) & (a < px1) & (y >= py0) & (y < py1) & (z >= pz0) & (z < EXHAUST_Z)
    setl(paul & L, "pauldron_L")
    setl(paul & ~L, "pauldron_R")
    # the claw and its wrist, below the forearm
    hx, (hz0, hz1) = HAND
    hand = (a > hx) & (z >= hz0) & (z < hz1)
    setl(hand & L, "hand_L")
    setl(hand & ~L, "hand_R")
    setl((z < FOOT_TOP) & L & (a > 0.1), "foot_L")
    setl((z < FOOT_TOP) & ~L & (a > 0.1), "foot_R")
    # the back: vented stacks, the rear pack and the bent exhaust
    bx, by, bz = BACK
    back = ((a < bx) & (y > by) & (z > bz) & ~paul) | ((z > EXHAUST_Z) & (a < 0.36))
    setl(back, "back")
    # the hull canopy and the face under it
    cx_, cy_, cz_ = HELM_CANOPY
    fx, fy, (fz0, fz1) = HELM_FACE
    helm = ((a < cx_) & (y < cy_) & (z > cz_) & (z < EXHAUST_Z)) | ((a < fx) & (y < fy) & (z > fz0) & (z <= fz1))
    setl(helm & ~back, "helm")
    # the gun: the figure's right forearm
    (gx0, gx1), (gy0, gy1), (gz0, gz1) = GUN
    gbox = (x >= gx0) & (x < gx1) & (y >= gy0) & (y < gy1)
    drum = gbox & (y > GUN_DRUM_Y) & (z >= GUN_DRUM_Z) & (z < gz1)
    setl((gbox & (z >= gz0) & (z < gz1)) | drum, "gun")
    # chains (dropped): under the gun, and hanging from the belt between the thighs
    setl(gbox & (z < GUN_CHAIN_Z) & (z > -0.3) & ~drum, "chain")
    (cl, cr), czz = PELVIS_CHAIN
    setl(np.where(L, a < cl, a < cr) & (z < czz) & (z > FOOT_TOP), "chain")
    # knuckles: inside a ball (and its sleeve), the cut is the plane through its centre, square to the joint's axis
    for child, side, c, ax, R in knuckles():
        lab_c, lab_p = _knuckle_labels(child, side)
        c, ax = c.astype(np.float32), ax.astype(np.float32)
        q = P - c
        along = q @ ax
        radial = np.linalg.norm(q - along[:, None] * ax, axis=1)
        inside = (np.linalg.norm(q, axis=1) < R * 1.02) | ((along < R * region_top(child)) & (along > -R * SLEEVE[2])
                                                           & (radial < R * SLEEVE[0] * 1.12))
        if child in WIDE_CUT:   # wider, but only between the two parts that meet here
            wr, wd = WIDE_CUT[child]
            pair = np.isin(lab, [names.index(n) for n in (lab_c, lab_p) if n in names])
            inside |= pair & (along < R * region_top(child)) & (along > -R * wd) & (radial < R * wr)
        setl(inside & (along < 0), lab_c)
        setl(inside & (along >= 0), lab_p)
    return lab, names



# --- ball knuckles (the Foundries bible: "thick ball-and-socket hips and shoulders", "chunky riveted collars") --------
# The Scavenger is the scout frame, 42 mm to the hull roof at 1.5x: its Meshy elbows, knees and ankles are 3 to 4 mm
# across, and the first cut found only 1.7 mm pegs with 1 x 1 magnets there and no room at all at the shoulder. So those
# four joints get a designed knuckle, added to the figure before the cut (as on the Seer and the Goliath): a blackened
# iron ball split by a worn brass seam band, a collar housing up the parent's bone (iron, brass band at its top) and an
# iron collar on the child's half. child part -> (joint, axis from the child into its parent, ball radius).


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _toward(a, b):
    return _unit(np.subtract(JOINTS[b], JOINTS[a]))


HOCK = (0.38, 0.21, -0.52)          # the digitigrade leg's rear joint (inside the shin part)
KNUCKLES = {
    "arm": ("shoulder", (-1.0, 0.0, 0.12), 0.076),
    "forearm": ("elbow", _toward("elbow", "shoulder"), 0.078),
    # the knee bends sharply (thigh forward and down, shin back to the hock): the cut bisects the bend
    "shin": ("knee", _unit(_toward("knee", "hip") - _unit(np.subtract(HOCK, JOINTS["knee"]))), 0.082),
    "foot": ("ankle", _unit(np.subtract(HOCK, JOINTS["ankle"])), 0.080),
}
# The child's collar follows its own bone where that leaves the ball off the knuckle's axis.
CHILD_AXIS = {"arm": _toward("elbow", "shoulder"), "shin": _unit(np.subtract(JOINTS["knee"], HOCK))}
SLEEVE = (1.0, 2.5, 0.7)
# The assembly check (docs/scavenger-composite/README.md) found two hooks that stop a part sliding straight onto its peg: a
# flange of the upper arm curling over the torso's shoulder block, and a tongue of the thigh hanging down behind the shin's
# knuckle. Out to this radius (x R) and this depth below the cut (x R), the cut plane decides between the two parts.
WIDE_CUT = {"arm": (1.6, 0.7), "shin": (1.5, 1.4)}
HOUSING_TOP = {"arm": 1.1, "shin": 1.2, "forearm": 1.3, "foot": 1.3}


def housing_top(child):
    return HOUSING_TOP[child]


def region_top(child):
    import seer
    return housing_top(child) + seer.HOUSING["cone"] + 0.15


def knuckles():
    """(child, side, centre, axis, radius) for every knuckle, figure units. Sided parts get a mirrored copy, except the
    right elbow, which is the gun's own elbow (GUN_ELBOW): RESEAT_SHIFT moves it onto the left elbow with the gun."""
    out = []
    for child, (jn, ax, R) in KNUCKLES.items():
        c, a = np.asarray(JOINTS[jn], float), _unit(ax)
        out.append((child, "L", c, a, R))
        cr = np.asarray(GUN_ELBOW, float) if child == "forearm" else c * (-1, 1, 1)
        out.append((child, "R", cr, a * (-1, 1, 1), R))
    return out


def _knuckle_labels(child, side):
    parent = TREE[child][2]
    if side == "R" and child == "forearm":
        return "gun", "arm_R"
    lc = PARTS[child][0] if side == "L" else PARTS["_" + child + "_R"][0]
    lp = PARTS[parent][0] if (side == "L" or parent not in SIDED) else PARTS["_" + parent + "_R"][0]
    return lc, lp


def _child_axis(child, side):
    if child not in CHILD_AXIS:
        return None
    a = _unit(CHILD_AXIS[child])
    return a * (-1, 1, 1) if side == "R" else a


GOLD_UV, FRAME_UV = (-2.0, -2.0), (-3.0, -3.0)     # build.py: KNUCKLE_FINISH (worn brass), FRAME_FINISH (iron)


def foundry_knuckle(mf, c, a, r, child_axis=None, top=1.6):
    """A Foundries knuckle at c (print mm), ball radius r: iron ball, brass seam band square to `a`, iron collar on the
    child's side, iron housing with a brass band at its top up the parent's bone `a` (seer.housing's shape). Two brass
    rings per joint: the first bake had four and the knees read as stacks of striped cans."""
    import seer
    h = seer.HOUSING
    sh, sr = h["seam"]
    lo, hi, cr = h["child_collar"]
    seam = seer._tag(mf.Manifold.cylinder(2 * sh * r, sr * r, sr * r, 64).translate((0, 0, -sh * r)), GOLD_UV)
    collar = seer._tag(mf.Manifold.cylinder((hi - lo) * r, cr * r, cr * r, 48).translate((0, 0, lo * r)), FRAME_UV)
    hs = seer.housing(mf, r, h["start"] * r, top * r)
    hs[1] = seer._tag(hs[1], FRAME_UV)       # the housing's foot collar in iron: brass only on the seam and the top band
    up = mf.Manifold.batch_boolean(hs, mf.OpType.Add)
    parts = [seer._tag(mf.Manifold.sphere(r, 64).translate(tuple(np.asarray(c, float))), FRAME_UV),
             seer._orient(seam, a, c), seer._orient(collar, a if child_axis is None else child_axis, c),
             seer._orient(up, a, c)]
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def knuckle_at(mf, to_mm, child, side, c, a, R):
    cm = to_mm(c)
    return foundry_knuckle(mf, cm, a, R * S * PRINT_SCALE, child_axis=_child_axis(child, side),
                           top=housing_top(child)), cm


def extra_solids(mf, to_mm):
    """Designed additions, fused to the figure before the cut: the knuckles, and an iron strap that joins the gun's
    ammunition drum to the breech (Meshy left a gap between them, so the drum came out as a loose piece)."""
    out = [knuckle_at(mf, to_mm, *k)[0] for k in knuckles()]
    (x0, x1), (y0, y1), (z0, z1) = DRUM_STRAP
    a, b = to_mm(np.array([x0, y0, z0])), to_mm(np.array([x1, y1, z1]))
    strap = mf.Manifold.cube(tuple(float(v) for v in b - a)).translate(tuple(float(v) for v in a))
    out.append(strap.set_properties(2, lambda p, old: FRAME_UV))
    for sx in (1, -1):      # the pauldron's backing plate, under Meshy's 0.6 mm shoulder cap
        (x0, x1), (y0, y1), (z0, z1) = CAP_BACKING
        a = to_mm(np.array([min(x0 * sx, x1 * sx), y0, z0]))
        b = to_mm(np.array([max(x0 * sx, x1 * sx), y1, z1]))
        out.append(mf.Manifold.cube(tuple(float(v) for v in b - a)).translate(tuple(float(v) for v in a))
                   .set_properties(2, lambda p, old: FRAME_UV))
    return mf.Manifold.batch_boolean(out, mf.OpType.Add)



DRUM_STRAP = ((-0.615, -0.535), (0.19, 0.30), (-0.03, 0.05))   # figure units, the figure's right
# Meshy's shoulder cap is a 0.6 mm sheet on an open-topped shoulder block: too thin to print alone or to hold a peg. An
# iron backing plate under it (inside its lips, below its top, so the cap's own surface still shows) makes the pauldron
# a solid 1.5 mm plate that pegs down into the shoulder block. The walker's left; mirrored for the right.
CAP_BACKING = ((0.38, 0.555), (0.035, 0.245), (0.405, 0.452))


def true_knuckles(solid, mf):
    """Each part gets its exact half of every knuckle it meets: the voxel regions' smoothed edge rounds off a few tenths
    of a mm inside the ball's rim, so cut-face metal would show through round the child's half ball (seer.true_knuckles)."""
    from layout import to_mm
    for child, side, c, a, R in knuckles():
        parent = TREE[child][2]
        if side == "R" and parent in SIDED:
            continue
        k, cm = knuckle_at(mf, to_mm, child, side, c, a, R)
        a = _unit(a)
        up = k.trim_by_plane(tuple(a), float(a @ cm))
        down = k.trim_by_plane(tuple(-a), float(-a @ cm))
        if side == "L" and child in solid:
            solid[child] = (solid[child] - up) + down
        if parent in solid:
            solid[parent] = (solid[parent] - down) + up
    return solid


def design(solid, mf):
    """True the knuckles, then drop any floating bits the dropped chains leave on a part."""
    solid = true_knuckles(solid, mf)
    out = {}
    for k, m in solid.items():
        ps = sorted(m.decompose(), key=lambda p: -p.volume())
        keep = [p for p in ps if p.volume() >= 0.25 * ps[0].volume()]
        out[k] = mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]
        if len(keep) < len(ps):
            print(f"  {k}: dropped {len(ps) - len(keep)} floating piece(s)")
    return out


# build.py finishes for the designed solids, linear: worn brass (the bible's #6e4d2f, a little brighter where worn) and
# blackened iron (#34322f), so the knuckles read as the Brute's fittings rather than the Reliquary's gold.
KNUCKLE_FINISH = ((0.16, 0.09, 0.035), 0.5, 0.85)
FRAME_FINISH = ((0.036, 0.033, 0.030), 0.5, 0.8)
SHARP_DESIGNED = 35.0
DESIGNED_WEAR = True


# --- Foundries finish (the bible's palette) -------------------------------------------------------------------------
# Meshy's retexture came out dusty: pinkish-red plates (mean sRGB 110, 75, 67) on a beige-grey body (82, 71, 65), all of it
# the same half-metal, so the walker read pale grey in the renders. The bible (docs/style-bible/foundries.md) and the Brute
# are rust-red lacquer plates over blackened iron with worn brass fittings. surface_textures grades each texel toward that
# by what it is in Meshy's colour (soft weights, so edges blend), keeping Meshy's light and dark within each class as the
# detail, and rebuilds metal/roughness from the class (brute_polish's PAINT, BRASS and IRON). The single lens eye under the
# canopy glows furnace orange (glow_weight, build.py's emissive bake).
LACQUER = np.array([0.48, 0.125, 0.07])          # #8d2912 (sRGB 0.553, 0.161, 0.071), a little duller: it is lit by k
BRASS_C = np.array([0.431, 0.302, 0.184])       # #6e4d2f
IRON_C = np.array([0.215, 0.198, 0.178])        # #34322f, a touch warmer (soot and rust)
STENCIL_C = np.array([0.80, 0.77, 0.70])        # the white unit stencils, a dirty cream
ORANGE_C = np.array([0.52, 0.27, 0.15])         # Meshy's peach panels: the bible's orange lacquer (#be6a35), weathered
GRADE_KEEP = 0.30                               # how much of Meshy's own colour stays (grime, rust streaks)
LENS = ((0.005, 0.282), 0.048, -0.30, 0.006)    # the lens eye: centre (x, z), radius, in front of y, soft edge (figure units)
GLOW_STRENGTH = 3.0


def _ss(x, a, b):
    return np.clip((x - a) / (b - a), 0, 1)


def classes(rgb):
    """Soft weights (lacquer, orange, brass, iron) per texel of Meshy's colour (sRGB 0..1)."""
    import brute_polish as BP
    h, s, v = BP._hsv(rgb)
    hd = np.abs(((h + 180) % 360) - 180)            # degrees from pure red
    red = _ss(s, 0.18, 0.30) * (1 - _ss(hd, 12, 18)) * _ss(v, 0.16, 0.26)
    orange = _ss(s, 0.26, 0.38) * _ss(h, 13, 18) * (1 - _ss(h, 28, 34)) * _ss(v, 0.26, 0.36) * (1 - red)
    brass = _ss(s, 0.30, 0.42) * _ss(h, 30, 34) * (1 - _ss(h, 46, 54)) * _ss(v, 0.26, 0.38) * (1 - red - orange)
    white = _ss(v, 0.62, 0.74) * (1 - _ss(s, 0.16, 0.26)) * (1 - red - orange - brass)   # stencilled unit marks
    iron = np.clip(1 - red - orange - brass - white, 0, 1)
    return red, orange, brass, white, iron


def surface_textures(work):
    """Graded base colour, metal/roughness and the lens glow for build.py: {image key: path}."""
    from pathlib import Path
    from PIL import Image
    import brute_polish as BP
    Image.MAX_IMAGE_PIXELS = None
    work = Path(work)
    paths = {"base": work / "tex_0_foundries.jpg", "mr": work / "tex_1_foundries.png", "glow": work / "tex_glow.png"}
    if all(p.exists() for p in paths.values()):
        return paths
    rgb = np.asarray(Image.open(work / "tex_0.jpg").convert("RGB"), np.float32) / 255.0
    n = rgb.shape[0]
    meshy = np.asarray(Image.open(work / "tex_1.jpg").convert("RGB").resize((n, n), Image.BILINEAR), np.float32) / 255.0
    red, orange, brass, white, iron = classes(rgb)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    out = np.zeros_like(rgb)
    for w, target in ((red, LACQUER), (orange, ORANGE_C), (brass, BRASS_C), (white, STENCIL_C), (iron, IRON_C)):
        sel = w > 0.5
        ref = np.median(lum[sel]) if sel.any() else 0.3
        k = np.clip(lum / ref, 0.4, 1.6) ** 0.8
        out += w[..., None] * np.clip(target[None, None] * k[..., None], 0, 1)
    red = red + orange + white  # all paint below
    out = (1 - GRADE_KEEP) * out + GRADE_KEEP * rgb * (out.mean(-1, keepdims=True) / np.maximum(rgb.mean(-1, keepdims=True), 1e-3))
    metal = red * BP.PAINT[0] + brass * BP.BRASS[0] + iron * BP.IRON[0]
    rough = red * BP.PAINT[1] + brass * BP.BRASS[1] + iron * BP.IRON[1]
    rough = np.clip(rough + BP.ROUGH_WEAR * (meshy[..., 1] - 0.45), 0.12, 1.0)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(paths["base"], quality=95)
    mr = np.stack([np.ones_like(metal), rough, metal], -1)
    Image.fromarray((mr * 255 + 0.5).astype(np.uint8)).save(paths["mr"])
    # glow: the lens's painted brightness through the Brute's furnace ramp
    t = np.clip((lum - 0.25) / 0.5, 0, 1) ** 1.2
    ramp_t = np.array([0.0, 0.35, 0.7, 1.0])
    ramp_c = np.array([[0.25, 0.04, 0.0], [0.95, 0.30, 0.03], [1.0, 0.58, 0.15], [1.0, 0.86, 0.58]])
    glow = np.stack([np.interp(t, ramp_t, ramp_c[:, i]) for i in range(3)], -1)
    Image.fromarray((np.clip(glow, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)).save(paths["glow"])
    print("graded the Meshy textures to the Foundries finish: paint", round(float(red.mean()), 3), "brass",
          round(float(brass.mean()), 3), "iron", round(float(iron.mean()), 3), flush=True)
    return paths


def glow_weight(P_mm):
    """0..1 per vertex (print mm, kit axes): the lens eye, a disc on the face under the canopy (soft rim)."""
    from layout import from_mm
    Q = from_mm(np.asarray(P_mm, np.float64))
    (cx, cz), r, y1, e = LENS
    d = np.hypot(Q[:, 0] - cx, Q[:, 2] - cz)
    return np.clip((r - d) / e, 0, 1) * np.clip((y1 - Q[:, 1]) / e, 0, 1)
