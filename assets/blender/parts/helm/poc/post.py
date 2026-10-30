"""Bloom, vignette and grain on a raw render: python post.py in.png out.png"""
import sys
import numpy as np
from PIL import Image, ImageFilter
im = Image.open(sys.argv[1]).convert("RGB")
a = np.asarray(im).astype(np.float32) / 255
lum = a.max(axis=2, keepdims=True)
bright = np.clip((lum - 0.55) / 0.45, 0, 1) * a
b = Image.fromarray((bright * 255).astype(np.uint8))
bloom = sum(np.asarray(b.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255 * w for r, w in ((6, 0.5), (22, 0.5), (60, 0.45)))
out = 1 - (1 - a) * (1 - np.clip(bloom, 0, 1))
h, w_ = a.shape[:2]
yy, xx = np.mgrid[0:h, 0:w_]
d = np.sqrt(((xx - w_ / 2) / (w_ / 2)) ** 2 + ((yy - h * 0.45) / (h / 2)) ** 2)
out *= np.clip(1.15 - 0.45 * d ** 2, 0.35, 1)[..., None]
out += np.random.default_rng(1).normal(0, 0.012, out.shape)
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(sys.argv[2])
