"""The Reliquary Seer's settings for the composite pipeline (MODEL=seer). See README.md.

Luke's Meshy Gilded Seraphim, cut into closed parts that plug together. Lessons from the Paladin are built in:

  * Print scale. The Seer is a Striker (36 mm to the helm top in the game) and its limbs are rods about 0.04 Meshy
    units thick, under 1 mm at game scale. Solids, pegs and magnets are cut at PRINT_SCALE = 1.5, Luke's collector
    scale (about 56 mm to the helm top, 68 mm to the crown spire); the game GLBs are scaled back to kit mm.
  * Designed joints. Even at 1.5x a limb rod is about 1.2 mm across, too thin for any peg. So every limb joint gets a
    gilded ball knuckle (a sphere with a short sleeve along each bone), and the cut between the two parts is a plane
    through the knuckle's centre, square to the bone. Each side gets half a ball with a flat, round face that has room
    for a keyed peg and a 2 x 1 mm magnet. The reference already has orbs at the shoulders and knees, so the knuckles
    read as part of the design. Knuckle surfaces carry UV (-2, -2) and bake as polished gold.
  * One arm, mirrored. The Meshy figure's right arm is bent to couch its spear and read badly on its own, and its left
    hand had a sword grown into it. The left arm is now the arm: its sword is cut off below the fist (SWORD), the fist
    gets a bore, and the right arm is the left one mirrored, like the legs (Luke, 2026-11-02). The pauldrons and wings
    were native to each side at first, but the right wing's front spar reached out level with the shoulder and read as a
    third arm, so the right pauldron and wing are now the left ones mirrored too (Luke, 2026-11-02).
  * One solid per part. The left wing is a separate shell in the Meshy file (it floats behind the pauldron); design()
    fuses any loose piece of a part to the part's main body with a strut, so nothing has to be glued in place.
  * The spear is equipment (the Seer's arc spear) and is held through either fist, in the old sword's pose.

Positions are absolute Meshy units (z up, facing -Y, left is +X), measured from slices of the mesh. The figure's
centre line is x = 0.235 (the shoulder orbs and feet), not the 0.28 the first Seraphim cut used.
"""
import numpy as np

NAME = "seer"
TUNE = "reliquary/striker"
CX = 0.235
PRINT_SCALE = 1.5           # Luke, 2026-11-01: collector scale is 1.5x the game (a Titan is about 75 mm)
S, FOOT_Z, BASE = 36 / 1.75, -0.95, 3.0     # game: mm per Meshy unit, foot level, base thickness (../meshy/seraphim_cut.py)
H = 0.008                                   # voxel size in Meshy units (0.25 mm at print scale)
CLOTH_T = 0.016

# Bigger joints at print scale: 3 x 2 mm magnets where there is room, then 2 x 1, then 1 x 1.
MAGNETS = ((1.5, 2.0), (1.0, 1.0), (0.5, 1.0))
RADII = (2.5, 2.2, 2.0, 1.75, 1.5, 1.3, 1.15, 1.0, 0.85, 0.75, 0.65, 0.55)
LENGTHS = (3.5, 3.0, 2.6, 2.2, 1.8, 1.5, 1.2, 1.0)
PREFER_MAGNET = True        # a slightly thinner peg with a magnet beats a fatter one without
CRUMB = 0.3                 # joints.py: loose bits under this (mm3) are dropped (trimming for the mirrored arm leaves one)


def _c(p):
    """Absolute Meshy position to centred (x - CX)."""
    return (p[0] - CX, p[1], p[2])


# Joints, absolute Meshy units. Left side (the right arm, pauldron and legs are mirrored). shoulder_r is the old native right
# pauldron's origin, kept for the labels.
JOINTS_ABS = {
    "pelvis": (CX, 0.08, -0.02), "spine": (CX, 0.08, 0.06), "chest": (CX, 0.10, 0.30),
    "neck": (CX, 0.05, 0.565), "head": (CX, 0.03, 0.62),
    "shoulder": (0.475, 0.16, 0.49), "elbow": (0.605, 0.19, 0.08), "wrist": (0.715, 0.08, -0.34),
    "hip": (0.38, 0.08, -0.03), "knee": (0.465, 0.065, -0.40), "ankle": (0.57, 0.03, -0.80),
    "grip": (0.7406, 0.0583, -0.4542),      # the left fist's centre, on the line of the old sword's grip
    "shoulder_r": (2 * CX - 0.475, 0.16, 0.49),     # the mirror of the left shoulder: the right pauldron's origin
    "pauldron_mount": (0.41, 0.26, 0.58),
}
JOINTS = {k: _c(v) for k, v in JOINTS_ABS.items()}     # centred
# Where the Meshy figure's own right arm is (bent, couching the spear). Only used to find and cut it away.
NATIVE_R = {k: _c(v) for k, v in {"shoulder": (-0.005, 0.14, 0.47), "elbow": (-0.075, -0.04, 0.18),
                                  "wrist": (-0.08, -0.26, -0.01)}.items()}
# The old sword in the left fist runs from the grip down, a little out and forward (measured on the hand's slices).
# Everything of the hand more than SWORD_CUT past the grip along it is the blade, and is cut away.
SWORD = (0.243, -0.304, -0.921)
SWORD_CUT = 0.058                          # Meshy units (about 1.8 mm at print scale): the bottom of the fist


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _toward(a, b):
    return _unit(np.subtract(JOINTS[b], JOINTS[a]))


# Ball knuckles: child part -> (joint, axis from the child into its parent, radius in Meshy units).
KG = 1.15                    # knuckles grown a little so 1.5x still leaves room for magnets
KNUCKLES = {
    "helm": ("neck", (0.0, 0.0, -1.0), 0.05),
    "arm": ("shoulder", (-1.0, 0.0, 0.0), 0.062),
    "forearm": ("elbow", _toward("elbow", "shoulder"), 0.055),
    "hand": ("wrist", _toward("wrist", "elbow"), 0.05),
    "thigh": ("hip", _toward("knee", "hip"), 0.062),
    "shin": ("knee", _toward("knee", "hip"), 0.058),
    "foot": ("ankle", _toward("ankle", "knee"), 0.055),
    # The left wing floats in the Meshy file and the left pauldron touches the torso only at a sliver, so it gets a
    # knuckle behind the shoulder, where the right wing's root meets the torso, above the arm's socket.
    "pauldron": ("pauldron_mount", (0.0, -1.0, 0.0), 0.04),
}
KNUCKLES = {k: (j, a, r * KG) for k, (j, a, r) in KNUCKLES.items()}
# The child's collar goes where its limb leaves the ball. That is down the knuckle's own axis everywhere but the shoulder,
# whose knuckle points into the torso while the upper arm hangs from the ball.
CHILD_AXIS = {"arm": _toward("elbow", "shoulder")}
# Knuckle housing: radius, and reach up the parent's bone / down the child's, as fractions of the ball's radius. The hole
# (with its magnet) is in the parent, so the housing runs deep on that side; the child side is the bare lower half of the
# ball (no sleeve), so the joint reads as a ball in a socket.
#
# Polish pass (2026-11-08). The first knuckles were a polished gold ball inside a gold can as wide as the ball, with a
# domed lid: next to Meshy's filigree they read as tin cans, and in the game their bright, flat gold bloomed. The hole and
# its 0.4 mm wall still need a housing about as wide as the ball up the parent's bone, so the envelope stays and the look
# changes:
#   * the ball is aged gold, a shade under Meshy's own gilding, with a raised band split by the seam, so the cut between
#     the two parts reads as the groove of a bearing ring;
#   * the housing is darkened bronze (a near-black frame metal was tried first: on the figure it read as black cans) with a
#     gold collar at the ball and a gold band at its top, and it ends in a short taper into the limb instead of a lid;
#   * the child's half of the ball has a slim gold collar where the limb leaves it, and no can below.
# SLEEVE only labels the voxels now (seer_wrist.py also cuts the hand's cap with it): within SLEEVE[0] x 1.12 of the bone,
# from SLEEVE[2] below the cut to SLEEVE[1] above it, the cut plane decides which part a voxel goes to. 0.7 below keeps
# whatever Meshy has round the child's half ball with the child: with 0.15, the forearm's cuff wrapped under the hand's
# ball and the hand no longer pulled straight off (seer_wrist.py's check). Above the cut the region reaches just past the
# housing's cone (region_top below), and design() puts the knuckle's two exact halves back afterwards (true_knuckles).
SLEEVE = (1.0, 2.5, 0.7)
HOUSING = {"start": 0.42, "top": 2.15, "taper": 0.97, "cone_to": 0.5, "cone": 0.35, "collar": (0.60, 0.74, 1.06),
           "band": 0.12, "seam": (0.12, 1.07), "child_collar": (-1.06, -0.80, 0.6)}
# The hip housings run up into the pelvis towards the waist: at full length their cone's tip reached the torso's side of
# the waist cut and the torso caught on it when lifted off (1.1 mm3 in the straight pull, 0.15 before the polish). Under
# the loincloths they can be short; the pelvis round them holds the hole's wall.
HOUSING_TOP = {"thigh": 1.55}


def housing_top(child):
    return HOUSING_TOP.get(child, HOUSING["top"])


def region_top(child):
    """How far up the parent's bone (x the ball's radius) the cut plane decides a voxel's part: past the housing's cone."""
    return housing_top(child) + HOUSING["cone"] + 0.15
GOLD_UV, FRAME_UV = (-2.0, -2.0), (-3.0, -3.0)
# build.py: designed surfaces. Aged gold matched to Meshy's gilding on this figure (median gold texel, linear: 0.31, 0.24,
# 0.14; its brightest quarter 0.43, 0.34, 0.20; roughness about 0.31), a little rougher so a large smooth ball does not
# flare; the housings are a darker, browner bronze, so the ball and the gold trim still read against them.
KNUCKLE_FINISH = ((0.34, 0.26, 0.145), 0.40, 0.85)
FRAME_FINISH = ((0.16, 0.11, 0.06), 0.45, 0.9)       # darkened bronze (near-black frame metal read as black cans on the figure)
SHARP_DESIGNED = 35.0       # build.py: crisp rims on the designed solids (smooth shading streaked them)
ROUGH_FLOOR = 0.42          # build.py: no mirror-smooth texels (the chest plate glared white under the game's bloom)
DESIGNED_WEAR = True        # build.py: cavity darkening and a faint mottle on the designed surfaces, like Meshy's own texture

# part: (kit component it publishes as, joint its origin sits on, parent part(s) it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "torso": ("torso", "spine", "pelvis"),
    "helm": ("helm", "neck", "torso"),
    "crown": ("crown", "head", ("helm", "back", "torso")),
    "back": ("back", "chest", "torso"),
    "arm": ("arm", "shoulder", "torso"),
    "pauldron": ("pauldron", "shoulder", ("torso", "arm")),     # on a small knuckle behind the shoulder (below)
    "forearm": ("forearm", "elbow", "arm"),
    "hand": ("hand", "wrist", "forearm"),
    "thigh": ("thigh", "hip", "pelvis"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
    "spear": (None, "grip", "hand"),       # equipment: item_arc-cannon@seer, held through the fist (either side)
}
# Held equipment has no peg: its shaft goes through a bore in the fist (see design()).
GRIP_T, SHAFT_R, BORE_CLEAR = 5.25, 0.8, 0.06     # grip point on the shaft (mm from the spear's centre), shaft radius
HELD = {"spear": {"parent": "hand", "peg": None,
                  "how": f"shaft ({2 * SHAFT_R:g} mm) push-fits through a {2 * (SHAFT_R + BORE_CLEAR):.2f} mm bore in either fist"}}
SIDED = {"thigh", "shin", "foot", "arm", "forearm", "hand", "pauldron"}
# joints.py: trim the centre parts (the torso) where the mirrored right arm and pauldron sit. Not the legs: they were cut
# before this and already fit.
CLEAR_MIRRORED = ("arm", "forearm", "hand", "pauldron")

# Physical parts and the labels each is made of; right-side mirrored parts' labels only carve the torso and pelvis.
PARTS = {
    "torso": ["torso", "cloth_upper"], "pelvis": ["pelvis", "cloth_lower"],
    "helm": ["helm"], "crown": ["crown"], "back": ["back"],
    "pauldron": ["pauldron_L"], "_pauldron_R": ["pauldron_R"],
    "arm": ["arm_L"], "forearm": ["forearm_L"], "hand": ["hand_L"],
    "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"], "spear": ["spear"],
    "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"], "_foot_R": ["foot_R"],
    "_arm_R": ["arm_R"], "_forearm_R": ["forearm_R"], "_hand_R": ["hand_R"], "_sword": ["sword"],
}

J = JOINTS
BONES = {  # label: (A, B, radius), centred
    "torso": ((0, 0.09, 0.12), (0, 0.09, 0.52), 0.15),
    "pelvis": ((0, 0.08, -0.10), (0, 0.08, 0.04), 0.15),
    "pauldron_L": (_c((0.47, 0.17, 0.55)), _c((0.56, 0.24, 0.53)), 0.08),
    "arm_L": (J["shoulder"], J["elbow"], 0.065), "forearm_L": (J["elbow"], J["wrist"], 0.08),
    "hand_L": (J["wrist"], _c((0.80, -0.02, -0.80)), 0.06),
    "arm_R": (NATIVE_R["shoulder"], NATIVE_R["elbow"], 0.065), "forearm_R": (NATIVE_R["elbow"], NATIVE_R["wrist"], 0.07),
    "hand_R": (NATIVE_R["wrist"], _c((-0.11, -0.36, -0.08)), 0.07),
    "thigh_L": (J["hip"], J["knee"], 0.08), "shin_L": (J["knee"], J["ankle"], 0.08),
}
BONES["pauldron_R"] = ((-0.24, 0.17, 0.55), (-0.33, 0.24, 0.53), 0.08)
for k in ("thigh", "shin"):
    p, q, r = BONES[k + "_L"]
    BONES[k + "_R"] = ((-p[0], p[1], p[2]), (-q[0], q[1], q[2]), r)
SPEAR = (_c((-0.11, 0.02, 0.15)), _c((-0.82, -0.60, -0.90)), 0.10)

_extra = {}


def seg_d(P, A, B):
    A, B = np.asarray(A, np.float32), np.asarray(B, np.float32)
    AB = B - A
    t = np.clip(((P - A) @ AB) / (AB @ AB), 0, 1)
    return np.linalg.norm(P - (A + t[:, None] * AB), axis=1), t


def cloth_tris(work, V, F, UV):
    """The red banner: red texels, smoothed over neighbouring triangles (as ../meshy/seraphim_cut.py)."""
    from pathlib import Path
    from PIL import Image
    from scipy.spatial import cKDTree
    C = V[F].mean(1)
    uv = UV[F].mean(1)
    tex = np.asarray(Image.open(Path(work) / "tex_0.jpg").convert("RGB"))
    n = tex.shape[0]
    c = tex[np.clip((uv[:, 1] * (n - 1)).astype(int), 0, n - 1), np.clip((uv[:, 0] * (n - 1)).astype(int), 0, n - 1)].astype(int)
    red = ((c[:, 0] > 90) & (c[:, 0] > 2 * c[:, 1]) & (c[:, 0] > 2 * c[:, 2])).astype(np.float32)
    _, nn = cKDTree(C).query(C, k=24, workers=-1)
    return red[nn].mean(1) > 0.30


def prepare(work, V, F, UV):
    """The left wing is a loose shell in the Meshy file: remember its triangles so its voxels go to the pauldron."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    _, inv = np.unique(np.round(V * 1e5).astype(np.int64), axis=0, return_inverse=True)
    T = inv.ravel()[F]
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]]])
    nv = T.max() + 1
    n, lab = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(nv, nv)), directed=False)
    fl = lab[T[:, 0]]
    sizes = np.bincount(fl)
    C = V[F].mean(1)
    loose = C[fl != sizes.argmax()]
    print("loose shells:", n - 1, "triangles:", len(loose), flush=True)
    _extra["wing"] = cKDTree(loose) if len(loose) else None


def label_points(P, cloth_near):
    """Label points P (centred Meshy units) with the Seer's rules."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    names = list(BONES)
    D = np.stack([seg_d(P, *BONES[k][:2])[0] - BONES[k][2] for k in names], 1)
    lab = D.argmin(1).astype(np.int16)
    del D

    def setl(mask, name):
        if name not in names:
            names.append(name)
        lab[mask] = names.index(name)

    def isin(*ks):
        return np.isin(lab, [names.index(k) for k in ks if k in names])

    # wings: the left one is a loose shell; both spread behind the shoulders
    clear_l = (seg_d(P, *BONES["arm_L"][:2])[0] > 0.07) & (seg_d(P, *BONES["forearm_L"][:2])[0] > 0.08)
    clear_r = (seg_d(P, *BONES["arm_R"][:2])[0] > 0.085) & (seg_d(P, *BONES["forearm_R"][:2])[0] > 0.075)
    setl((x > 0.15) & (y > 0.2) & (z > 0.15) & (z < 0.64) & clear_l, "pauldron_L")
    setl((x < -0.15) & (y > 0.2) & (z > 0.15) & (z < 0.64) & clear_r, "pauldron_R")
    # the right wing is attached and reaches out past the arm: anything up there clear of the right arm's bones
    setl((x < -0.2) & (z > 0.2) & (z < 0.64) & clear_r, "pauldron_R")
    if _extra.get("wing") is not None:
        d, _ = _extra["wing"].query(P, k=1, distance_upper_bound=0.02, workers=-1)
        setl(np.isfinite(d), "pauldron_L")
    # feet
    L = x >= 0
    setl(L & (z < J["ankle"][2]) & (np.abs(x) < 0.6), "foot_L")
    setl(~L & (z < J["ankle"][2]) & (np.abs(x) < 0.6), "foot_R")
    # the left hand's sword: everything of the hand past the bottom of the fist, along the blade, is cut away
    past = (P - np.asarray(J["grip"], np.float32)) @ _unit(SWORD).astype(np.float32)
    setl(isin("hand_L") & (past > SWORD_CUT), "sword")
    # the spear, couched under the right arm (from just past the elbow knuckle to the tip)
    ds, ts = seg_d(P, SPEAR[0], SPEAR[1])
    setl((ds < SPEAR[2]) & (ts > 0.07) & (x < -0.1), "spear")
    # helm, the halo with its crown spire, the spires on the back
    hx, hy, hz = J["head"]
    helm = ((x - 0) ** 2 / 0.085 ** 2 + (y - hy) ** 2 / 0.10 ** 2 + (z - 0.645) ** 2 / 0.095 ** 2 < 1) & (z > 0.565)
    halo = ((x ** 2 + (z - 0.79) ** 2) < 0.215 ** 2) & (y > 0.03) & (y < 0.19) & (z > 0.62) & ~helm
    spire = (np.abs(x) < 0.05) & (z > 0.725) & (y > -0.06) & (y < 0.19)
    setl(helm, "helm")
    setl(halo | spire, "crown")
    setl((y >= 0.19) & (z > 0.53) & (np.abs(x) < 0.34), "back")
    # cloth: the banner is torso above the waist, pelvis below; the loincloths between the legs are pelvis
    cl = cloth_near & ~isin("spear", "back", "crown", "helm")
    setl(cl & (z >= 0.04), "cloth_upper")
    setl(cl & (z < 0.04), "cloth_lower")
    setl((np.abs(x) < 0.085) & (z < 0.0) & (z > -0.78) & ~isin("spear"), "cloth_lower")
    # knuckles: inside a ball (and its sleeve), the cut is the plane through its centre, square to the bone
    for child, side, c, a, R in knuckles():
        lab_c, lab_p = _knuckle_labels(child, side)
        c, a = c.astype(np.float32), a.astype(np.float32)
        q = P - c
        along = q @ a
        radial = np.linalg.norm(q - along[:, None] * a, axis=1)
        inside = (np.linalg.norm(q, axis=1) < R * 1.02) | ((along < R * region_top(child)) & (along > -R * SLEEVE[2])
                                                           & (radial < R * SLEEVE[0] * 1.12))   # bands too
        setl(inside & (along < 0), lab_c)
        setl(inside & (along >= 0), lab_p)
    return lab, names


def knuckles():
    """(child, side, centre, axis, radius) for every knuckle, centred Meshy units; sided parts get a mirrored copy."""
    out = []
    for child, (jn, ax, R) in KNUCKLES.items():
        c, a = np.asarray(J[jn], float), _unit(ax)
        out.append((child, "L", c, a, R))
        if child in SIDED:
            out.append((child, "R", c * (-1, 1, 1), a * (-1, 1, 1), R))
    return out


def _knuckle_labels(child, side):
    parent = TREE[child][2]
    parent = parent[0] if isinstance(parent, tuple) else parent
    lc = PARTS[child][0] if side == "L" else PARTS["_" + child + "_R"][0]
    lp = PARTS[parent][0] if (side == "L" or parent not in SIDED) else PARTS["_" + parent + "_R"][0]
    return lc, lp


def _tag(m, uv):
    return m.set_properties(2, lambda p, old: uv)


def housing(mf, r, z0, z1, rh=None, collar=True, cone=True, n=64):
    """A knuckle housing along local z from z0 to z1 (print mm, r the ball's radius): bronze (frame UV), a gold collar at its
    foot, a gold band at its top and a short taper into the limb. The wrist spear's sleeve uses it too."""
    h = HOUSING
    rh = r if rh is None else rh
    r1 = rh * h["taper"]
    parts = [_tag(mf.Manifold.cylinder(z1 - z0, rh, r1, n).translate((0, 0, z0)), FRAME_UV)]
    if collar:
        c0, c1, cr = h["collar"]
        parts.append(_tag(mf.Manifold.cylinder((c1 - c0) * r, cr * rh, cr * rh, n).translate((0, 0, c0 * r)), GOLD_UV))
    b = h["band"] * r
    parts.append(_tag(mf.Manifold.cylinder(b, r1 * 1.06, r1 * 1.06, n).translate((0, 0, z1 - b)), GOLD_UV))
    if cone:
        parts.append(_tag(mf.Manifold.cylinder(h["cone"] * r, r1, h["cone_to"] * r, n).translate((0, 0, z1)), FRAME_UV))
    return parts


def _orient(m, axis, c):
    """A solid built along local +z, turned so +z runs along `axis` and moved to c."""
    M = np.concatenate([_align(np.array([0.0, 0.0, 1.0]), _unit(axis)), np.asarray(c, float)[:, None]], 1)
    return m.transform(M.tolist())


def knuckle_solid(mf, c, a, r, seam_axis=None, child_axis=None, top=None):
    """The knuckle at centre c (print mm), ball radius r, tagged gold UV (-2, -2) and frame metal UV (-3, -3): the ball, the
    seam band (square to `seam_axis`, the normal of the cut between the two parts), the child's collar (along `child_axis`,
    the child's bone) and the housing up the parent's bone `a` (from the child into the parent). The axes are all `a` for a
    straight joint; seer_elbow.py bends the elbow, so there the cut and the forearm's bone lean off the upper arm's. `top`:
    the housing's length up the bone, x r (HOUSING["top"] by default)."""
    h = HOUSING
    sh, sr = h["seam"]
    lo, hi, cr = h["child_collar"]
    seam = _tag(mf.Manifold.cylinder(2 * sh * r, sr * r, sr * r, 64).translate((0, 0, -sh * r)), GOLD_UV)
    collar = _tag(mf.Manifold.cylinder((hi - lo) * r, cr * r, cr * r, 48).translate((0, 0, lo * r)), GOLD_UV)
    up = mf.Manifold.batch_boolean(housing(mf, r, h["start"] * r, (h["top"] if top is None else top) * r), mf.OpType.Add)
    parts = [_tag(mf.Manifold.sphere(r, 64).translate(tuple(np.asarray(c, float))), GOLD_UV),
             _orient(seam, a if seam_axis is None else seam_axis, c),
             _orient(collar, a if child_axis is None else child_axis, c),
             _orient(up, a, c)]
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def child_axis(child, side="L"):
    """The child's bone at its knuckle (into the parent), or None where it is the knuckle's own axis."""
    if child not in CHILD_AXIS:
        return None
    a = _unit(CHILD_AXIS[child])
    return a * (-1, 1, 1) if side == "R" else a


def knuckle_at(mf, to_mm, child, side, c, a, R):
    """One knuckle of knuckles() as a solid in print mm, and its centre there."""
    cm = to_mm(c)
    return knuckle_solid(mf, cm, a, R * S * PRINT_SCALE, child_axis=child_axis(child, side), top=housing_top(child)), cm


def extra_solids(mf, to_mm):
    """The ball knuckles (with their housings along the bone) as one solid, in print mm, tagged gold and frame metal."""
    out = [knuckle_at(mf, to_mm, *k)[0] for k in knuckles()]
    return mf.Manifold.batch_boolean(out, mf.OpType.Add)


def true_knuckles(solid, mf):
    """Give each part its exact half of every knuckle it meets. The parts are cut from voxel regions whose smoothed
    boundary rounds off where the cut plane meets the edge of the labelled cylinder, a few tenths of a mm inside the ball's
    rim and the seam band, so the cut face showed through there: dark patches (cut-face metal) round the top of the child's
    half ball. Here the child gets the knuckle's half below the plane through the ball's centre and loses the half above,
    the parent the other way round. A right-hand child is the left one mirrored later, so only its parent (the torso,
    the pelvis) is trued on that side."""
    from layout import to_mm
    for child, side, c, a, R in knuckles():
        parent = TREE[child][2]
        parent = parent[0] if isinstance(parent, tuple) else parent
        if side == "R" and parent in SIDED:
            continue
        k, cm = knuckle_at(mf, to_mm, child, side, c, a, R)
        a = _unit(a)
        up = k.trim_by_plane(tuple(a), float(a @ cm))               # the parent's half (along the bone into the parent)
        down = k.trim_by_plane(tuple(-a), float(-a @ cm))           # the child's
        if side == "L" and child in solid:
            solid[child] = (solid[child] - up) + down
        if parent in solid:
            solid[parent] = (solid[parent] - down) + up
    return solid


def _rot(axis, deg):
    a = _unit(axis)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


def _align(zc, ax):
    """Rotation taking unit vector zc onto unit vector ax."""
    w = np.cross(zc, ax)
    s, cth = np.linalg.norm(w), zc @ ax
    if s < 1e-8:
        return np.eye(3) if cth > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - cth) / s ** 2)


def seat_spear(solid, mf):
    """Put the spear in the left fist, in the pose of the sword the Meshy figure held there (Luke liked that pose). In the
    Meshy figure the spear is couched under the right arm and touches it only at the elbow, where there is no room for a
    peg; held in the fist, either hand can carry it (the right fist is the left one mirrored). The spear keeps its own
    shape: it is turned onto the old sword's line, moved so a plain stretch of shaft runs through the fist, turned a
    little more (within 30 degrees, and about its own axis) to clear the arm, body and legs and stay off the base, the
    grip stretch is trued up as a round shaft, and the fist gets the matching bore."""
    from layout import joint
    sp, fist = solid["spear"], solid["hand"]
    P = np.asarray(sp.to_mesh().vert_properties)[:, :3]
    c = P.mean(0)
    a = np.linalg.svd(P - c, full_matrices=False)[2][0]
    a = a if a[2] < 0 else -a                      # from the butt towards the tip
    s = _unit(SWORD)
    G = np.array(joint("grip"))                    # the fist's grip centre
    floor = BASE * PRINT_SCALE                     # top of the base: the tip must stay above it
    others = [solid[k].simplify(0.3) for k in ("arm", "forearm", "torso", "pelvis", "thigh", "shin", "foot", "pauldron")
              if k in solid]
    lite = sp.simplify(0.3)
    best = None
    for grip_t in (GRIP_T, GRIP_T + 2.0, GRIP_T - 2.0):
        g0 = c + grip_t * a                        # grip point on the shaft
        for roll in (0, 90, 180, 270):
            R0 = _align(a, s) @ _rot(a, roll)      # onto the sword's line, turned about its own axis
            for ax_a in (0, -10, 10, -20, 20, -30, 30):
                for ax_b in (0, -10, 10, -20, 20, -30, 30):
                    Rm = _rot((1, 0, 0), ax_a) @ _rot((0, 1, 0), ax_b) @ R0
                    T = np.concatenate([Rm, (G - Rm @ g0)[:, None]], 1).tolist()
                    moved = lite.transform(T)
                    hit = sum((moved ^ o).volume() for o in others)
                    low = max(0.0, floor - moved.bounding_box()[2])
                    score = hit + 5.0 * low + 0.02 * (abs(ax_a) + abs(ax_b)) + 0.3 * abs(grip_t - GRIP_T)
                    if best is None or score < best[0]:
                        best = (score, grip_t, roll, ax_a, ax_b, T, hit, Rm, low)
    _, grip_t, roll, ax_a, ax_b, T, hit, Rm, low = best
    print(f"  spear: grip at {grip_t} mm, roll {roll}, turned {ax_a} / {ax_b} deg off the sword's line, "
          f"overlap with body {hit:.1f} mm3, below the base {low:.1f} mm", flush=True)
    sp = sp.transform(T)
    na = Rm @ a
    L = 9.0                                          # bore and true-up length, through the fist
    Rz = _align(np.array([0.0, 0.0, 1.0]), na)
    M4 = np.concatenate([Rz, G[:, None]], 1).tolist()
    shaft = mf.Manifold.cylinder(L + 1.2, SHAFT_R, -1.0, 32).translate((0, 0, -L / 2 - 0.6)).transform(M4)   # overlaps the cut ends
    bore = mf.Manifold.cylinder(L + 6, SHAFT_R + BORE_CLEAR, -1.0, 32).translate((0, 0, -L / 2 - 3)).transform(M4)
    # true up the grip: whatever the Meshy shaft has there (rings, flares) is replaced by a plain round shaft
    clear = mf.Manifold.cylinder(L, 4.0, -1.0, 32).translate((0, 0, -L / 2)).transform(M4)
    solid["spear"] = (sp - clear) + shaft.set_properties(2, lambda q, old: (-2.0, -2.0))
    solid["hand"] = fist - bore.set_properties(2, lambda q, old: (-1.0, -1.0))
    _extra["spear_seat"] = {"grip_t_mm": grip_t, "roll_deg": roll, "turn_deg": [ax_a, ax_b],
                            "overlap_mm3": round(hit, 1), "axis": [round(float(v), 4) for v in na]}
    return solid


def design(solid, mf):
    """True the knuckles, seat the spear in the fist, then fuse every loose piece of a part to its main body with a short
    strut."""
    from scipy.spatial import cKDTree
    solid = true_knuckles(solid, mf)
    if "spear" in solid and "hand" in solid:
        solid = seat_spear(solid, mf)
    out = {}
    for k, m in solid.items():
        ps = sorted(m.decompose(), key=lambda p: -p.volume())
        if len(ps) == 1:
            out[k] = m
            continue
        body = ps[0]
        for p in ps[1:]:
            A = np.asarray(body.to_mesh().vert_properties)[:, :3]
            B = np.asarray(p.to_mesh().vert_properties)[:, :3]
            d, i = cKDTree(A).query(B, k=1)
            j = int(d.argmin())
            a, b = A[i[j]], B[j]
            v = b - a
            L = float(np.linalg.norm(v))
            if p.volume() < 0.5 or (L > 2.5 and p.volume() < 20):   # crumbs, or small bits far away: drop
                if p.volume() > 0.05:
                    print(f"  {k}: dropped a {p.volume():.1f} mm3 piece {L:.1f} mm away", flush=True)
                continue
            r = 0.6 if L < 2.5 else 0.85
            ax = v / max(L, 1e-6)
            # strut from 0.8 mm inside the body to 0.8 mm inside the piece
            st = mf.Manifold.cylinder(L + 1.6, r, -1.0, 20).translate((0, 0, -0.8))
            zc = np.array([0.0, 0.0, 1.0])
            w = np.cross(zc, ax)
            s, cth = np.linalg.norm(w), zc @ ax
            if s < 1e-8:
                Rm = np.eye(3) if cth > 0 else np.diag([1.0, -1.0, -1.0])
            else:
                vx = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
                Rm = np.eye(3) + vx + vx @ vx * ((1 - cth) / s ** 2)
            st = st.transform(np.concatenate([Rm, a[:, None]], 1).tolist()).set_properties(2, lambda q, old: (-2.0, -2.0))
            body = body + p + st
            print(f"  {k}: strut {L:.2f} mm to a {p.volume():.1f} mm3 piece", flush=True)
        out[k] = body
    return out


# part: (game triangles, texture size)
# The arm carries the Hellfire socket in its own mesh and textures since the 2026-11-08 polish (seer_items.py), so it has a
# bigger budget than its 1800 triangles and 512 px before.
BUDGET = {
    "torso": (10000, 1024), "pelvis": (7000, 1024), "helm": (3000, 768), "crown": (4000, 768), "back": (5000, 768),
    "pauldron": (6500, 1024), "arm": (2600, 768), "forearm": (2800, 768), "hand": (3000, 768),
    "thigh": (3200, 768), "shin": (3800, 768), "foot": (2500, 512), "spear": (7000, 1024),
}
LABEL = {
    "pelvis": "Pelvis + loincloths + banner", "torso": "Torso + banner", "helm": "Helm", "crown": "Halo + crown spire",
    "back": "Reliquary spires", "pauldron": "Pauldron + wing", "arm": "Upper arm",
    "forearm": "Forearm", "hand": "Fist (spear bore)",
    "thigh": "Thigh", "shin": "Greave", "foot": "Foot", "spear": "Spear (equipment)",
}
POSE = {
    "arm_L": (25, 0, 10), "forearm_L": (-35, 0, 0), "arm_R": (-30, 0, 0), "helm": (0, 0, 20),
    "thigh_L": (-20, 0, 0), "shin_L": (25, 0, 0), "foot_L": (-5, 0, 0),
}
EXPLODE, EXPLODE_MARGIN = 10.0, 0.85     # render.py: exploded view reach (print mm) and framing
