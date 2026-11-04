"""Close the pin-holes in a Meshy mesh so manifold3d accepts it (numpy only).

    python3 -I repair_mesh.py WORK        # reads WORK/mesh.npz, keeps the original as mesh_raw.npz, writes the repaired one

The Paladin, Brute and Seer meshes were watertight; the Sentinel's (multi-image-to-3D, retextured) has a few hundred open
edges and a few edges shared by three faces. Meshy splits vertices along UV seams, so closeness is judged on merged positions.
Steps: drop faces that make an edge three-way (and exact duplicates), then fan-fill every boundary loop with new faces that use
the existing vertices (and so their UVs: the patches are tiny). Prints what it did.
"""
import sys
from pathlib import Path

import numpy as np


def main(work):
    work = Path(work)
    raw = work / "mesh_raw.npz"
    src = raw if raw.exists() else work / "mesh.npz"
    d = np.load(src)
    V, F, UV = d["V"], d["F"].astype(np.int64), d["UV"]
    q = np.round(V.astype(np.float64) * 1e5).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    n = len(first)
    keep = np.ones(len(F), bool)
    for _ in range(4):
        Fm = inv[F]
        deg = (Fm[:, 0] == Fm[:, 1]) | (Fm[:, 1] == Fm[:, 2]) | (Fm[:, 0] == Fm[:, 2])
        keep &= ~deg
        Fk = Fm[keep]
        idx = np.nonzero(keep)[0]
        e = np.concatenate([Fk[:, [0, 1]], Fk[:, [1, 2]], Fk[:, [2, 0]]])
        fid = np.concatenate([idx, idx, idx])
        k = e[:, 0] * n + e[:, 1]
        u, cnt = np.unique(k, return_counts=True)
        bad = np.isin(k, u[cnt > 1])
        if not bad.any():
            break
        # of the faces on a doubled edge, drop all but the first
        for kk in np.unique(k[bad]):
            fs = np.unique(fid[k == kk])
            keep[fs[1:]] = False
    Fm = inv[F][keep]
    e = np.concatenate([Fm[:, [0, 1]], Fm[:, [1, 2]], Fm[:, [2, 0]]])
    k = e[:, 0] * n + e[:, 1]
    rk = e[:, 1] * n + e[:, 0]
    open_e = e[~np.isin(k, rk)]
    print("faces dropped", int((~keep).sum()), "open edges", len(open_e))
    nxt = {}
    for a, b in open_e:
        nxt.setdefault(int(a), []).append(int(b))
    seen, new = set(), []
    for a0 in list(nxt):
        for b0 in nxt[a0]:
            if (a0, b0) in seen:
                continue
            loop, a, b = [a0], a0, b0
            while (a, b) not in seen:
                seen.add((a, b))
                loop.append(b)
                opts = [c for c in nxt.get(b, []) if (b, c) not in seen]
                if not opts:
                    break
                a, b = b, opts[0]
                if b == a0:
                    seen.add((a, b))
                    break
            loop = loop[:-1] if loop[-1] == loop[0] and len(loop) > 1 else loop
            if len(loop) >= 3:
                R = loop[::-1]
                new += [(R[0], R[i], R[i + 1]) for i in range(1, len(R) - 1)]
    print("hole faces added", len(new))
    # back to the original vertex indices (the first copy of each merged vertex)
    F2 = np.concatenate([F[keep], first[np.array(new, np.int64).reshape(-1, 3)]]) if new else F[keep]
    if not raw.exists():
        (work / "mesh.npz").rename(raw)
    np.savez(work / "mesh.npz", V=V, F=F2.astype(np.int32), UV=UV)
    print("faces", len(F), "->", len(F2))


if __name__ == "__main__":
    main(sys.argv[1])
