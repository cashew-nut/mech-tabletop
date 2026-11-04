"""The Ashen Foundries Artillery's settings for the composite pipeline (MODEL=artillery; numpy only). See README.md.

Second whole-body walker from the Meshy pipeline (docs/model-pipeline-plan.md): Luke's approved concept art
(docs/concept-art/artillery/) went to one multi-image-to-3D mesh and one retexture (project folder
meshy-sources/artillery/model/), and this module cuts it into closed parts the way the Sentinel was cut. What is specific
to this figure:

* **Axes.** cut.py extract puts the figure z up, facing -Y, the walker's left +X. Meshy normalised the model to y -1..1
  (the howitzer's length), so z runs -0.80 (sole) to 0.80 (smokestack tops). The figure's centre line is x = 0.09
  (stacks, feet and torso agree on it), so CX = 0.09.
* **Print scale.** Sole to the torso roof (z = 0.50) is the bulwark frame's 42 kit mm, so S = 42 / 1.30 kit mm per unit;
  at Luke's 1.5x the stack tops stand about 78 mm.
* **Three legs.** Meshy read the three-quarter "side" view as a third, rear leg (x -0.4, y 0.4..1.0). It is dropped
  (label _rear); the walker keeps the two front legs, the left one cut and mirrored for the right.
* **No head.** The mesh has no head (the concept's is hidden behind the howitzer's breech), so the helm is the armoured
  cupola dome on top of the torso, just behind the breech.
* **The howitzer** stays with the torso (cradle and barrel are one solid with it, 80 mm front to back at print scale: the
  barrel is a thin tube). The back is the two smokestacks, the rear ammunition pack and the roof plates, one solid on the
  torso's roof on one peg. The cupola plugs into the back's roof.
* **Arms.** The left arm holds an artillery shell in a clamp, the forearm level and pointing forward (like the Sentinel's
  gun arm); it is mirrored for the right. The figure's own right arm (a heavy autocannon-like block hanging from the
  elbow) is not cut: it needs a peg design of its own (see docs/artillery-composite/README.md).
"""
import numpy as np

NAME = "artillery"
TUNE = "foundries/artillery"   # not used: the joints are measured below (this model measures its own)
CX = 0.09
PRINT_SCALE = 1.5               # Luke, 2026-11-01: collector scale is 1.5x the game
FOOT_Z = -0.8033                # z of the sole
S = 42 / 1.30                   # kit mm per figure unit (sole to torso roof 42 mm, the bulwark frame)
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
    "torso": ((0.0, 0.12, 0.02), (0.0, 0.12, 0.36), 0.33),
    "pelvis": ((0.0, 0.10, -0.32), (0.0, 0.10, -0.12), 0.32),
}
BONES_S = {
    "pauldron": ((0.40, 0.28, 0.32), (0.52, 0.28, 0.34), 0.18),
    "arm": ((0.43, 0.22, 0.28), (0.61, 0.22, 0.0), 0.12),
    "forearm": ((0.61, 0.22, 0.0), (0.61, -0.15, -0.10), 0.15),
    "hand": ((0.61, -0.18, -0.10), (0.61, -0.50, -0.12), 0.13),
    "thigh": ((0.30, 0.12, -0.22), (0.47, -0.15, -0.45), 0.17),
    "shin": ((0.47, -0.15, -0.45), (0.53, -0.15, -0.66), 0.15),
}
PAULDRON_BOX = ((0.28, 0.80), (0.0, 0.60), (0.22, 0.50))     # |x|, y, z ranges of the shoulder plate
FOOT_TOP = -0.62                                              # below this, everything on a side is its foot
REAR_LEG = ((-0.75, 0.10), (0.48, 1.2), (-0.9, -0.05))       # x, y, z of Meshy's invented third leg (dropped)
HELM = ((0.0, 0.08, 0.50), (0.11, 0.13, 0.085))              # cupola dome: centre, radii
ROOF_Z = 0.43

PARTS = {
    "torso": ["torso"], "pelvis": ["pelvis"], "helm": ["helm"], "back": ["back"],
    "pauldron": ["pauldron_L"], "arm": ["arm_L"], "forearm": ["forearm_L"], "hand": ["hand_L"],
    "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"],
    "_pauldron_R": ["pauldron_R"], "_arm_R": ["arm_R"], "_forearm_R": ["forearm_R"], "_hand_R": ["hand_R"],
    "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"], "_foot_R": ["foot_R"], "_rear": ["rear"],
}

JOINTS = {
    "pelvis": (0.0, 0.10, -0.12), "spine": (0.0, 0.10, 0.0), "chest": (0.0, 0.10, 0.30),
    "neck": (0.0, 0.08, 0.44), "head": (0.0, 0.08, 0.49),
    "shoulder": (0.43, 0.22, 0.28), "elbow": (0.61, 0.22, 0.0), "wrist": (0.61, -0.15, -0.10),
    "hip": (0.30, 0.12, -0.22), "knee": (0.47, -0.15, -0.45), "ankle": (0.53, -0.15, -0.66),
}

# part: (kit component it publishes as, joint its origin sits on, parent part it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "thigh": ("thigh", "hip", "pelvis"),       # before the torso: the hips get first pick of the pelvis for their holes
    "torso": ("torso", "spine", "pelvis"),
    "back": ("back", "chest", "torso"),
    "helm": ("helm", "head", "back"),          # the cupola sits on the roof plates, which are part of the back
    "pauldron": ("pauldron", "shoulder", "torso"),
    "arm": ("arm", "shoulder", "pauldron"),
    "forearm": ("forearm", "elbow", "arm"),
    "hand": ("hand", "wrist", "forearm"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
}
SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot"}

# part: (game triangles, texture size)
BUDGET = {
    "torso": (11000, 1024), "pelvis": (7000, 1024), "helm": (2500, 512), "back": (12000, 1024),
    "pauldron": (7500, 1024), "arm": (2200, 512), "forearm": (5500, 1024), "hand": (3500, 768),
    "thigh": (4500, 768), "shin": (4500, 768), "foot": (3000, 512),
}
LABEL = {
    "pelvis": "Pelvis", "torso": "Torso + howitzer", "helm": "Cupola", "back": "Stacks + ammo pack",
    "pauldron": "Pauldron", "arm": "Upper arm", "forearm": "Shell arm", "hand": "Clamp + shell", "thigh": "Thigh",
    "shin": "Shin", "foot": "Foot",
}
EXPLODE, EXPLODE_DROP = 11.0, 4.0
POSE = {
    "arm_L": (-25, 0, 0), "forearm_L": (-30, 0, 0), "helm": (0, 0, -20),
    "thigh_L": (-12, 0, 0), "shin_L": (15, 0, 0), "foot_L": (-3, 0, 0),
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
    (px0, px1), (py0, py1), (pz0, pz1) = PAULDRON_BOX
    paul = (a >= px0) & (a < px1) & (y >= py0) & (y < py1) & (z >= pz0) & (z < pz1)
    setl(paul & L, "pauldron_L")
    setl(paul & ~L, "pauldron_R")
    setl((z < FOOT_TOP) & L & (a > 0.2), "foot_L")
    setl((z < FOOT_TOP) & ~L & (a > 0.2), "foot_R")
    # the howitzer, its cradle, the roof plates, the stacks and the rear pack are one part
    (hc, hr) = HELM
    helm = (((x - hc[0]) / hr[0]) ** 2 + ((y - hc[1]) / hr[1]) ** 2 + ((z - hc[2]) / hr[2]) ** 2 < 1) & (z > 0.44)
    barrel = (y < -0.20) & (a < 0.20) & (z > 0.28)
    roof = (z > ROOF_Z) & (a < 0.36)
    pack = (y > 0.42) & (z > 0.0) & (a < 0.40)
    stacks = (z > 0.55) & (y > 0.30) & (a < 0.34)
    back = barrel | roof | pack | stacks
    setl(back, "back")
    setl(helm, "helm")
    # Meshy's invented third leg
    (rx0, rx1), (ry0, ry1), (rz0, rz1) = REAR_LEG
    setl((x >= rx0) & (x < rx1) & (y >= ry0) & (y < ry1) & (z >= rz0) & (z < rz1) & ~back, "rear")
    return lab, names
