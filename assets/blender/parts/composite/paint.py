"""Paint a composite part panel by panel, the way a modeller would (numpy, scipy, pillow; no Blender). Used by build.py
when the model module defines `paint(k, s)` (the Artillery, artillery.py).

Meshy bakes one muddy texture over the whole figure. Recolouring that texture by brightness in UV space
(tools/recolour/foundry_palette.py) gives camouflage blotches, because the UV charts are tiny and brightness does not follow
the armour. Here the paint follows the solid instead:

1. `surface()` reads a part's full-resolution solid (print mm) with Meshy's UVs, welds it, and measures every vertex: its
   normal, a curvature (how far its normal turns from the normals around it), Meshy's colour under it and the mean
   brightness of the surface round it (`lm`, over about 1.2 mm of surface).
2. `panels()` floods the surface between creases: neighbours join when their normals are within 8 degrees and neither sits
   on a sharp edge. What comes out are the plates, rings, drums and tubes a modeller would pick one by one; the creases
   between them stay unassigned (they become panel lines).
3. The model's `paint(k, s)` gives every vertex a finish (red lacquer, blackened iron, brass, steel, white stencil, soot)
   from the panels' size, facing and place, so a whole plate is red or a whole ring is brass.
4. `finish_arrays()` turns finishes into colour, roughness and metal per vertex. In the bake (build.py) the colour is
   multiplied by Meshy's texture divided by `lm`: the rivets, grilles, dents and grime Meshy painted survive as light and
   dark, but its ochre and brown do not. Designed solids (no Meshy texture) carry their finish in their UVs
   (u = v = -(10 + finish index)).

The colours are the Brute's own texels, so the game's livery shader (apps/web/src/model/assemble.ts) repaints the red
plate and leaves iron, brass and the stencils alone, as on the Brute.
"""
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components

# finish: (sRGB 0-255, roughness, metallic, detail strength)
FINISHES = {
    "iron": ((36, 34, 31), 0.62, 0.65, 1.0),     # blackened iron: frame, guns, undercarriage
    "red": ((135, 22, 17), 0.58, 0.0, 1.0),      # red lacquer plate (the Brute's texels; the livery shader repaints it)
    "brass": ((150, 104, 58), 0.36, 1.0, 0.8),   # worn brass: collars, rims, rivets, shell casings
    "steel": ((74, 73, 72), 0.40, 0.9, 0.9),     # gun steel: the howitzer's tube
    "white": ((214, 206, 188), 0.62, 0.0, 0.5),  # stencilled unit numbers
    "soot": ((17, 16, 15), 0.85, 0.3, 0.6),      # stack mouths, vents
    "glow": ((255, 120, 30), 0.5, 0.0, 0.0),     # furnace light behind grilles (not emissive in the game)
    "hazard": ((214, 160, 32), 0.55, 0.0, 0.6),  # hazard yellow (stripes with iron)
}
NAMES = list(FINISHES)
F = {n: i for i, n in enumerate(NAMES)}
CODE0 = 10                      # designed solids: UV (-(CODE0 + i), -(CODE0 + i)) is finish NAMES[i]


def code(name):
    """The UV value that marks a designed solid's faces with a finish."""
    return float(-(CODE0 + F[name]))


def srgb_to_lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _sample(img, uv):
    """Bilinear lookup of an image (rows from the top, glTF UVs) at uv."""
    H, W = img.shape[:2]
    x = np.clip(uv[:, 0] % 1.0 * W - 0.5, 0, W - 1.001)
    y = np.clip(uv[:, 1] % 1.0 * H - 0.5, 0, H - 1.001)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy) + img[y0 + 1, x0] * (1 - fx) * fy
            + img[y0 + 1, x0 + 1] * fx * fy)


class Surface:
    """A welded part surface with per-vertex measures (see the module docstring). Arrays are per welded vertex."""

    def __init__(self, P, T, used, faces, tex):
        self.V = P[used, :3].astype(np.float64)
        self.F = faces
        n = len(self.V)
        uvc = P[T.ravel(), 3:5].astype(np.float64)
        cap = (np.abs(uvc + 1) < 0.5).all(1)
        des = uvc[:, 0] < -1.5
        meshy = ~cap & ~des
        vid = faces.ravel()
        # kind: 0 Meshy surface, 1 cut face / peg / hole, 2 designed solid
        kind = np.ones(n, np.int8)
        kind[vid[des]] = 2
        kind[vid[meshy]] = 0
        self.kind = kind
        self.code = np.full(n, -1, np.int16)
        dc = np.round(-uvc[des, 0]).astype(int)
        self.code[vid[des]] = np.where(dc >= CODE0, dc - CODE0, F["brass"])      # -2 (knuckles) paint as brass
        # Meshy's colour under each vertex (linear), averaged over its corners
        acc, cnt = np.zeros((n, 3)), np.zeros(n)
        if tex is not None and meshy.any():
            col = srgb_to_lin(_sample(tex, uvc[meshy]))
            np.add.at(acc, vid[meshy], col)
            np.add.at(cnt, vid[meshy], 1)
        self.alb = acc / np.maximum(cnt, 1)[:, None]
        self.L = self.alb @ np.array([0.2126, 0.7152, 0.0722])
        # normals and vertex areas
        A, B, C = (self.V[faces[:, k]] for k in range(3))
        fn = np.cross(B - A, C - A)
        self.fa = np.linalg.norm(fn, axis=1) / 2
        vn = np.zeros((n, 3))
        va = np.zeros(n)
        for k in range(3):
            np.add.at(vn, faces[:, k], fn)
            np.add.at(va, faces[:, k], self.fa / 3)
        self.vn = vn / (np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12)
        self.va = va
        self.edge = float(np.linalg.norm(B - A, axis=1).mean())
        e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
        e = np.unique(np.sort(e, 1), axis=0)
        self.E = e
        Ad = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
        self.A = (Ad + Ad.T).astype(np.float32)
        self.deg = np.asarray(self.A.sum(1)).ravel() + 1
        # brightness round each vertex (Meshy surface only), and a curvature
        w = (kind == 0).astype(float)
        it = self.iters(1.2)
        self.lm = self.diffuse(self.L * w, it) / np.maximum(self.diffuse(w, it), 1e-6)
        self.lm = np.maximum(self.lm, 1e-4)
        ns = self.diffuse(self.vn, self.iters(0.8))
        ns /= np.linalg.norm(ns, axis=1, keepdims=True) + 1e-12
        self.curv = self.diffuse(1 - np.einsum("ij,ij->i", self.vn, ns), self.iters(0.5))
        self.lab = None

    def iters(self, mm):
        """Diffusion steps that spread a value over about `mm` of surface."""
        return max(1, int((mm / self.edge) ** 2 / 2))

    def diffuse(self, x, iters):
        d = self.deg[:, None] if x.ndim == 2 else self.deg
        for _ in range(iters):
            x = (x + self.A @ x) / d
        return x

    def near(self, mask, mm):
        """Vertices within about `mm` of surface from a masked vertex."""
        x = mask.astype(np.float32)
        for _ in range(max(1, int(round(mm / self.edge)))):
            x = np.maximum(x, (self.A @ x > 0).astype(np.float32))
        return x > 0


def panels(s, angle=8.0, curv_max=0.3, min_area=0.6):
    """Flood the surface between creases. Sets s.lab (panel per vertex, -1 on creases and specks) and returns the panels'
    measures: area mm2, mean normal (unit), flatness (length of the area-weighted mean normal, 1 = flat), centroid,
    Meshy brightness, and the panel's extent along its own principal axes."""
    e = s.E
    a, b = e[:, 0], e[:, 1]
    ok = ((s.vn[a] * s.vn[b]).sum(1) > np.cos(np.radians(angle))) & (s.curv[a] < curv_max) & (s.curv[b] < curv_max)
    ok &= (s.kind[a] != 1) & (s.kind[b] != 1) & (s.kind[a] == s.kind[b])
    ok &= (s.code[a] == s.code[b])
    n = len(s.V)
    G = sparse.coo_matrix((np.ones(ok.sum()), (a[ok], b[ok])), shape=(n, n))
    _, lab = connected_components(G, directed=False)
    lab = split_bent(s, lab, a[ok], b[ok])
    area = np.bincount(lab, s.va)
    lab = np.where(area[lab] >= min_area, lab, -1)
    lab[s.kind == 1] = -1
    ids, lab2 = np.unique(lab, return_inverse=True)
    lab2 = lab2 - (1 if ids[0] == -1 else 0)
    lab2[lab == -1] = -1
    s.lab = lab2
    m = lab2 >= 0
    k = lab2[m]
    npan = int(k.max()) + 1 if m.any() else 0
    w = s.va[m]
    area = np.bincount(k, w, npan)
    nsum = np.stack([np.bincount(k, w * s.vn[m, i], npan) for i in range(3)], 1)
    flat = np.linalg.norm(nsum, axis=1) / np.maximum(area, 1e-9)
    nrm = nsum / (np.linalg.norm(nsum, axis=1, keepdims=True) + 1e-12)
    cen = np.stack([np.bincount(k, w * s.V[m, i], npan) for i in range(3)], 1) / np.maximum(area, 1e-9)[:, None]
    lum = np.bincount(k, w * s.lm[m], npan) / np.maximum(area, 1e-9)
    kind = np.bincount(k, w * (s.kind[m] == 2), npan) / np.maximum(area, 1e-9) > 0.5
    # Shape: the spread of the panel's normals. A plate's normals agree (one big eigenvalue); a ring, band or tube has its
    # normals in a plane round an axis (two big, the third near 0, its eigenvector the axis); a bolt head or dome has
    # them all over. `width` is the panel's length along that axis, which tells a narrow ring from a long tube.
    nn = s.vn[m]
    cov = np.zeros((npan, 3, 3))
    for i in range(3):
        for j in range(i, 3):
            cov[:, i, j] = cov[:, j, i] = np.bincount(k, w * nn[:, i] * nn[:, j], npan)
    cov /= np.maximum(area, 1e-9)[:, None, None]
    lam, vec = np.linalg.eigh(cov)                  # ascending
    axis = vec[:, :, 0]
    ext, width = np.zeros(npan), np.zeros(npan)
    order = np.argsort(k, kind="stable")
    starts = np.searchsorted(k[order], np.arange(npan + 1))
    Vm = s.V[m][order]
    for i in range(npan):
        q = Vm[starts[i]:starts[i + 1]]
        if len(q) > 3:
            ext[i] = float(np.linalg.norm(q.max(0) - q.min(0)))
            t = q @ axis[i]
            width[i] = float(t.max() - t.min())
    return {"n": npan, "area": area, "normal": nrm, "flat": flat, "centre": cen, "lum": lum, "designed": kind,
            "extent": ext, "lam": lam[:, ::-1], "axis": axis, "width": width}


def split_bent(s, lab, ea, eb, flat_min=0.8, area_min=20.0, kmax=4, seed=3):
    """Panels that flooded across a smooth bend (a shoulder plate running over the top into the side) come out with a
    low flatness and would paint as one. Split each such panel by k-means on its normals (the smallest k whose parts
    are each flat), then by connectivity within each part. ea, eb: the edges the flood used."""
    n = len(lab)
    area = np.bincount(lab, s.va)
    nsum = np.stack([np.bincount(lab, s.va * s.vn[:, i]) for i in range(3)], 1)
    flat = np.linalg.norm(nsum, axis=1) / np.maximum(area, 1e-9)
    bent = np.flatnonzero((area >= area_min) & (flat < flat_min))
    if not len(bent):
        return lab
    rng = np.random.default_rng(seed)
    sub = lab.copy()
    nxt = lab.max() + 1
    order = np.argsort(lab, kind="stable")
    starts = np.searchsorted(lab[order], np.arange(lab.max() + 2))
    for p in bent:
        idx = order[starts[p]:starts[p + 1]]
        N, w = s.vn[idx], s.va[idx]
        best = None
        for k in range(2, kmax + 1):
            C = N[rng.choice(len(N), k, replace=False)]
            for _ in range(12):
                g = np.argmax(N @ C.T, 1)
                C = np.stack([(N[g == j] * w[g == j, None]).sum(0) for j in range(k)])
                C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-12
            g = np.argmax(N @ C.T, 1)
            fl = [np.linalg.norm((N[g == j] * w[g == j, None]).sum(0)) / max(w[g == j].sum(), 1e-9) for j in range(k)]
            best = g
            if min(fl) >= 0.9:
                break
        sub[idx] = nxt + best
        nxt += kmax
    # connectivity within each new label
    keep = sub[ea] == sub[eb]
    G = sparse.coo_matrix((np.ones(keep.sum()), (ea[keep], eb[keep])), shape=(n, n))
    _, cc = connected_components(G, directed=False)
    return cc


def shapes(pan, ring_width=1.6):
    """Boolean masks over panels: `ring` (a band round an axis, narrower than ring_width mm), `tube` (the same, longer),
    `knob` (small and curved every way: bolt heads, rivets, caps)."""
    l1, l2, l3 = pan["lam"].T
    round_ = (l2 >= 0.33) & (l3 <= 0.12)
    ring = round_ & (pan["width"] <= ring_width)
    tube = round_ & (pan["width"] > ring_width)
    knob = (pan["area"] < 3.0) & (l3 > 0.12)
    return ring, tube, knob


def finish_arrays(s, fin, tone=None):
    """Per-vertex linear colour, roughness, metallic and detail strength from per-vertex finish indices. Designed
    vertices take their own finish (their UV code) unless `fin` already set them. `tone` multiplies the colour (per-panel
    variety)."""
    fin = np.asarray(fin, int).copy()
    des = (s.kind == 2) & (fin < 0)
    fin[des] = s.code[des]
    fin[fin < 0] = F["iron"]
    tab = np.array([srgb_to_lin(np.array(FINISHES[nm][0]) / 255.0) for nm in NAMES])
    rgb = tab[fin]
    if tone is not None:
        rgb = rgb * tone[:, None]
    rough = np.array([FINISHES[nm][1] for nm in NAMES])[fin]
    metal = np.array([FINISHES[nm][2] for nm in NAMES])[fin]
    detail = np.array([FINISHES[nm][3] for nm in NAMES])[fin] * (s.kind == 0)
    return rgb, rough, metal, detail


def corner_arrays(s, P, T, rgb, rough, metal, detail):
    """Per face corner (len(T) * 3) values from per-vertex ones, with every designed face taking its own finish at all
    three corners. A welded vertex where a brass rivet meets a red plate has one finish; spread over a plate's few big
    triangles it would tint the whole plate, so the bake reads the finish per corner instead."""
    F_ = s.F.ravel()
    rgb, rough, metal, detail = rgb[F_], rough[F_], metal[F_], detail[F_]
    u = P[T.ravel(), 3]
    des = u < -(CODE0 - 0.5)
    if des.any():
        fi = np.clip(np.round(-u[des]).astype(int) - CODE0, 0, len(NAMES) - 1)
        tab = np.array([srgb_to_lin(np.array(FINISHES[nm][0]) / 255.0) for nm in NAMES])
        rgb = rgb.copy()
        rgb[des] = tab[fi]
        rough, metal, detail = rough.copy(), metal.copy(), detail.copy()
        rough[des] = np.array([FINISHES[nm][1] for nm in NAMES])[fi]
        metal[des] = np.array([FINISHES[nm][2] for nm in NAMES])[fi]
        detail[des] = 0.0
    return rgb, rough, metal, detail


def panel_tone(s, seed=7, spread=0.10):
    """A small brightness change per panel (weathering varies plate to plate), 1 on creases."""
    rng = np.random.default_rng(seed)
    t = 1 + spread * (rng.random(int(s.lab.max()) + 2) * 2 - 1)
    out = np.ones(len(s.V))
    m = s.lab >= 0
    out[m] = t[s.lab[m]]
    return out


def detail_preview(s, gamma=0.75, lo=0.45, hi=1.7):
    """The bake's texture detail, per vertex (for quick previews without Blender)."""
    d = np.clip((np.maximum(s.L, 1e-5) / s.lm) ** gamma, lo, hi)
    return np.where(s.kind == 0, d, 1.0)
