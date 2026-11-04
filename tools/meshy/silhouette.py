#!/usr/bin/env python3
"""Gate D check: render a Meshy GLB in orthographic front, side and back views (z-buffered point splat, grey-shaded)
and put them above the turnaround images, for a visual silhouette comparison.

  silhouette.py MODEL.glb OUT.png [--turn front.png side.png back.png]
Needs numpy, pillow, trimesh (pip install trimesh). Mesh is Y-up with the front facing +Z (Meshy default).
"""
import argparse, numpy as np, trimesh
from PIL import Image

def render(pts, nrm, view, H=700):
    # view: 'front' looks down -Z from +Z; 'back' from -Z; 'side' from +X
    ang = {"front": 0, "back": np.pi, "side": np.pi / 2}[view]
    c, s = np.cos(ang), np.sin(ang)
    R = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])
    p, n = pts @ R.T, nrm @ R.T
    y0, y1 = p[:, 1].min(), p[:, 1].max()
    sc = (H * 0.92) / (y1 - y0)
    cx = (p[:, 0].min() + p[:, 0].max()) / 2 if view != "side" else (p[:, 0].min() + p[:, 0].max()) / 2
    W = int(H * 0.75)
    u = ((p[:, 0] - cx) * sc + W / 2).astype(int)
    v = (H - (p[:, 1] - y0) * sc - H * 0.04).astype(int)
    ok = (u >= 0) & (u < W) & (v >= 0) & (v < H)
    u, v, z, n = u[ok], v[ok], p[ok, 2], n[ok]
    order = np.argsort(z)  # far first, near overwrites
    img = np.full((H, W, 3), 200, np.uint8)
    shade = np.clip(0.35 + 0.65 * (n[:, 2] * 0.7 + n[:, 1] * 0.3), 0, 1)
    g = (shade * 170 + 40).astype(np.uint8)
    for dx in (0, 1):
        for dy in (0, 1):
            uu = np.clip(u[order] + dx, 0, W - 1); vv = np.clip(v[order] + dy, 0, H - 1)
            img[vv, uu] = np.stack([g[order]] * 3, 1)
    return Image.fromarray(img)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("glb"); ap.add_argument("out")
    ap.add_argument("--turn", nargs=3)
    a = ap.parse_args()
    m = trimesh.load(a.glb, force="mesh", process=False)
    print("triangles", len(m.faces), "bounds", m.bounds.round(3).tolist())
    # sample surface points (face centres plus random barycentric) for splatting
    pts, fi = trimesh.sample.sample_surface(m, 1_500_000)
    nrm = m.face_normals[fi]
    views = [render(pts, nrm, v) for v in ("front", "side", "back")]
    W, H = views[0].size
    rows = [Image.new("RGB", (W * 3, H))]
    for i, im in enumerate(views): rows[0].paste(im, (i * W, 0))
    if a.turn:
        r2 = Image.new("RGB", (W * 3, H), (200, 200, 200))
        for i, f in enumerate(a.turn):
            t = Image.open(f).convert("RGBA"); sc = H * 0.92 / t.height
            t = t.resize((int(t.width * sc), int(t.height * sc)))
            bg = Image.new("RGBA", t.size, (200, 200, 200, 255)); bg.alpha_composite(t)
            r2.paste(bg.convert("RGB"), (i * W + (W - t.width) // 2, int(H * 0.04)))
        rows.append(r2)
    out = Image.new("RGB", (W * 3, H * len(rows)))
    for i, r in enumerate(rows): out.paste(r, (0, i * H))
    out.save(a.out)

if __name__ == "__main__":
    main()
