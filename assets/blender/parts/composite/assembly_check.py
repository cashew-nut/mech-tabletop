"""Assembly check of a composite build, from build.py's output (OUT/stl, assembled in print mm, and OUT/report.json).
    ~/bvenv/bin/python -I assembly_check.py OUT          (needs trimesh, manifold3d and rtree; about 3 minutes)

joints.py checks each peg and hole on its own. This checks that the parts go together:
1. every pair of parts, assembled: overlap volume (should be about 0: pegs sit in their holes with clearance). Checked with
   the plain forearm and hand, and again with the equipment forearm (`gun`) in their place.
2. every joint: the child (with the parts plugged into it) pulled off along its peg's axis in steps up to the peg's length
   plus 1 mm, overlap with the rest at each step. A part that cannot come off straight cannot go on straight: a flange or
   tongue of one part hooked round the other shows here.
3. every joint: how much of the child's surface within 4 mm of the peg lies within 0.3 mm of the parent (the parts meet).
"""
import sys, json, itertools, numpy as np, trimesh, manifold3d as mf

out = sys.argv[1]
rep = json.load(open(f"{out}/report.json"))
J = rep["joints"]
names = list(rep["parts"])


def load(n, mirror=False):
    m = trimesh.load(f"{out}/stl/{n}.stl")
    V, F = np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.uint32)
    if mirror:
        V = V * np.array([-1, 1, 1], np.float32)
        F = F[:, ::-1].copy()
    return mf.Manifold(mf.Mesh(vert_properties=V, tri_verts=F)), m


parts = {n: load(n) for n in names}
children = {}
for c, j in J.items():
    children.setdefault(j["parent"], []).append(c)


def desc(n):
    out_ = [n]
    for c in children.get(n, []):
        out_ += desc(c)
    return out_


def bb(m):
    b = m.bounding_box()
    return np.array(b[:3]), np.array(b[3:])


def overlap(a, b):
    (a0, a1), (b0, b1) = bb(a), bb(b)
    if (a1 < b0).any() or (b1 < a0).any():
        return 0.0
    return (a ^ b).volume()


configs = {"claw arm": [n for n in names if n != "gun"], "gun arm": [n for n in names if n not in ("forearm", "hand")]}
bad = 0
for cname, ps in configs.items():
    print(f"\n== {cname}: overlaps over 0.3 mm3 ==")
    for a, b in itertools.combinations(ps, 2):
        v = overlap(parts[a][0], parts[b][0])
        if v > 0.3:
            bad += 1
            print(f"  {a:9s} x {b:9s} {v:7.2f} mm3")
print("\n== pull-off along the peg axis (child + its children vs the rest) ==")
for c, j in J.items():
    ax = np.array(j["axis"], float)
    ax /= np.linalg.norm(ax)
    if j["peg_on"] not in (c, "forearm" if c == "gun" else c):      # the axis points from the peg's part into the other: pull the child the right way
        ax = -ax
    moving = [n for n in desc(c) if not (c == "gun" and n == "hand")]
    cfg = configs["gun arm"] if c == "gun" else configs["claw arm"]
    rest = [n for n in cfg if n not in moving]
    worst = []
    for t in (0.5, 1.0, 1.5, 2.0, 3.0, j['peg_length'] + 1.0):
        off = tuple(float(v) for v in -ax * t)
        tot, who = 0.0, []
        for m in moving:
            mm = parts[m][0].translate(off)
            for r in rest:
                v = overlap(mm, parts[r][0])
                if v > 0.05:
                    tot += v
                    ctr_ = np.round(np.array(bb(mm ^ parts[r][0])).mean(0), 1).tolist()
                    who.append(f"{m}x{r} {v:.2f} at {ctr_}")
        worst.append((t, tot, who))
    hit = [(t, tot, who) for t, tot, who in worst if tot > 0.3]
    flag = "OK " if not hit else "HIT"
    bad += bool(hit)
    print(f"  {flag} {c:9s} -> {j['parent']:9s} peg r{j['peg_radius']} L{j['peg_length']}  " +
          ("; ".join(f"t={t}: {tot:.2f} ({', '.join(who[:3])})" for t, tot, who in hit[:3]) if hit else ""))
print("\n== contact round the peg (gap child-parent within 4 mm of the peg centre) ==")
for c, j in J.items():
    p = j["parent"]
    ctr = np.array(j["centre"])
    tm_c, tm_p = parts[c][1], parts[p][1]
    pts, _ = trimesh.sample.sample_surface(tm_c, 60000, seed=1)
    pts = pts[np.linalg.norm(pts - ctr, axis=1) < 4.0]
    if len(pts) == 0:
        print(f"  ?? {c}: no child surface near the peg")
        continue
    d = np.abs(trimesh.proximity.signed_distance(tm_p, pts[:4000]))
    close = (d < 0.3).mean()
    print(f"  {c:9s} -> {p:9s} min gap {d.min():.2f} mm, {close*100:4.0f}% of nearby child surface within 0.3 mm")
print(f"\nflags: {bad}")
