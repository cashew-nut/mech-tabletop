"""Cycles review renders and side-by-side comparisons with crops of the art.

    kit.render.studio()                               # moody overcast lights
    kit.render.shot(objs, "out.png", az=35, el=12)    # frame and render
    kit.render.compare(["out.png"], "helm_covenant", "cmp.png")

Crops are named boxes on the concept boards, listed in assets/art/crops.json.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .core import bounds, direction, link, look_at

ART = Path(__file__).resolve().parents[2] / "art"


def crops():
    return json.loads((ART / "crops.json").read_text())["crops"]


def crop(name):
    """The named crop of the concept art as a PIL image."""
    c = crops()[name]
    return Image.open(ART / c["board"]).convert("RGB").crop(tuple(c["box"]))


def studio(key=(1.0, 0.86, 0.70), rim=(0.75, 0.82, 1.0), strength=1.0, floor=False):
    """A dark smoky backdrop, a warm high key, a cool rim and a faint fill,
    as in the helm proof of concept. Positions are relative to a unit-sized
    subject; shot() scales the rig to fit the subject."""
    scene = bpy.context.scene
    world = bpy.data.worlds.get("kit_studio") or bpy.data.worlds.new("kit_studio")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        if n.type not in {"OUTPUT_WORLD", "BACKGROUND"}:
            nt.nodes.remove(n)
    bg = nt.nodes["Background"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.006, 0.006, 0.008, 1)
    ramp.color_ramp.elements[1].color = (0.06, 0.06, 0.07, 1)
    nt.links.new(coord.outputs["Generated"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -0.2
    mr.inputs["From Max"].default_value = 0.8
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    rig = bpy.data.objects.get("kit_rig") or link(bpy.data.objects.new("kit_rig", None))
    for o in list(rig.children):
        bpy.data.objects.remove(o)
    for name, loc, energy, colour, size in (
        ("key", (-3.2, -3.0, 2.2), 520, key, 2.0),
        ("rim", (3.0, 3.0, 1.6), 1400, rim, 1.0),
        ("fill", (3.0, -4.0, -1.2), 70, (0.6, 0.65, 0.8), 3.0),
        ("top", (0, 1.0, 4.5), 90, (0.9, 0.9, 1.0), 1.5),
    ):
        data = bpy.data.lights.new(f"kit_{name}", "AREA")
        data.energy = energy * strength
        data.color = colour
        data.size = size
        lamp = link(bpy.data.objects.new(f"kit_{name}", data))
        lamp.location = loc
        look_at(lamp, (0, 0, 0.1))
        lamp.parent = rig
    if floor:
        bpy.ops.mesh.primitive_plane_add(size=200)
        pl = bpy.context.object
        pl.name = "kit_floor"
        m = bpy.data.materials.new("kit_floor")
        m.use_nodes = True
        m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.022, 1)
        m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
        pl.data.materials.append(m)
        pl.parent = rig
    return rig


def shot(objs, out, az=35.0, el=12.0, samples=48, res=(720, 900), lens=60, margin=0.8, dof=False, look="AgX - Punchy"):
    """Frame `objs` from azimuth/elevation (degrees, 0 = front) and render to `out`."""
    scene = bpy.context.scene
    lo, hi = bounds(objs)
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)
    rig = bpy.data.objects.get("kit_rig")
    if rig is not None:
        # The light rig is built for a unit subject; scale it to this one.
        rig.location = centre
        rig.scale = (radius,) * 3
        for o in rig.children:
            if o.type == "LIGHT":
                if "base_energy" not in o.data:
                    o.data["base_energy"] = o.data.energy
                o.data.energy = o.data["base_energy"] * radius * radius
            elif o.name == "kit_floor":
                o.location = (0, 0, (lo.z - centre.z) / radius)
    cam_data = bpy.data.cameras.get("kit_cam") or bpy.data.cameras.new("kit_cam")
    cam_data.lens = lens
    cam = bpy.data.objects.get("kit_cam") or link(bpy.data.objects.new("kit_cam", cam_data))
    aspect = res[1] / res[0]
    fov = 2 * math.atan(18 / lens) * (1 if aspect >= 1 else aspect)
    dist = radius * margin / math.sin(fov / 2)
    cam.location = centre + direction(az, el) * dist
    look_at(cam, centre)
    cam_data.clip_start = dist * 0.01
    cam_data.clip_end = dist * 10
    cam_data.dof.use_dof = dof
    if dof:
        cam_data.dof.focus_distance = dist
        cam_data.dof.aperture_fstop = 2.8
    scene.camera = cam
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = look
    scene.render.filepath = str(out)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.render.render(write_still=True)
    return out


def post(src, dst=None, bloom=1.0, vignette=True, grain=0.012):
    """Bloom, vignette and grain, as on the helm renders."""
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255
    lum = a.max(axis=2, keepdims=True)
    bright = np.clip((lum - 0.55) / 0.45, 0, 1) * a
    b = Image.fromarray((bright * 255).astype(np.uint8))
    s = max(a.shape[:2]) / 1100
    glow = sum(np.asarray(b.filter(ImageFilter.GaussianBlur(r * s))).astype(np.float32) / 255 * w for r, w in ((6, 0.5), (22, 0.5), (60, 0.45)))
    out = 1 - (1 - a) * (1 - np.clip(glow * bloom, 0, 1))
    if vignette:
        h, w_ = a.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w_]
        d = np.sqrt(((xx - w_ / 2) / (w_ / 2)) ** 2 + ((yy - h * 0.45) / (h / 2)) ** 2)
        out *= np.clip(1.15 - 0.45 * d ** 2, 0.35, 1)[..., None]
    if grain:
        out += np.random.default_rng(1).normal(0, grain, out.shape)
    Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(dst or src)
    return dst or src


def _font(size):
    for f in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def compare(images, art, out, height=700, labels=None, title=None):
    """Lay renders side by side with an art crop (a crops.json name or a
    PIL image) at the same height, labelled, on the board's dark ground."""
    tiles = [Image.open(p).convert("RGB") if not isinstance(p, Image.Image) else p for p in images]
    names = list(labels or [Path(p).stem if not isinstance(p, Image.Image) else "" for p in images])
    strip = None
    if art is not None:
        a = crop(art) if isinstance(art, str) else art
        if a.width > a.height * 3:
            strip = a  # a swatch strip goes along the bottom instead
        else:
            tiles.append(a)
            names.append("concept art" if isinstance(art, str) else "art")
    tiles = [t.resize((max(1, round(t.width * height / t.height)), height), Image.LANCZOS) for t in tiles]
    pad, top = 16, 44 if title else 16
    W = sum(t.width for t in tiles) + pad * (len(tiles) + 1)
    H = height + top + 40
    if strip is not None:
        strip = strip.resize((W - 2 * pad, round(strip.height * (W - 2 * pad) / strip.width)), Image.LANCZOS)
        H += strip.height + 40
    sheet = Image.new("RGB", (W, H), (12, 13, 16))
    d = ImageDraw.Draw(sheet)
    if title:
        d.text((pad, 12), title, fill=(220, 210, 190), font=_font(22))
    x = pad
    for t, n in zip(tiles, names):
        sheet.paste(t, (x, top))
        d.text((x, top + height + 10), n, fill=(170, 165, 150), font=_font(16))
        x += t.width + pad
    if strip is not None:
        y = top + height + 40
        sheet.paste(strip, (pad, y))
        d.text((pad, y + strip.height + 10), "concept art swatches", fill=(170, 165, 150), font=_font(16))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out
