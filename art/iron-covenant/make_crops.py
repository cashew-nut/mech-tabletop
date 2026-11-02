"""Cut Variant B (artillery platform) and its component close-ups from the
Iron Covenant concept board. Native crops are exact pixels from the board;
the 4x files are plain Lanczos upscales (no AI detail added).

Run from the repo root:  python3 art/iron-covenant/make_crops.py
"""
import json
from PIL import Image, ImageFilter

BOARD = "assets/art/iron-covenant-board.png"
OUT = "art/iron-covenant/variant-b-artillery"
SCALE = 4
# Variant B panel on the board, trimmed 2 px to drop the panel frame line.
PANEL = (657, 550, 981, 886)
# Component boxes in board pixels [left, top, right, bottom].
CROPS = {
    "00-whole-platform": PANEL,
    "01-hull-spires-and-head": (718, 575, 903, 685),
    "02-cannon-barrel-and-eye": (853, 655, 972, 720),
    "03-shoulder-and-chest-plates": (760, 678, 842, 755),
    "04-front-leg-knee-and-shin": (765, 735, 848, 842),
    "05-right-leg-and-foot": (850, 735, 930, 850),
    "06-left-leg-and-blade": (665, 672, 745, 840),
}

im = Image.open(BOARD).convert("RGB")
report = {}
for name, box in CROPS.items():
    c = im.crop(box)
    c.save(f"{OUT}/native/{name}.png")
    up = c.resize((c.width * SCALE, c.height * SCALE), Image.LANCZOS)
    up = up.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    up.save(f"{OUT}/{name}-4x.png")
    report[name] = {"board_box": list(box), "native": list(c.size), "upscaled_4x": list(up.size)}
json.dump(report, open(f"{OUT}/crops.json", "w"), indent=1)
print(json.dumps(report, indent=1))
