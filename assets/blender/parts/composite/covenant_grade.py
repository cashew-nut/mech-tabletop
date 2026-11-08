"""Grade a Meshy retexture to the Iron Covenant finish before it is baked (numpy, scipy, pillow; no Blender).

    python3 -I covenant_grade.py WORK [--preview OUT.jpg]      # or MODEL=sentinel split.py WORK, which calls it (sentinel.prepare)

Meshy's retexture of the Sentinel came out dusty: khaki trim (about 104, 88, 69 once baked) that is only half metal and
rough (0.63), brick-pink cloth, and warm grey-brown plate speckled with dust. The concept art, the part sheets and the
Paladin (the faction's reference walker, docs/style-bible/covenant.md) are black enamel with bright worn gold and crimson
cloth. This sorts every texel of the Meshy textures softly into gold, red, light cloth or dark plate by its hue, saturation
and brightness, and moves each class to the Paladin's baked values (gold 154, 125, 79 at roughness 0.37; crimson; neutral
black at roughness 0.42), keeping each texel's brightness relative to its class so filigree, wear and shading survive.
The dark plate's dust is calmed by pulling each texel part of the way to its neighbourhood's mean.

The originals are kept as tex_0_meshy.jpg and tex_1_meshy.jpg the first time; every run grades from them, so it can be run
again safely. Nothing here knows about parts: build.py bakes the graded textures as it would Meshy's.
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


def grade_work(work):
    work = Path(work)
    for k in (0, 1):
        orig = work / f"tex_{k}_meshy.jpg"
        if not orig.exists():
            orig.write_bytes((work / f"tex_{k}.jpg").read_bytes())
    base = np.asarray(Image.open(work / "tex_0_meshy.jpg").convert("RGB")).astype(np.float32) / 255
    mr = np.asarray(Image.open(work / "tex_1_meshy.jpg").convert("RGB")).astype(np.float32) / 255
    b2, mr2, stats = grade(base, mr)
    Image.fromarray((b2 * 255 + 0.5).astype(np.uint8)).save(work / "tex_0.jpg", quality=96)
    Image.fromarray((mr2 * 255 + 0.5).astype(np.uint8)).save(work / "tex_1.jpg", quality=96)
    print("graded the Meshy textures to the Covenant finish:", stats, flush=True)
    return b2


if __name__ == "__main__":
    a = sys.argv[1:]
    b2 = grade_work(a[0])
    if "--preview" in a:
        orig = Image.open(Path(a[0]) / "tex_0_meshy.jpg").convert("RGB").resize((1024, 1024))
        new = Image.fromarray((b2 * 255 + 0.5).astype(np.uint8)).resize((1024, 1024))
        sheet = Image.new("RGB", (2048, 1024))
        sheet.paste(orig, (0, 0))
        sheet.paste(new, (1024, 0))
        sheet.save(a[a.index("--preview") + 1], quality=88)
