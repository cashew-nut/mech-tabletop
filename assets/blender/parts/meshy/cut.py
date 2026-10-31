"""Cut the Meshy Paladin into kit parts (step 1 of 2; needs numpy, scipy, pillow, no Blender).

    python3 -I cut.py extract TEXTURED.glb WORKDIR        # mesh.npz + textures into WORKDIR
    python3 -I cut.py label   WORKDIR [--preview]         # lab.npy + names.json (+ coloured views)

The mesh is Y up facing +Z in the GLB; we convert to Z up facing -Y (the kit's axes), keep Meshy's
units (the figure is ~1.88 tall, feet at z=-0.90), and hand each triangle to the nearest bone
(signed capsule distance), then apply rules for equipment, cloth, feet, helm and collar.
Left is +X. build.py (Blender) turns the labels into parts.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

# Joint positions in Meshy units (z up, left +X, centre line x=CX). Measured from front and side
# renders with a 0.1 grid; build.py writes them (scaled to mm) into data/model-kit.json frameTunes.
CX = 0.025
JOINTS = {
    "pelvis": (0.0, 0.0, 0.02), "spine": (0.0, 0.0, 0.12), "chest": (0.0, 0.0, 0.28),
    "neck": (0.0, -0.05, 0.44), "head": (0.0, -0.10, 0.50),
    "shoulder": (0.34, 0.0, 0.34), "elbow": (0.45, 0.0, 0.08), "wrist": (0.55, -0.05, -0.19),
    "hip": (0.19, -0.02, -0.03), "knee": (0.21, -0.05, -0.42), "ankle": (0.23, -0.05, -0.82),
}

BONES_C = {  # name: (A, B, radius)  (x is centred on CX)
    "helm": ((0, -0.10, 0.51), (0, -0.10, 0.55), 0.12),
    "collar": ((0, -0.04, 0.44), (0, -0.04, 0.46), 0.09),
    "torso": ((0, -0.02, 0.20), (0, -0.02, 0.40), 0.20),
    "pelvis": ((0, 0, -0.02), (0, 0, 0.07), 0.17),
}
BONES_S = {  # left side; right is mirrored unless overridden below
    "pauldron": ((0.34, 0, 0.37), (0.38, 0, 0.42), 0.17),
    "arm": ((0.36, 0, 0.28), (0.45, 0, 0.10), 0.085),
    "forearm": ((0.46, 0, 0.08), (0.55, -0.04, -0.17), 0.095),
    "hand": ((0.56, -0.05, -0.20), (0.60, -0.30, -0.30), 0.09),
    "thigh": ((0.18, -0.02, -0.03), (0.20, -0.05, -0.38), 0.15),
    "shin": ((0.21, -0.05, -0.43), (0.23, -0.05, -0.78), 0.14),
    "foot": ((0.23, -0.10, -0.86), (0.23, -0.25, -0.87), 0.10),
}
BONES_R = {  # the right arm hangs a little closer in
    "arm": ((-0.36, 0, 0.28), (-0.44, 0, 0.10), 0.085),
    "forearm": ((-0.45, 0, 0.08), (-0.48, -0.04, -0.17), 0.10),
    "hand": ((-0.49, -0.05, -0.20), (-0.52, -0.30, -0.30), 0.09),
}


def read_glb(path):
    b = Path(path).read_bytes()
    jl = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + jl])
    off = 20 + jl
    bl = struct.unpack("<I", b[off:off + 4])[0]
    return j, b[off + 8:off + 8 + bl]


def extract(glb, work):
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    j, b = read_glb(glb)

    def acc(i):
        a = j["accessors"][i]
        bv = j["bufferViews"][a["bufferView"]]
        dt = {5126: "<f4", 5125: "<u4", 5123: "<u2"}[a["componentType"]]
        n = {"VEC3": 3, "VEC2": 2, "SCALAR": 1}[a["type"]]
        o = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        r = np.frombuffer(b, dt, a["count"] * n, o)
        return r.reshape(-1, n) if n > 1 else r
    prim = j["meshes"][0]["primitives"][0]
    at = prim["attributes"]
    P, UV, F = acc(at["POSITION"]), acc(at["TEXCOORD_0"]), acc(prim["indices"]).reshape(-1, 3)
    V = np.stack([P[:, 0], -P[:, 2], P[:, 1]], 1).astype(np.float32)
    np.savez(work / "mesh.npz", V=V, F=F.astype(np.int32), UV=UV.astype(np.float32))
    for k, im in enumerate(j["images"]):
        bv = j["bufferViews"][im["bufferView"]]
        o = bv.get("byteOffset", 0)
        (work / f"tex_{k}.jpg").write_bytes(b[o:o + bv["byteLength"]])
    print("extracted", V.shape, F.shape)


def seg_d(P, A, B):
    A, B = np.array(A, np.float32), np.array(B, np.float32)
    AB = B - A
    t = np.clip(((P - A) @ AB) / (AB @ AB), 0, 1)
    return np.linalg.norm(P - (A + t[:, None] * AB), axis=1)


def label(work, preview=False):
    from PIL import Image
    from scipy.spatial import cKDTree
    work = Path(work)
    d = np.load(work / "mesh.npz")
    V, F, UV = d["V"].copy(), d["F"], d["UV"]
    V[:, 0] -= CX
    C = V[F].mean(1)
    uv = UV[F].mean(1)
    tex = np.asarray(Image.open(work / "tex_0.jpg").convert("RGB"))
    n = tex.shape[0]
    col = tex[np.clip((uv[:, 1] * (n - 1)).astype(int), 0, n - 1), np.clip((uv[:, 0] * (n - 1)).astype(int), 0, n - 1)]
    x, y, z = C[:, 0], C[:, 1], C[:, 2]
    a = np.abs(x)
    names, D = [], []
    mir = lambda p: (-p[0], p[1], p[2])
    for k, (p, q, r) in BONES_C.items():
        names.append(k)
        D.append(seg_d(C, p, q) - r)
    for k, (p, q, r) in BONES_S.items():
        names.append(k + "_L")
        D.append(seg_d(C, p, q) - r)
        p2, q2, r2 = BONES_R.get(k, (mir(p), mir(q), r))
        names.append(k + "_R")
        D.append(seg_d(C, p2, q2) - r2)
    lab = np.stack(D, 1).argmin(1)

    def setl(mask, name):
        if name not in names:
            names.append(name)
        lab[mask] = names.index(name)

    L = x >= 0
    for s, sg in (("L", L), ("R", ~L)):
        setl(sg & (z < -0.805) & (a < 0.5), f"foot_{s}")

    def sword(s, A, B, w):
        sg = L if s == "L" else ~L
        P = np.stack([x, z], 1).astype(np.float32)
        A, B = np.array(A, np.float32), np.array(B, np.float32)
        AB = B - A
        t = np.clip(((P - A) @ AB) / (AB @ AB), 0, 1)
        dd = np.linalg.norm(P - (A + t[:, None] * AB), axis=1)
        setl(sg & (dd < w) & (z < -0.33) & (np.abs(y + 0.31) < 0.16) & (a > 0.38), f"sword_{s}")
    sword("L", (0.61, -0.35), (0.92, -0.95), 0.055)
    sword("R", (-0.45, -0.36), (-0.94, -0.95), 0.055)
    # shoulder pods (equipment), the spire and the pod struts (back)
    spire = (z > 0.56) & (x > -0.015 + 0.0) & (x < 0.07) & (y > -0.12)
    pod = (z > 0.56) & (a < 0.33) & (y > -0.12) & ~spire
    setl(pod & L, "pod_L")
    setl(pod & ~L, "pod_R")
    setl(spire, "back")
    setl((y > 0.12) & (z > 0.2) & (z <= 0.56) & (a < 0.32), "back")
    # helm and collar
    helm = ((x - 0.0) ** 2 / 0.10 ** 2 + (y + 0.10) ** 2 / 0.13 ** 2 + (z - 0.52) ** 2 / 0.11 ** 2 < 1) & (z > 0.44)
    setl(helm & (lab != names.index("back")), "helm")
    setl((z > 0.455) & (a < 0.17) & (y < 0.06) & (z < 0.57) & ~helm & np.isin(lab, [names.index("torso"), names.index("helm")]), "collar")
    # cloth: red texture, smoothed over 24 neighbours, in the zones where cloth hangs
    c = col.astype(int)
    red = ((c[:, 0] > 90) & (c[:, 0] > 2 * c[:, 1]) & (c[:, 0] > 2 * c[:, 2])).astype(np.float32)
    _, nn = cKDTree(C).query(C, k=24)
    redsm = red[nn].mean(1)
    zone = (y > 0.02) | (a > 0.5) | ((a < 0.15) & (z < 0.0) & (y < 0.0))
    setl((redsm > 0.30) & zone & (z < 0.46) & (lab != names.index("back")), "cloth")
    np.save(work / "lab.npy", lab.astype(np.int8))
    (work / "names.json").write_text(json.dumps(names))
    counts = {k: int((lab == i).sum()) for i, k in enumerate(names)}
    print(counts)
    if preview:
        sys.path.insert(0, str(Path(__file__).parent))
        import preview as pv
        FN = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        FN /= np.linalg.norm(FN, axis=1, keepdims=True) + 1e-12
        pv.parts_views(C, FN, lab, names, work / "cut")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "extract":
        extract(sys.argv[2], sys.argv[3])
    else:
        label(sys.argv[2], "--preview" in sys.argv)
