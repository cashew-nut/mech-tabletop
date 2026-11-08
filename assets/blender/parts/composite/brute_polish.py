"""The Brute's polish pass (2026-11-08): what the composite cut lost against Luke's concept image, put back.

Luke's concept image (the picture Meshy turned into the Brute) reads at a glance: a glowing furnace under the "07"
plate, two hot eyes, red lacquer plates, brass trim and blackened iron. The cut model kept every shape and every texel
of Meshy's colour, but it lost that read:

* **Everything was the same half-metal.** Meshy's metal/roughness map is about 0.45 / 0.45 everywhere, so the red
  lacquer, the white stencils, the brass and the iron all shine the same way and the walker renders as one dark,
  speckled mass. `surface_textures` rebuilds the map from the colour: lacquer, stencils and hazard paint are paint
  (not metal, satin), brass is polished metal, iron is dark worn metal. Meshy's own roughness is kept as the wear.
* **No glow.** The concept's focal point, the furnace behind its grille, is painted into Meshy's colour as a cream
  window but nothing makes it shine. `glow_weight` marks the furnace window, the eye slits and the lamp on the foot;
  build.py bakes an emissive map from the painted window (bright texels burn white-gold, the bars stay dark) and the
  game's bloom does the rest.
* **Needle antennae.** Meshy grew 0.3 to 0.6 mm wire antennae on the pauldron tops and the rear pack (eight on the
  walker once the pauldron is mirrored). They are far too thin to print and read as stray hairs in the game.
  `design` cuts every thin column under NEEDLE_D mm from the parts that carry them; the chimney, the cone-topped
  stacks and the crown spike (1 mm and up) stay.

Nothing here moves a joint, a peg or a magnet: the antennae are re-made before joints.py runs, far from any joint, and the
texture changes only touch the bake.
"""
from pathlib import Path

import numpy as np

# --- needle antennae -----------------------------------------------------------------------------------------------
NEEDLE_PARTS = ("pauldron", "back", "torso", "helm")
NEEDLE_D = 0.8          # mm: a column thinner than this (median section) is a wire antenna and goes
NEEDLE_MIN_LEN = 4.0    # mm: shorter thin columns are rivet heads, pipe ends and the like; they stay
SLICE = 0.3             # mm between the slices that track a column upward


def _area_centroid(poly):
    x, y = poly[:, 0], poly[:, 1]
    x2, y2 = np.roll(x, -1), np.roll(y, -1)
    c = x * y2 - x2 * y
    A = c.sum() / 2
    if abs(A) < 1e-9:
        return 0.0, poly.mean(0)
    return abs(A), np.array([((x + x2) * c).sum() / (6 * A), ((y + y2) * c).sum() / (6 * A)])


def thin_columns(m):
    """Vertical runs of small cross-sections (under about 1.6 mm across), tracked slice by slice from the bottom up.
    Returns [(z, area, centroid xy), ...] per column, in print mm."""
    bb = m.bounding_box()
    cols, open_ = [], []
    for z in np.arange(bb[2] + 0.15, bb[5], SLICE):
        nxt = []
        for poly in m.slice(float(z)).to_polygons():
            A, c = _area_centroid(np.asarray(poly))
            if not 0.01 < A < 2.0:
                continue
            col = next((q for q in open_ if np.linalg.norm(q[-1][2] - c) < 0.6), None)
            if col is None:
                col = []
                cols.append(col)
            col.append((float(z), A, c))
            nxt.append(col)
        open_ = nxt
    return cols


def needles(m):
    """The wire antennae of one solid: (base xyz, top xyz, cutter radius, median diameter) in print mm."""
    out = []
    for col in thin_columns(m):
        z = np.array([q[0] for q in col])
        if z[-1] - z[0] < NEEDLE_MIN_LEN:
            continue
        A = np.array([q[1] for q in col])
        d = 2 * np.sqrt(np.median(A) / np.pi)
        if d >= NEEDLE_D:
            continue
        C = np.array([q[2] for q in col])
        # the axis: a straight line through the section centres (antennae lean a little)
        fx, fy = np.polyfit(z, C[:, 0], 1), np.polyfit(z, C[:, 1], 1)
        z0, z1 = z[0] - 0.15, z[-1] + 1.0
        a = np.array([np.polyval(fx, z0), np.polyval(fy, z0), z0])
        b = np.array([np.polyval(fx, z1), np.polyval(fy, z1), z1])
        r = min(1.0, np.sqrt(A.max() / np.pi) + 0.3)
        out.append((a, b, r, d))
    return out


def _rod(mf, a, b, r, tip=False):
    """A cylinder from a to b (print mm), with a round end at b if `tip`; its faces are tagged as cut faces
    (UV -1, -1), so they bake as the walker's blackened gunmetal."""
    v = b - a
    L = float(np.linalg.norm(v))
    ax = v / L
    zc = np.array([0.0, 0.0, 1.0])
    w = np.cross(zc, ax)
    s, c = np.linalg.norm(w), zc @ ax
    if s < 1e-8:
        R = np.eye(3)
    else:
        vx = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
        R = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)
    rod = mf.Manifold.cylinder(L, r, -1.0, 20)
    if tip:
        rod = rod + mf.Manifold.sphere(r * 1.25, 20).translate([0.0, 0.0, L])
    return rod.transform(np.concatenate([R, a[:, None]], 1).tolist()).set_properties(
        2, lambda q, old: (-1.0, -1.0))


ANTENNA_D = 1.0         # mm: each wire antenna is re-made as a rod this thick, on the wire's own line
SINK = 0.6              # mm the rod runs down into the mount it stands on


def _merge(found):
    """One rod per antenna: Meshy's label boundary can split a wire between two parts (the one beside the chimney
    runs from the rear pack up into the torso). Columns whose lines pass within 1 mm of each other are one antenna:
    it goes to the part that holds its foot, from the lowest foot to the highest tip."""
    found = sorted(found, key=lambda f: f[1][2])
    out = []
    for k, a, top, d in found:
        for q in out:
            ax, at = q[1], q[2]
            u = (at - ax) / np.linalg.norm(at - ax)
            def off(p):
                v = p - ax
                return np.linalg.norm(v - (v @ u) * u)
            if max(off(a), off(top)) < 1.0:
                if top[2] > q[2][2]:
                    q[2] = top
                q[3] = min(q[3], d)
                q[4].append(k)
                break
        else:
            out.append([k, a, top, d, [k]])
    return out


def design(solid, mf):
    """Re-make the wire antennae (thinner than NEEDLE_D) as ANTENNA_D mm rods with a round tip, on the same line
    and to the same height, so the silhouette the concept has stays and the print holds. Each rod is checked: it
    may only add about a rod's own volume (a rod that would swallow a bigger shape is left alone). The rod is cut
    out of every other part (with clearance), so no two parts share it."""
    out = dict(solid)
    found = []
    for k in NEEDLE_PARTS:
        if k in out:
            for a, b, r, d in needles(out[k]):
                found.append((k, a, b - (b - a) / np.linalg.norm(b - a) * 1.0, d))  # needles() reaches 1 mm past the tip
    for k, a, top, d, ks in _merge(found):
        m = out[k]
        base = a - (top - a) / np.linalg.norm(top - a) * SINK
        rod = _rod(mf, base, top, ANTENNA_D / 2, tip=True)
        added = (rod - m).volume()
        expect = np.pi * (ANTENNA_D / 2) ** 2 * np.linalg.norm(top - base) + 1.0
        if added > 1.2 * expect:
            print(f"  {k}: kept a column at ({a[0]:.1f}, {a[1]:.1f}): the rod would add {added:.1f} mm3", flush=True)
            continue
        out[k] = m + rod
        clear = _rod(mf, base, top, ANTENNA_D / 2 + 0.15, tip=True)
        took = {}
        for o in NEEDLE_PARTS:
            if o != k and o in out:
                v = (out[o] ^ clear).volume()
                if v > 1e-3:
                    out[o] = out[o] - clear
                    took[o] = round(v, 2)
        print(f"  {k}: {d:.2f} mm wire at ({a[0]:.1f}, {a[1]:.1f}), z {a[2]:.1f} to {top[2]:.1f} -> {ANTENNA_D} mm rod "
              f"(+{added:.1f} mm3){' from ' + '+'.join(sorted(set(ks))) if len(set(ks)) > 1 else ''}"
              f"{', cleared ' + str(took) if took else ''}", flush=True)
    for k in NEEDLE_PARTS:      # crumbs the rods and clearances leave behind
        if k in out:
            ps = sorted(out[k].decompose(), key=lambda p: -p.volume())
            if len(ps) > 1:
                out[k] = mf.Manifold.batch_boolean([p for p in ps if p.volume() > 0.5] or ps[:1], mf.OpType.Add)
    return out


# --- materials -----------------------------------------------------------------------------------------------------
# (metallic, roughness) per finish. Meshy's own roughness rides on top as wear (ROUGH_WEAR of its deviation).
PAINT = (0.0, 0.58)       # red lacquer, white stencils, orange hazard paint
BRASS = (0.9, 0.34)       # fittings, collars, trim
IRON = (0.72, 0.52)       # blackened iron: frame, guns, undercarriage
ROUGH_WEAR = 0.8


def _hsv(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    s = np.where(mx > 1e-4, d / np.maximum(mx, 1e-4), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    m = d > 1e-4
    rm, gm = m & (mx == r), m & (mx == g) & (mx != r)
    bm = m & ~rm & ~gm
    h[rm] = ((g - b)[rm] / d[rm]) % 6
    h[gm] = (b - r)[gm] / d[gm] + 2
    h[bm] = (r - g)[bm] / d[bm] + 4
    return h * 60, s, mx


def finishes(rgb):
    """Weights (paint, brass, iron) per texel of Meshy's colour (0..1 floats, sRGB). Soft, so edges blend."""
    from scipy import ndimage
    h, s, v = _hsv(rgb)
    ss = lambda x, a, b: np.clip((x - a) / (b - a), 0, 1)
    # red lacquer: red hue, saturated, not dark
    red = ss(s, 0.45, 0.65) * ss(v, 0.22, 0.35) * ((h < 18) | (h > 340))
    # brass and ochre: orange to yellow hue, saturated enough, bright enough
    warm = ss(s, 0.30, 0.50) * ss(v, 0.30, 0.45) * ((h >= 18) & (h < 55))
    # white stencils and cream paint
    white = ss(v, 0.62, 0.75) * (1 - ss(s, 0.22, 0.35))
    # broad ochre panels (thigh plates, hazard chevrons) are paint, thin bright lines are brass: what survives an
    # opening of a few texels at 4k is a panel
    panel = ndimage.grey_opening(warm, size=(9, 9))
    panel = ndimage.uniform_filter(panel, 5)
    paint = np.clip(red + white + 0.8 * panel * warm, 0, 1)
    brass = np.clip(warm - 0.8 * panel * warm, 0, 1) * (1 - paint)
    iron = np.clip(1 - paint - brass, 0, 1)
    return paint, brass, iron


def surface_textures(work):
    """Write WORK/tex_mr_polish.png (metal/roughness from the colour, see above) and WORK/tex_glow.png (furnace light
    for the glowing parts, from the painted window). Returns {image key: path} for build.py."""
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    work = Path(work)
    mr_p, glow_p = work / "tex_mr_polish.png", work / "tex_glow.png"
    if mr_p.exists() and glow_p.exists():
        return {"mr": mr_p, "glow": glow_p}
    base = Image.open(work / "tex_0.jpg").convert("RGB")
    n = base.size[0]
    rgb = np.asarray(base, np.float32) / 255.0
    meshy = np.asarray(Image.open(work / "tex_1.jpg").convert("RGB").resize((n, n), Image.BILINEAR), np.float32) / 255.0
    paint, brass, iron = finishes(rgb)
    metal = paint * PAINT[0] + brass * BRASS[0] + iron * IRON[0]
    rough = paint * PAINT[1] + brass * BRASS[1] + iron * IRON[1]
    rough = np.clip(rough + ROUGH_WEAR * (meshy[..., 1] - 0.45), 0.08, 1.0)
    mr = np.stack([np.ones_like(metal), rough, metal], -1)
    Image.fromarray((mr * 255 + 0.5).astype(np.uint8)).save(mr_p)
    # glow: the brightness of the painted window, through a furnace ramp (deep orange, orange, white-gold)
    h, s, v = _hsv(rgb)
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    t = np.clip((lum - 0.30) / 0.55, 0, 1) ** 1.3
    ramp_t = np.array([0.0, 0.35, 0.7, 1.0])
    ramp_c = np.array([[0.10, 0.015, 0.0], [0.85, 0.22, 0.02], [1.0, 0.52, 0.12], [1.0, 0.86, 0.58]])
    glow = np.stack([np.interp(t, ramp_t, ramp_c[:, i]) for i in range(3)], -1)
    Image.fromarray((np.clip(glow, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)).save(glow_p)
    return {"mr": mr_p, "glow": glow_p}


# --- glow regions --------------------------------------------------------------------------------------------------
# Boxes in Meshy units (x relative to CX, y forward is negative, z up): (x0, x1), (y0, y1), (z0, z1), soft edge.
GLOW_BOXES = (
    ((-0.160, -0.020), (-0.30, 0.00), (0.168, 0.312), 0.006),     # the furnace window under the "07" plate
    ((-0.110, 0.005), (-0.20, 0.10), (0.588, 0.648), 0.006),      # the eye slits on the helm's face plate
)
GLOW_STRENGTH = 3.0      # emission strength (glTF KHR_materials_emissive_strength), so the furnace blooms in the game


def glow_weight(P_mm):
    """0..1 per vertex (print mm, kit axes): how much of the glow texture a vertex shows."""
    from brute import from_mm
    Q = from_mm(np.asarray(P_mm, np.float64))
    w = np.zeros(len(Q))
    for (x0, x1), (y0, y1), (z0, z1), e in GLOW_BOXES:
        f = np.ones(len(Q))
        for c, (lo, hi) in ((0, (x0, x1)), (1, (y0, y1)), (2, (z0, z1))):
            f *= np.clip((Q[:, c] - lo) / e, 0, 1) * np.clip((hi - Q[:, c]) / e, 0, 1)
        w = np.maximum(w, f)
    return w
