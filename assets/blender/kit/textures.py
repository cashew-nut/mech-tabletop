"""Generated greyscale masks for relief and decals: white is raised (filigree)
or painted (stencils). Materials read them through the "Decal" UV map that
the shape helpers lay out, and the bake turns their relief into normal maps.

Files are drawn once into assets/blender/.cache/ and reused.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

CACHE = Path(__file__).resolve().parents[1] / ".cache"


def _cached(name, draw):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / name
    if not path.exists():
        draw().save(path)
    return str(path)


def _scroll(d, cx, cy, r, turns, direction, w):
    pts = []
    for i in range(90):
        t = i / 89
        a = direction * t * turns * 2 * math.pi
        rr = r * (1 - 0.85 * t)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.line(pts, fill=255, width=w, joint="curve")


def _leaf(d, cx, cy, ang, size):
    pts = [(size * math.cos(t), size * 0.32 * math.sin(t)) for t in (i / 23 * math.pi for i in range(24))]
    pts += [(x, -y) for x, y in reversed(pts)]
    c, s = math.cos(ang), math.sin(ang)
    d.polygon([(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts], fill=255)


def filigree(n=1024):
    """Tileable baroque C-scrolls with leaves, the Covenant and Reliquary inlay."""
    def draw():
        im = Image.new("L", (n, n), 0)
        d = ImageDraw.Draw(im)
        cell = n // 4
        for gy in range(5):
            for gx in range(5):
                cx, cy = gx * cell, gy * cell
                flip = 1 if (gx + gy) % 2 == 0 else -1
                _scroll(d, cx + cell * 0.25, cy, cell * 0.24, 1.15, flip, max(2, n // 110))
                _scroll(d, cx - cell * 0.25, cy, cell * 0.24, 1.15, -flip, max(2, n // 110))
                box = (cx - cell * 0.5, cy - cell * 0.5, cx + cell * 0.5, cy + cell * 0.5)
                d.arc(box, 200, 340, fill=255, width=max(2, n // 140))
                d.arc(box, 20, 160, fill=255, width=max(2, n // 140))
                for k in range(4):
                    a = k * math.pi / 2 + math.pi / 4
                    _leaf(d, cx + math.cos(a) * cell * 0.36, cy + math.sin(a) * cell * 0.36, a, cell * 0.09)
                d.ellipse((cx - n / 100, cy - n / 100, cx + n / 100, cy + n / 100), fill=255)
        return im.filter(ImageFilter.GaussianBlur(n / 850))
    return _cached(f"filigree-{n}.png", draw)


def tread_plate(n=512):
    """Raised diamond tread and weld beads, the Foundries relief."""
    def draw():
        im = Image.new("L", (n, n), 0)
        d = ImageDraw.Draw(im)
        step = n // 8
        for gy in range(9):
            for gx in range(9):
                cx, cy = gx * step + (step // 2 if gy % 2 else 0), gy * step
                a = math.pi / 4 if (gx + gy) % 2 else -math.pi / 4
                dx, dy = math.cos(a) * step * 0.32, math.sin(a) * step * 0.32
                d.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=255, width=max(2, n // 64))
        return im.filter(ImageFilter.GaussianBlur(n / 300))
    return _cached(f"tread-{n}.png", draw)


def glyphs(n=1024):
    """Tileable incised ring glyphs, the Reliquary relief."""
    def draw():
        im = Image.new("L", (n, n), 0)
        d = ImageDraw.Draw(im)
        cell = n // 4
        w = max(3, n // 80)
        for gy in range(5):
            for gx in range(5):
                cx, cy = gx * cell, gy * cell
                r = cell * 0.3
                d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=255, width=w)
                d.ellipse((cx - r * 0.45, cy - r * 0.45, cx + r * 0.45, cy + r * 0.45), outline=255, width=w)
                for k in range(8):
                    a = k * math.pi / 4
                    d.line((cx + math.cos(a) * r * 0.5, cy + math.sin(a) * r * 0.5, cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35), fill=255, width=w)
                d.line((cx + cell * 0.5, cy - cell * 0.5, cx + cell * 0.5, cy + cell * 0.5), fill=255, width=w)
        return im.filter(ImageFilter.GaussianBlur(n / 900))
    return _cached(f"glyphs2-{n}.png", draw)


def stencil(text="07", n=512):
    """A sprayed stencil number, white on black, for Foundries hull plates."""
    def draw():
        im = Image.new("L", (n, n), 0)
        d = ImageDraw.Draw(im)
        font = None
        for f in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"):
            try:
                font = ImageFont.truetype(f, int(n * 0.62))
                break
            except OSError:
                continue
        font = font or ImageFont.load_default()
        x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
        d.text(((n - (x1 - x0)) / 2 - x0, (n - (y1 - y0)) / 2 - y0), text, fill=255, font=font)
        # Stencil bridges: the gaps a cut stencil leaves through each glyph.
        for x in range(n // 6, n, n // 3):
            d.rectangle((x - n // 90, 0, x + n // 90, n), fill=0)
        return im.filter(ImageFilter.GaussianBlur(n / 400))
    return _cached(f"stencil-{text}-{n}.png", draw)
