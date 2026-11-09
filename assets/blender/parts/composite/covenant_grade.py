"""Grade a Meshy retexture to the Iron Covenant finish, and light its painted lamps (numpy, scipy, pillow; no Blender).

    ~/bvenv/bin/python -I covenant_grade.py WORK [--preview OUT.jpg]   # the grade only; build.py calls surface_textures
                                                                     # through the model (sentinel.py), lamps included

Meshy's retexture of the Sentinel came out dusty: khaki trim (about 104, 88, 69 once baked) that is only half metal and
rough (0.63), brick-pink cloth, and warm grey-brown plate speckled with dust. The concept art, the part sheets and the
Paladin (the faction's reference walker, docs/style-bible/covenant.md) are black enamel with bright worn gold and crimson
cloth. This sorts every texel of the Meshy textures softly into gold, red, light cloth or dark plate by its hue, saturation
and brightness, and moves each class to the Paladin's baked values (gold 154, 125, 79 at roughness 0.37; crimson; neutral
black at roughness 0.42), keeping each texel's brightness relative to its class so filigree, wear and shading survive.
The dark plate's dust is calmed by pulling each texel part of the way to its neighbourhood's mean.

Meshy also painted the concept's lights: the eyes under the brow and the furnace window behind the chest grille are cream
texels. `glow_map` turns bright texels into furnace light (deep red-orange to amber) and `lamp_mask` keeps it to the
lamps the model names (sentinel.py's glow regions, found through the mesh's UVs), so the gold trim elsewhere stays unlit;
a lit texel's own colour goes to dark amber glass, so its light reads as amber rather than as pale paint.

Meshy's own tex_0.jpg and tex_1.jpg are never changed: the graded copies are tex_0_covenant.jpg and tex_1_covenant.jpg
and the light is tex_glow.png, all in WORK and made again whenever they are missing.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Targets, sRGB 0..1 (the Paladin's composite bake, measured from its torso and pauldron GLBs)
GOLD = np.array([156, 124, 76]) / 255
RED = np.array([128, 20, 18]) / 255
DARK = np.array([35, 36, 38]) / 255
# roughness, metallic per class (the light cloth keeps Meshy's)
GOLD_RM = (0.36, 0.55)
RED_RM = (0.62, 0.02)
DARK_RM = (0.42, 0.26)
CALM = 0.55          # dark plate: keep this share of each texel's difference from its neighbourhood (dust)
CALM_SIGMA = 3.0     # texels


def _ramp(x, a, b):
    """0 below a, 1 above b, smooth between (a > b gives the falling ramp)."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def hsv(c):
    mx, mn = c.max(-1), c.min(-1)
    d = mx - mn + 1e-6
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, (mx - mn) / (mx + 1e-6), mx


def weights(c):
    """Soft class weights (gold, red, light, dark) per texel, summing to 1. Gold needs to be bright as well as warm: the
    dusty plate is warm too, but darker, and a narrow brightness ramp (on a lightly smoothed value, against speckle) keeps
    the trim crisp against the black instead of smearing gold dust over the plates."""
    from scipy import ndimage as ndi
    h, s, v = hsv(c)
    vs = ndi.gaussian_filter(v, 0.8)
    wg = _ramp(h, 16, 26) * _ramp(h, 66, 56) * _ramp(s, 0.17, 0.27) * _ramp(vs, 0.25, 0.34)
    hr = np.minimum(h, 360 - h)                           # hue distance from red
    wr = _ramp(hr, 26, 14) * _ramp(s, 0.30, 0.45) * _ramp(v, 0.10, 0.18)
    wr *= 1 - wg
    wl = (1 - wg - wr) * _ramp(v, 0.42, 0.58) * _ramp(s, 0.30, 0.16)
    wd = np.clip(1 - wg - wr - wl, 0, 1)
    return wg, wr, wl, wd


def lum(c):
    return c @ np.array([0.2126, 0.7152, 0.0722])


def grade(base, mr):
    """base: sRGB float (n, n, 3); mr: Meshy's metallic-roughness texture (G roughness, B metallic). Returns both graded."""
    from scipy import ndimage as ndi
    wg, wr, wl, wd = weights(base)
    L = lum(base)

    def ref(w):
        return float((L * w).sum() / max(w.sum(), 1.0))

    # gold and red: the target colour, shaded by the texel's brightness relative to its class
    gold = GOLD * np.clip(L / ref(wg), 0.45, 1.5)[..., None] ** 0.8
    red = RED * np.clip(L / ref(wr), 0.40, 1.3)[..., None]
    # dark plate: calm the dust, then neutral black at the Paladin's level
    m = wd > 0.5
    k = ndi.gaussian_filter(m.astype(np.float32), CALM_SIGMA) + 1e-6
    Ls = ndi.gaussian_filter(np.where(m, L, 0.0), CALM_SIGMA) / k
    Lc = np.where(m, Ls + CALM * (L - Ls), L)
    dark = DARK * np.clip(Lc / ref(wd), 0.25, 2.6)[..., None]
    out = wg[..., None] * gold + wr[..., None] * red + wl[..., None] * base + wd[..., None] * dark
    rough, metal = mr[..., 1], mr[..., 2]

    def rm(w, target, src, spread):
        mean = float((src * w).sum() / max(w.sum(), 1.0))
        return np.clip(target + spread * (src - mean), 0.05, 1.0)
    r2 = (wg * rm(wg, GOLD_RM[0], rough, 0.4) + wr * rm(wr, RED_RM[0], rough, 0.4) + wl * rough
          + wd * rm(wd, DARK_RM[0], rough, 0.4))
    m2 = wg * GOLD_RM[1] + wr * RED_RM[1] + wl * metal + wd * DARK_RM[1]
    mr2 = mr.copy()
    mr2[..., 1], mr2[..., 2] = r2, m2
    stats = {k: round(float(w.mean()), 3) for k, w in (("gold", wg), ("red", wr), ("light", wl), ("dark", wd))}
    return np.clip(out, 0, 1), np.clip(mr2, 0, 1), stats


GLOW_LUM = (0.42, 0.80)   # luminance of the Meshy texel: no light below, full light above
# Light colour from cool to hot: deep red-orange to amber (the hottest stays amber, as the concept's eyes and grille; the
# Brute's foundry ramp ends white-gold, which read as cream paint on the Sentinel's pale painted window)
GLOW_RAMP = ((0.0, 0.35, 0.7, 1.0),
             ((0.12, 0.02, 0.0), (0.80, 0.24, 0.02), (1.0, 0.48, 0.08), (1.0, 0.68, 0.28)))
LAMP_BASE = np.array([0.20, 0.08, 0.025])   # a lit pane's own colour (dark amber glass), so its light reads as colour
LAMP_DARKEN = 0.85                          # how far a fully lit texel goes to LAMP_BASE


def glow_map(base):
    """Furnace light from Meshy's painted lamps: the brighter the texel, the hotter. Returns (light rgb, heat 0..1)."""
    t = np.clip((lum(base) - GLOW_LUM[0]) / (GLOW_LUM[1] - GLOW_LUM[0]), 0, 1) ** 1.3
    ts, cs = np.array(GLOW_RAMP[0]), np.array(GLOW_RAMP[1])
    g = np.stack([np.interp(t, ts, cs[:, i]) for i in range(3)], -1)
    return np.where(t[..., None] > 0, g, 0.0), t


def lamp_mask(work, where, n):
    """0..1 per texel: the texels of the figure's lamps. `where(points)` (figure units, as WORK/mesh.npz) weighs each
    triangle by its centre, and the weighed triangles are drawn into the texture's UV space (grown 1 texel for seams)."""
    from PIL import ImageDraw
    from scipy import ndimage as ndi
    d = np.load(Path(work) / "mesh.npz")
    V, F, UV = d["V"], d["F"], d["UV"]
    w = np.asarray(where(V[F].mean(1)))
    im = Image.new("L", (n, n), 0)
    dr = ImageDraw.Draw(im)
    for i in np.nonzero(w > 0.01)[0]:
        dr.polygon([(float(u) * n, float(v) * n) for u, v in UV[F[i]]], fill=int(round(255 * min(w[i], 1.0))))
    return ndi.grey_dilation(np.asarray(im), size=3).astype(np.float32) / 255


def surface_textures(work, lamps=None):
    """The graded base colour and metal/roughness for build.py, and with `lamps` (where the figure's lamps are, see
    lamp_mask) their light, tex_glow.png, with each lit texel's own colour darkened to amber glass: {image key: path}."""
    work = Path(work)
    paths = {"base": work / "tex_0_covenant.jpg", "mr": work / "tex_1_covenant.jpg"}
    if lamps is not None:
        paths["glow"] = work / "tex_glow.png"
    if all(p.exists() for p in paths.values()):
        return paths
    base = np.asarray(Image.open(work / "tex_0.jpg").convert("RGB")).astype(np.float32) / 255
    mr = np.asarray(Image.open(work / "tex_1.jpg").convert("RGB")).astype(np.float32) / 255
    b2, mr2, stats = grade(base, mr)
    if lamps is not None:
        g, t = glow_map(base)
        k = (lamp_mask(work, lamps, base.shape[0]) * t)[..., None]
        b2 = b2 * (1 - LAMP_DARKEN * k) + LAMP_BASE * (LAMP_DARKEN * k)
        Image.fromarray((np.clip(g * (k > 0), 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)).save(paths["glow"])
        stats["lamp texels"] = int((k > 0.05).sum())
    Image.fromarray((np.clip(b2, 0, 1) * 255 + 0.5).astype(np.uint8)).save(paths["base"], quality=96)
    Image.fromarray((mr2 * 255 + 0.5).astype(np.uint8)).save(paths["mr"], quality=96)
    print("graded the Meshy textures to the Covenant finish:", stats, flush=True)
    return paths


if __name__ == "__main__":
    a = sys.argv[1:]
    w = Path(a[0])
    for p in (w / "tex_0_covenant.jpg", w / "tex_1_covenant.jpg", w / "tex_glow.png"):
        p.unlink(missing_ok=True)
    out = surface_textures(w)
    if "--preview" in a:
        tiles = [Image.open(w / "tex_0.jpg").convert("RGB"), Image.open(out["base"]).convert("RGB")]
        sheet = Image.new("RGB", (1024 * len(tiles), 1024))
        for i, t in enumerate(tiles):
            sheet.paste(t.resize((1024, 1024)), (1024 * i, 0))
        sheet.save(a[a.index("--preview") + 1], quality=88)
