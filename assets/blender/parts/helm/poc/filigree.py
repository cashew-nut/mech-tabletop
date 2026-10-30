"""Draw a tileable gold scrollwork mask (white = raised gold) for the inlay decals."""
import math
import sys

from PIL import Image, ImageDraw, ImageFilter

N = 1024


def scroll(d, cx, cy, r, turns, direction, w):
    pts = []
    steps = 90
    for i in range(steps):
        t = i / (steps - 1)
        a = direction * t * turns * 2 * math.pi
        rr = r * (1 - 0.85 * t)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.line(pts, fill=255, width=w, joint="curve")


def leaf(d, cx, cy, ang, size):
    pts = []
    for i in range(24):
        t = i / 23 * math.pi
        x = size * math.cos(t) * 1.0
        y = size * 0.35 * math.sin(2 * t) if False else size * 0.32 * math.sin(t)
        pts.append((x, y))
    pts += [(x, -y) for x, y in reversed(pts)]
    c, s = math.cos(ang), math.sin(ang)
    d.polygon([(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts], fill=255)


def main(out):
    im = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(im)
    cell = N // 4
    for gy in range(5):
        for gx in range(5):
            cx, cy = gx * cell, gy * cell
            flip = 1 if (gx + gy) % 2 == 0 else -1
            # Main C-scrolls back to back, the classic baroque motif.
            scroll(d, cx + cell * 0.25, cy, cell * 0.24, 1.15, flip, 9)
            scroll(d, cx - cell * 0.25, cy, cell * 0.24, 1.15, -flip, 9)
            # The stem that links neighbouring cells.
            d.arc((cx - cell * 0.5, cy - cell * 0.5, cx + cell * 0.5, cy + cell * 0.5), 200, 340, fill=255, width=7)
            d.arc((cx - cell * 0.5, cy - cell * 0.5, cx + cell * 0.5, cy + cell * 0.5), 20, 160, fill=255, width=7)
            for k in range(4):
                a = k * math.pi / 2 + math.pi / 4
                leaf(d, cx + math.cos(a) * cell * 0.36, cy + math.sin(a) * cell * 0.36, a, cell * 0.09)
            d.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), fill=255)
    im = im.filter(ImageFilter.GaussianBlur(1.2))
    im.save(out)


if __name__ == "__main__":
    main(sys.argv[1])
