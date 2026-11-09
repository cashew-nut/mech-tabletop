"""The Ashen Foundries Artillery's settings for the composite pipeline (MODEL=artillery; numpy only). See README.md.

Second whole-body walker from the Meshy pipeline (docs/model-pipeline-plan.md): Luke's approved concept art
(docs/concept-art/artillery/) went to one multi-image-to-3D mesh and one retexture (project folder
meshy-sources/artillery/model/), and this module cuts it into closed parts the way the Sentinel was cut. What is specific
to this figure:

* **Axes.** cut.py extract puts the figure z up, facing -Y, the walker's left +X. Meshy normalised the model to y -1..1
  (the howitzer's length), so z runs -0.80 (sole) to 0.80 (smokestack tops). The figure's centre line is x = 0.09
  (stacks, feet and torso agree on it), so CX = 0.09.
* **Print scale.** Sole to the torso roof (z = 0.50) is the bulwark frame's 42 kit mm, so S = 42 / 1.30 kit mm per unit;
  at Luke's 1.5x the stack tops stand about 78 mm.
* **Three legs.** Meshy read the three-quarter "side" view as a third, rear leg (x -0.4, y 0.4..1.0). It is dropped
  (label _rear); the walker keeps the two front legs, the left one cut and mirrored for the right.
* **No head.** The mesh has no head (the concept's is hidden behind the howitzer's breech), so the helm is the armoured
  cupola dome on top of the torso, just behind the breech.
* **The howitzer** stays with the torso (cradle and barrel are one solid with it, 80 mm front to back at print scale: the
  barrel is a thin tube). The back is the two smokestacks, the rear ammunition pack and the roof plates, one solid on the
  torso's roof on one peg. The cupola plugs into the back's roof.
* **Arms.** The left arm holds an artillery shell in a clamp, the forearm level and pointing forward (like the Sentinel's
  gun arm); it is mirrored for the right. The figure's own right arm (a heavy autocannon-like block hanging from the
  elbow) is not cut: it needs a peg design of its own (see docs/artillery-composite/README.md).
"""
import numpy as np

NAME = "artillery"
TUNE = "foundries/artillery"   # not used: the joints are measured below (this model measures its own)
CX = 0.09
PRINT_SCALE = 1.5               # Luke, 2026-11-01: collector scale is 1.5x the game
FOOT_Z = -0.8033                # z of the sole
S = 42 / 1.30                   # kit mm per figure unit (sole to torso roof 42 mm, the bulwark frame)
BASE = 3.0
H = 0.25 / (S * PRINT_SCALE)    # voxel size in figure units (0.25 mm at print scale)
CLOTH_T = 0.02

MAGNETS = ((1.5, 2.0), (1.0, 1.0), (0.5, 1.0))
RADII = (3.0, 2.75, 2.5, 2.2, 2.0, 1.75, 1.5, 1.3, 1.15, 1.0, 0.85, 0.75, 0.65, 0.55)
LENGTHS = (3.5, 3.0, 2.6, 2.2, 1.8, 1.5, 1.2, 1.0)
PREFER_MAGNET = True
STRICT = True
CLEAR_MIRRORED = True
CRUMB = 2.0

# Bones, figure units, x centred. Sided bones are tested on |x|: labels are mirror images, and the walker's left is +X.
BONES_C = {
    "torso": ((0.0, 0.12, 0.02), (0.0, 0.12, 0.36), 0.33),
    "pelvis": ((0.0, 0.10, -0.32), (0.0, 0.10, -0.12), 0.32),
}
BONES_S = {
    "pauldron": ((0.40, 0.28, 0.32), (0.52, 0.28, 0.34), 0.18),
    "arm": ((0.43, 0.22, 0.28), (0.61, 0.22, 0.0), 0.12),
    "forearm": ((0.61, 0.22, 0.0), (0.61, -0.15, -0.10), 0.15),
    "hand": ((0.61, -0.18, -0.10), (0.61, -0.50, -0.12), 0.13),
    "thigh": ((0.30, 0.12, -0.22), (0.47, -0.15, -0.45), 0.17),
    "shin": ((0.47, -0.15, -0.45), (0.53, -0.15, -0.66), 0.15),
}
PAULDRON_BOX = ((0.28, 0.80), (0.0, 0.60), (0.22, 0.50))     # |x|, y, z ranges of the shoulder plate
FOOT_TOP = -0.62                                              # below this, everything on a side is its foot
REAR_LEG = ((-0.75, 0.10), (0.48, 1.2), (-0.9, -0.05))       # x, y, z of Meshy's invented third leg (dropped)
HELM = ((0.0, 0.08, 0.50), (0.11, 0.13, 0.085))              # cupola dome: centre, radii
ROOF_Z = 0.43

PARTS = {
    "torso": ["torso"], "pelvis": ["pelvis"], "helm": ["helm"], "back": ["back"],
    "pauldron": ["pauldron_L"], "arm": ["arm_L"], "forearm": ["forearm_L"], "hand": ["hand_L"],
    "thigh": ["thigh_L"], "shin": ["shin_L"], "foot": ["foot_L"],
    "_pauldron_R": ["pauldron_R"], "_arm_R": ["arm_R"], "_forearm_R": ["forearm_R"], "_hand_R": ["hand_R"],
    "_thigh_R": ["thigh_R"], "_shin_R": ["shin_R"], "_foot_R": ["foot_R"], "_rear": ["rear"],
}

JOINTS = {
    "pelvis": (0.0, 0.10, -0.12), "spine": (0.0, 0.10, 0.0), "chest": (0.0, 0.10, 0.30),
    "neck": (0.0, 0.08, 0.44), "head": (0.0, 0.08, 0.49),
    "shoulder": (0.43, 0.22, 0.28), "elbow": (0.61, 0.22, 0.0), "wrist": (0.61, -0.15, -0.10),
    "hip": (0.30, 0.12, -0.22), "knee": (0.47, -0.15, -0.45), "ankle": (0.53, -0.15, -0.66),
}

# part: (kit component it publishes as, joint its origin sits on, parent part it plugs into)
TREE = {
    "pelvis": ("pelvis", "pelvis", None),
    "thigh": ("thigh", "hip", "pelvis"),       # before the torso: the hips get first pick of the pelvis for their holes
    "torso": ("torso", "spine", "pelvis"),
    "back": ("back", "chest", "torso"),
    "helm": ("helm", "head", "back"),          # the cupola sits on the roof plates, which are part of the back
    "pauldron": ("pauldron", "shoulder", "torso"),
    "arm": ("arm", "shoulder", "pauldron"),
    "forearm": ("forearm", "elbow", "arm"),
    "hand": ("hand", "wrist", "forearm"),
    "shin": ("shin", "knee", "thigh"),
    "foot": ("foot", "ankle", "shin"),
}
SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot"}

# part: (game triangles, texture size)
BUDGET = {
    "torso": (11000, 1024), "pelvis": (7000, 1024), "helm": (2500, 512), "back": (12000, 1024),
    "pauldron": (7500, 1024), "arm": (2200, 512), "forearm": (5500, 1024), "hand": (3500, 768),
    "thigh": (4500, 768), "shin": (4500, 768), "foot": (3000, 512),
}
LABEL = {
    "pelvis": "Pelvis", "torso": "Torso + howitzer", "helm": "Cupola", "back": "Stacks + ammo pack",
    "pauldron": "Pauldron", "arm": "Upper arm", "forearm": "Shell arm", "hand": "Clamp + shell", "thigh": "Thigh",
    "shin": "Shin", "foot": "Foot",
}
EXPLODE, EXPLODE_DROP = 11.0, 4.0
POSE = {
    "arm_L": (-25, 0, 0), "forearm_L": (-30, 0, 0), "helm": (0, 0, -20),
    "thigh_L": (-12, 0, 0), "shin_L": (15, 0, 0), "foot_L": (-3, 0, 0),
}


def seg_d(P, A, B):
    A, B = np.array(A, np.float32), np.array(B, np.float32)
    AB = B - A
    t = np.clip(((P - A) @ AB) / (AB @ AB), 0, 1)
    return np.linalg.norm(P - (A + t[:, None] * AB), axis=1)


def label_points(P, _cloth=None):
    """Label points P (figure units, x centred). Sided bones are tested on |x|, so labels are mirror images."""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    a = np.abs(x)
    Pm = np.stack([a, y, z], 1)
    cn, sn = list(BONES_C), list(BONES_S)
    names = cn + [k + "_L" for k in sn] + [k + "_R" for k in sn]
    D = [seg_d(P, *BONES_C[k][:2]) - BONES_C[k][2] for k in cn]
    D += [seg_d(Pm, *BONES_S[k][:2]) - BONES_S[k][2] for k in sn]
    D = np.stack(D, 1)
    lab = D.argmin(1).astype(np.int16)
    del D
    right = (lab >= len(cn)) & (x < 0)
    lab[right] += len(sn)

    def setl(mask, name):
        if name not in names:
            names.append(name)
        lab[mask] = names.index(name)

    L = x >= 0
    (px0, px1), (py0, py1), (pz0, pz1) = PAULDRON_BOX
    paul = (a >= px0) & (a < px1) & (y >= py0) & (y < py1) & (z >= pz0) & (z < pz1)
    setl(paul & L, "pauldron_L")
    setl(paul & ~L, "pauldron_R")
    setl((z < FOOT_TOP) & L & (a > 0.2), "foot_L")
    setl((z < FOOT_TOP) & ~L & (a > 0.2), "foot_R")
    # the howitzer, its cradle, the roof plates, the stacks and the rear pack are one part
    (hc, hr) = HELM
    helm = (((x - hc[0]) / hr[0]) ** 2 + ((y - hc[1]) / hr[1]) ** 2 + ((z - hc[2]) / hr[2]) ** 2 < 1) & (z > 0.44)
    barrel = (y < -0.20) & (a < 0.20) & (z > 0.28)
    roof = (z > ROOF_Z) & (a < 0.36)
    pack = (y > 0.42) & (z > 0.0) & (a < 0.40)
    stacks = (z > 0.55) & (y > 0.30) & (a < 0.34)
    back = barrel | roof | pack | stacks
    setl(back, "back")
    setl(helm, "helm")
    # Meshy's invented third leg
    (rx0, rx1), (ry0, ry1), (rz0, rz1) = REAR_LEG
    setl((x >= rx0) & (x < rx1) & (y >= ry0) & (y < ry1) & (z >= rz0) & (z < rz1) & ~back, "rear")
    return lab, names


# ---- polish pass (2026-11-09, artillery_polish.py): clawed feet, rear plate, no cable or chains, a real cupola -------
from artillery_polish import design, CHANGED  # noqa: E402,F401


# ---- paint (paint.py): the Brute's scheme, plate by plate --------------------------------------------------------------
BARREL = ((0.003, -0.60, 0.447), (0.007, -0.971, 0.238))     # a point on the howitzer's axis and its direction (figure units)
STACKS_XY = ((0.115, 0.545), (-0.115, 0.545))                # the two smokestacks' centres (x, y), figure units
RED_SHARE = {"torso": 0.22, "pauldron": 0.40, "pelvis": 0.15, "back": 0.06, "thigh": 0.22, "shin": 0.32,
             "forearm": 0.10, "arm": 0.0, "helm": 0.0, "hand": 0.0, "foot": 0.0}   # share of a part's Meshy surface
RED_MIN = {"pauldron": 6.0, "torso": 8.0, "pelvis": 6.0, "back": 8.0, "thigh": 5.0, "shin": 4.0, "forearm": 5.0,
           "arm": 99.0, "helm": 3.0, "hand": 99.0, "foot": 3.0}


def _axis_mm():
    from layout import to_mm
    p = to_mm(np.array(BARREL[0], float))
    d = np.array(BARREL[1], float)
    return p, d / np.linalg.norm(d)


def _outward(k, c):
    """Unit vectors from a part's core to points c (print mm): the bone for limbs, a vertical axis for centre parts."""
    from layout import joint
    if k in SIDED and TREE[k][2] is not None:
        A = np.array(joint(TREE[k][1]))
        child = [q for q, v in TREE.items() if v[2] == k]
        B = np.array(joint(TREE[child[0]][1])) if child else A + np.array([0.0, -6.0, -6.0])
        if np.linalg.norm(B - A) < 1:
            B = A + np.array([0.0, -6.0, -6.0])
        AB = B - A
        t = np.clip(((c - A) @ AB) / (AB @ AB), 0, 1)
        d = c - (A + t[:, None] * AB)
    else:
        mid = np.array([0.0, np.median(c[:, 1]) if len(c) else 0.0, 0.0])
        d = c - mid
        d[:, 2] = 0
    return d / (np.linalg.norm(d, axis=1, keepdims=True) + 1e-9)


def _barrel_r(c):
    """Distance (mm) of points c from the howitzer's axis, and how far along it they are past the breech (mm)."""
    p, d = _axis_mm()
    v = c - p
    t = v @ d
    return np.linalg.norm(v - t[:, None] * d, axis=1), t


def paint(k, s, pan):
    """Finish per vertex for part k (paint.py's Surface s and its panels), in the Brute's scheme: blackened iron for the
    frame, red lacquer on the big armour plates that face out (the part sheet's plates), worn brass on rings, collars,
    bolt heads and the shell, gun steel on the howitzer's tube, soot in the stack mouths. Designed solids keep the finish
    they were built with (artillery_polish.py)."""
    import paint as PA
    F = PA.F
    n = pan["n"]
    fin_p = np.full(n, F["iron"], int)
    stencil_i = None
    if n:
        c, nrm, area, flat = pan["centre"], pan["normal"], pan["area"], pan["flat"]
        out = _outward(k, c)
        face_out = (nrm * out).sum(1)
        up = nrm[:, 2]
        ring, tube, knob = PA.shapes(pan)
        plate = (area >= RED_MIN.get(k, 99.0)) & (flat >= 0.85) & ((face_out >= 0.30) | (up >= 0.8))
        # the biggest plates first, up to the part's red share of its surface (the Brute is mostly iron: red is the
        # armour you see first, not every flat face)
        cand = np.flatnonzero(plate)
        cand = cand[np.argsort(-area[cand])]
        total = s.va[s.kind == 0].sum()
        take = cand[np.cumsum(area[cand]) <= RED_SHARE.get(k, 0.0) * total + 1e-9]
        if len(cand) and not len(take) and RED_SHARE.get(k, 0.0) > 0:
            take = cand[:1]
        fin_p[take] = F["red"]
        # rings and collars: narrow bands round an axis; bolt heads and caps
        fin_p[ring & (area >= 0.8) & (area < 30)] = F["brass"]
        fin_p[knob & (area >= 0.25)] = F["brass"]
        if k == "torso":            # the howitzer: steel tube, brass bands, iron muzzle brake
            r, t = _barrel_r(c)
            on = (r < BARREL_R) & (t > 0)
            fin_p[on] = F["steel"]
            fin_p[on & ring] = F["brass"]
            fin_p[on & (t > MUZZLE_T)] = F["iron"]
        if k == "back":             # the stacks: iron, brass lips, soot inside
            from layout import to_mm
            for sx, sy in STACKS_XY:
                q = to_mm(np.array([sx, sy, 0.0]))
                d = np.hypot(c[:, 0] - q[0], c[:, 1] - q[1])
                lip = (d < STACK_R) & (c[:, 2] > STACK_LIP_Z)
                fin_p[lip & (fin_p == F["red"])] = F["iron"]
                fin_p[lip & (ring | (up > 0.7))] = F["brass"]
                fin_p[(d < STACK_R * 0.55) & (c[:, 2] > STACK_LIP_Z) & (up < -0.2)] = F["soot"]
        if k in STENCILS:          # the part sheet's white unit marks on a red plate
            text, side, hf = STENCILS[k]
            red_ = np.flatnonzero((fin_p == F["red"]) & (nrm[:, 1] < -0.7 if k == "torso" else fin_p == F["red"])
                                  & ((c[:, 0] * side > 1.0) if side else True))
            if len(red_):
                stencil_i = red_[np.argmax(area[red_])]
        if k == "hand":             # the shell: a brass casing and ogive ahead of the clamp
            y0, y1 = s.V[:, 1].min(), s.V[:, 1].max()
            fin_p[c[:, 1] < y0 + 0.45 * (y1 - y0)] = F["brass"]
    fin = np.full(len(s.V), -1, int)
    m = s.lab >= 0
    fin[m] = fin_p[s.lab[m]]
    fin[(s.kind == 0) & ~m] = F["iron"]
    # worn brass on the sharp outer edges (the Brute's gilt edge wear): crease vertices that stand proud of their
    # neighbours, next to a painted or iron plate
    nb = (s.A @ s.V) / np.maximum(s.deg - 1, 1)[:, None]
    proud = ((s.V - nb) * s.vn).sum(1)
    edge = (s.kind == 0) & ~m & (proud > EDGE_PROUD * s.edge)
    fin[edge] = F["brass"]
    if stencil_i is not None:       # build.py reads s.stencil: atlas UVs per vertex and the plate they are on
        text, side, hf = STENCILS[k]
        on = s.lab == stencil_i
        s.stencil = (stencil(s.V, on, pan["normal"][stencil_i], text, hf), on)
    des = s.kind == 2
    fin[des] = s.code[des]           # designed solids: their own finish
    tone = PA.panel_tone(s)
    return fin, tone


# part: (text, side (-1 the walker's right, 1 its left, 0 either), letter height as a share of the plate's height)
STENCILS = {"torso": ("107", -1, 0.62), "pauldron": ("III", 0, 0.5)}
GLYPHS = {      # 3 x 5 cells, rows from the top; stencil gaps are left where a stroke would close a loop
    "1": ["01", "11", "01", "01", "01"], "0": ["111", "101", "101", "101", "111"], "7": ["111", "001", "010", "010", "010"],
    "I": ["1", "1", "1", "1", "1"],
}


ATLAS_W, ATLAS_ROW = 1024, 256         # the stencil atlas: one row per text in STENCILS, white glyphs on black


def _glyph_mask(text, a, b):
    """Inside the stencilled text at glyph coordinates (a across, b down, in cells; 5 cells tall)."""
    hit = np.zeros(np.shape(a), bool)
    x0 = 0.0
    for ch in text:
        g = GLYPHS[ch]
        w = len(g[0])
        fa, fb = a - x0, b
        col, row = np.floor(fa).astype(int), np.floor(fb).astype(int)
        for r in range(5):
            for cc in range(w):
                if g[r][cc] != "1":
                    continue
                # a stroke fills its cell but for a thin margin, so the cells of one stroke join and the gaps between
                # strokes read as stencil bridges
                right = 1.0 if cc + 1 < w and g[r][cc + 1] == "1" else 0.94
                hit |= (row == r) & (col == cc) & (fa - cc > 0.06) & (fa - cc < right) & (fb - r >= 0) & (fb - r < 1)
        x0 += w + 0.8
    return hit


def _row_frame(text):
    """(cells across, pixel size of a cell, x offset px) for text in its atlas row."""
    span = sum(len(GLYPHS[ch][0]) for ch in text) + 0.8 * (len(text) - 1)
    cell = min(0.86 * ATLAS_ROW / 5.0, 0.94 * ATLAS_W / span)
    return span, cell, 0.5 * (ATLAS_W - span * cell)


def stencil_atlas(path):
    """Write the stencil atlas PNG (rows in STENCILS order from the top)."""
    from PIL import Image
    texts = [v[0] for v in STENCILS.values()]
    img = np.zeros((ATLAS_ROW * len(texts), ATLAS_W), np.uint8)
    yy, xx = np.mgrid[0:ATLAS_ROW, 0:ATLAS_W] + 0.5
    for i, t in enumerate(texts):
        span, cell, x0 = _row_frame(t)
        y0 = 0.5 * (ATLAS_ROW - 5 * cell)
        m = _glyph_mask(t, (xx - x0) / cell, (yy - y0) / cell)
        img[i * ATLAS_ROW:(i + 1) * ATLAS_ROW] = m * 255      # row i from the top (Blender: v = 1 at the top)
    Image.fromarray(img).save(path)
    return path


def stencil(V, on, n, text, hf):
    """The stencil atlas UV of every vertex of the plate `on` (centred on the plate, `hf` of its height tall, along the
    plate's own axes: u level across it, v up it). UVs are linear in position, so the text stays crisp however coarse
    the plate's triangles are (build.py samples the atlas per pixel)."""
    n = n / np.linalg.norm(n)
    u = np.cross([0.0, 0.0, 1.0], n)
    if np.linalg.norm(u) < 1e-3:
        u = np.array([1.0, 0.0, 0.0])
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    q = V[on]
    pu, pv = q @ u, q @ v
    cu, cv = 0.5 * (pu.min() + pu.max()), 0.5 * (pv.min() + pv.max())
    span, cpx, x0 = _row_frame(text)
    h = min(hf * (pv.max() - pv.min()), 0.78 * (pu.max() - pu.min()) / (span / 5.0))
    cell = h / 5.0
    a = (V @ u - cu + span * cell / 2) / cell                # glyph space: a across, b down
    b = (cv + h / 2 - V @ v) / cell
    row = list(STENCILS).index(next(k for k, t in STENCILS.items() if t[0] == text))
    nrow = len(STENCILS)
    x = (x0 + a * cpx) / ATLAS_W
    y_top = row * ATLAS_ROW + 0.5 * (ATLAS_ROW - 5 * cpx) + b * cpx           # px from the atlas top
    uv = np.stack([x, 1.0 - y_top / (ATLAS_ROW * nrow)], 1)
    return uv


PAINT_GLOW = True       # the cupola's vision slit and periscope glass glow (build.py's emissive bake)
GLOW_STRENGTH = 3.0
SHARP_DESIGNED = 30     # crisp rims on the designed plates in the bake source
GAME_SPLIT = 45         # and on the game copy (smooth normals bent the lames' big triangles into diagonal streaks)
NORMAL_SIZE = 1024      # sharper maps, as the Brute's polish
ORM_SIZE = 512
EDGE_PROUD = 0.12      # crease vertices this far proud of their neighbours (share of the mean edge) get worn brass
BARREL_R = 4.6          # mm: panels this close to the howitzer's axis (and ahead of the breech) are the barrel
MUZZLE_T = 26.0         # mm along the axis: the muzzle brake starts here
STACK_R = 3.6           # mm: the smokestacks' radius (lips and mouths within it)
STACK_LIP_Z = 76.0      # mm: the stack tops start here
