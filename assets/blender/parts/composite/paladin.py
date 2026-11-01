"""The Covenant Paladin's settings for the composite pipeline (MODEL=paladin, the default). See README.md.

Everything here is specific to Luke's Meshy Paladin: how the space round the figure is labelled into parts (split.py),
the joint tree (joints.py, build.py), the game budget (build.py), and the labels and pose for the review renders.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "meshy"))
import cut  # noqa: E402  (joint and bone positions, Meshy units)

NAME = "paladin"
TUNE = "covenant/titan"          # data/model-kit.json frameTunes entry the joints come from (mm, game scale)
CX = cut.CX                      # the figure's centre line (Meshy x)
PRINT_SCALE = 1.5                # Luke, 2026-11-01: collector scale is 1.5x the game (pegs and magnets are cut at it)

S, FOOT_Z, BASE = 50 / 1.5, -0.90, 3.0      # mm per Meshy unit, foot level, base thickness (as ../meshy/build.py)
H = 0.25 / (S * PRINT_SCALE)                 # voxel size in Meshy units (0.25 mm at print scale)
CLOTH_T = 0.02                               # cloth is a thin sheet: only voxels this close to a cloth triangle are cloth

# Joints at print scale (as seer.py): 3 x 2 mm magnets where there is room, then 2 x 1, then 1 x 1. The Paladin's torso,
# helm and pauldron faces are broad enough for a 6 mm peg, so the radii start at 3 mm.
MAGNETS = ((1.5, 2.0), (1.0, 1.0), (0.5, 1.0))
RADII = (3.0, 2.75, 2.5, 2.2, 2.0, 1.75, 1.5, 1.3, 1.15, 1.0, 0.85, 0.75, 0.65, 0.55)
LENGTHS = (3.5, 3.0, 2.6, 2.2, 1.8, 1.5, 1.2, 1.0)
PREFER_MAGNET = True        # a slightly thinner peg with a magnet beats a fatter one without
STRICT = True               # joints.py: check holes against the real solids (no collisions, no break-outs)
CLEAR_MIRRORED = True       # trim the pelvis and torso where the mirrored right thigh and pauldron would sink in
CRUMB = 4.0                 # mm3: drops the scrap of pelvis armour that trim cuts loose (3.1 mm3)

# Physical parts and the cut labels each is made of. Sided parts are built for the walker's left (+X) only and mirrored
# for the right, so the right side's labels exist only to carve the torso and pelvis.
PARTS = {
    "torso": ["torso", "collar", "cloth_upper"],
    "pelvis": ["pelvis", "cloth_lower"],
    "helm": ["helm"],
    "back": ["back"],
    "pauldron": ["pauldron_L", "cloth_L"],
    "arm": ["arm_L"], "forearm": ["forearm_L"], "hand": ["hand_L"],
    "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"],
    "blade": ["sword_L"], "pod": ["pod_L"],
    # right side, used only to know where the torso and pelvis end
    "_pauldron_R": ["pauldron_R", "cloth_R"], "_arm_R": ["arm_R"], "_forearm_R": ["forearm_R"], "_hand_R": ["hand_R"],
    "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"], "_foot_R": ["foot_R"], "_blade_R": ["sword_R"], "_pod_R": ["pod_R"],
}


def label_points(P, cloth_near):
    """cut.label's rules applied to arbitrary points P (Meshy units, x centred). cloth_near: bool per point."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    a = np.abs(x)
    names, D = [], []
    mir = lambda p: (-p[0], p[1], p[2])
    for k, (p, q, r) in cut.BONES_C.items():
        names.append(k)
        D.append(cut.seg_d(P, p, q) - r)
    for k, (p, q, r) in cut.BONES_S.items():
        names.append(k + "_L")
        D.append(cut.seg_d(P, p, q) - r)
        # the figure's own right side (its right arm hangs closer in), so the torso is cut where that arm really is
        p2, q2, r2 = cut.BONES_R.get(k, (mir(p), mir(q), r))
        names.append(k + "_R")
        D.append(cut.seg_d(P, p2, q2) - r2)
    lab = np.stack(D, 1).argmin(1).astype(np.int16)
    del D

    def setl(mask, name):
        if name not in names:
            names.append(name)
        lab[mask] = names.index(name)

    L = x >= 0
    for s, sg in (("L", L), ("R", ~L)):
        setl(sg & (z < -0.805) & (a < 0.5), f"foot_{s}")

    def sword(s, A, B, w):
        sg = L if s == "L" else ~L
        Q = np.stack([x, z], 1).astype(np.float32)
        A, B = np.array(A, np.float32), np.array(B, np.float32)
        AB = B - A
        t = np.clip(((Q - A) @ AB) / (AB @ AB), 0, 1)
        dd = np.linalg.norm(Q - (A + t[:, None] * AB), axis=1)
        setl(sg & (dd < w) & (z < -0.33) & (np.abs(y + 0.31) < 0.16) & (a > 0.38), f"sword_{s}")
    sword("L", (0.61, -0.35), (0.92, -0.95), 0.055)
    sword("R", (-0.45, -0.36), (-0.94, -0.95), 0.055)
    spire = (z > 0.56) & (x > -0.015) & (x < 0.07) & (y > -0.12)
    pod = (z > 0.56) & (a < 0.33) & (y > -0.12) & ~spire
    setl(pod & L, "pod_L")
    setl(pod & ~L, "pod_R")
    setl(spire, "back")
    setl((y > 0.12) & (z > 0.2) & (z <= 0.56) & (a < 0.32), "back")
    helm = (x ** 2 / 0.10 ** 2 + (y + 0.10) ** 2 / 0.13 ** 2 + (z - 0.52) ** 2 / 0.11 ** 2 < 1) & (z > 0.44)
    setl(helm & (lab != names.index("back")), "helm")
    setl((z > 0.455) & (a < 0.17) & (y < 0.06) & (z < 0.57) & ~helm
         & np.isin(lab, [names.index("torso"), names.index("helm")]), "collar")
    # Cloth: capes on the arms go with the pauldrons, the tabard with the pelvis, the banner on the back with the torso.
    cl = cloth_near & (lab != names.index("back")) & (z < 0.46)
    setl(cl & (a >= 0.30) & L, "cloth_L")
    setl(cl & (a >= 0.30) & ~L, "cloth_R")
    setl(cl & (a < 0.30) & (z < 0.05), "cloth_lower")
    setl(cl & (a < 0.30) & (z >= 0.05), "cloth_upper")
    # Elbow: Meshy sculpted a thin lip over a 0.5 mm slot at the top of the left forearm. Cut at the bone rule, the
    # forearm's face is that lip, with air behind it, so no peg fits (1.5 mm across at best). Hand the lip, the slot
    # and the top 2 mm of the forearm (print scale) to the arm so the seam is a flat face through solid metal.
    d = P - ELBOW_C
    s = d @ ELBOW_AX
    rad = np.linalg.norm(d - s[:, None] * ELBOW_AX, axis=1)
    setl((lab == names.index("forearm_L")) & (s < ELBOW_SEAM) & (rad < ELBOW_RAD), "arm_L")
    return lab, names


# the elbow peg's line (centred Meshy units, axis pointing down the forearm), the new seam and the column it applies to
ELBOW_C = np.array([0.4172, -0.0976, 0.1035])
ELBOW_AX = np.array([0.3962, -0.1408, -0.9073])
ELBOW_SEAM, ELBOW_RAD = 0.040, 0.066        # 2.0 mm and 3.3 mm at print scale


def cloth_tris(work, V, F, UV):
    """Triangles that are cloth (the red tabard, capes and banner): cut.py's labels."""
    tlab = np.load(Path(work) / "lab.npy")
    tnames = json.loads((Path(work) / "names.json").read_text())
    return tlab == tnames.index("cloth")


# part: (kit component it publishes as, joint its origin sits on, parent part it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "thigh": ("thigh", "hip", "pelvis"),       # before the torso: the hips get first pick of the pelvis for their holes
    "torso": ("torso", "spine", "pelvis"),
    "helm": ("helm", "head", "torso"),
    "back": ("back", "chest", "torso"),
    "pauldron": ("pauldron", "shoulder", "torso"),
    "arm": ("arm", "shoulder", "pauldron"),   # the Meshy shoulder joint sits inside the pauldron, so the arm plugs into it
    "forearm": ("forearm", "elbow", "arm"),
    "hand": ("hand", "wrist", "forearm"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
    "blade": (None, "wrist", "hand"),      # equipment: item_lance@paladin
    "pod": (None, "chest", ("torso", "back")),   # equipment: item_carapace-gun@paladin (tries each parent in turn)
}
SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot", "blade", "pod"}

# part: (game triangles, texture size). Close to ../meshy/build.py's budget (cloth and collar now live in pelvis,
# torso and pauldron).
BUDGET = {
    "torso": (11000, 1024), "pelvis": (7000, 1024), "helm": (3500, 1024), "back": (5500, 768),
    "pauldron": (7500, 1024), "arm": (1800, 512), "forearm": (2800, 768), "hand": (2500, 512),
    "thigh": (3500, 768), "shin": (4200, 768), "foot": (2500, 512), "blade": (3000, 1024), "pod": (4000, 768),
}
LABEL = {
    "pelvis": "Pelvis + tabard", "torso": "Torso + collar + back banner", "helm": "Helm", "back": "Reliquary spire",
    "pauldron": "Pauldron + cape", "arm": "Upper arm", "forearm": "Forearm", "hand": "Gauntlet", "thigh": "Thigh",
    "shin": "Greave", "foot": "Sabaton", "blade": "Siege blade (equipment)", "pod": "Shoulder pod (equipment)",
}
# render.py's posed shot: object name -> (x, y, z) rotation in degrees about the part's own joint
POSE = {
    "arm_L": (-30, 0, 0), "forearm_L": (-45, 0, 0), "arm_R": (20, 0, 0), "helm": (0, 0, -25),
    "thigh_L": (-20, 0, 0), "shin_L": (25, 0, 0), "foot_L": (-5, 0, 0),
}
