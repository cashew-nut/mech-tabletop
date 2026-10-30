"""Lay the review renders from `items.py --render DIR` out as a sheet: one row
per item, one column per faction, under each faction's class art.

    ~/bvenv/bin/python assets/blender/parts/equipment/sheet.py DIR out.png [item ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # assets/blender
from PIL import Image, ImageDraw  # noqa: E402

from kit.render import _font, crop  # noqa: E402

FACTIONS = ("covenant", "foundries", "reliquary")
HEAD = {"covenant": "class_sentinel", "foundries": "class_brute", "reliquary": "class_seer"}


def main():
    src, out, *items = sys.argv[1:]
    src = Path(src)
    if not items:
        items = sorted({p.stem.split("@")[0] for p in src.glob("*@*.png")})
    T, pad, label = 300, 12, 150
    W = label + len(FACTIONS) * (T + pad) + pad
    head = 240
    H = head + 40 + len(items) * (T + pad) + pad
    sheet = Image.new("RGB", (W, H), (12, 13, 16))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(FACTIONS):
        x = label + pad + i * (T + pad)
        art = crop(HEAD[f])
        art = art.resize((T, round(art.height * T / art.width)))
        sheet.paste(art.crop((0, 0, T, min(head, art.height))), (x, pad))
        d.text((x, head + 12), f"{f} (art: {HEAD[f].split('_')[1]})", fill=(200, 190, 170), font=_font(16))
    for r, item in enumerate(items):
        y = head + 40 + r * (T + pad)
        d.text((pad, y + T // 2 - 10), item, fill=(200, 190, 170), font=_font(15))
        for i, f in enumerate(FACTIONS):
            p = src / f"{item}@{f}.png"
            if p.exists():
                sheet.paste(Image.open(p).convert("RGB").resize((T, T)), (label + pad + i * (T + pad), y))
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
