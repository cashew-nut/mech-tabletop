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
  * Both arms are their own. The Seer's character is its asymmetry (spear couched under the right arm, a sword-hand on
    the left), so arms and pauldrons are built natively for each side; legs are built for the left and mirrored.
  * One solid per part. The left wing is a separate shell in the Meshy file (it floats behind the pauldron); design()
    fuses any loose piece of a part to the part's main body with a strut, so nothing has to be glued in place.
  * The spear is equipment (the Seer's arc cannon slot) and plugs into the right arm where it is couched.

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


def _c(p):
    """Absolute Meshy position to centred (x - CX)."""
    return (p[0] - CX, p[1], p[2])


# Joints, absolute Meshy units. Left side unless named _r (the right arm is its own part).
JOINTS_ABS = {
    "pelvis": (CX, 0.08, -0.02), "spine": (CX, 0.08, 0.06), "chest": (CX, 0.10, 0.30),
    "neck": (CX, 0.05, 0.565), "head": (CX, 0.03, 0.62),
    "shoulder": (0.475, 0.16, 0.49), "elbow": (0.605, 0.19, 0.08), "wrist": (0.715, 0.08, -0.34),
    "shoulder_r": (-0.005, 0.14, 0.47), "elbow_r": (-0.075, -0.04, 0.18), "wrist_r": (-0.08, -0.26, -0.01),
    "hip": (0.38, 0.08, -0.03), "knee": (0.465, 0.065, -0.40), "ankle": (0.57, 0.03, -0.80),
    "grip_r": (-0.086, -0.304, -0.075),
    "pauldron_mount": (0.41, 0.26, 0.58),
}
JOINTS = {k: _c(v) for k, v in JOINTS_ABS.items()}     # centred


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
    "arm_r": ("shoulder_r", (1.0, 0.0, 0.0), 0.062),
    "forearm_r": ("elbow_r", _toward("elbow_r", "shoulder_r"), 0.055),
    "hand_r": ("wrist_r", _toward("wrist_r", "elbow_r"), 0.05),
    "thigh": ("hip", _toward("knee", "hip"), 0.062),
    "shin": ("knee", _toward("knee", "hip"), 0.058),
    "foot": ("ankle", _toward("ankle", "knee"), 0.055),
    # The left wing floats in the Meshy file and the left pauldron touches the torso only at a sliver, so it gets a
    # knuckle behind the shoulder, where the right wing's root meets the torso, above the arm's socket.
    "pauldron": ("pauldron_mount", (0.0, -1.0, 0.0), 0.04),
}
KNUCKLES = {k: (j, a, r * KG) for k, (j, a, r) in KNUCKLES.items()}
# Knuckle sleeve: radius, and length into the parent / into the child, as fractions of the ball's radius. The hole
# (with its magnet) is in the parent, so the sleeve runs deep on that side; the child side carries only the peg root.
SLEEVE = (1.0, 2.2, 0.7)

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
    "arm_r": ("arm-right", "shoulder_r", "torso"),
    "pauldron_r": ("pauldron-right", "shoulder_r", ("arm_r", "torso")),
    "forearm_r": ("forearm-right", "elbow_r", "arm_r"),
    "hand_r": ("hand-right", "wrist_r", "forearm_r"),
    "thigh": ("thigh", "hip", "pelvis"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
    "spear": (None, "grip_r", "hand_r"),   # equipment: item_arc-cannon@seer, held through the right fist
}
# Held equipment has no peg: its shaft goes through a bore in the fist (see design()).
GRIP_T, SHAFT_R, BORE_CLEAR = 5.25, 0.8, 0.06     # grip point on the shaft (mm from the spear's centre), shaft radius
HELD = {"spear": {"parent": "hand_r", "peg": None,
                  "how": f"shaft ({2 * SHAFT_R:g} mm) push-fits through a {2 * (SHAFT_R + BORE_CLEAR):.2f} mm bore in the right fist"}}
SIDED = {"thigh", "shin", "foot"}

# Physical parts and the labels each is made of; right-side mirrored parts' labels only carve the torso and pelvis.
PARTS = {
    "torso": ["torso", "cloth_upper"], "pelvis": ["pelvis", "cloth_lower"],
    "helm": ["helm"], "crown": ["crown"], "back": ["back"],
    "pauldron": ["pauldron_L"], "pauldron_r": ["pauldron_R"],
    "arm": ["arm_L"], "forearm": ["forearm_L"], "hand": ["hand_L"],
    "arm_r": ["arm_R"], "forearm_r": ["forearm_R"], "hand_r": ["hand_R"],
    "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"], "spear": ["spear"],
    "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"], "_foot_R": ["foot_R"],
}

J = JOINTS
BONES = {  # label: (A, B, radius), centred
    "torso": ((0, 0.09, 0.12), (0, 0.09, 0.52), 0.15),
    "pelvis": ((0, 0.08, -0.10), (0, 0.08, 0.04), 0.15),
    "pauldron_L": (_c((0.47, 0.17, 0.55)), _c((0.56, 0.24, 0.53)), 0.08),
    "arm_L": (J["shoulder"], J["elbow"], 0.065), "forearm_L": (J["elbow"], J["wrist"], 0.08),
    "hand_L": (J["wrist"], _c((0.80, -0.02, -0.80)), 0.06),
    "arm_R": (J["shoulder_r"], J["elbow_r"], 0.065), "forearm_R": (J["elbow_r"], J["wrist_r"], 0.07),
    "hand_R": (J["wrist_r"], _c((-0.11, -0.36, -0.08)), 0.07),
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
        inside = (np.linalg.norm(q, axis=1) < R * 1.02) | ((along < R * SLEEVE[1]) & (along > -R * SLEEVE[2])
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


def extra_solids(mf, to_mm):
    """The ball knuckles (with sleeves along the bone) as one solid, in print mm. Their faces get UV (-2, -2)."""
    out = []
    for child, side, c, a, R in knuckles():
        c = to_mm(c)
        r = R * S * PRINT_SCALE
        ball = mf.Manifold.sphere(r, 48)
        rs, up, dn = SLEEVE[0] * r, SLEEVE[1] * r, SLEEVE[2] * r
        sl = mf.Manifold.cylinder(up + dn - rs * 0.6, rs, -1.0, 40).translate((0, 0, -dn))
        cap = mf.Manifold.sphere(rs, 40).scale((1, 1, 0.6)).translate((0, 0, up - rs * 0.6))   # domed end, not a can
        bands = [mf.Manifold.cylinder(0.12 * r, rs * 1.1, -1.0, 40).translate((0, 0, z * r)) for z in (0.95, 1.55)]
        k = mf.Manifold.batch_boolean([ball, sl, cap] + bands, mf.OpType.Add)
        # rotate local z onto the bone axis
        zc = np.array([0.0, 0.0, 1.0])
        v = np.cross(zc, a)
        s, cth = np.linalg.norm(v), zc @ a
        if s < 1e-8:
            Rm = np.eye(3) if cth > 0 else np.diag([1.0, -1.0, -1.0])
        else:
            vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
            Rm = np.eye(3) + vx + vx @ vx * ((1 - cth) / s ** 2)
        M = np.concatenate([Rm, c[:, None]], 1)
        out.append(k.transform(M.tolist()))
    solid = mf.Manifold.batch_boolean(out, mf.OpType.Add)
    return solid.set_properties(2, lambda p, old: (-2.0, -2.0))


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
    """Put the spear in the right fist. In the Meshy figure it is couched under the arm and touches it only at the elbow,
    where there is no room for a peg; held in the fist, any hand with the bore can carry it. The spear keeps its own
    shape: it is moved so a plain stretch of shaft runs through the fist, turned (within 40 degrees) to clear the arm,
    body and legs, the grip stretch is trued up as a round shaft, and the fist gets the matching bore."""
    from layout import joint
    sp, fist = solid["spear"], solid["hand_r"]
    P = np.asarray(sp.to_mesh().vert_properties)[:, :3]
    c = P.mean(0)
    a = np.linalg.svd(P - c, full_matrices=False)[2][0]
    a = a if a[2] < 0 else -a                      # from the butt towards the tip
    g0 = c + GRIP_T * a                            # grip point on the shaft
    G = np.array(joint("grip_r"))                  # the fist's grip centre
    others = []
    for k in ("arm_r", "forearm_r", "torso", "pelvis", "thigh", "shin", "foot", "pauldron_r"):
        m = solid[k].simplify(0.3)
        others.append(m.transform([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]]) if k in SIDED else m)
    lite = sp.simplify(0.3)
    best = None
    for ax_a in (0, -15, 15, -30, 30, -40, 40):
        for ax_b in (0, -15, 15, -30, 30, -40, 40):
            Rm = _rot((1, 0, 0), ax_a) @ _rot((0, 1, 0), ax_b)
            T = np.concatenate([Rm, (G - Rm @ g0)[:, None]], 1).tolist()
            moved = lite.transform(T)
            hit = sum((moved ^ o).volume() for o in others)
            score = hit + 0.02 * (abs(ax_a) + abs(ax_b))
            if best is None or score < best[0]:
                best = (score, ax_a, ax_b, T, hit, Rm)
    _, ax_a, ax_b, T, hit, Rm = best
    print(f"  spear: grip at {GRIP_T} mm, turned {ax_a} / {ax_b} deg, overlap with body {hit:.1f} mm3", flush=True)
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
    solid["hand_r"] = fist - bore.set_properties(2, lambda q, old: (-1.0, -1.0))
    _extra["spear_seat"] = {"turn_deg": [ax_a, ax_b], "overlap_mm3": round(hit, 1), "axis": [round(float(v), 4) for v in na]}
    return solid


def design(solid, mf):
    """Seat the spear in the fist, then fuse every loose piece of a part to its main body with a short strut."""
    from scipy.spatial import cKDTree
    if "spear" in solid and "hand_r" in solid:
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
BUDGET = {
    "torso": (10000, 1024), "pelvis": (7000, 1024), "helm": (3000, 768), "crown": (4000, 768), "back": (5000, 768),
    "pauldron": (6500, 1024), "pauldron_r": (6500, 1024), "arm": (1800, 512), "forearm": (2800, 768), "hand": (3000, 768),
    "arm_r": (1800, 512), "forearm_r": (2800, 768), "hand_r": (2500, 512),
    "thigh": (3200, 768), "shin": (3800, 768), "foot": (2500, 512), "spear": (7000, 1024),
}
LABEL = {
    "pelvis": "Pelvis + loincloths + banner", "torso": "Torso + banner", "helm": "Helm", "crown": "Halo + crown spire",
    "back": "Reliquary spires", "pauldron": "Pauldron + wing (left)", "pauldron_r": "Pauldron + wing (right)", "arm": "Upper arm (left)", "forearm": "Forearm (left)",
    "hand": "Sword hand (left)", "arm_r": "Upper arm (right)", "forearm_r": "Forearm (right)", "hand_r": "Fist (right)",
    "thigh": "Thigh", "shin": "Greave", "foot": "Foot", "spear": "Spear (equipment)",
}
POSE = {
    "arm": (25, 0, 10), "forearm": (-35, 0, 0), "arm_r": (-30, 0, 0), "helm": (0, 0, 20),
    "thigh_L": (-20, 0, 0), "shin_L": (25, 0, 0), "foot_L": (-5, 0, 0),
}
EXPLODE = 15.0              # render.py: exploded view reach, print mm
