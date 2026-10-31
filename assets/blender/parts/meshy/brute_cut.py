"""Cut the Meshy Ashen Foundries Brute into kit parts (numpy, scipy, pillow; no Blender).

    python3 -I cut.py extract TEXTURED.glb WORKDIR           # shared with the Paladin
    python3 -I brute_cut.py label WORKDIR [--preview] [--step N]

Same axes as cut.py: Z up, facing -Y, left is +X. The Meshy figure strides (its feet sit at x=-0.30 and +0.53),
so bones are given in absolute Meshy units and CX is the centre line used for the kit skeleton.
The two forearm guns (gatling on the right arm, barrel cluster on the left) are equipment.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cut import seg_d  # noqa: E402

CX = 0.12
BONES = {  # name: (A, B, radius), absolute Meshy units
    "helm": ((0.10, 0.15, 0.66), (0.10, 0.15, 0.78), 0.14),
    "collar": ((0.10, 0.12, 0.55), (0.10, 0.12, 0.58), 0.12),
    "torso": ((0.12, 0.10, 0.18), (0.12, 0.10, 0.42), 0.30),
    "pelvis": ((0.12, 0.10, -0.10), (0.12, 0.10, 0.06), 0.24),
    "pauldron_L": ((0.50, 0.10, 0.38), (0.52, 0.10, 0.42), 0.17),
    "pauldron_R": ((-0.40, 0.00, 0.36), (-0.38, 0.00, 0.40), 0.20),
    "arm_L": ((0.46, 0.12, 0.34), (0.52, 0.10, 0.14), 0.13),
    "arm_R": ((-0.28, 0.10, 0.30), (-0.30, 0.00, 0.15), 0.10),
    "forearm_L": ((0.52, 0.10, 0.12), (0.57, 0.02, -0.03), 0.13),
    "forearm_R": ((-0.30, 0.00, 0.15), (-0.38, -0.08, 0.02), 0.14),
    "hand_L": ((0.57, 0.02, -0.03), (0.62, -0.05, -0.10), 0.13),   # the breech block behind the barrels
    "hand_R": ((-0.38, -0.08, 0.02), (-0.46, -0.12, -0.02), 0.15),
    "gun_L": ((0.62, -0.05, -0.10), (0.72, -0.25, -0.32), 0.12),
    "gun_R": ((-0.46, -0.12, -0.02), (-0.76, -0.45, -0.42), 0.14),
    "thigh_L": ((0.34, 0.08, -0.05), (0.48, 0.05, -0.38), 0.15),
    "thigh_R": ((-0.10, 0.08, -0.08), (-0.17, 0.05, -0.42), 0.15),
    "shin_L": ((0.48, 0.05, -0.40), (0.54, 0.0, -0.78), 0.15),
    "shin_R": ((-0.17, 0.05, -0.44), (-0.30, 0.0, -0.78), 0.15),
}
FOOT_Z = -0.80   # feet are cut off the shins here

# Build settings (build.py reads these with MODEL=brute). Positions are Meshy units, x centred on CX.
FACTION, CLS, FRAME = "foundries", "brute", "bulwark"
S = 35.7 / 1.8                      # mm per Meshy unit: foot (-0.95) to helm top (0.85) is the bulwark frame's 35.7 mm
BUILD_FOOT_Z = -0.95
ITEM_SCALE = 1.4                    # bulwark parts are grown by 1.4 in the web
MIRRORED = set()                    # the two legs differ, so every sided part is built for both sides
NATIVE_RIGHT = {"autocannon@brute"} # the gatling is the right arm's; the web flips it for the left
JOINTS = {
    "pelvis": (0.0, 0.10, -0.02), "spine": (0.0, 0.10, 0.14), "chest": (0.0, 0.10, 0.30),
    "neck": (0.0, 0.12, 0.55), "head": (0.0, 0.15, 0.66),
    "shoulder": (0.45, 0.10, 0.36), "elbow": (0.40, 0.08, 0.14), "wrist": (0.50, -0.04, -0.05),
    "hip": (0.22, 0.08, -0.08), "knee": (0.32, 0.05, -0.40), "ankle": (0.42, 0.0, -0.80),
}
MOUNT_ARM = (0.50, -0.05, -0.10)    # left gun origin; the right mount is its mirror
_T = (768, 384, 128)
PARTS = {
    "helm": ("head", 3500, (1024, 384, 128)), "torso": ("spine", 8000, (1024, 384, 128)),
    "pelvis": ("pelvis", 3500, (768, 384, 128)), "back": ("chest", 4500, (768, 384, 128)),
    "pauldron": ("shoulder", 4500, (1024, 384, 128)), "arm": ("shoulder", 1800, (512, 256, 128)),
    "forearm": ("elbow", 2800, _T), "hand": ("wrist", 1800, (512, 256, 128)),
    "thigh": ("hip", 3200, _T), "shin": ("knee", 3800, _T), "foot": ("ankle", 2200, (512, 256, 128)),
}
ITEMS = {
    "rocket-pod": ("gun_L", "item_rocket-pod@brute", MOUNT_ARM, 5000, (1024, 384, 128)),
    "autocannon": ("gun_R", "item_autocannon@brute", (-MOUNT_ARM[0], MOUNT_ARM[1], MOUNT_ARM[2]), 8000, (1024, 512, 256)),
}


def label(work, preview=False, step=1):
    work = Path(work)
    d = np.load(work / "mesh.npz")
    V, F = d["V"], d["F"][::step]
    C = V[F].mean(1)
    names = list(BONES) + ["foot_L", "foot_R", "back"]
    D = np.stack([seg_d(C, p, q) - r for p, q, r in BONES.values()], 1)
    lab = D.argmin(1)
    x, y, z = C[:, 0] - CX, C[:, 1], C[:, 2]

    def setl(m, n):
        lab[m] = names.index(n)
    foot = z < FOOT_Z
    setl(foot & (C[:, 0] > CX), "foot_L")
    setl(foot & (C[:, 0] <= CX), "foot_R")
    # chimney stacks and the rear pack
    head = ((x + CX - 0.10) ** 2 / 0.15 ** 2 + (y - 0.15) ** 2 / 0.17 ** 2 + (z - 0.72) ** 2 / 0.20 ** 2) < 1
    back = ((z > 0.62) & ~head) | ((y > 0.30) & (z > 0.10) & (np.abs(x) < 0.42))
    gun = np.isin(lab, [names.index("gun_L"), names.index("gun_R")])
    setl(back & ~gun & (z > -0.0), "back")
    setl(head & (z > 0.55), "helm")
    np.save(work / "lab.npy", lab.astype(np.int8))
    (work / "names.json").write_text(json.dumps(names))
    print({k: int((lab == i).sum()) for i, k in enumerate(names)})
    if preview:
        import preview as pv
        FN = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        FN /= np.linalg.norm(FN, axis=1, keepdims=True) + 1e-12
        pv.parts_views(C - np.array([CX, 0, 0], np.float32), FN, lab, names, work / "cut")


if __name__ == "__main__":
    a = sys.argv
    label(a[2], "--preview" in a, int(a[a.index("--step") + 1]) if "--step" in a else 1)
