"""Recolour a baked Ashen Foundries base-colour texture to the Brute's scheme (blackened iron, red plate, worn brass).

usage: python3 -I foundry_palette.py IN.png OUT.png

The Artillery's Meshy retexture came out ochre and brown (the turnaround drifted), while the Brute is mostly blackened iron
with red lacquer plates and brass fittings (docs/style-bible/foundries.md, Palette). The UV charts of a baked part are small
islands, one per panel, so each island is sorted whole into plate, brass or iron by how bright and how warm it is, and
recoloured with the Brute's own texel colours (red about 135,22,17; brass 143,96,57; iron 32,30,28). The original shading is
kept as the brightness variation, so wear and chipped paint survive. Flat cut-face islands (the gunmetal the pipeline bakes
on pegs and joints) are left alone. The red texels are what the game's livery shader repaints, as on the Brute.
"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

# Brute texel colours (sampled from its torso and pauldron bakes), 0..1
RED = np.array([135, 22, 17]) / 255
BRASS = np.array([143, 96, 57]) / 255
IRON = np.array([32, 30, 28]) / 255

PLATE_SHARE = 0.15   # the brightest sixth of the painted area becomes red plate (the Brute: pauldrons 9% red, torso 1%, and black elsewhere)
SIGMA = 5.0          # texels
BRASS_SHARE = 0.08   # then the most saturated of the rest is brass


def recolour(img: Image.Image) -> Image.Image:
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255
    mx = a.max(2)
    mn = a.min(2)
    sat = (mx - mn) / (mx + 1e-6)
    valid = mx > 0.04
    # The UV charts are padded until they touch, so they cannot be told apart by connectivity. Smooth brightness and warmth
    # over a few texels instead (only over painted texels), which gives patches about a panel wide that follow the baked shading.
    w = ndi.gaussian_filter(valid.astype(np.float32), SIGMA) + 1e-6
    vs = ndi.gaussian_filter(np.where(valid, mx, 0), SIGMA) / w
    ss = ndi.gaussian_filter(np.where(valid, sat, 0), SIGMA) / w
    var = ndi.gaussian_filter(np.where(valid, mx * mx, 0), SIGMA) / w - vs * vs
    flat = valid & (var < 2e-5) & (ss < 0.15)        # baked gunmetal (cut faces, pegs, holes): leave as is
    ok = valid & ~flat
    plate_cut = np.quantile(vs[ok], 1 - PLATE_SHARE)
    plate = ok & (vs >= plate_cut)
    rest = ok & ~plate
    brass_cut = np.quantile(ss[rest], 1 - BRASS_SHARE / (1 - PLATE_SHARE))
    brass = rest & (ss >= brass_cut)
    iron = rest & ~brass
    c = np.zeros(mx.shape, np.int8)   # 0 untouched, 1 plate, 2 brass, 3 iron
    c[plate] = 1
    c[brass] = 2
    c[iron] = 3

    out = a.copy()
    # shading: brightness relative to the class median, so wear and chips show
    for k, base, vref, gain, lo, hi in ((1, RED, 0.52, 1.0, 0.25, 1.35), (2, BRASS, 0.56, 1.0, 0.3, 1.4), (3, IRON, 0.16, 1.0, 0.4, 2.2)):
        m = c == k
        if not m.any():
            continue
        med = np.median(mx[m])
        rel = np.clip(1 + gain * (mx[m] / med - 1), lo, hi)
        col = base[None, :] * rel[:, None]
        if k == 1:
            # chipped lacquer: the darkest plate texels show iron through the paint
            chip = np.clip((0.62 - mx[m] / med) / 0.2, 0, 1)[:, None]
            col = col * (1 - chip) + IRON[None, :] * np.clip(rel, 0.6, 1.4)[:, None] * chip
        out[m] = np.clip(col, 0, 1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGB")


if __name__ == "__main__":
    src, dst = sys.argv[1:3]
    recolour(Image.open(src)).save(dst)
