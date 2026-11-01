"""Cut a Meshy figure into closed, separate solid parts (step 1 of 3; numpy, scipy, scikit-image, manifold3d).

    [MODEL=brute|seer] ~/bvenv/bin/python split.py WORK   # WORK holds mesh.npz (+ lab.npy, names.json for the Paladin)

The model's own rules (labels, parts, designed additions) are in paladin.py, brute.py or seer.py; see layout.py.

The Meshy figure is one closed (watertight) surface, so it can be treated as a solid. The old route (../meshy/build.py)
gave each part the triangles labelled for it, which leaves open, ragged shells that only look right in place. Here the
space around the figure is labelled voxel by voxel with the same rules as ../meshy/cut.py (bone capsules for the body,
boxes for helm, collar, back, pods and blades, the red-cloth triangles for cloth), every part's region is turned into a
closed mesh, and the figure is intersected with it. Each part comes out closed, with a flat-ish cap where it met its
neighbour, and keeps Meshy's UVs on the original surface (cap faces get UV (-1, -1) so the bake can tell them apart).

Then joints.py adds a keyed peg and magnet pockets at every joint. Output: WORK/parts/<part>.npz (print mm, kit axes).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from layout import M, PS, MM, to_mm, from_mm  # noqa: E402  (labelling rules live in paladin.py, brute.py, seer.py)

CHIP = getattr(M, "CHIP_SCALE", PS ** 3)    # sliver and crumb sizes scale with the print volume


def main(work):
    from scipy import ndimage
    from scipy.spatial import cKDTree
    from skimage.measure import marching_cubes
    import manifold3d as mf

    work = Path(work)
    out = work / "parts"
    out.mkdir(exist_ok=True)
    t0 = time.time()
    d = np.load(work / "mesh.npz")
    V, F, UV = d["V"].copy(), d["F"], d["UV"]
    V[:, 0] -= M.CX
    H, PARTS = M.H, M.PARTS
    if hasattr(M, "prepare"):
        M.prepare(work, V, F, UV)

    # --- voxel labels -------------------------------------------------------------------------------------------
    lo, hi = V.min(0) - 4 * H, V.max(0) + 4 * H
    shape = np.ceil((hi - lo) / H).astype(int) + 1
    print("grid", shape, int(np.prod(shape)) / 1e6, "M voxels", flush=True)
    ctree = None
    if hasattr(M, "cloth_tris"):    # cloth is a thin sheet: voxels close to a cloth triangle are cloth
        ctree = cKDTree(V[F].mean(1)[M.cloth_tris(work, V, F, UV)])
    labels = np.empty(tuple(shape), np.int16)
    names = None
    xs = lo[0] + H * np.arange(shape[0])
    ys = lo[1] + H * np.arange(shape[1])
    zs = lo[2] + H * np.arange(shape[2])
    for i0 in range(0, shape[0], 24):
        xi = xs[i0:i0 + 24]
        P = np.stack(np.meshgrid(xi, ys, zs, indexing="ij"), -1).reshape(-1, 3).astype(np.float32)
        if ctree is None:
            lab, names = M.label_points(P, None)
        else:
            dc, _ = ctree.query(P, k=1, distance_upper_bound=M.CLOTH_T, workers=-1)
            lab, names = M.label_points(P, np.isfinite(dc))
        labels[i0:i0 + len(xi)] = lab.reshape(len(xi), shape[1], shape[2])
    print("labelled", f"{time.time() - t0:.0f}s", flush=True)

    # --- the figure as a manifold, with UVs as vertex properties ------------------------------------------------
    Vmm = to_mm(V).astype(np.float32)
    props = np.concatenate([Vmm, UV], 1).astype(np.float32)
    mesh = mf.Mesh(vert_properties=props, tri_verts=F.astype(np.uint32))
    mesh.merge()            # Meshy splits vertices along its UV seams: tell manifold which ones are the same point
    fig = mf.Manifold(mesh)
    if hasattr(M, "extra_solids"):
        # designed additions (the Seer's ball knuckles); they become part of the figure before it is cut
        fig = fig + M.extra_solids(mf, to_mm)
    print("figure", fig.status(), fig.num_tri(), "tris", f"{time.time() - t0:.0f}s", flush=True)

    # --- one region mesh per part, intersected with the figure --------------------------------------------------
    info = {"keys": list(PARTS), "names": names, "lo": lo.tolist(), "h": H, "shape": shape.tolist(), "parts": {}}
    part_of = np.full(len(names), -1, np.int16)
    keys = list(PARTS)
    for pi, k in enumerate(keys):
        for n in PARTS[k]:
            part_of[names.index(n)] = pi
    assert (part_of >= 0).all(), [n for n, p in zip(names, part_of) if p < 0]
    plabel = part_of[labels]

    # Occupancy: slice the figure at every voxel layer and fill the outlines (even-odd, so holes stay holes).
    from skimage.draw import polygon as fillpoly
    occ = np.zeros(tuple(shape), bool)
    for kz in range(shape[2]):
        layer = np.zeros((shape[0], shape[1]), bool)
        for poly in fig.slice(float(to_mm(np.array([0, 0, zs[kz]]))[2])).to_polygons():
            q = np.asarray(poly) / MM
            rr, cc = fillpoly((q[:, 0] - lo[0]) / H, (q[:, 1] - lo[1]) / H, layer.shape)
            layer[rr, cc] ^= True
        occ[:, :, kz] = layer
    print("occupancy", f"{occ.mean():.3f}", f"{time.time() - t0:.0f}s", flush=True)
    # Inside the figure, every part should be one connected lump. Smaller lumps (a plate whose only link to its part
    # runs through a neighbour) are handed to the neighbour they touch most, voxel by voxel, so the part they join
    # stays one connected solid.
    st = ndimage.generate_binary_structure(3, 1)
    for _ in range(3):
        moved = 0
        for pi, k in enumerate(keys):
            comp, n = ndimage.label((plabel == pi) & occ, st)
            if n < 2:
                continue
            sizes = np.bincount(comp.ravel())[1:]
            big = sizes.argmax() + 1
            for c in range(1, n + 1):
                if c == big or sizes[c - 1] > 0.25 * sizes.max():
                    continue
                m = comp == c
                ring = ndimage.binary_dilation(m, st) & ~m & occ
                nb = plabel[ring]
                nb = nb[nb != pi]
                if len(nb):
                    plabel[m] = np.bincount(nb).argmax()
                    moved += 1
        print("relabelled lumps:", moved, flush=True)
        if not moved:
            break
    np.save(work / "part_grid.npy", plabel.astype(np.int8))
    np.save(work / "occ.npy", occ)
    solids, pieces_of = {}, {}
    for pi, k in enumerate(keys):
        ind = (plabel == pi)
        if not ind.any():
            print("empty", k)
            continue
        idx = np.argwhere(ind)
        a, b = np.maximum(idx.min(0) - 3, 0), np.minimum(idx.max(0) + 4, shape)
        sub = ndimage.gaussian_filter(ind[a[0]:b[0], a[1]:b[1], a[2]:b[2]].astype(np.float32), 1.0)
        sub = np.pad(sub, 1)
        vv, ff, _, _ = marching_cubes(sub, 0.5)
        rm = to_mm(lo + H * (vv - 1 + a)).astype(np.float32)
        rp = np.concatenate([rm, -np.ones((len(rm), 2), np.float32)], 1)   # cap faces get UV (-1, -1)
        region = mf.Manifold(mf.Mesh(vert_properties=rp, tri_verts=ff[:, ::-1].astype(np.uint32)))
        if region.status() != mf.Error.NoError:
            print("region not manifold", k, region.status())
        pieces_of[k] = sorted((fig ^ region).decompose(), key=lambda m: -m.volume())
    print("intersected", f"{time.time() - t0:.0f}s", flush=True)

    # A part's smaller loose pieces (a plate whose only link to the part ran through a neighbour) go to the neighbour
    # they touch most; crumbs are dropped. Pieces of the right-side parts are only there to carve the torso and pelvis.
    def neighbour(piece, own):
        mm = piece.to_mesh()
        P = np.asarray(mm.vert_properties)[:, :3]
        g = np.round((from_mm(P) - lo) / H).astype(int)
        hits = []
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                for dz in (-2, 0, 2):
                    q = np.clip(g + (dx, dy, dz), 0, shape - 1)
                    hits.append(plabel[q[:, 0], q[:, 1], q[:, 2]])
        hits = np.concatenate(hits)
        hits = hits[hits != own]
        return keys[np.bincount(hits).argmax()] if len(hits) else None
    final = {k: [] for k in pieces_of}
    moved = []
    for k, ps in pieces_of.items():
        if not ps:
            continue
        main_v = ps[0].volume()
        final[k].append(ps[0])
        for p in ps[1:]:
            v = p.volume()
            if v < 0.02 * CHIP:
                continue
            if v > 0.25 * main_v:
                final[k].append(p)
                continue
            to = neighbour(p, keys.index(k))
            if to is not None and to in final:
                final[to].append(p)
                moved.append((k, to, round(v, 2)))
    for k, to, v in moved:
        print(f"  piece {v} mm3: {k} -> {to}")
    solid = {}
    for k, ps in final.items():
        if k.startswith("_") or not ps:
            continue
        part = mf.Manifold.batch_boolean(ps, mf.OpType.Add) if len(ps) > 1 else ps[0]
        keep = [p for p in part.decompose() if p.volume() > 0.05 * CHIP]      # zero-volume slivers from the cut
        solid[k] = mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]
    if hasattr(M, "design"):
        # the model's own structural changes: struts, mounts, pieces moved between parts (see seer.py)
        solid = M.design(solid, mf)
    for k, part in solid.items():
        n = len(part.decompose())
        m = part.to_mesh()
        P, T = np.asarray(m.vert_properties), np.asarray(m.tri_verts)
        np.savez(out / f"{k}.npz", P=P, T=T, mf=np.asarray(m.merge_from_vert), mt=np.asarray(m.merge_to_vert))
        info["parts"][k] = {"tris": int(len(T)), "pieces": n, "volume": round(part.volume(), 1)}
        print(f"{k:10s} {len(T):7d} tris  {n} piece(s)  vol {part.volume():8.1f} mm3", flush=True)
    info["moved"] = moved
    (work / "split.json").write_text(json.dumps(info, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
