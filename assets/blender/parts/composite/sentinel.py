"""The Iron Covenant Sentinel's settings for the composite pipeline (MODEL=sentinel; numpy only). See README.md.

The Sentinel is a new walker: Luke's approved concept art (docs/concept-art/sentinel/) was turned into one Meshy
whole-body model (multi-image-to-3D, then retexture; project folder meshy-sources/sentinel/model/), and this module cuts
it into closed parts the way the Paladin, Brute and Seer were cut. What is specific to this figure:

* **Axes.** cut.py extract puts the figure z up, facing -Y, walker's left +X. Meshy normalised this model to z -1..1
  (sole to spire tip), so the figure's own units differ from the Paladin's; every number here is in those units. The
  figure's centre line is x = 0 (y is arbitrary: the body sits around y = 0.2).
* **Print scale.** A bulwark is 42 kit mm to the helm top, 63 mm printed at Luke's 1.5x (docs/model-pipeline-plan.md);
  the helm top (crest) is z = 0.69, the sole z = -1.0, so S = 42 / 1.69 kit mm per unit. The back spires reach 79 mm.
* **The gun arm.** The right arm is the Carapace Gun: the upper arm hangs and the whole forearm is a rotary gun held
  level, pointing forward. Like the Brute's gatling, the gun is cut from the figure's right, mirrored, turned and
  re-seated on the left forearm's socket (RESEAT), so it fits an elbow of either side. The body keeps one plain
  left arm (arm, forearm, hand), mirrored for the right when the gun is not fitted.
* **Tabard.** The hanging cloth in front of the pelvis is part of the pelvis (as on the Paladin); the banner pole and
  flag in the concept art did not come out of Meshy (too thin), so the back part is the two spires and the pack.
* **Symmetry.** Labels are symmetric (|x|), so the right half of the torso and pelvis is carved where the mirrored
  left limbs sit. Torso, pelvis, helm and back keep Meshy's own detail.
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
LOADOUT = {"gun": "R"}                         # the figure's own pose; the left copy is a hidden spare

# part: (game triangles, texture size)
BUDGET = {
    "torso": (11000, 1024), "pelvis": (7000, 1024), "helm": (3500, 1024), "back": (6500, 1024),
    "pauldron": (7500, 1024), "arm": (1800, 512), "forearm": (2800, 768), "hand": (2500, 512),
    "thigh": (3500, 768), "shin": (4200, 768), "foot": (2500, 512), "gun": (9000, 1024),
}
LABEL = {
    "pelvis": "Pelvis + tabard", "torso": "Torso + gorget", "helm": "Helm", "back": "Spires + pack",
    "pauldron": "Pauldron", "arm": "Upper arm", "forearm": "Forearm", "hand": "Gauntlet", "thigh": "Thigh",
    "shin": "Greave", "foot": "Sabaton", "gun": "Carapace Gun (equipment)",
}
EXPLODE, EXPLODE_DROP = 11.0, 4.0
POSE = {
    "gun_R": (-90, 0, 0), "arm_L": (-25, 0, 0), "forearm_L": (-45, 0, 0), "helm": (0, 0, -20),
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

