"""Grade the Goliath's Meshy retexture to the Reliquary finish, and light its soul-lights (numpy, scipy, pillow; no Blender).

    ~/bvenv/bin/python -I reliquary_grade.py WORK [--preview OUT.jpg]   # MODEL=goliath; build.py calls surface_textures
                                                                       # through goliath.py

Meshy's retexture of the Goliath came out as one dusty khaki stone (median texel about 92, 81, 66, roughness 0.61,
metallic 0.09), so the cut model read pale bone from head to foot with only the designed knuckles in gold. The concept
art, the turnaround and the part sheet (docs/concept-art/goliath/) are aged gold and bronze over black frame metal, with
bone-white kept for the hood, the wing membranes and the chest plates, a teal soul-light in the chest cage and the eye
slits, and dark crimson cloth. The style bible (docs/style-bible/reliquary.md) gives the same palette.

Meshy's texture still has the right detail: its lighter texels are plates, its mid tones the ribbing and filigree between
them and its darkest the frame and recesses. So every texel is sorted softly by brightness into bone, gold or frame,
and where it falls depends on the part it is on (`gilt` per figure region, drawn into the texture's UV space through the
mesh): on the hood and the wings only the darker ribbing turns gold and the plates stay bone; on the limbs, the cannon,
the spires and the halo almost everything but the frame turns gold. Each class takes the palette colour, roughness and
metal, shaded by the texel's brightness relative to its class, so the carving survives. Red texels (the banner) go
to deep crimson; teal texels stay teal and, inside the model's glow regions, become the light map.

Meshy's tex_0.jpg and tex_1.jpg are never changed: the graded copies are tex_0_reliquary.jpg and tex_1_reliquary.jpg and
the light is tex_glow.png, all in WORK and made again whenever they are missing.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from covenant_grade import _ramp, hsv, lum

# Targets, sRGB 0..1. The style bible's bone (#a98f77) and aged gold (#94704d); the gold is lifted a little so the
# metal still reads as gilding once it is metallic (metal shows its colour only in reflections); the frame is the
# bible's dark gunmetal (#263237) warmed a touch towards bronze so it sits with the gold.
BONE = np.array([176, 156, 128]) / 255
GOLD = np.array([148, 108, 62]) / 255
FRAME = np.array([40, 38, 36]) / 255
RED = np.array([78, 12, 15]) / 255
# roughness, metallic per class (bone is satin enamel, gold aged and worn, frame dull metal, cloth matt)
BONE_RM = (0.52, 0.0)
GOLD_RM = (0.40, 0.88)
FRAME_RM = (0.50, 0.65)
RED_RM = (0.80, 0.0)
TEAL_RM = (0.30, 0.0)
# Brightness splits (luminance of Meshy's texel): below FRAME_L is frame metal; above bone_l(g) is bone, between is gold.
# g is the region's gilt, 0 (the hood) to 1 (the limbs); at g = 1 the bone split is above any texel.
FRAME_L = (0.16, 0.235)             # ramp: all frame below the first, none above the second
BONE_L = (0.27, 0.80)              # bone split at g = 0 and g = 1
BONE_SOFT = 0.06


def gilt_of(names):
    """Gilt per part label (goliath.label_points names): how much of a region's texture turns gold."""
    g = {"helm": 0.0, "pauldron": 0.08, "torso": 0.30, "pelvis": 0.45, "tabard": 0.45, "back": 0.55,
         "arm": 0.95, "forearm": 0.9, "hand": 0.95, "thigh": 0.85, "shin": 0.85, "foot": 0.8, "gun": 0.85,
         "drop": 0.5}
    return np.array([g.get(n.rsplit("_", 1)[0] if n.endswith(("_L", "_R")) else n, 0.5) for n in names], np.float32)


def uv_raster(V, F, UV, val, n, sigma=1.0):
    """Draw a value per triangle into an n x n texture through the mesh's UVs (Meshy's UVs are many small islands, about
    two texels per triangle): each triangle's corners, edge midpoints, centre and inner points are splatted, the texels
    no triangle reaches take the nearest drawn value, and the result is blurred a little."""
    from scipy import ndimage as ndi
    W = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1], [.5, .5, 0], [0, .5, .5], [.5, 0, .5], [1 / 3, 1 / 3, 1 / 3],
                  [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]], np.float32)
    acc = np.zeros(n * n, np.float64)
    cnt = np.zeros(n * n, np.float64)
    uvt = UV[F]                                     # (t, 3, 2)
    for w in W:
        p = np.einsum("k,tkd->td", w, uvt)
        ix = np.clip((p[:, 0] * n).astype(np.int64), 0, n - 1)
        iy = np.clip((p[:, 1] * n).astype(np.int64), 0, n - 1)
        idx = iy * n + ix
        np.add.at(acc, idx, val)
        np.add.at(cnt, idx, 1.0)
    have = cnt > 0
    out = np.zeros(n * n, np.float32)
    out[have] = acc[have] / cnt[have]
    out, have = out.reshape(n, n), have.reshape(n, n)
    _, (iy, ix) = ndi.distance_transform_edt(~have, return_indices=True)
    out = out[iy, ix]
    return ndi.gaussian_filter(out, sigma) if sigma else out


def weights(c, g):
    """Soft class weights (bone, gold, frame, red, teal) per texel, summing to 1."""
    from scipy import ndimage as ndi
    h, s, v = hsv(c)
    L = ndi.gaussian_filter(lum(c), 0.7)
    hr = np.minimum(h, 360 - h)
    wr = _ramp(hr, 24, 12) * _ramp(s, 0.32, 0.46) * _ramp(v, 0.12, 0.20)
    wt = _ramp(np.abs(h - 172), 34, 18) * _ramp(s, 0.22, 0.38) * (1 - wr)
    rest = 1 - wr - wt
    wf = rest * _ramp(L, FRAME_L[1], FRAME_L[0])
    split = BONE_L[0] + (BONE_L[1] - BONE_L[0]) * g
    wb = (rest - wf) * _ramp(L, split - BONE_SOFT, split + BONE_SOFT)
    wg = np.clip(rest - wf - wb, 0, 1)
    return wb, wg, wf, wr, wt


def grade(base, mr, g):
    """base: sRGB float (n, n, 3); mr: Meshy's metallic-roughness texture (G roughness, B metallic); g: gilt (n, n)."""
    wb, wg, wf, wr, wt = weights(base, g)
    L = lum(base)

    def ref(w):
        return float((L * w).sum() / max(w.sum(), 1.0))

    def shade(target, w, lo, hi, k=1.0):
        return target * (np.clip(L / ref(w), lo, hi)[..., None] ** k)
    bone = shade(BONE, wb, 0.6, 1.35, 0.8)
    gold = shade(GOLD, wg, 0.40, 1.6, 0.9)
    frame = shade(FRAME, wf, 0.45, 1.6)
    red = shade(RED, wr, 0.45, 1.2)
    teal = base * np.array([0.75, 1.08, 1.05])           # verdigris, a touch deeper
    out = (wb[..., None] * bone + wg[..., None] * gold + wf[..., None] * frame + wr[..., None] * red
           + wt[..., None] * teal)
    rough = mr[..., 1]

    def rm(w, target, spread=0.35):
        mean = float((rough * w).sum() / max(w.sum(), 1.0))
        return np.clip(target + spread * (rough - mean), 0.08, 1.0)
    r2 = (wb * rm(wb, BONE_RM[0]) + wg * rm(wg, GOLD_RM[0]) + wf * rm(wf, FRAME_RM[0]) + wr * rm(wr, RED_RM[0])
          + wt * rm(wt, TEAL_RM[0]))
    m2 = wb * BONE_RM[1] + wg * GOLD_RM[1] + wf * FRAME_RM[1] + wr * RED_RM[1] + wt * TEAL_RM[1]
    mr2 = mr.copy()
    mr2[..., 1], mr2[..., 2] = r2, m2
    stats = {k: round(float(w.mean()), 3) for k, w in (("bone", wb), ("gold", wg), ("frame", wf), ("red", wr),
                                                       ("teal", wt))}
    return np.clip(out, 0, 1), np.clip(mr2, 0, 1), stats, wt


# Soul-light: teal texels inside the model's glow regions. Light colour runs from deep verdigris to pale cyan with the
# texel's brightness; the lit texel's own colour goes to dark teal glass so the light reads as colour, not paint.
GLOW_LO, GLOW_HI = (0.01, 0.09, 0.07), (0.08, 0.74, 0.58)
GLASS = np.array([0.03, 0.10, 0.09])
GLASS_K = 0.85


def surface_textures(work, gilt, lamps=None, eyes=None):
    """The graded base colour and metal/roughness (and with `lamps`, the soul-light map tex_glow.png) for build.py.
    `gilt(points) -> 0..1`, `lamps(points) -> 0..1` and `eyes(points) -> 0..1` take triangle centres in figure units (as
    WORK/mesh.npz). Lamps light the teal texels in them; eyes are lit whatever Meshy painted there (it painted none)."""
    work = Path(work)
    paths = {"base": work / "tex_0_reliquary.jpg", "mr": work / "tex_1_reliquary.jpg"}
    if lamps is not None:
        paths["glow"] = work / "tex_glow.png"
    if all(p.exists() for p in paths.values()):
        return paths
    base = np.asarray(Image.open(work / "tex_0.jpg").convert("RGB")).astype(np.float32) / 255
    mr = np.asarray(Image.open(work / "tex_1.jpg").convert("RGB")).astype(np.float32) / 255
    n = base.shape[0]
    d = np.load(work / "mesh.npz")
    V, F, UV = d["V"], d["F"], d["UV"]
    C = V[F].mean(1)
    g = uv_raster(V, F, UV, np.asarray(gilt(C), np.float32), n)
    b2, mr2, stats, wt = grade(base, mr, g)
    if lamps is not None:
        mask = np.clip(uv_raster(V, F, UV, np.asarray(lamps(C), np.float32), n, sigma=0.6), 0, 1)
        t = np.clip((lum(base) - 0.18) / 0.32, 0, 1) ** 0.8
        k = mask * wt
        if eyes is not None:
            ke = np.clip(uv_raster(V, F, UV, np.asarray(eyes(C), np.float32), n, sigma=0.6), 0, 1)
            k = np.maximum(k, ke)
            t = np.maximum(t, ke * 0.85)
        lo, hi = np.array(GLOW_LO), np.array(GLOW_HI)
        light = (lo + (hi - lo) * t[..., None]) * k[..., None]
        b2 = b2 * (1 - GLASS_K * k[..., None]) + GLASS * (GLASS_K * k[..., None])
        Image.fromarray((np.clip(light, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)).save(paths["glow"])
        stats["lit texels"] = int((k > 0.1).sum())
    Image.fromarray((np.clip(b2, 0, 1) * 255 + 0.5).astype(np.uint8)).save(paths["base"], quality=96)
    Image.fromarray((mr2 * 255 + 0.5).astype(np.uint8)).save(paths["mr"], quality=96)
    np.save(work / "gilt.npy", g.astype(np.float16))
    print("graded the Meshy textures to the Reliquary finish:", stats, flush=True)
    return paths


if __name__ == "__main__":
    import goliath
    a = sys.argv[1:]
    w = Path(a[0])
    for p in (w / "tex_0_reliquary.jpg", w / "tex_1_reliquary.jpg", w / "tex_glow.png"):
        p.unlink(missing_ok=True)
    out = goliath.surface_textures(w)
    if "--preview" in a:
        tiles = [Image.open(w / "tex_0.jpg").convert("RGB"), Image.open(out["base"]).convert("RGB")]
        if "glow" in out:
            tiles.append(Image.open(out["glow"]).convert("RGB"))
        sheet = Image.new("RGB", (1024 * len(tiles), 1024))
        for i, t in enumerate(tiles):
            sheet.paste(t.resize((1024, 1024)), (1024 * i, 0))
        sheet.save(a[a.index("--preview") + 1], quality=88)
