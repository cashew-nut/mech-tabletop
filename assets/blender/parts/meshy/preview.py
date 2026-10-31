"""Numpy point-splat views (front, side, back) with a 0.1 grid, for checking cuts without a GPU or Blender."""
import numpy as np
from PIL import Image, ImageDraw

PAL = np.array([[230, 60, 60], [60, 200, 80], [70, 110, 240], [240, 200, 40], [200, 70, 220], [60, 220, 220], [250, 140, 40],
                [160, 160, 160], [120, 60, 20], [250, 150, 200], [255, 255, 255], [0, 120, 60], [130, 0, 130], [255, 255, 120]] * 3, np.uint8)


def splat(C, N, col, path, view, W=900, H=1000, scale=1000 / 2.1, grid=True):
    if view == "front":
        u, d, sh = C[:, 0], C[:, 1], -N[:, 1]
    elif view == "back":
        u, d, sh = -C[:, 0], -C[:, 1], N[:, 1]
    else:
        u, d, sh = C[:, 1], -C[:, 0], N[:, 0]
    px = (W / 2 + u * scale).astype(int)
    py = (H / 2 - C[:, 2] * scale).astype(int)
    idx = np.where((px >= 0) & (px < W) & (py >= 0) & (py < H))[0]
    order = idx[np.argsort(-d[idx])]
    img = np.full((H, W, 3), (70, 70, 76), np.uint8)
    shaded = (col * np.clip(0.45 + 0.55 * np.clip(sh, 0, 1), 0, 1)[:, None]).astype(np.uint8)
    for dx in (0, 1):
        for dy in (0, 1):
            img[np.clip(py[order] + dy, 0, H - 1), np.clip(px[order] + dx, 0, W - 1)] = shaded[order]
    im = Image.fromarray(img)
    if grid:
        dr = ImageDraw.Draw(im)
        for i in range(-9, 10):
            v = i / 10
            x, y = W / 2 + v * scale, H / 2 - v * scale
            dr.line([(x, 0), (x, H)], fill=(0, 120, 120) if i % 5 else (0, 220, 220))
            dr.line([(0, y), (W, y)], fill=(120, 120, 0) if i % 5 else (220, 220, 0))
    im.save(path)


def parts_views(C, N, lab, names, prefix):
    base = lambda n: n.rsplit("_", 1)[0] if n[-2:] in ("_L", "_R") else n
    bn = list(dict.fromkeys(base(n) for n in names))
    colr = np.array([PAL[bn.index(base(n))] * (0.6 if n.endswith("_R") else 1) for n in names], float)
    cc = colr[lab].astype(np.uint8)
    for v in ("front", "side", "back"):
        splat(C, N, cc, f"{prefix}-{v}.png", v)
    print("legend", {b: PAL[i].tolist() for i, b in enumerate(bn)})
