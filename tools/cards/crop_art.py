"""Cut the card art out of the concept art (docs/concept-art), no Meshy and no rendering.

    python3 tools/cards/crop_art.py [outDir] [artKey ...]     (default outDir: cards/art)

Every card's `art` key in data/cards.json is one entry in CROPS: a source image, the centre of the crop (cx, cy, in source pixels)
and its width. The height follows from the 55 x 46 mm art window's aspect (1100 x 850), and the crop is scaled up to that size
with Lanczos plus a light sharpen. The concept art is only 1024 px (Paladin: a 1312 px board), so most crops are 300-500 px
wide and are enlarged 2-4x; that is as soft as they get, and `contact` mode writes a sheet to check them by eye.
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
CA = ROOT / "docs/concept-art"
W, H = 1100, 850

# key: (source relative to docs/concept-art, cx, cy, width)
CROPS = json.loads((Path(__file__).with_name("crops.json")).read_text())


def cut(key):
    src, cx, cy, w = CROPS[key]
    im = Image.open(CA / src).convert("RGB")
    h = w * H / W
    x0, y0 = cx - w / 2, cy - h / 2
    # slide the box back inside the picture instead of padding it
    x0 = min(max(0, x0), im.width - w)
    y0 = min(max(0, y0), im.height - h)
    out = im.crop((round(x0), round(y0), round(x0 + w), round(y0 + h))).resize((W, H), Image.LANCZOS)
    return out.filter(ImageFilter.UnsharpMask(radius=1.6, percent=60, threshold=2))


def main():
    args = sys.argv[1:]
    out_dir = Path(args[0]) if args and not args[0] in CROPS else ROOT / "cards/art"
    keys = [a for a in args if a in CROPS] or list(CROPS)
    out_dir.mkdir(parents=True, exist_ok=True)
    for k in keys:
        cut(k).save(out_dir / f"{k}.jpg", quality=90)
        print(out_dir / f"{k}.jpg")


if __name__ == "__main__":
    main()
