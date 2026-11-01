"""Shared names and joint positions for the composite walkers (no Blender needed).

MODEL=paladin (default) or MODEL=brute picks the walker; brute.py holds the Brute's settings.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
KIT = json.loads((REPO / "data" / "model-kit.json").read_text())
TUNE = KIT["frameTunes"]["covenant/titan"]["joints"]     # mm, left side, measured from the Meshy Paladin

# part: (kit component it publishes as, joint its origin sits on, parent part it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "torso": ("torso", "spine", "pelvis"),
    "helm": ("helm", "head", "torso"),
    "back": ("back", "chest", "torso"),
    "pauldron": ("pauldron", "shoulder", "torso"),
    "arm": ("arm", "shoulder", "pauldron"),   # the Meshy shoulder joint sits inside the pauldron, so the arm plugs into it
    "forearm": ("forearm", "elbow", "arm"),
    "hand": ("hand", "wrist", "forearm"),
    "thigh": ("thigh", "hip", "pelvis"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
    "blade": (None, "wrist", "hand"),      # equipment: item_lance@paladin
    "pod": (None, "chest", ("torso", "back")),   # equipment: item_carapace-gun@paladin (tries each parent in turn)
}
SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot", "blade", "pod"}
RESEAT = {}
LABEL = None
NAME = "paladin"
M = None
if os.environ.get("MODEL", "paladin") == "brute":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import brute as M  # noqa: E402
    NAME, TREE, SIDED, RESEAT, LABEL = "brute", M.TREE, M.SIDED, M.RESEAT, M.LABEL
    TUNE = {k: [round(float(v), 3) for v in M.to_mm(p)] for k, p in M.JOINTS.items()}
JOINT_OF = {k: v[1] for k, v in TREE.items()}


def joint(name, side="L"):
    p = list(TUNE[name])
    if side == "R":
        p[0] = -p[0]
    return p


def load_npz(path):
    d = np.load(path)
    return d["P"], d["T"]
