"""Add a keyed peg and magnet pockets at every joint of the split Paladin (step 2 of 3; numpy, scipy, manifold3d).

    ~/bvenv/bin/python -I joints.py WORK          # reads WORK/parts/*.npz (split.py), writes WORK/kit/*.npz + joints.json

Every part plugs into its parent (common.TREE): the child grows a D-shaped peg out of the face where it was cut from
the parent, and the parent gets the matching D-shaped hole, 0.1 mm looser. The flat on the D keys the part so it only
fits one way round. Where the peg is thick enough, a disc magnet sits flush in the peg's tip and another at the bottom
of the hole (2 x 1 mm, or 1 x 1 mm on thin joints), so parts click on and off without glue.

Where the peg goes is a search over the voxel grid split.py left behind: axes (the cut face's mean normal, the bone
from this joint to the parent's, and blends), centres (the joint, the face's most interior point, and a grid round
them), radii from 2.0 mm down to 0.5 mm. A candidate is good when the peg's root lies inside the child, and the hole
plus a 0.4 mm wall lies inside the parent. The biggest good peg wins; then the longest. Sided parts are built for the
left; a centre parent (torso, pelvis, back) gets the right side's hole mirrored.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from layout import TREE, SIDED, RESEAT, NAME, joint  # noqa: E402
import split  # noqa: E402

CLEAR = 0.10          # peg-to-hole clearance (radius), mm
WALL = 0.40           # minimum wall round a hole, mm
MAGNETS = ((1.0, 1.0), (0.5, 1.0))     # (radius, thickness) mm: 2 x 1 mm discs, else 1 x 1 mm
RADII = (2.0, 1.75, 1.5, 1.3, 1.15, 1.0, 0.85, 0.75, 0.65, 0.55)
LENGTHS = (3.0, 2.6, 2.2, 1.8, 1.5, 1.2, 1.0)
CRUMB = 0.2           # mm3: loose bits smaller than this are dropped
CLEAR_MIRRORED = False  # trim centre parts where mirrored right-hand parts would overlap them
BOTH_WAYS = False     # also try the peg on the parent, and keep whichever holds better
if NAME == "brute":   # cut at 1.5x print scale with thick joints: bigger pegs, and stock 5 x 2 or 3 x 2 mm magnets
    MAGNETS = ((2.5, 2.0), (1.5, 2.0), (1.0, 1.0))
    RADII = (4.0, 3.5, 3.0, 2.6, 2.3, 2.0) + RADII[1:]
    LENGTHS = (5.0, 4.5, 4.0, 3.5) + LENGTHS
    CRUMB = 1.0
    BOTH_WAYS = True
    CLEAR_MIRRORED = True


def load(path):
    import manifold3d as mf
    d = np.load(path)
    return mf.Manifold(mf.Mesh(vert_properties=d["P"].astype(np.float32), tri_verts=d["T"].astype(np.uint32),
                               merge_from_vert=d["mf"].astype(np.uint32), merge_to_vert=d["mt"].astype(np.uint32)))


def save(m, path):
    mm = m.to_mesh()
    np.savez(path, P=np.asarray(mm.vert_properties), T=np.asarray(mm.tri_verts),
             mf=np.asarray(mm.merge_from_vert), mt=np.asarray(mm.merge_to_vert))


def frame(axis, key_hint):
    """Orthonormal frame with z = axis; x points at the key flat (towards key_hint, projected)."""
    z = axis / np.linalg.norm(axis)
    x = key_hint - z * (key_hint @ z)
    if np.linalg.norm(x) < 1e-3:
        x = np.array([0.0, -1.0, 0.0]) - z * (-z[1])
    x /= np.linalg.norm(x)
    return np.stack([x, np.cross(z, x), z], 1)     # columns


def d_shape(r, z0, z1, R, origin, flat=0.6):
    """A D-section prism along local z from z0 to z1: a cylinder with a flat at x = flat * r."""
    import manifold3d as mf
    cyl = mf.Manifold.cylinder(z1 - z0, r, -1.0, 48).translate((0, 0, z0))
    cut = mf.Manifold.cube((2 * r, 4 * r, z1 - z0 + 2)).translate((flat * r, -2 * r, z0 - 1))
    shp = cyl - cut
    return place(shp, R, origin)


def disc(r, z0, z1, R, origin):
    import manifold3d as mf
    return place(mf.Manifold.cylinder(z1 - z0, r, -1.0, 40).translate((0, 0, z0)), R, origin)


def place(m, R, origin):
    M = np.concatenate([R, np.asarray(origin, float)[:, None]], 1)
    return m.transform(M.tolist()).set_properties(2, lambda p, old: (-1.0, -1.0))


def mirror(m):
    return m.transform([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])


def interface(child, plabel, keys, parent_key, lo, h):
    """Cap faces of the child that face the parent: (centroids, normals, areas) in mm."""
    mm = child.to_mesh()
    P, T = np.asarray(mm.vert_properties), np.asarray(mm.tri_verts)
    cap = (P[T, 3] < -0.5).all(1)
    A, B, Cc = (P[T[:, k], :3] for k in range(3))
    n = np.cross(B - A, Cc - A)
    area = np.linalg.norm(n, axis=1) / 2
    n = n / (2 * area[:, None] + 1e-12)
    c = (A + B + Cc) / 3
    probe = split.from_mm(c + 0.4 * n)
    g = np.clip(np.round((probe - lo) / h).astype(int), 0, np.array(plabel.shape) - 1)
    hit = plabel[g[:, 0], g[:, 1], g[:, 2]] == keys.index(parent_key)
    sel = cap & hit & (area > 0)
    return c[sel], n[sel], area[sel]


def peg_site(c, n, a, R):
    """Most interior point of the interface seen along the axis, its inradius, and the face's offset there."""
    from scipy import ndimage
    q = (c - c.mean(0)) @ R            # local coords: x, y in the face, z along the axis
    px = 0.1
    ij = np.round((q[:, :2] - q[:, :2].min(0)) / px).astype(int) + 3
    img = np.zeros(ij.max(0) + 4, bool)
    img[ij[:, 0], ij[:, 1]] = True
    img = ndimage.binary_closing(img, iterations=3)
    img = ndimage.binary_fill_holes(img)
    dt = ndimage.distance_transform_edt(img) * px
    i, j = np.unravel_index(dt.argmax(), dt.shape)
    xy = (np.array([i, j]) - 3) * px + q[:, :2].min(0)
    near = np.linalg.norm(q[:, :2] - xy, axis=1) < max(0.5, dt.max() * 0.5)
    zoff = np.median(q[near, 2]) if near.any() else np.median(q[:, 2])
    centre = c.mean(0) + R @ np.array([xy[0], xy[1], zoff])
    return centre, dt.max()


def disc_pts(r, n_r=4, n_a=16):
    """Sample points over a disc of radius r (local x, y)."""
    pts = [(0.0, 0.0)]
    for i in range(1, n_r + 1):
        rr = r * i / n_r
        for k in range(n_a):
            t = 2 * np.pi * k / n_a
            pts.append((rr * np.cos(t), rr * np.sin(t)))
    return np.array(pts)


class Grid:
    def __init__(self, plabel, occ, keys, lo, h):
        self.lab, self.occ, self.keys, self.lo, self.h = plabel, occ, keys, lo, h
        self.shape = np.array(plabel.shape)

    def who(self, P):
        g = np.round((split.from_mm(P) - self.lo) / self.h).astype(int)
        inside = (g >= 0).all(1) & (g < self.shape).all(1)
        g = np.clip(g, 0, self.shape - 1)
        lab = self.lab[g[:, 0], g[:, 1], g[:, 2]].astype(int)
        lab[~(inside & self.occ[g[:, 0], g[:, 1], g[:, 2]])] = -1
        return lab


def try_peg(grid, ci, pi, centre, axis, r):
    """Fit a peg of radius r on the line (centre, axis). Returns (t0, L, magnet) or None."""
    R = frame(axis, np.array([0.0, -1.0, 0.0]) if abs(axis[1]) < 0.8 else np.array([0.0, 0.0, 1.0]))
    t = np.arange(-8, 8.01, 0.1)
    line = grid.who(centre + t[:, None] * axis)
    # the cut: last child voxel before the first run of parent voxels
    t0 = None
    for k in range(1, len(t)):
        if line[k] == pi and line[k - 1] in (ci, -1) and (line[max(0, k - 12):k] == ci).any():
            t0 = t[k]
            break
    if t0 is None:
        return None
    root = disc_pts(r)
    R2 = R[:, :2]
    zs_root = np.arange(-1.2, -0.29, 0.15)
    P = (centre + (t0 + zs_root)[:, None, None] * axis + (root @ R2.T)[None]).reshape(-1, 3)
    if (grid.who(P) == ci).mean() < 0.80:
        return None
    best = None
    for L in LENGTHS:
        if L > 2.2 * r + 0.6:
            continue
        mag = next(((mr, mt) for mr, mt in MAGNETS if r >= mr + 0.3 and L >= mt + 0.3), None)
        bottom = L + 0.15 + (mag[1] + 0.1 if mag else 0)
        ring = disc_pts(r + CLEAR + WALL, 5, 24)
        zs = np.arange(0.5, bottom + WALL + 0.01, 0.2)
        P = (centre + (t0 + zs)[:, None, None] * axis + (ring @ R2.T)[None]).reshape(-1, 3)
        if (grid.who(P) == pi).mean() >= 0.93:
            best = (t0, L, mag)
            break
    return best


def candidates(parts, grid, child, parent):
    """Axes and centres to try for the joint child -> parent, and the cut face's inradius (for the log)."""
    keys, cj = grid.keys, TREE[child][1]
    c, n, a = interface(parts[child], grid.lab, keys, parent, grid.lo, grid.h)
    axes, centres, rho = [], [np.array(joint(cj))], 0.0
    bone = np.array(joint(TREE[parent][1])) - np.array(joint(cj))
    if np.linalg.norm(bone) > 1:
        axes.append(bone / np.linalg.norm(bone))
    if len(c) >= 10:
        fa = (n * a[:, None]).sum(0)
        fa /= np.linalg.norm(fa)
        if axes:
            m = axes[0] + fa
            axes.append(m / np.linalg.norm(m))
        axes.insert(0, fa)
        site, rho = peg_site(c, n, a, frame(fa, np.array([0.0, 0.0, 1.0])))
        centres += [site, c.mean(0)]
    axes += [np.array(v, float) for v in ([0, 0, 1], [0, 0, -1], [-1, 0, 0], [0, 1, 0], [0, -1, 0])]
    return axes, centres, rho


def search(grid, ci, pi, axes, centres, sign):
    for r in RADII:
        for ax in axes:
            R = frame(ax, np.array([0.0, 0.0, 1.0]))
            for c0 in centres:
                for dx in (0, -1, 1, -2, 2, -3, 3):
                    for dy in (0, -1, 1, -2, 2, -3, 3):
                        cc = c0 + R[:, 0] * dx * 0.6 + R[:, 1] * dy * 0.6
                        res = try_peg(grid, ci, pi, cc, sign * ax, r)
                        if res:
                            return r, sign * ax, cc, res
    return None


def peg_shapes(r, L, mag, axis, centre):
    """The peg (to add to the male part) and the hole (to cut from the female part) for one joint."""
    R = frame(axis, np.array([0.0, -1.0, 0.0]) if abs(axis[1]) < 0.8 else np.array([0.0, 0.0, 1.0]))
    add = d_shape(r, -1.2, L, R, centre)
    sub = d_shape(r + CLEAR, -0.6, L + 0.15, R, centre, flat=0.6 + CLEAR / r)
    if mag:
        mr, mt = mag
        add = add - disc(mr + 0.05, L - mt - 0.1, L + 0.01, R, centre)        # magnet flush in the peg's tip
        sub = sub + disc(mr + 0.05, L + 0.1, L + 0.15 + mt + 0.1, R, centre)  # and at the bottom of the hole
    return add, sub


def gun_frame(m, toward):
    """A gun's barrel axis (principal axis of its surface, pointing at `toward`) and the centre of its breech end (the
    last 2 mm of the gun along that axis)."""
    mm = m.to_mesh()
    P, T = np.asarray(mm.vert_properties), np.asarray(mm.tri_verts)
    A, B, C = (P[T[:, k], :3] for k in range(3))
    area = np.linalg.norm(np.cross(B - A, C - A), axis=1) / 2
    c = (A + B + C) / 3
    mu = (c * area[:, None]).sum(0) / area.sum()
    w, v = np.linalg.eigh(((c - mu) * area[:, None]).T @ (c - mu))
    ax = v[:, -1]
    if ax @ (toward - mu) < 0:
        ax = -ax
    t = (c - mu) @ ax
    end = t > t.max() - 2.0
    breech = (c[end] * area[end, None]).sum(0) / area[end].sum()
    return ax, breech, mu


def rot_between(a, b):
    """Smallest rotation taking unit vector a onto b."""
    v, c = np.cross(a, b), float(a @ b)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def reseat(parts, log, part, like):
    """Mirror `part` (cut from the figure's right) to the left, move it onto the socket `like` uses on the same parent,
    trim it where it would clash with the parent, and give it the same peg (or hole) plus a collar to carry it."""
    import manifold3d as mf
    e = log[like]
    host = e["parent"]
    m = mirror(parts[part])
    toward = np.array(e["centre"])
    a_src, b_src, _ = gun_frame(m, toward)
    a_dst, b_dst, _ = gun_frame(parts[like], toward)
    Rm = rot_between(a_src, a_dst)
    t = b_dst - Rm @ b_src
    m = m.transform(np.concatenate([Rm, t[:, None]], 1).tolist())
    axis, centre = np.array(e["axis"]), np.array(e["centre"])
    r, L, mag = e["peg_radius"], e["peg_length"], e["_mag"]
    add, sub = peg_shapes(r, L, mag, axis, centre)
    on_gun = e["peg_on"] == like
    sgn = 1.0 if on_gun else -1.0      # axis points from the peg's part into the hole's part
    R = frame(axis, np.array([0.0, 0.0, 1.0]))
    collar = place(mf.Manifold.cylinder(3.0, r + 1.2, -1.0, 48).translate((0, 0, -3.0 if on_gun else 0.0)), R, centre)
    m = (m - parts[host]) + (collar - parts[host])
    m = m + add if on_gun else m - sub
    keep = sorted(m.decompose(), key=lambda p: -p.volume())
    parts[part] = keep[0]
    lost = sum(p.volume() for p in keep[1:])
    ang = float(np.degrees(np.arccos(np.clip(a_src @ a_dst, -1, 1))))
    return dict(e, reseated_from=like, turned_deg=round(ang, 1), moved_mm=round(float(np.linalg.norm(b_dst - b_src)), 2),
                dropped_mm3=round(lost, 1), mirrored_for_right=False)


def hold(found):
    """How well a peg holds, for comparing two: magnet size first, then peg girth times length."""
    r, _, _, (_, L, mag) = found
    return (mag[0] if mag else 0.0, r * L)


def fit(parts, grid, child, parent):
    """Cut the peg and hole for child -> parent into `parts`. Returns the log entry, or None if there is no room."""
    keys = grid.keys
    ci, pi = keys.index(child), keys.index(parent)
    axes, centres, rho = candidates(parts, grid, child, parent)
    # the peg grows from the child into the parent; if there is no room, from the parent into the child
    found, flipped = search(grid, ci, pi, axes, centres, 1.0), False
    if BOTH_WAYS:     # try the other way round too and keep the thicker (then longer) peg
        other = search(grid, pi, ci, axes, centres, -1.0)
        if other and (not found or hold(other) > hold(found)):
            found, flipped = other, True
    elif not found:
        found, flipped = search(grid, pi, ci, axes, centres, -1.0), True
    if not found:
        return None
    r, axis, cc, (t0, L, mag) = found
    centre = cc + t0 * axis
    male, female = (parent, child) if flipped else (child, parent)
    add, sub = peg_shapes(r, L, mag, axis, centre)
    newm, newf = parts[male] + add, parts[female] - sub
    if child in SIDED and parent not in SIDED:
        # the right-hand part is the left one mirrored, so the centre part gets the right side's peg or hole too
        if flipped:
            newm = newm + mirror(add)
        else:
            newf = newf - mirror(sub)
    parts[male], parts[female] = newm, newf
    return {"parent": parent, "peg_on": male, "centre": [round(float(v), 3) for v in centre],
            "axis": [round(float(v), 4) for v in axis], "peg_radius": r, "peg_length": L,
            "_mag": list(mag) if mag else None,
            "magnet": f"{2 * mag[0]:g} x {mag[1]:g} mm" if mag else None, "face_inradius": round(float(rho), 2),
            "mirrored_for_right": child in SIDED and parent not in SIDED}


def main(work):
    work = Path(work)
    info = json.loads((work / "split.json").read_text())
    keys, lo, h = info["keys"], np.array(info["lo"]), info["h"]
    grid = Grid(np.load(work / "part_grid.npy"), np.load(work / "occ.npy"), keys, lo, h)
    src, dst = work / "parts", work / "kit"
    dst.mkdir(exist_ok=True)
    parts = {k: load(src / f"{k}.npz") for k in TREE if (src / f"{k}.npz").exists()}
    log = {}
    for child, (_, _, parents) in TREE.items():
        if parents is None or child not in parts:
            continue
        if child in RESEAT:
            continue
        for parent in (parents if isinstance(parents, tuple) else (parents,)):
            entry = fit(parts, grid, child, parent)
            if entry:
                break
        log[child] = entry or {"parent": parents, "peg": None}
        if entry:
            print(f"{child:8s} -> {parent:8s} peg on {entry['peg_on']:8s} r {entry['peg_radius']:.2f} "
                  f"L {entry['peg_length']:.2f} magnet {entry['magnet']}", flush=True)
        else:
            print(f"{child} -> {parents}: no room for a peg", flush=True)
    for child, like in RESEAT.items():
        if child in parts and log.get(like, {}).get("peg_radius"):
            log[child] = reseat(parts, log, child, like)
            print(f"{child:8s} re-seated on {like}'s socket: turned {log[child]['turned_deg']} deg, "
                  f"moved {log[child]['moved_mm']} mm, dropped {log[child]['dropped_mm3']} mm3", flush=True)
    for e in log.values():
        e.pop("_mag", None)
    if CLEAR_MIRRORED:
        # the right-hand parts are the left ones mirrored, so trim the centre parts wherever a mirrored part would sit
        for c in [k for k in parts if k not in SIDED]:
            before = parts[c].volume()
            for k in [k for k in parts if k in SIDED]:
                parts[c] = parts[c] - mirror(parts[k])
            print(f"  {c:9s} trimmed {before - parts[c].volume():.2f} mm3 for the mirrored right side", flush=True)
    import manifold3d as mf
    for k, m in parts.items():
        keep = [p for p in m.decompose() if p.volume() > CRUMB]   # slivers a hole sheared off, loose crumbs
        m = parts[k] = mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]
        save(m, dst / f"{k}.npz")
        print(f"  {k:9s} {m.num_tri():7d} tris  {len(m.decompose())} piece(s)  {m.status()}")
    (work / "joints.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
