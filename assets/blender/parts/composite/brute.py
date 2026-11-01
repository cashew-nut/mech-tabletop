"""Settings for the composite Ashen Foundries Brute (MODEL=brute; numpy only).

The Meshy Brute (`Meshy_AI_ashen_foundry_mech_..._image-to-3d-texture.glb`, 6.24M triangles) is one closed surface,
like the Paladin, so split.py cuts it into closed parts the same way. What is different, and why:

* **Symmetric body, asymmetric character.** The Meshy figure strides (left foot forward) and holds its gatling up on
  the right arm. For a kit, one arm card and one leg card should fit either side, so every sided part is cut from the
  walker's left (+X) and mirrored for the right. The voxel labels are symmetric too: the right half of the torso and
  pelvis is carved where the mirrored left limbs will sit, not where Meshy's right limbs were, so the mirrored parts
  seat without gaps or overlaps. The torso, pelvis, helm and stacks keep Meshy's asymmetric detail (the "07" plate
  straddles the centre line, so mirroring a half would break it).
* **Print scale.** Luke's print scale is 1.5x the size the game shows (2026-11-01: a Titan about 75 mm, like the old
  MechWarrior figures). The game grows bulwark parts by 1.4 (ITEM_SCALE in ../meshy/brute_cut.py), so the Brute is
  cut at 1.5 x 1.4 = 2.1x the bulwark kit: about 75 mm to the helm top, 79 mm to the chimney. Pegs and magnet pockets
  are sized for that print. Game GLBs are written at kit scale (divided by GAME_SCALE), with origins on the
  foundries/bulwark joints, so they can replace the open-shell parts without moving anything.
* **Gun forearms, one socket.** The Brute has no hands: below the elbow each forearm is a gun. So each gun is a whole
  forearm and plugs into the elbow, and both use the same socket: the cannon arm is native to the left; the gatling
  arm (native to the raised right arm) is mirrored, re-seated on the cannon's socket frame, trimmed where it would
  clash with the pauldron, and given the identical peg. Either gun fits either elbow.
"""
import numpy as np

NAME = "brute"
CX = 0.12                     # centre line in Meshy x (feet sit at 0.53 and -0.30)
FOOT_Z = -0.95                # Meshy z of the sole
PRINT_SCALE = 1.5             # Luke's print scale, relative to the size the game shows
GAME_SCALE = 1.4 * PRINT_SCALE  # print (and Blender) size / kit size; the web grows bulwark parts by 1.4
S = GAME_SCALE * 35.7 / 1.8   # mm per Meshy unit (sole to helm top is the bulwark frame's 35.7 mm, times 2.1)
BASE = 3.0 * GAME_SCALE       # so that kit = print / GAME_SCALE exactly, matching frameTunes["foundries/bulwark"]
H = 0.007                     # voxel size in Meshy units (0.29 mm at print scale)

# Bones in Meshy units, x relative to CX, for the walker's left; the right side is the mirror image. Measured from
# ortho views and occupancy sections of the Meshy figure (../meshy/brute_cut.py's arm bones sat 0.14 too far back).
BONES_C = {
    "helm": ((-0.02, 0.15, 0.66), (-0.02, 0.15, 0.78), 0.14),
    "torso": ((0.0, 0.08, 0.18), (0.0, 0.08, 0.42), 0.22),
    "pelvis": ((0.0, 0.10, -0.10), (0.0, 0.10, 0.06), 0.24),
}
BONES_S = {
    "pauldron": ((0.30, -0.08, 0.38), (0.40, -0.08, 0.42), 0.15),
    "arm": ((0.28, -0.07, 0.32), (0.35, -0.05, 0.18), 0.08),
    "rockets": ((0.38, -0.03, 0.13), (0.47, -0.30, -0.18), 0.13),
    "thigh": ((0.22, 0.08, -0.05), (0.36, 0.05, -0.38), 0.15),
    "shin": ((0.36, 0.05, -0.40), (0.42, -0.10, -0.78), 0.15),
}
TORSO_HALF = 0.20             # the furnace box: |x| below this, between the pelvis and the collar, is torso
PAULDRON_BOX = ((0.20, 0.55), (-0.25, 0.08), (0.27, 0.53))    # x (|x|), y, z ranges of the shoulder plate
FOOT_TOP = -0.80              # below this, everything on a side is its foot
# Meshy's gatling arm (right, raised and pointing forward), from the elbow to the muzzle. Below the elbow, voxels inside
# this capsule become the gatling.
GATLING = ((-0.55, 0.02, 0.14), (-0.86, -0.20, -0.38), 0.19)
GATLING_TOP = 0.16

# Physical parts and the labels each is made of. Names starting with "_" carve the torso and pelvis, then are dropped.
# The Brute's forearms are its guns, so a gun is the whole forearm and plugs into the elbow (no separate hand). Its
# upper arm is a 3 mm stub hidden under the pauldron, too small to print or handle, so it is part of the pauldron:
# the pauldron is the shoulder unit, and the elbow socket is on its underside.
PARTS = {
    "torso": ["torso"], "pelvis": ["pelvis"], "helm": ["helm"], "back": ["back"],
    "pauldron": ["pauldron_L", "arm_L"], "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"],
    "rockets": ["rockets_L"], "gatling": ["gatling"],
    "_pauldron_R": ["pauldron_R", "arm_R"], "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"],
    "_foot_R": ["foot_R"], "_rockets_R": ["rockets_R"],
}

# Kit joints (Meshy units, x relative to CX, left side).
JOINTS = {
    "pelvis": (0.0, 0.10, -0.02), "spine": (0.0, 0.10, 0.14), "chest": (0.0, 0.10, 0.30),
    "neck": (0.0, 0.12, 0.55), "head": (0.0, 0.15, 0.66),
    "shoulder": (0.30, -0.07, 0.31), "elbow": (0.355, -0.05, 0.17), "wrist": (0.44, -0.20, -0.05),
    "hip": (0.22, 0.08, -0.08), "knee": (0.32, 0.05, -0.40), "ankle": (0.42, -0.10, -0.80),
}

# part: (kit component it publishes as, joint its origin sits on, parent part it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "torso": ("torso", "spine", "pelvis"),
    "helm": ("helm", "head", "torso"),
    "back": ("back", "chest", "torso"),
    "pauldron": ("pauldron", "shoulder", "torso"),
    "thigh": ("thigh", "hip", "pelvis"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
    "rockets": ("forearm", "elbow", "pauldron"),    # weapon forearm: item_rocket-pod@brute
    "gatling": ("forearm", "elbow", "pauldron"),    # weapon forearm: item_autocannon@brute, re-seated on the same socket
}
SIDED = {"pauldron", "thigh", "shin", "foot", "rockets", "gatling"}
RESEAT = {"gatling": "rockets"}            # part: the part whose socket (frame and peg) it takes over
LOADOUT = {"rockets": "L", "gatling": "R"} # default arms, as Meshy had them; the other copies are hidden spares

# Cut at 1.5x print scale with thick joints: bigger pegs, stock 5 x 2 or 3 x 2 mm magnets, and pegs tried both ways.
MAGNETS = ((2.5, 2.0), (1.5, 2.0), (1.0, 1.0))
RADII = (4.0, 3.5, 3.0, 2.6, 2.3, 2.0, 1.75, 1.5, 1.3, 1.15, 1.0, 0.85, 0.75, 0.65, 0.55)
LENGTHS = (5.0, 4.5, 4.0, 3.5, 3.0, 2.6, 2.2, 1.8, 1.5, 1.2, 1.0)
CRUMB = 1.0                   # mm3: loose bits smaller than this are dropped after the pegs are cut
BOTH_WAYS = True
CLEAR_MIRRORED = True
CHIP_SCALE = 1.0              # split.py's sliver sizes stay as they were (not scaled with the print volume)
RAY = 1.8                     # bake ray reach, relative to the Paladin's
EXPLODE, EXPLODE_DROP = 14.0, 0.0     # render.py: exploded view reach (print mm), centred on the chest
POSE_MARGIN = 0.9
# The Meshy Brute's own stance, rebuilt from symmetric parts: gatling raised to fire, left leg striding (degrees).
POSE = {
    "gatling_R": (-55, 0, 0), "rockets_L": (-10, 0, 0), "helm": (0, 0, 15),
    "thigh_L": (-14, 0, 0), "shin_L": (10, 0, 0), "foot_L": (4, 0, 0),
    "thigh_R": (12, 0, 0), "shin_R": (6, 0, 0), "foot_R": (-18, 0, 0),
}

# part: (game triangles, texture size)
BUDGET = {
    "torso": (14000, 1024), "pelvis": (6000, 1024), "helm": (4000, 1024), "back": (8000, 1024),
    "pauldron": (6000, 1024), "thigh": (4000, 768), "shin": (5000, 768), "foot": (4500, 768),
    "rockets": (8000, 1024), "gatling": (9000, 1024),
}
LABEL = {
    "pelvis": "Pelvis", "torso": "Furnace torso", "helm": "Helm", "back": "Stacks + rear pack",
    "pauldron": "Pauldron + shoulder", "thigh": "Thigh", "shin": "Shin", "foot": "Foot",
    "rockets": "Cannon arm (weapon)", "gatling": "Gatling arm (weapon)",
}


def seg_d(P, A, B):
    A, B = np.array(A, np.float32), np.array(B, np.float32)
    AB = B - A
    t = np.clip(((P - A) @ AB) / (AB @ AB), 0, 1)
    return np.linalg.norm(P - (A + t[:, None] * AB), axis=1)


def to_mm(P):
    P = np.asarray(P, np.float64)
    return np.stack([P[..., 0] * S, P[..., 1] * S, (P[..., 2] - FOOT_Z) * S + BASE], -1)


def from_mm(P):
    P = np.asarray(P, np.float64)
    return np.stack([P[..., 0] / S, P[..., 1] / S, (P[..., 2] - BASE) / S + FOOT_Z], -1)


def label_points(P, _cloth=None):
    """Label points P (Meshy units, x relative to CX). Sided bones are tested on |x|, so labels are mirror images."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    a = np.abs(x)
    Pm = np.stack([a, y, z], 1)
    cn, sn = list(BONES_C), list(BONES_S)
    names = cn + [k + "_L" for k in sn] + [k + "_R" for k in sn]
    D = [seg_d(P, *BONES_C[k][:2]) - BONES_C[k][2] for k in cn]
    D += [seg_d(Pm, *BONES_S[k][:2]) - BONES_S[k][2] for k in sn]
    D = np.stack(D, 1)
    best = D.min(1)
    lab = D.argmin(1).astype(np.int16)
    right = (lab >= len(cn)) & (x < 0)
    lab[right] += len(sn)

    def setl(mask, name):
        if name not in names:
            names.append(name)
        lab[mask] = names.index(name)

    L = x >= 0
    (px0, px1), (py0, py1), (pz0, pz1) = PAULDRON_BOX
    setl((a < TORSO_HALF) & (z > 0.06) & (z < 0.55), "torso")
    paul = (a >= px0) & (a < px1) & (y >= py0) & (y < py1) & (z >= pz0) & (z < pz1)
    setl(paul & L, "pauldron_L")
    setl(paul & ~L, "pauldron_R")
    setl((z < FOOT_TOP) & L, "foot_L")
    setl((z < FOOT_TOP) & ~L, "foot_R")
    # chimney stacks, antennae and the rear pack
    head = ((x + 0.02) ** 2 / 0.15 ** 2 + (y - 0.15) ** 2 / 0.17 ** 2 + (z - 0.72) ** 2 / 0.20 ** 2) < 1
    back = ((z > 0.60) & ~head) | ((y > 0.30) & (z > 0.10) & (a < 0.30)) | ((y > py1) & (z > 0.50) & (a < 0.45))
    back |= (x > 0.20) & (x < 0.40) & (y > py1) & (z > 0.40)      # the big chimney behind the left shoulder
    setl(back, "back")
    setl(head & (z > 0.55), "helm")
    # Meshy's gatling arm, below its elbow
    dg = seg_d(P, *GATLING[:2]) - GATLING[2]
    setl((x < -0.30) & (dg < 0.0) & (z < GATLING_TOP), "gatling")
    return lab, names
