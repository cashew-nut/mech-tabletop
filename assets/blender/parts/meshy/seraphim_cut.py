"""Cut the Meshy Gilded Seraphim (Reliquary Seer, Striker frame) into kit parts (numpy, scipy, pillow; no Blender).

    python3 -I cut.py extract TEXTURED.glb WORKDIR           # shared with the Paladin and Brute
    python3 -I seraphim_cut.py label WORKDIR [--preview] [--step N]

Same axes as cut.py: Z up, facing -Y, left is +X. The figure is a little off centre (CX) and its stance is not
symmetric, so bones are absolute Meshy units and every sided part is built for both sides.
The spear (right hand) is equipment. The halo and its crown spire are the `crown` part (on the head joint), the spires
on the back are `back`. The red banner hanging from the left shoulder is torso down to the waist, then pelvis.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cut import seg_d  # noqa: E402

CX = 0.28
BONES = {  # name: (A, B, radius), absolute Meshy units
    "helm": ((0.27, 0.17, 0.55), (0.27, 0.17, 0.66), 0.11),
    "torso": ((0.27, 0.12, 0.15), (0.27, 0.12, 0.42), 0.21),
    "pelvis": ((0.28, 0.08, -0.10), (0.28, 0.08, 0.05), 0.18),
    "pauldron_L": ((0.58, 0.12, 0.48), (0.66, 0.12, 0.40), 0.16),
    "pauldron_R": ((-0.03, 0.12, 0.48), (-0.30, 0.10, 0.33), 0.15),
    "arm_L": ((0.62, 0.12, 0.38), (0.72, 0.08, 0.02), 0.07),
    "forearm_L": ((0.72, 0.08, 0.0), (0.77, 0.08, -0.40), 0.09),
    "hand_L": ((0.77, 0.08, -0.40), (0.80, 0.08, -0.74), 0.08),
    "arm_R": ((-0.02, 0.12, 0.38), (-0.06, -0.02, 0.20), 0.07),
    "forearm_R": ((-0.06, -0.02, 0.20), (-0.10, -0.25, 0.0), 0.08),
    "hand_R": ((-0.10, -0.28, -0.02), (-0.12, -0.30, -0.07), 0.09),
    "thigh_L": ((0.52, 0.07, -0.03), (0.50, 0.05, -0.40), 0.12),
    "shin_L": ((0.50, 0.05, -0.42), (0.53, 0.02, -0.78), 0.12),
    "thigh_R": ((0.05, 0.06, -0.03), (-0.10, 0.04, -0.40), 0.12),
    "shin_R": ((-0.10, 0.04, -0.42), (-0.15, 0.02, -0.78), 0.12),
}
FOOT_Z = -0.79
SPEAR = ((-0.78, -0.60, -0.95), (-0.22, -0.14, -0.02), 0.085)

# Build settings (build.py reads these with MODEL=seraphim). Positions are Meshy units, x centred on CX.
FACTION, CLS, FRAME = "reliquary", "seer", "striker"
S = 36 / 1.75                       # mm per Meshy unit: foot (-0.95) to helm top (0.72) is about the striker frame's 36 mm
BUILD_FOOT_Z = -0.95
ITEM_SCALE = 1.2                    # striker parts are grown by 1.2 in the web
MIRRORED = set()
NATIVE_RIGHT = {"arc-cannon@seer"}  # the spear is the right hand's; the web flips it for the left
JOINTS = {
    "pelvis": (0.0, 0.08, -0.04), "spine": (0.0, 0.10, 0.12), "chest": (0.0, 0.12, 0.30),
    "neck": (0.0, 0.14, 0.48), "head": (0.0, 0.17, 0.58),
    "shoulder": (0.30, 0.12, 0.46), "elbow": (0.44, 0.08, 0.02), "wrist": (0.49, 0.08, -0.40),
    "hip": (0.24, 0.07, -0.03), "knee": (0.22, 0.05, -0.42), "ankle": (0.25, 0.02, -0.80),
}
MOUNT_ARM = (0.38, -0.28, -0.04)    # spear grip (left mirror of the right fist)
_T = (768, 384, 128)
PARTS = {
    "helm": ("head", 3500, (1024, 384, 128)), "crown": ("head", 3000, (512, 256, 128)),
    "torso": ("spine", 8000, (1024, 384, 128)), "pelvis": ("pelvis", 6000, (1024, 384, 128)),
    "back": ("chest", 3500, (512, 256, 128)), "pauldron": ("shoulder", 4500, (1024, 384, 128)),
    "arm": ("shoulder", 1800, (512, 256, 128)), "forearm": ("elbow", 2800, _T), "hand": ("wrist", 1500, (512, 256, 128)),
    "thigh": ("hip", 3200, _T), "shin": ("knee", 3800, _T), "foot": ("ankle", 2200, (512, 256, 128)),
}
ITEMS = {  # id: (label, file, mount (centred, native right), triangles, sizes)
    "arc-cannon": ("spear", "item_arc-cannon@seer", (-MOUNT_ARM[0], MOUNT_ARM[1], MOUNT_ARM[2]), 9000, (1024, 384, 128)),
}


def label(work, preview=False, step=1):
    from PIL import Image
    from scipy.spatial import cKDTree
    work = Path(work)
    d = np.load(work / "mesh.npz")
    V, F, UV = d["V"], d["F"][::step], d["UV"]
    C = V[F].mean(1)
    uv = UV[F].mean(1)
    names = list(BONES) + ["foot_L", "foot_R", "crown", "back", "spear"]
    D = np.stack([seg_d(C, p, q) - r for p, q, r in BONES.values()], 1)
    lab = D.argmin(1)
    x, y, z = C[:, 0], C[:, 1], C[:, 2]

    def setl(m, n):
        lab[m] = names.index(n)
    foot = z < FOOT_Z
    setl(foot & (x > CX), "foot_L")
    setl(foot & (x <= CX), "foot_R")
    head = ((x - 0.27) ** 2 / 0.11 ** 2 + (y - 0.17) ** 2 / 0.15 ** 2 + (z - 0.60) ** 2 / 0.14 ** 2) < 1
    crown = ((x - 0.27) ** 2 + (z - 0.77) ** 2 < 0.25 ** 2) & (y > -0.05) & (y < 0.22) & (z > 0.58) & ~head
    back = (z > 0.55) & (y >= 0.22) & ~head
    setl(head & (z < 0.72), "helm")
    setl(crown, "crown")
    setl(back & ~crown, "back")
    # the banner: red hanging below the waist, and the dark cloth between the legs, belong to the pelvis
    tex = np.asarray(Image.open(work / "tex_0.jpg").convert("RGB"))
    n = tex.shape[0]
    c = tex[np.clip((uv[:, 1] * (n - 1)).astype(int), 0, n - 1), np.clip((uv[:, 0] * (n - 1)).astype(int), 0, n - 1)].astype(int)
    red = ((c[:, 0] > 90) & (c[:, 0] > 2 * c[:, 1]) & (c[:, 0] > 2 * c[:, 2])).astype(np.float32)
    _, nn = cKDTree(C).query(C, k=24)
    redsm = red[nn].mean(1)
    cloth = ((redsm > 0.30) & (z < 0.0) & (z > -0.93) & (np.abs(x - CX) < 0.40)) | ((x > 0.08) & (x < 0.40) & (z > -0.7) & (z < 0.0))
    setl(cloth & (lab != names.index("spear")), "pelvis")
    # the spear (below the fist)
    sp = (seg_d(C, SPEAR[0], SPEAR[1]) < SPEAR[2]) & (z < -0.02) & (x < -0.15)
    setl(sp, "spear")
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
