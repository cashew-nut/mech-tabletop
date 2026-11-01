"""Shared names and joint positions for the composite models (no Blender needed).

The model comes from the MODEL environment variable: `paladin` (default, paladin.py), `brute` (brute.py) or `seer`
(seer.py). Each model module holds its labelling rules, joint tree, budgets and render labels; the pipeline scripts are
shared.

Units: solids, pegs, magnet pockets and the .blend are in print mm. PS is print mm per kit mm (1 for the Paladin,
PRINT_SCALE for the Seer, GAME_SCALE for the Brute, whose kit is the bulwark frame grown 1.4x by the web); build.py
scales the game GLBs back down to kit mm.
"""
import importlib
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = Path(__file__).resolve().parents[4]
KIT = json.loads((REPO / "data" / "model-kit.json").read_text())

MODEL = os.environ.get("MODEL", "paladin")
M = importlib.import_module(MODEL)
NAME = getattr(M, "NAME", MODEL)
PS = getattr(M, "GAME_SCALE", getattr(M, "PRINT_SCALE", 1.0))
TREE, SIDED, LABEL = M.TREE, M.SIDED, M.LABEL
RESEAT = getattr(M, "RESEAT", {})      # part: the part whose socket it takes over (the Brute's gatling)
LOADOUT = getattr(M, "LOADOUT", {})    # part: the side it is fitted on by default (the other copy is a hidden spare)

if hasattr(M, "to_mm"):       # the model's own S and BASE are already print mm (the Brute)
    to_mm, from_mm, MM = M.to_mm, M.from_mm, M.S
else:
    MM = M.S * PS             # print mm per Meshy unit

    def to_mm(P):
        """Meshy units (x already centred on the model's CX) to print mm."""
        P = np.asarray(P, np.float64)
        return np.stack([P[..., 0] * MM, P[..., 1] * MM, ((P[..., 2] - M.FOOT_Z) * M.S + M.BASE) * PS], -1)

    def from_mm(P):
        P = np.asarray(P, np.float64)
        return np.stack([P[..., 0] / MM, P[..., 1] / MM, (P[..., 2] / PS - M.BASE) / M.S + M.FOOT_Z], -1)

if hasattr(M, "JOINTS"):      # the model measures its own joints (centred Meshy units)
    TUNE = {k: [float(v) / PS for v in to_mm(np.array(p, float))] for k, p in M.JOINTS.items()}
else:                         # kit mm, left side, measured from the Meshy figure
    TUNE = KIT["frameTunes"][M.TUNE]["joints"]
JOINT_OF = {k: v[1] for k, v in TREE.items()}


def joint(name, side="L", scale=None):
    """A joint's position, print mm by default (scale=1 gives kit mm)."""
    s = PS if scale is None else scale
    p = [v * s for v in TUNE[name]]
    if side == "R":
        p[0] = -p[0]
    return p


def load_npz(path):
    d = np.load(path)
    return d["P"], d["T"]
