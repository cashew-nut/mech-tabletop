"""The Iron Covenant Sentinel's settings for the composite pipeline (MODEL=sentinel; numpy only). See README.md.

The Sentinel is a new walker: Luke's approved concept art (docs/concept-art/sentinel/) was turned into one Meshy
whole-body model (multi-image-to-3D, then retexture; project folder meshy-sources/sentinel/model/), and this module cuts
it into closed parts the way the Paladin, Brute and Seer were cut. What is specific to this figure:

* **Axes.** cut.py extract puts the figure z up, facing -Y, walker's left +X. Meshy normalised this model to z -1..1
  (sole to spire tip), so the figure's own units differ from the Paladin's; every number here is in those units. The
  figure's centre line is x = 0 (y is arbitrary: the body sits around y = 0.2).
* **Print scale.** Sole to helm top is the bulwark frame's 42 kit mm (plus the 3 mm base), so S = 42 / 1.69 kit mm per unit
  (helm crest z = 0.69, sole z = -1.0); at Luke's 1.5x that is about 67 mm to the helm top and 79 mm to the spire tips.
* **The gun arm.** The right arm is the Carapace Gun: the upper arm hangs and the whole forearm is a rotary gun held
  level, pointing forward. Like the Brute's gatling, the gun is cut from the figure's right, mirrored and re-seated on
  the left forearm's socket (RESEAT), so it fits an elbow of either side. Meshy's two upper arms are mirror images, so
  the mirrored gun already sits on the left elbow: RESEAT_POSE keeps the sculpt's level pose instead of turning the gun
  onto the forearm's line (which hung it barrel-down to the ground) and trims it so it pulls straight off its peg. The
  body keeps one plain left arm (arm, forearm, hand), mirrored for the right when the gun is not fitted.
* **Tabard.** The hanging cloth in front of the pelvis is part of the pelvis (as on the Paladin); the banner pole and
  flag in the concept art did not come out of Meshy (too thin), so the back part is the two spires and the pack.
* **Symmetry.** Labels are symmetric (|x|), so the right half of the torso and pelvis is carved where the mirrored
  left limbs sit. Torso, pelvis, helm and back keep Meshy's own detail.
* **Banner, pennants, heavy elbow (second polish pass, 2026-11-09; sentinel_polish.py).** The banner staff and flag and the
  spire pennants are built in print mm and fused to the back; the elbow is a ball knuckle (KNUCKLES) whose halves go to the
  upper arm, the forearm and the gun, so the elbow takes a much bigger peg and magnet.
* **Finish (polish pass, 2026-11-09).** Meshy's retexture is dusty khaki and grey-brown; covenant_grade.py grades it to the
  Paladin's black enamel, bright gold and crimson before the bake (Meshy's own files are kept). Meshy painted the
  concept's lights as cream texels, the slanted eyes under the brow and the furnace window behind the chest grille;
  glow_weight lets the glow map show only there, so they burn amber in the game (GLOW_STRENGTH, with its bloom).
"""
import numpy as np

NAME = "sentinel"
TUNE = "covenant/bulwark"       # not used: the joints are measured below (this model measures its own)
CX = 0.0
PRINT_SCALE = 1.5               # Luke, 2026-11-01: collector scale is 1.5x the game
FOOT_Z = -1.0                   # Meshy z of the sole
S = 42 / 1.69                   # kit mm per figure unit (sole to helm top 42 mm, the bulwark frame)
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
    "helm": ((0.0, 0.0, 0.50), (0.0, 0.0, 0.58), 0.13),
    "torso": ((0.0, 0.07, 0.20), (0.0, 0.07, 0.43), 0.30),
    "pelvis": ((0.0, 0.10, -0.12), (0.0, 0.10, 0.07), 0.26),
}
BONES_S = {
    "pauldron": ((0.40, 0.25, 0.42), (0.52, 0.25, 0.46), 0.18),
    "arm": ((0.42, 0.23, 0.30), (0.50, 0.22, 0.12), 0.11),
    "forearm": ((0.50, 0.21, 0.12), (0.55, 0.12, -0.20), 0.12),
    "hand": ((0.56, 0.10, -0.20), (0.55, 0.08, -0.34), 0.11),
    "thigh": ((0.28, 0.20, -0.06), (0.34, 0.18, -0.47), 0.17),
    "shin": ((0.34, 0.18, -0.49), (0.46, 0.20, -0.86), 0.16),
}
PAULDRON_BOX = ((0.34, 0.66), (0.0, 0.52), (0.32, 0.66))     # |x|, y, z ranges of the shoulder plate and its spire
FOOT_TOP = -0.88                                              # below this, everything on a side is its foot
GUN = ((-0.66, -0.25), (-0.80, 0.80), (-0.25, 0.17))         # x (the figure's right), y, z: the gun, from the elbow down

PARTS = {
    "torso": ["torso", "collar"], "pelvis": ["pelvis", "tabard"], "helm": ["helm"], "back": ["back"],
    "pauldron": ["pauldron_L"], "arm": ["arm_L"], "forearm": ["forearm_L"], "hand": ["hand_L"],
    "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"], "gun": ["gun"],
    "_pauldron_R": ["pauldron_R"], "_arm_R": ["arm_R"], "_forearm_R": ["forearm_R"], "_hand_R": ["hand_R"],
    "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"], "_foot_R": ["foot_R"],
}

JOINTS = {
    "pelvis": (0.0, 0.10, 0.0), "spine": (0.0, 0.10, 0.14), "chest": (0.0, 0.10, 0.30),
    "neck": (0.0, 0.05, 0.46), "head": (0.0, 0.0, 0.52),
    "shoulder": (0.42, 0.23, 0.30), "elbow": (0.50, 0.22, 0.12), "wrist": (0.55, 0.12, -0.20),
    "hip": (0.28, 0.20, -0.06), "knee": (0.34, 0.18, -0.48), "ankle": (0.46, 0.20, -0.86),
}

# part: (kit component it publishes as, joint its origin sits on, parent part it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "thigh": ("thigh", "hip", "pelvis"),       # before the torso: the hips get first pick of the pelvis for their holes
    "torso": ("torso", "spine", "pelvis"),
    "helm": ("helm", "head", "torso"),
    "back": ("back", "chest", "torso"),
    "pauldron": ("pauldron", "shoulder", "torso"),
    "arm": ("arm", "shoulder", "pauldron"),
    "forearm": ("forearm", "elbow", "arm"),
    "hand": ("hand", "wrist", "forearm"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
    "gun": ("forearm", "elbow", "arm"),        # equipment forearm: the Carapace Gun, re-seated on the forearm's socket
}
SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot", "gun"}
RESEAT = {"gun": "forearm"}
RESEAT_POSE = {"gun": "mirror"}                # keep the sculpt's level pose (the arms are mirror images): joints.py
LOADOUT = {"gun": "R"}                         # the figure's own pose; the left copy is a hidden spare

# part: (game triangles, texture size). The back carries the banner and pennants, the arm the elbow housing (2026-11-09).
BUDGET = {
    "torso": (11000, 1024), "pelvis": (7000, 1024), "helm": (3500, 1024), "back": (9500, 1024),
    "pauldron": (7500, 1024), "arm": (2800, 768), "forearm": (3200, 768), "hand": (2500, 512),
    "thigh": (3500, 768), "shin": (4200, 768), "foot": (2500, 512), "gun": (9000, 1024),
}
LABEL = {
    "pelvis": "Pelvis + tabard", "torso": "Torso + gorget", "helm": "Helm", "back": "Spires + pack + banner",
    "pauldron": "Pauldron", "arm": "Upper arm + elbow", "forearm": "Forearm", "hand": "Gauntlet", "thigh": "Thigh",
    "shin": "Greave", "foot": "Sabaton", "gun": "Carapace Gun (equipment)",
}
EXPLODE, EXPLODE_DROP = 11.0, 4.0
POSE = {
    "arm_L": (-25, 0, 0), "forearm_L": (-45, 0, 0), "helm": (0, 0, -20),
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
    # the tabard hangs in front of and below the belt, between the thighs
    setl((a < 0.15) & (z < -0.08) & (z > -0.84) & (y < 0.28), "tabard")
    (px0, px1), (py0, py1), (pz0, pz1) = PAULDRON_BOX
    paul = (a >= px0) & (a < px1) & (y >= py0) & (y < py1) & (z >= pz0) & (z < pz1)
    setl(paul & L, "pauldron_L")
    setl(paul & ~L, "pauldron_R")
    setl((z < FOOT_TOP) & L & (a > 0.15), "foot_L")
    setl((z < FOOT_TOP) & ~L & (a > 0.15), "foot_R")
    # gorget, the spires and the back pack, the helm
    helm = ((x ** 2 / 0.13 ** 2) + ((y + 0.02) ** 2 / 0.17 ** 2) + ((z - 0.55) ** 2 / 0.14 ** 2) < 1) & (z > 0.42)
    back = ((y > 0.30) & (z > 0.12) & (a < 0.34)) | ((z > 0.60) & (a < 0.28) & (y > 0.05) & ~helm)
    setl(back, "back")
    setl(helm & ~back, "helm")
    setl((z > 0.44) & (z < 0.58) & (a < 0.2) & ~helm & ~back & np.isin(lab, [names.index("torso"), names.index("helm")]),
         "collar")
    # the gun: everything of the figure's right below the elbow and out past the upper arm
    (gx0, gx1), (gy0, gy1), (gz0, gz1) = GUN
    setl((x >= gx0) & (x < gx1) & (y >= gy0) & (y < gy1) & (z >= gz0) & (z < gz1), "gun")
    return lab, names



# --- finish and lights (polish pass, 2026-11-09) -------------------------------------------------------------------
MM = S * PRINT_SCALE            # print mm per figure unit
GLOW_STRENGTH = 3.0             # emission strength (glTF KHR_materials_emissive_strength), as the Brute's furnace
# Where the glow map may show, figure units (x centred, forward is -y). The grille box takes the recessed window only
# (the gold V plates in front of it are nearer than y -0.03); the eye bands follow the slant of the painted eyes
# (inner end lower) and stop short of the gold ridge down the face.
GRILLE = ((-0.058, 0.058), (-0.03, 0.08), (0.090, 0.184), 0.004)
EYES = dict(x=(0.006, 0.038), z0=0.5615, x0=0.0115, slope=0.64, half=0.007, y=(-0.08, 0.02), soft=0.0025)


def _to_mm(P):
    P = np.asarray(P, np.float64)
    return np.stack([P[..., 0] * MM, P[..., 1] * MM, ((P[..., 2] - FOOT_Z) * S + BASE) * PRINT_SCALE], -1)


def _from_mm(P):
    P = np.asarray(P, np.float64)
    return np.stack([P[..., 0] / MM, P[..., 1] / MM, (P[..., 2] / PRINT_SCALE - BASE) / S + FOOT_Z], -1)


def _band(v, lo, hi, e):
    return np.clip((v - lo) / e, 0, 1) * np.clip((hi - v) / e, 0, 1)


def glow_weight(P_mm):
    """0..1 per vertex (print mm, kit axes; the left-hand set is the figure's own left): how much light a vertex shows."""
    Q = _from_mm(P_mm)
    x, y, z = Q[:, 0], Q[:, 1], Q[:, 2]
    (gx0, gx1), (gy0, gy1), (gz0, gz1), e = GRILLE
    w = _band(x, gx0, gx1, e) * _band(y, gy0, gy1, e) * _band(z, gz0, gz1, e)
    a, k = np.abs(x), EYES
    zl = k["z0"] + k["slope"] * (a - k["x0"])
    eye = (_band(a, *k["x"], k["soft"]) * _band(z - zl, -k["half"], k["half"], k["soft"])
           * _band(y, *k["y"], k["soft"]) * (z > 0.50))
    return np.maximum(w, eye)


def surface_textures(work):
    """Graded base colour and metal/roughness, and the lamp light (covenant_grade.py), for build.py."""
    import covenant_grade
    return covenant_grade.surface_textures(work, lamps=lambda Q: glow_weight(_to_mm(Q)))


# --- banner, pennants and the heavy elbow (second polish pass, 2026-11-09) ------------------------------------------
# sentinel_polish.py builds them; split.py calls design() after the cut and re-stamps CHANGED into the voxel grid, so
# joints.py measures the elbow's peg and hole against the knuckle. Forearm last as well as first: its old voxels inside the
# arm's half ball are freed by the forearm's pass and taken by the arm's, and the arm's below the seam by the second.
CHANGED = ("forearm", "gun", "arm", "forearm", "back")
# The elbow's ball knuckle: joints.py tries its centre and the upper arm's bone first (child -> joint, axis into the parent).
KNUCKLES = {"forearm": ("elbow", tuple(np.subtract(JOINTS["shoulder"], JOINTS["elbow"])), 0.115)}
# Designed finishes (build.py), matched to covenant_grade's targets in linear light: gold trim, blackened steel, crimson cloth.
KNUCKLE_FINISH = ((0.33, 0.205, 0.075), 0.36, 0.9)
FRAME_FINISH = ((0.03, 0.031, 0.034), 0.32, 0.8)   # blackened steel, so the ball catches a highlight
CLOTH_FINISH = ((0.20, 0.010, 0.009), 0.66, 0.0)
SHARP_DESIGNED = 35.0       # crisp rims on the designed solids (as the Seer's)
DESIGNED_WEAR = True        # cavity darkening and a faint mottle, so the designed gold and cloth sit with Meshy's texture


def design(solid, mf):
    import sentinel_polish
    return sentinel_polish.design(solid, mf)
