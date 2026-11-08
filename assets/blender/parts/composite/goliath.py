"""The Reliquary Goliath's settings for the composite pipeline (MODEL=goliath; numpy only). See README.md.

Third whole-body walker from the Meshy pipeline (docs/model-pipeline-plan.md): Luke's approved concept art
(docs/concept-art/goliath/, hero roll 3) went to one multi-image-to-3D mesh and one retexture (project folder
meshy-sources/goliath/model/), and this module cuts it into closed parts the way the Sentinel was cut. What is specific
to this figure:

* **Axes.** cut.py extract puts the figure z up, facing -Y. Meshy normalised the model to z -1..1 (sole to spire tip).
  The Goliath carries its Arc Cannon on the +X arm, but the pipeline cuts the walker's left from +X and takes a gun from
  the figure's right, so the mesh is **mirrored in x once** before the cut (mesh_orig.npz keeps the original). After the
  mirror the Arc Cannon is on the figure's right (-X) and the staff arm is the plain left arm (+X). The figure's centre
  line is x = 0.
* **Print scale.** Sole to the hood top (z = 0.618) is the titan frame's 50 kit mm, so S = 50 / 1.618 kit mm per unit;
  at Luke's 1.5x that is 75 mm to the hood top and about 93 mm to the spire tips.
* **The Arc Cannon.** The figure's right forearm is the cannon, held level and pointing forward. Like the Sentinel's gun
  it is cut from the right, mirrored, and re-seated on the forearm's socket (RESEAT), so it fits an elbow of either side.
* **The staff.** The left hand holds a hooked staff in the mesh. Luke did not like the long white blade it made on both
  hands (the hand is mirrored), so it is dropped: the hand is a bare clawed hand. A staff item would be a new model (follow-up).
* **Dropped.** The tattered cloth, hanging chains and small lanterns that Meshy added to the wing spars and the gun
  (they would not print) are labelled `drop`, as is anything hanging below the elbows away from the legs. The central
  banner stays with the pelvis, as the Sentinel's tabard does.
* **Knuckles.** The limbs are gaunt (5 to 7 mm at print scale), so every limb joint (neck, shoulder, elbow, wrist, hip, knee,
  ankle) gets a designed ball knuckle in a gilded sleeve, as on the Seer, added to the figure before the cut.
* **Halo.** The halo ring and the two spires grow from the back, so they are one part with the pack (the hood is the helm).
"""
import numpy as np

NAME = "goliath"
TUNE = "reliquary/titan"        # not used: the joints are measured below (this model measures its own)
CX = 0.0
PRINT_SCALE = 1.5               # Luke, 2026-11-01: collector scale is 1.5x the game
FOOT_Z = -1.0                   # Meshy z of the sole
S = 50 / 1.618                  # kit mm per figure unit (sole to hood top 50 mm, the titan frame)
BASE = 3.0
H = 0.25 / (S * PRINT_SCALE)    # voxel size in figure units (0.25 mm at print scale)
CLOTH_T = 0.02

MAGNETS = ((1.5, 2.0), (1.0, 1.0), (0.5, 1.0))
RADII = (3.0, 2.75, 2.5, 2.2, 2.0, 1.75, 1.5, 1.3, 1.15, 1.0, 0.85, 0.75, 0.65, 0.55)
LENGTHS = (3.5, 3.0, 2.6, 2.2, 1.8, 1.5, 1.2, 1.0)
PREFER_MAGNET = True
STRICT = True
CLEAR_MIRRORED = True
CRUMB = 2.0

# Bones, figure units, x centred. Sided bones are tested on |x|: labels are mirror images, and the walker's left is +X.
BONES_C = {
    "torso": ((0.0, 0.25, 0.10), (0.0, 0.25, 0.42), 0.30),
    "pelvis": ((0.0, 0.20, -0.26), (0.0, 0.20, -0.02), 0.28),
}
BONES_S = {
    "pauldron": ((0.34, 0.27, 0.44), (0.50, 0.27, 0.40), 0.16),
    "arm": ((0.36, 0.27, 0.38), (0.40, 0.23, 0.02), 0.06),
    "forearm": ((0.40, 0.23, 0.02), (0.40, 0.15, -0.17), 0.10),
    "hand": ((0.40, 0.14, -0.17), (0.40, 0.05, -0.27), 0.10),
    "thigh": ((0.22, 0.20, -0.12), (0.34, 0.20, -0.38), 0.13),
    "shin": ((0.34, 0.20, -0.40), (0.42, 0.20, -0.84), 0.12),
}
PAULDRON_BOX = ((0.28, 0.80), (0.0, 0.62), (0.28, 0.62))      # |x|, y, z ranges of the shoulder plate and wing spar
FOOT_TOP = -0.88                                               # below this, everything on a side is its foot
GUN = ((-0.66, -0.28), (-0.80, 0.20), (-0.42, 0.10))          # x (the figure's right), y, z: the cannon, from the elbow
STAFF = ((0.30, 0.53), (-0.36, 0.18), (-0.66, 0.02))          # x (the left), y, z: the blade and hook held in the hand
HELM = ((0.0, 0.05, 0.52), (0.115, 0.14, 0.12))               # hood: centre, radii

PARTS = {
    "torso": ["torso"], "pelvis": ["pelvis", "tabard"], "helm": ["helm"], "back": ["back"],
    "pauldron": ["pauldron_L"], "arm": ["arm_L"], "forearm": ["forearm_L"], "hand": ["hand_L"],
    "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"], "gun": ["gun"],
    "_pauldron_R": ["pauldron_R"], "_arm_R": ["arm_R"], "_forearm_R": ["forearm_R"], "_hand_R": ["hand_R"],
    "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"], "_foot_R": ["foot_R"], "_drop": ["drop"],
}

JOINTS = {
    "pelvis": (0.0, 0.20, -0.08), "spine": (0.0, 0.22, 0.05), "chest": (0.0, 0.25, 0.30),
    "neck": (0.0, 0.08, 0.45), "head": (0.0, 0.06, 0.50),
    "shoulder": (0.36, 0.27, 0.38), "elbow": (0.40, 0.23, 0.02), "wrist": (0.40, 0.15, -0.17),
    "hip": (0.22, 0.20, -0.12), "knee": (0.34, 0.20, -0.39), "ankle": (0.42, 0.20, -0.84),
}

# part: (kit component it publishes as, joint its origin sits on, parent part it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "thigh": ("thigh", "hip", "pelvis"),       # before the torso: the hips get first pick of the pelvis for their holes
    "torso": ("torso", "spine", "pelvis"),
    "helm": ("helm", "head", "torso"),
    "back": ("back", "chest", "torso"),
    "pauldron": ("pauldron", "shoulder", "torso"),
    "arm": ("arm", "shoulder", "torso"),
    "forearm": ("forearm", "elbow", "arm"),
    "hand": ("hand", "wrist", "forearm"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
    "gun": ("forearm", "elbow", "arm"),        # equipment forearm: the Arc Cannon, re-seated on the forearm's socket
}
SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot", "gun"}
RESEAT = {"gun": "forearm"}
LOADOUT = {"gun": "R"}                         # the figure's own pose; the left copy is a hidden spare


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _toward(a, b):
    return _unit(np.subtract(JOINTS[b], JOINTS[a]))


# Ball knuckles in gilded sleeves (the Seer's standard, seer.py): the Goliath's limbs are gaunt, so every limb joint gets
# one, designed in rather than found. child part -> (joint, axis from the child into its parent, radius in figure units).
HAND_DIR = np.array([0.0, -0.97, -0.24])   # the claws reach forward and a little down, clear of the thigh
ARM_ROD_R = 2.2             # mm at print scale
KG = 0.8                     # first cut at 1.0 looked like gold top hats on the gaunt limbs
KNUCKLES = {
    "helm": ("neck", (0.0, 0.0, -1.0), 0.055),
    "arm": ("shoulder", (-1.0, 0.0, 0.2), 0.098),   # bigger: the shoulder peg needs depth for a magnet
    "forearm": ("elbow", _toward("elbow", "shoulder"), 0.068),
    "hand": ("wrist", _toward("wrist", "elbow"), 0.060),
    "thigh": ("hip", _toward("knee", "hip"), 0.078),
    "shin": ("knee", _toward("knee", "hip"), 0.072),
    "foot": ("ankle", _toward("ankle", "knee"), 0.068),
}
KNUCKLES = {k: (j, a, r * KG) for k, (j, a, r) in KNUCKLES.items()}
# Sleeve: radius, and length into the parent / into the child, as fractions of the ball's radius. The hole (with its
# magnet) is in the parent, so the sleeve runs deep on that side; the child side carries only the peg root.
SLEEVE = (1.0, 1.9, 0.6)


def knuckles():
    """(child, side, centre, axis, radius) for every knuckle, figure units; sided parts get a mirrored copy."""
    out = []
    for child, (jn, ax, R) in KNUCKLES.items():
        c, a = np.asarray(JOINTS[jn], float), _unit(ax)
        out.append((child, "L", c, a, R))
        if child in SIDED:
            out.append((child, "R", c * (-1, 1, 1), a * (-1, 1, 1), R))
    return out


def _knuckle_labels(child, side):
    parent = TREE[child][2]
    lc = PARTS[child][0] if side == "L" else PARTS["_" + child + "_R"][0]
    lp = PARTS[parent][0] if (side == "L" or parent not in SIDED) else PARTS["_" + parent + "_R"][0]
    return lc, lp


def extra_solids(mf, to_mm):
    """The ball knuckles (with sleeves along the bone) as one solid, in print mm. Their faces get UV (-2, -2)."""
    out = []
    for child, side, c, a, R in knuckles():
        c = to_mm(c)
        r = R * S * PRINT_SCALE
        ball = mf.Manifold.sphere(r, 48)
        rs, up, dn = SLEEVE[0] * r, SLEEVE[1] * r, SLEEVE[2] * r
        sl = mf.Manifold.cylinder(up + dn - rs * 0.6, rs, -1.0, 40).translate((0, 0, -dn))
        cap = mf.Manifold.sphere(rs, 40).scale((1, 1, 0.6)).translate((0, 0, up - rs * 0.6))
        bands = [mf.Manifold.cylinder(0.12 * r, rs * 1.1, -1.0, 40).translate((0, 0, z * r)) for z in (0.95, 1.55)]
        k = mf.Manifold.batch_boolean([ball, sl, cap] + bands, mf.OpType.Add)
        zc = np.array([0.0, 0.0, 1.0])
        v = np.cross(zc, a)
        sn, cth = np.linalg.norm(v), zc @ a
        if sn < 1e-8:
            Rm = np.eye(3) if cth > 0 else np.diag([1.0, -1.0, -1.0])
        else:
            vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
            Rm = np.eye(3) + vx + vx @ vx * ((1 - cth) / sn ** 2)
        Mx = np.concatenate([Rm, c[:, None]], 1)
        out.append(k.transform(Mx.tolist()))
    # the upper arm: a gilded rod with two bands between the shoulder and elbow knuckles (both sides)
    A, B = to_mm(np.array(JOINTS["shoulder"])), to_mm(np.array(JOINTS["elbow"]))
    for sx in (1, -1):
        a, b = A * (sx, 1, 1), B * (sx, 1, 1)
        out.append(_capsule(mf, a, b, ARM_ROD_R))
        for t in (0.38, 0.62):
            c = a + (b - a) * t
            d = (b - a) / np.linalg.norm(b - a)
            out.append(_capsule(mf, c - d * 0.45, c + d * 0.45, ARM_ROD_R * 1.3))
    # the hand: the mesh has almost none (the staff hid it), so it is a gilded palm with four long clawed fingers
    Wr = to_mm(np.array(JOINTS["wrist"]))
    d = HAND_DIR
    for sx in (1, -1):
        w = Wr * (sx, 1, 1)
        dd = d * (sx, 1, 1)
        e1 = np.array([sx, 0.0, 0.0])
        out.append(mf.Manifold.sphere(2.7, 32).translate(tuple(w + dd * 1.5)))
        for off in (-2.1, -0.7, 0.7, 2.1):
            p0 = w + dd * 2.2 + e1 * off
            p1 = p0 + dd * 4.0 - e1 * off * 0.1
            bend = dd * np.cos(np.radians(38)) + np.array([0.0, 0.0, -np.sin(np.radians(38))])
            p2 = p1 + bend * 3.6
            out.append(_capsule(mf, p0, p1, 0.8, r1=0.65))
            out.append(mf.Manifold.sphere(0.65, 16).translate(tuple(p1)))
            out.append(_capsule(mf, p1, p2, 0.65, r1=0.18))
    solid = mf.Manifold.batch_boolean(out, mf.OpType.Add)
    return solid.set_properties(2, lambda p, old: (-2.0, -2.0))


def _capsule(mf, A, B, r, props=False, r1=None):
    A, B = np.asarray(A, float), np.asarray(B, float)
    d = B - A
    h = np.linalg.norm(d)
    a = d / h
    cyl = mf.Manifold.cylinder(h, r, r if r1 is None else r1, 24)
    zc = np.array([0.0, 0.0, 1.0])
    v = np.cross(zc, a)
    sn, cth = np.linalg.norm(v), zc @ a
    if sn < 1e-8:
        Rm = np.eye(3) if cth > 0 else np.diag([1.0, -1.0, -1.0])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        Rm = np.eye(3) + vx + vx @ vx * ((1 - cth) / sn ** 2)
    out = cyl.transform(np.concatenate([Rm, A[:, None]], 1).tolist())
    return out.set_properties(2, lambda p, old: (-2.0, -2.0)) if props else out


def design(solid, mf):
    """Drop the floating bits that Meshy's hanging chains and lanterns leave on a part."""
    from layout import joint
    out = {}
    for k, m in solid.items():
        ps = sorted(m.decompose(), key=lambda p: -p.volume())
        keep = [p for p in ps if p.volume() >= 0.25 * ps[0].volume()]
        out[k] = mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]
        if len(keep) < len(ps):
            print(f"  {k}: dropped {len(ps) - len(keep)} floating piece(s)")
    return out


# part: (game triangles, texture size)
BUDGET = {
    "torso": (11000, 1024), "pelvis": (7000, 1024), "helm": (3500, 1024), "back": (9000, 1024),
    "pauldron": (7500, 1024), "arm": (2200, 512), "forearm": (3000, 768), "hand": (5000, 768),
    "thigh": (4000, 768), "shin": (4500, 768), "foot": (3000, 512), "gun": (9000, 1024),
}
LABEL = {
    "pelvis": "Pelvis + banner", "torso": "Reliquary torso", "helm": "Hood", "back": "Spires + halo + pack",
    "pauldron": "Wing pauldron", "arm": "Upper arm", "forearm": "Forearm", "hand": "Hand", "thigh": "Thigh",
    "shin": "Shin", "foot": "Foot", "gun": "Arc Cannon (equipment)",
}
EXPLODE, EXPLODE_DROP = 11.0, 4.0
HOLD = {"gun_R": (-90, 0, 0)}                   # assembled view: the Arc Cannon held level, as in the concept art
POSE = {
    "gun_R": (-90, 0, 0), "arm_L": (-25, 0, 0), "forearm_L": (-35, 0, 0), "helm": (0, 0, -20),
    "thigh_L": (-18, 0, 0), "shin_L": (22, 0, 0), "foot_L": (-4, 0, 0),
}


def seg_d(P, A, B):
    A, B = np.array(A, np.float32), np.array(B, np.float32)
    AB = B - A
    t = np.clip(((P - A) @ AB) / (AB @ AB), 0, 1)
    return np.linalg.norm(P - (A + t[:, None] * AB), axis=1)


def label_points(P, _cloth=None):
    """Label points P (figure units, x centred). Sided bones are tested on |x|, so labels are mirror images."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    a = np.abs(x)
    Pm = np.stack([a, y, z], 1)
    cn, sn = list(BONES_C), list(BONES_S)
    names = cn + [k + "_L" for k in sn] + [k + "_R" for k in sn]
    D = [seg_d(P, *BONES_C[k][:2]) - BONES_C[k][2] for k in cn]
    D += [seg_d(Pm, *BONES_S[k][:2]) - BONES_S[k][2] for k in sn]
    D = np.stack(D, 1)
    lab = D.argmin(1).astype(np.int16)
    del D
    right = (lab >= len(cn)) & (x < 0)
    lab[right] += len(sn)

    def setl(mask, name):
        if name not in names:
            names.append(name)
        lab[mask] = names.index(name)

    L = x >= 0
    # the central banner hangs in front of the legs
    setl((a < 0.12) & (z < -0.04) & (z > -0.84) & (y < 0.26), "tabard")
    # chains, lanterns and tatters hanging off the wing spars and the gun are not printable
    setl((a > 0.28) & (y < 0.08) & (z < -0.27) & (z > -0.86), "drop")
    setl((a > 0.28) & (y > 0.33) & (z < 0.12) & (z > -0.70), "drop")
    setl((a > 0.52) & (z < 0.20) & (z > -0.86), "drop")
    # the Meshy upper arm is a hollow shell half hidden by cloth: only a thin tube round the bone is kept (the designed
    # gilded rod, see extra_solids); the shell round it is dropped. The cannon and the knuckles are labelled after this.
    dshell = seg_d(Pm, *BONES_S["arm"][:2])
    setl((dshell > 0.062) & (dshell < 0.12) & (z > 0.04) & (z < 0.34) & (a > 0.31), "drop")
    (px0, px1), (py0, py1), (pz0, pz1) = PAULDRON_BOX
    paul = (a >= px0) & (a < px1) & (y >= py0) & (y < py1) & (z >= pz0) & (z < pz1)
    setl(paul & L, "pauldron_L")
    setl(paul & ~L, "pauldron_R")
    setl((z < FOOT_TOP) & L & (a > 0.15), "foot_L")
    setl((z < FOOT_TOP) & ~L & (a > 0.15), "foot_R")
    # hood, then the spires, halo and pack behind it
    (hc, hr) = HELM
    helm = (((x - hc[0]) / hr[0]) ** 2 + ((y - hc[1]) / hr[1]) ** 2 + ((z - hc[2]) / hr[2]) ** 2 < 1) & (z > 0.40)
    back = (((y > 0.30) & (z > 0.0) & (a < 0.28)) | ((z > 0.50) & (a < 0.32) & (y > 0.04))) & ~helm
    setl(back, "back")
    setl(helm, "helm")
    # the cannon (figure's right) and the staff (figure's left)
    (gx0, gx1), (gy0, gy1), (gz0, gz1) = GUN
    setl((x >= gx0) & (x < gx1) & (y >= gy0) & (y < gy1) & (z >= gz0) & (z < gz1), "gun")
    (sx0, sx1), (sy0, sy1), (sz0, sz1) = STAFF
    setl((x >= sx0) & (x < sx1) & (y >= sy0) & (y < sy1) & (z >= sz0) & (z < sz1), "drop")   # Luke: no white staff blades
    # the designed claw hand: a short capsule from the wrist along the claws' direction (clear of the thigh: y < 0.09)
    wr = np.array(JOINTS["wrist"], np.float32)
    dh = HAND_DIR.astype(np.float32)
    dh = dh / np.linalg.norm(dh)
    Wm = wr * np.array([1, 1, 1], np.float32)
    t = np.clip(((Pm - Wm) @ dh) / 0.34, 0, 1)
    dist = np.linalg.norm(Pm - (Wm + t[:, None] * 0.34 * dh), axis=1)
    claw = (dist < 0.09) & (y < 0.09) & (a > 0.30)
    setl(claw & L, "hand_L")
    setl(claw & ~L, "hand_R")
    # knuckles: inside a ball (and its sleeve), the cut is the plane through its centre, square to the bone
    for child, side, c, a, R in knuckles():
        lab_c, lab_p = _knuckle_labels(child, side)
        c, a = c.astype(np.float32), a.astype(np.float32)
        q = P - c
        along = q @ a
        radial = np.linalg.norm(q - along[:, None] * a, axis=1)
        inside = (np.linalg.norm(q, axis=1) < R * 1.02) | ((along < R * SLEEVE[1]) & (along > -R * SLEEVE[2])
                                                           & (radial < R * SLEEVE[0] * 1.12))
        setl(inside & (along < 0), lab_c)
        setl(inside & (along >= 0), lab_p)
    return lab, names
