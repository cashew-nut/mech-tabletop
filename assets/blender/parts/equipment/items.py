"""Package 8b: the shared defence, mobility and system equipment.

Every shared item gets one part per faction, `item_<id>@<faction>`, because
the baked textures carry the faction's materials (blackened iron and gold,
rusted red plate and brass, bone ceramic and pale gold). The forms change too:
Covenant gear is gothic (lancet windows, spires, crosses, sunbursts), Foundries
gear is riveted, stencilled and blunt, Reliquary gear is slender ceramic with
gold rings, halos and teal light.

Items are built at Scout scale (the web scales them by frame) with the origin
at the attachment point, Z up and the front facing -Y.

    ~/bvenv/bin/python assets/blender/parts/equipment/items.py                 # publish all 39
    ~/bvenv/bin/python assets/blender/parts/equipment/items.py jump-jets       # one item, three factions
    ~/bvenv/bin/python assets/blender/parts/equipment/items.py --faction foundries
    ~/bvenv/bin/python assets/blender/parts/equipment/items.py --render out/   # review renders, no publish
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # assets/blender
import kit  # noqa: E402
from kit import shapes  # noqa: E402
from kit.core import bmesh, mesh_obj, mod  # noqa: E402
from mathutils import Euler, Vector  # noqa: E402

FACTIONS = ("covenant", "foundries", "reliquary")
HERE = Path(__file__).resolve().parent


# ------------------------------------------------------------------ helpers

class Kit:
    """The faction's materials and a parent for everything built."""

    def __init__(self, faction, root):
        self.f = faction
        self.m = kit.materials.library(faction)
        self.root = root
        self.n = 0

    def __getattr__(self, role):
        return self.__dict__["m"][role]

    def name(self, stem):
        self.n += 1
        return f"{self.root.name}_{stem}{self.n}"

    @property
    def C(self):
        return self.f == "covenant"

    @property
    def F(self):
        return self.f == "foundries"

    @property
    def R(self):
        return self.f == "reliquary"


def prism(k, outline, depth, mat, y=0.0, bevel=0.12, loc=(0, 0, 0), rot=(0, 0, 0), stem="prism"):
    """Extrude an (x, z) outline along Y, centred on `y`. Front face at y - depth/2."""
    bm = bmesh.new()
    front = [bm.verts.new((x, y - depth / 2, z)) for x, z in outline]
    back = [bm.verts.new((x, y + depth / 2, z)) for x, z in outline]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[j], front[i], back[i], back[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(k.name(stem), bm, mat, smooth=False)
    if bevel:
        mod(ob, "BEVEL", width=bevel, segments=2, limit_method="ANGLE", angle_limit=math.radians(30), harden_normals=True)
        ob.data.shade_smooth()
        mod(ob, "WEIGHTED_NORMAL", keep_sharp=True)
    ob.location = loc
    ob.rotation_euler = rot
    ob.parent = k.root
    shapes.decal_uv(ob, 3.0)
    return ob


def scaled(outline, s, dz=0.0):
    return [(x * s, z * s + dz) for x, z in outline]


def arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def heater(w, h, top_peak=0.0):
    """A heater shield: a flat (or peaked) top, sides curving in to a point."""
    hw, top = w / 2, h * 0.35
    right = [(hw * math.cos(t * math.pi / 2) ** 0.8, top - h * t ** 1.6) for t in (i / 12 for i in range(13))]
    left = [(-x, z) for x, z in reversed(right[:-1])]
    return right + left + ([(0, top + top_peak)] if top_peak else [])


def vesica(w, h, n=16):
    """A pointed almond, as on Reliquary shields and windows."""
    right = [(w / 2 * math.sin(math.pi * i / n) ** 0.9, h / 2 * math.cos(math.pi * i / n)) for i in range(n + 1)]
    left = [(-x, z) for x, z in reversed(right[1:-1])]
    return right + left


def chamfer_rect(w, h, c):
    hw, hh = w / 2, h / 2
    return [(-hw + c, -hh), (hw - c, -hh), (hw, -hh + c), (hw, hh - c), (hw - c, hh), (-hw + c, hh), (-hw, hh - c), (-hw, -hh + c)]


def gothic_arch(w, h):
    """A lancet outline standing on z=0."""
    spring = max(0.0, h - w * math.sqrt(3) / 2)
    right = [(-w / 2 + w * math.cos(math.radians(60 * i / 10)), spring + w * math.sin(math.radians(60 * i / 10))) for i in range(11)]
    left = [(-x, z) for x, z in reversed(right[:-1])]
    return [(-w / 2, 0.0), (w / 2, 0.0), *right, *left]


def ring(k, r, tube, mat, loc=(0, 0, 0), axis="Y", n=None, stem="ring"):
    """A torus as a swept circle. `axis` is the ring's normal."""
    n = n or max(12, min(32, round(r * 14)))
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        c, s = math.cos(a) * r, math.sin(a) * r
        p = {"Y": (c, 0, s), "Z": (c, s, 0), "X": (0, c, s)}[axis]
        pts.append(Vector(loc) + Vector(p))
    return shapes.sweep(k.name(stem), pts, tube, mat, cyclic=True, parent=k.root, resolution=thin(tube))


def thin(radius):
    """Bevel resolution for a swept tube: fine trim needs few sides at this scale."""
    return 1 if radius < 0.15 else 2


def edge(k, outline, radius, mat, y, scale=1.0, dz=0.0, stem="edge"):
    """Raised trim round an (x, z) outline at depth y."""
    pts = [Vector((x * scale, y, z * scale + dz)) for x, z in outline]
    return shapes.sweep(k.name(stem), pts, radius, mat, cyclic=True, parent=k.root, resolution=thin(radius))


def cyl(k, r, d, mat, loc=(0, 0, 0), rot=(0, 0, 0), verts=24, bevel=None, r2=None, stem="cyl"):
    return shapes.cylinder(k.name(stem), r, d, mat, loc=loc, rot=rot, parent=k.root, verts=verts,
                           bevel=min(r, d) * 0.12 if bevel is None else bevel, r2=r2)


def box(k, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), bevel=None, stem="box", **kw):
    return shapes.box_plate(k.name(stem), size, mat, bevel=min(size) * 0.18 if bevel is None else bevel, loc=loc, rot=rot,
                            parent=k.root, **kw)


def ball(k, r, mat, loc=(0, 0, 0), scale=(1, 1, 1), stem="ball"):
    return shapes.sphere(k.name(stem), r, mat, loc=loc, scale=scale, parent=k.root, segments=16)


def lathe(k, profile, mat, loc=(0, 0, 0), rot=(0, 0, 0), segments=24, stem="lathe"):
    return shapes.lathe(k.name(stem), profile, mat, loc=loc, rot=rot, parent=k.root, segments=segments)


def along(a, b):
    """Euler rotation turning local Z towards b - a."""
    return (Vector(b) - Vector(a)).to_track_quat("Z", "Y").to_euler()


def rod(k, a, b, r, mat, verts=16, stem="rod"):
    a, b = Vector(a), Vector(b)
    return cyl(k, r, (b - a).length, mat, loc=(a + b) / 2, rot=along(a, b), verts=verts, stem=stem)


def rivets(k, p0, p1, n, r=0.12, normal=(0, -1, 0), mat=None):
    return shapes.rivet_row(k.name("rivets"), p0, p1, n, r, mat or k.metal, parent=k.root, normal=normal)


def stencil(k, size, loc, rot=(0, 0, 0)):
    """A stencilled plate with one whole "07" across its face."""
    ob = box(k, size, k.stencil, loc=loc, rot=rot, bevel=min(size) * 0.15)
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name="Decal")
    w, h = size[0], size[2]
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (co.x / w + 0.5, co.z / h + 0.5)
    return ob


def sunburst(k, r, rays, y, centre=(0, 0), mat=None, boss=None, thick=0.18, stem="sun"):
    """Flat gold rays in the XZ plane facing -Y, alternating long and short."""
    mat = mat or k.trim
    cx, cz = centre
    for i in range(rays):
        a = 2 * math.pi * i / rays
        L = r * (1.0 if i % 2 == 0 else 0.62)
        w = r * 0.16
        out = [(0, -w / 2), (L, 0), (0, w / 2)]
        pts = [(cx + x * math.cos(a) - z * math.sin(a), cz + x * math.sin(a) + z * math.cos(a)) for x, z in out]
        prism(k, pts, thick, mat, y=y, bevel=0.03, stem=stem)
    ball(k, r * 0.26, boss or mat, loc=(cx, y - thick * 0.2, cz), scale=(1, 0.55, 1), stem=stem + "boss")


def cross(k, size, y, mat, centre=(0, 0), thick=0.22):
    """A flared Covenant cross."""
    cx, cz = centre
    a, b = size * 0.5, size * 0.12
    arm = [(-b, 0), (b, 0), (b * 1.9, a), (-b * 1.9, a)]
    for ang in (0, 90, 180, 270):
        t = math.radians(ang)
        pts = [(cx + x * math.cos(t) - z * math.sin(t), cz + x * math.sin(t) + z * math.cos(t)) for x, z in arm]
        prism(k, pts, thick, mat, y=y, bevel=0.04, stem="cross")


def halo(k, r, tube, mat, loc, axis="Y", spikes=12, spike=0.5, stem="halo"):
    """A Reliquary halo: a gold ring with spikes standing off it."""
    ring(k, r, tube, mat, loc=loc, axis=axis, stem=stem)
    c = Vector(loc)
    for i in range(spikes):
        a = 2 * math.pi * i / spikes
        d = {"Y": Vector((math.cos(a), 0, math.sin(a))), "Z": Vector((math.cos(a), math.sin(a), 0))}[axis]
        L = spike * (1.0 if i % 2 == 0 else 0.55)
        p = c + d * (r + L / 2)
        cyl(k, tube * 1.2, L, mat, loc=p, rot=along(p - d, p), verts=6, bevel=0, r2=0.01, stem=stem + "spike")


def spire(k, w, h, loc, glow=False):
    return shapes.spire(k.name("spire"), w, h, k.armour, trim=k.trim, loc=loc, parent=k.root, crockets=3,
                        glow=k.glow if glow else None, sides=8)


def bell(k, r0, r1, length, mat, loc, rot=(0, 0, 0), lip=None, stem="bell"):
    """A rocket nozzle opening downward from its throat at `loc`."""
    prof = [(r1 * 0.55, 0.0), (r1 * 0.5, -length * 0.15)]
    for i in range(1, 9):
        t = i / 8
        prof.append((r1 * 0.5 + (r0 - r1 * 0.5) * t ** 1.8, -length * (0.15 + 0.85 * t)))
    prof.append((r0 * 0.92, -length * 0.98))
    prof.append((r1 * 0.45, -length * 0.2))
    ob = lathe(k, prof, mat, loc=loc, rot=rot, stem=stem)
    mod(ob, "SOLIDIFY", thickness=0.12, offset=0)
    return ob


def gauge(k, r, loc, rot=(0, 0, 0)):
    return shapes.gauge(k.name("gauge"), r, k.trim, k.armour if k.R else k.metal, k.glow, loc=loc, rot=rot, parent=k.root)


def lancets(k, w, h, y, xs, z0, depth=0.35):
    for x in xs:
        shapes.lancet(k.name("lancet"), w, h, depth, k.trim, glow=k.glow, loc=(x, y, z0), parent=k.root)


# ------------------------------------------------------------------ defence

def ablative_plating(k):
    """Bolt-on layered armour, facing -Y, about 5 x 4 mm."""
    box(k, (4.6, 0.7, 3.8), k.metal, loc=(0, 0.35, 0.3), bevel=0.15)
    if k.C:
        # Three gothic lames, each a peaked plate with gold edging, over a cross boss.
        for i, z in enumerate((1.4, 0.3, -0.8)):
            ol = [(-2.5, 0.7), (2.5, 0.7), (2.5, -0.35), (0, -0.85), (-2.5, -0.35)]
            y = -0.25 - i * 0.28
            prism(k, ol, 0.4, k.filigree, y=y, loc=(0, 0, z), rot=(-0.12, 0, 0), stem="lame")
            e = edge(k, ol, 0.09, k.trim, y - 0.22, stem="lamet")
            e.location, e.rotation_euler = (0, 0, z), (-0.12, 0, 0)
        cross(k, 2.0, -1.25, k.trim, centre=(0, 0.6))
        ball(k, 0.28, k.glow, loc=(0, -1.4, 0.6), scale=(1, 0.5, 1))
    elif k.F:
        # Welded slabs, a stencilled centre plate and heavy bolts.
        box(k, (5.2, 0.6, 1.6), k.hull, loc=(0, -0.2, 1.4), rot=(-0.08, 0, 0), panel_lines=2)
        stencil(k, (5.0, 0.7, 2.0), loc=(0, -0.5, -0.2), rot=(-0.05, 0, 0))
        box(k, (5.4, 0.5, 0.9), k.armour, loc=(0, -0.3, -1.6), rot=(0.1, 0, 0))
        for z, y in ((1.4, -0.55), (-1.6, -0.6)):
            rivets(k, (-2.3, y, z), (2.3, y, z), 7, r=0.16)
        for x in (-2.3, 2.3):
            rivets(k, (x, -0.88, 0.6), (x, -0.88, -1.0), 3, r=0.18)
    else:
        # Overlapping ceramic scales edged in pale gold, a teal gem at the heart.
        for i, z in enumerate((1.5, 0.55, -0.4, -1.35)):
            ol = vesica(5.0 - i * 0.5, 1.6, 12)
            y = -0.2 - i * 0.2
            prism(k, ol, 0.35, k.armour, y=y, loc=(0, 0, z), rot=(-0.15, 0, 0), stem="scale")
            e = edge(k, ol, 0.07, k.trim, y - 0.19, stem="scalet")
            e.location, e.rotation_euler = (0, 0, z), (-0.15, 0, 0)
        ring(k, 0.7, 0.09, k.trim, loc=(0, -1.15, 0.3), axis="Y")
        ball(k, 0.42, k.glow, loc=(0, -1.1, 0.3), scale=(1, 0.6, 1.3))


def reactive_shell(k):
    """A grid of explosive tiles on a backplate (core), facing -Y."""
    box(k, (5.0, 0.8, 3.8), k.metal, loc=(0, 0.4, 0.3), bevel=0.15)
    xs, zs = (-1.65, 0, 1.65), (-0.6, 1.2)
    for x in xs:
        for z in zs:
            if k.C:
                ol = gothic_arch(1.3, 1.6)
                prism(k, scaled(ol, 1, -0.8), 0.55, k.filigree, y=-0.25, loc=(x, 0, z))
                edge(k, scaled(ol, 1, -0.8), 0.07, k.trim, -0.55, stem="tilet").location = (x, 0, z)
                ball(k, 0.16, k.trim, loc=(x, -0.6, z - 0.4), scale=(1, 0.6, 1))
            elif k.F:
                box(k, (1.45, 0.9, 1.6), k.hull, loc=(x, -0.2, z), bevel=0.14)
                for dx in (-0.5, 0.5):
                    for dz in (-0.6, 0.6):
                        ball(k, 0.11, k.metal, loc=(x + dx, -0.68, z + dz), scale=(1, 0.6, 1))
                box(k, (1.1, 0.1, 0.18), k.trim, loc=(x, -0.68, z), bevel=0.02)
            else:
                hexo = [(math.cos(math.radians(60 * i + 30)) * 0.85, math.sin(math.radians(60 * i + 30)) * 0.85) for i in range(6)]
                prism(k, hexo, 0.5, k.armour, y=-0.2, loc=(x, 0, z))
                edge(k, hexo, 0.06, k.trim, -0.47, stem="hext").location = (x, 0, z)
                ball(k, 0.18, k.glow, loc=(x, -0.5, z), scale=(1, 0.5, 1))
    if k.C:
        box(k, (5.3, 0.4, 0.35), k.trim, loc=(0, -0.1, 2.3), bevel=0.08)
        for x in (-2.5, 2.5):
            spire(k, 0.6, 1.8, (x, 0.0, 2.1))
    elif k.F:
        box(k, (5.4, 0.5, 0.5), k.armour, loc=(0, -0.15, 2.35), bevel=0.1)
        rivets(k, (-2.4, -0.42, 2.35), (2.4, -0.42, 2.35), 8)
    else:
        halo(k, 1.1, 0.08, k.trim, loc=(0, 0.1, 2.6), spikes=10, spike=0.4)


def kinetic_shield(k):
    """An arm shield in front of the wrist, facing -Y, about 8 x 10 mm."""
    # Clamp and arm straps behind the face.
    box(k, (1.6, 1.4, 2.4), k.metal, loc=(0, 0.6, 0), bevel=0.2)
    for z in (-0.6, 0.6):
        box(k, (2.4, 0.4, 0.35), k.metal, loc=(0, 0.2, z), bevel=0.08)
    if k.C:
        ol = heater(8.0, 10.0, top_peak=0.8)
        prism(k, ol, 0.5, k.trim, y=-0.2, bevel=0.15)          # gilded rim
        prism(k, scaled(ol, 0.93, 0.05), 0.5, k.filigree, y=-0.45)
        prism(k, scaled(ol, 0.62, 0.3), 0.3, k.hull, y=-0.75)   # crimson field
        edge(k, ol, 0.14, k.trim, -0.72, scale=0.94, dz=0.05)
        edge(k, ol, 0.1, k.trim, -0.92, scale=0.64, dz=0.3)
        cross(k, 3.6, -1.0, k.trim, centre=(0, 0.3), thick=0.26)
        ball(k, 0.42, k.glow, loc=(0, -1.15, 0.3), scale=(1, 0.5, 1))
        ring(k, 0.5, 0.09, k.trim, loc=(0, -1.12, 0.3))
    elif k.F:
        ol = chamfer_rect(7.6, 9.6, 1.4)
        prism(k, ol, 0.8, k.armour, y=-0.2, bevel=0.2, loc=(0, 0, -0.8))
        stencil(k, (6.0, 0.3, 4.2), loc=(0, -0.7, -0.6))
        prism(k, chamfer_rect(6.4, 2.2, 0.5), 0.3, k.hull, y=-0.7, loc=(0, 0, 2.3))
        box(k, (4.0, 0.6, 0.35), k.metal, loc=(0, -0.75, 1.0), bevel=0.05)    # view slit
        box(k, (3.6, 0.2, 0.12), k.glow, loc=(0, -0.95, 1.0), bevel=0.0)
        for x in (-3.4, 3.4):
            rivets(k, (x, -0.68, 2.8), (x, -0.68, -3.8), 8, r=0.17)
        for z in (3.65, -5.15):
            rivets(k, (-2.2, -0.68, z), (2.2, -0.68, z), 6, r=0.17)
        for x in (-2.6, 2.6):                                      # reinforcing ribs
            box(k, (0.4, 0.5, 8.6), k.metal, loc=(x, 0.4, -0.8), bevel=0.1)
    else:
        ol = vesica(6.4, 11.0, 20)
        prism(k, ol, 0.45, k.trim, y=-0.15, bevel=0.12, loc=(0, 0, -0.8))
        prism(k, scaled(ol, 0.92), 0.5, k.armour, y=-0.4, loc=(0, 0, -0.8))
        prism(k, scaled(ol, 0.55), 0.3, k.hull, y=-0.7, loc=(0, 0, -0.8))
        edge(k, ol, 0.08, k.trim, -0.88, scale=0.56, dz=-0.8)
        sunburst(k, 1.7, 16, -0.9, centre=(0, -0.4), boss=k.glow)
        halo(k, 2.0, 0.12, k.trim, loc=(0, 0.35, 4.2), spikes=14, spike=0.7)
        for z in (2.6, -3.6):
            ball(k, 0.25, k.glow, loc=(0, -0.72, z), scale=(1, 0.5, 1.6))


def smoke_launcher(k):
    """A bank of discharger tubes angled up and forward (core)."""
    tilt = (-0.5, 0, 0)
    if k.C:
        # Organ pipes: graduated tubes with gold collars on a gothic base.
        box(k, (4.2, 1.8, 1.2), k.filigree, loc=(0, 0.2, 0.6), bevel=0.2)
        box(k, (4.5, 2.0, 0.3), k.trim, loc=(0, 0.2, 1.3), bevel=0.08)
        for i, x in enumerate((-1.5, -0.75, 0, 0.75, 1.5)):
            h = 2.2 + (2 - abs(i - 2)) * 0.7
            cyl(k, 0.32, h, k.armour, loc=(x, 0.3, 1.4 + h / 2), verts=16)
            cyl(k, 0.4, 0.22, k.trim, loc=(x, 0.3, 1.4 + h - 0.1), verts=16)
            cyl(k, 0.22, 0.1, k.glow, loc=(x, 0.3, 1.45 + h), verts=12, bevel=0)
            shapes.lancet(k.name("mouth"), 0.3, 0.5, 0.2, k.trim, loc=(x, -0.02, 1.7), parent=k.root)
    elif k.F:
        box(k, (4.0, 2.0, 1.6), k.hull, loc=(0, 0.2, 0.8), bevel=0.2, panel_lines=1)
        rivets(k, (-1.7, -0.82, 1.35), (1.7, -0.82, 1.35), 6)
        stencil(k, (1.6, 0.2, 0.9), loc=(1.0, -0.84, 0.6))
        for x in (-1.3, 0, 1.3):
            base = Vector((x, 0.0, 1.6))
            tip = base + Vector((0, -1.3, 2.4))
            rod(k, base, tip, 0.5, k.metal, verts=18)
            cyl(k, 0.58, 0.3, k.trim, loc=tip, rot=along(base, tip), verts=18)
            cyl(k, 0.38, 0.1, k.armour, loc=tip + (tip - base).normalized() * 0.12, rot=along(base, tip), verts=14, bevel=0)
        shapes.pipe(k.name("hose"), [(-2.0, 0.6, 0.6), (-2.4, 0.2, 1.2), (-1.8, -0.3, 2.1)], 0.16, k.metal)
    else:
        # Three slender censers, ceramic with gold caps, venting a teal haze.
        box(k, (3.8, 1.6, 0.6), k.trim, loc=(0, 0.2, 0.3), bevel=0.12)
        for x in (-1.2, 0, 1.2):
            prof = [(0.01, 0), (0.45, 0.1), (0.55, 0.8), (0.42, 2.0), (0.3, 2.6), (0.38, 2.8), (0.2, 3.0), (0.01, 3.05)]
            base = Vector((x, 0.2, 0.6))
            up = lambda h: base + Euler(tilt).to_matrix() @ Vector((0, 0, h))  # noqa: E731
            lathe(k, prof, k.armour, loc=base, rot=tilt)
            r = ring(k, 0.56, 0.06, k.trim, loc=(0, 0, 0), axis="Z")
            r.location, r.rotation_euler = up(0.8), tilt
            r = ring(k, 0.34, 0.05, k.trim, loc=(0, 0, 0), axis="Z")
            r.location, r.rotation_euler = up(2.7), tilt
            ball(k, 0.2, k.glow, loc=up(3.0))
        halo(k, 0.8, 0.06, k.trim, loc=(0, 0.6, 2.2), spikes=8, spike=0.35)


# ------------------------------------------------------------------ mobility

def jump_jets(k):
    """A thruster pack on the outer thigh, nozzles pointing down."""
    if k.C:
        box(k, (4.0, 2.2, 2.6), k.filigree, loc=(0, 0.4, 0.6), bevel=0.3, taper=0.15)
        edge(k, chamfer_rect(4.0, 2.6, 0.4), 0.08, k.trim, -0.72, dz=0.6)
        for x in (-1.2, 1.2):
            bell(k, 1.05, 1.0, 2.4, k.metal, (x, 0.4, -0.7))
            ring(k, 0.98, 0.09, k.trim, loc=(x, 0.4, -3.05), axis="Z")
            ring(k, 0.62, 0.08, k.trim, loc=(x, 0.4, -1.4), axis="Z")
            cyl(k, 0.45, 0.06, k.glow, loc=(x, 0.4, -1.0), verts=16, bevel=0)
            spire(k, 0.75, 2.4, (x, 0.6, 1.9))
        lancets(k, 0.55, 1.0, -0.62, (0,), 0.2)
    elif k.F:
        box(k, (4.4, 2.4, 2.4), k.hull, loc=(0, 0.4, 0.4), bevel=0.25, panel_lines=1)
        cyl(k, 0.8, 2.6, k.armour, loc=(0, 1.7, 0.6), verts=20)            # fuel drum behind
        for z in (-0.4, 1.4):
            ring(k, 0.84, 0.1, k.metal, loc=(0, 1.7, z), axis="Z")
        for x in (-1.3, 1.3):
            bell(k, 1.2, 1.1, 2.0, k.metal, (x, 0.4, -0.8))
            ring(k, 1.15, 0.12, k.trim, loc=(x, 0.4, -2.75), axis="Z")
            cyl(k, 0.5, 0.06, k.glow, loc=(x, 0.4, -1.05), verts=16, bevel=0)
        rivets(k, (-1.9, -0.82, 1.4), (1.9, -0.82, 1.4), 7)
        rivets(k, (-1.9, -0.82, -0.6), (1.9, -0.82, -0.6), 7)
        stencil(k, (1.8, 0.2, 1.2), loc=(-0.9, -0.86, 0.4))
        shapes.pipe(k.name("feed"), [(-0.6, 1.7, 1.9), (-0.6, 0.6, 2.2), (-1.3, 0.4, 1.7)], 0.15, k.trim)
        box(k, (0.7, 0.8, 1.0), k.metal, loc=(1.6, 0.4, 1.95), bevel=0.1)    # stub exhaust
    else:
        # A slender ceramic pod, gold-banded nozzles with teal light, a small halo.
        lathe(k, [(0.01, -0.6), (0.9, -0.4), (1.2, 0.6), (1.0, 2.4), (0.5, 3.4), (0.01, 3.6)], k.armour, loc=(0, 0.6, -0.4))
        for z in (0.2, 1.6):
            ring(k, 1.13 if z < 1 else 1.0, 0.08, k.trim, loc=(0, 0.6, z), axis="Z")
        for x in (-1.15, 1.15):
            bell(k, 0.75, 0.7, 2.2, k.metal, (x, 0.5, -0.4))
            ring(k, 0.72, 0.1, k.trim, loc=(x, 0.5, -2.55), axis="Z")
            ring(k, 0.55, 0.08, k.glow, loc=(x, 0.5, -2.4), axis="Z")
            rod(k, (0, 0.6, 0.6), (x, 0.5, -0.3), 0.2, k.trim)
        halo(k, 0.8, 0.07, k.trim, loc=(0, 0.6, 3.9), spikes=10, spike=0.35)


def sprint_servos(k):
    """Geared actuators and a drive piston down the thigh."""
    if k.C:
        cyl(k, 1.7, 0.5, k.trim, loc=(0.4, 0, 1.1), rot=(0, math.pi / 2, 0), verts=28)
        cyl(k, 1.4, 0.6, k.filigree, loc=(0.7, 0, 1.1), rot=(0, math.pi / 2, 0), verts=28)
        sunburst_x(k, 1.2, 12, 1.05, (0, 1.1))
        cyl(k, 0.9, 0.45, k.trim, loc=(0.3, -0.5, -0.5), rot=(0, math.pi / 2, 0), verts=24)
        teeth(k, 1.75, 16, 0.4, (0, 1.1))
    elif k.F:
        cyl(k, 2.0, 0.7, k.metal, loc=(0.4, 0, 1.0), rot=(0, math.pi / 2, 0), verts=28)       # flywheel
        for i in range(6):
            a = math.pi * i / 3
            box(k, (0.25, 0.35, 1.5), k.trim, loc=(0.8, math.cos(a) * 0.95, 1.0 + math.sin(a) * 0.95), rot=(a + math.pi / 2, 0, 0), bevel=0.05)
        teeth(k, 2.05, 20, 0.5, (0, 1.0))
        cyl(k, 0.5, 0.9, k.hull, loc=(0.5, 0, 1.0), rot=(0, math.pi / 2, 0), verts=20)
        coil = [Vector((0.3 + 0.35 * math.cos(t), -1.2 + 0.35 * math.sin(t), -2.6 + t * 0.18)) for t in (i * 0.5 for i in range(30))]
        shapes.sweep(k.name("spring"), coil, 0.09, k.trim, parent=k.root)
    else:
        ring(k, 1.6, 0.18, k.trim, loc=(0.4, 0, 1.1), axis="X")
        ring(k, 1.15, 0.1, k.trim, loc=(0.5, 0, 1.1), axis="X")
        cyl(k, 0.9, 0.5, k.armour, loc=(0.35, 0, 1.1), rot=(0, math.pi / 2, 0), verts=32)
        ball(k, 0.5, k.glow, loc=(0.65, 0, 1.1), scale=(0.6, 1, 1))
        for i in range(8):
            a = math.pi * i / 4
            p = Vector((0.4, math.cos(a) * 1.15, 1.1 + math.sin(a) * 1.15))
            q = Vector((0.4, math.cos(a) * 1.6, 1.1 + math.sin(a) * 1.6))
            rod(k, p, q, 0.07, k.trim, verts=8)
    # The drive piston, common to all three.
    top, bot = Vector((0.2, -0.3, 0.6)), Vector((0.2, -1.2, -3.0))
    rod(k, top, top.lerp(bot, 0.55), 0.42, k.armour if not k.F else k.hull)
    rod(k, top.lerp(bot, 0.45), bot, 0.24, k.metal)
    cyl(k, 0.5, 0.25, k.trim, loc=top.lerp(bot, 0.55), rot=along(top, bot))
    ball(k, 0.35, k.trim, loc=bot)


def sunburst_x(k, r, rays, x, centre):
    """A sunburst facing +X (outwards on a left-side part)."""
    cy, cz = centre
    for i in range(rays):
        a = 2 * math.pi * i / rays
        L = r * (1.0 if i % 2 == 0 else 0.6)
        w = r * 0.15
        d = Vector((0, math.cos(a), math.sin(a)))
        n = Vector((0, -math.sin(a), math.cos(a)))
        base = Vector((x, cy, cz))
        tri = [base - n * w / 2, base + d * L, base + n * w / 2]
        bm = bmesh.new()
        f = [bm.verts.new(p) for p in tri]
        b = [bm.verts.new(p + Vector((0.15, 0, 0))) for p in tri]
        bm.faces.new(f)
        bm.faces.new(list(reversed(b)))
        for j in range(3):
            jj = (j + 1) % 3
            bm.faces.new((f[jj], f[j], b[j], b[jj]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        ob = mesh_obj(k.name("ray"), bm, k.trim, smooth=False, parent=k.root)
        shapes.decal_uv(ob)
    ball(k, r * 0.25, k.glow if k.C else k.trim, loc=(x + 0.15, cy, cz), scale=(0.5, 1, 1))


def teeth(k, r, n, w, centre):
    cy, cz = centre
    for i in range(n):
        a = 2 * math.pi * i / n
        box(k, (w, 0.35, 0.35), k.trim if not k.F else k.metal, loc=(0.4, cy + math.cos(a) * r, cz + math.sin(a) * r), rot=(a, 0, 0), bevel=0.05)


def gyro_stabilisers(k):
    """A gimballed flywheel in a cage on the thigh."""
    c = Vector((0, 0, 0.6))
    if k.C:
        ball(k, 1.15, k.filigree, loc=c)
        ring(k, 2.1, 0.2, k.trim, loc=c, axis="Y")
        ring(k, 1.75, 0.16, k.trim, loc=c, axis="X")
        ring(k, 1.4, 0.13, k.metal, loc=c, axis="Z")
        for a in range(4):
            t = math.pi / 2 * a + math.pi / 4
            ball(k, 0.2, k.glow, loc=c + Vector((math.cos(t) * 0.9, -0.7, math.sin(t) * 0.9)))
        rod(k, c + Vector((0, 0, -2.6)), c + Vector((0, 0, 2.6)), 0.2, k.metal)
        cross(k, 1.0, -1.2, k.trim, centre=(0, c.z), thick=0.15)
        spire(k, 0.55, 1.6, c + Vector((0, 0, 2.3)))
    elif k.F:
        ball(k, 1.2, k.hull, loc=c)
        for ax, r in (("Y", 2.1), ("X", 1.7)):
            ring(k, r, 0.28, k.metal, loc=c, axis=ax)
        for i in range(8):
            a = math.pi * i / 4
            ball(k, 0.14, k.trim, loc=c + Vector((math.cos(a) * 2.1, -0.24, math.sin(a) * 2.1)), scale=(1, 0.6, 1))
        box(k, (1.2, 1.0, 5.2), k.armour, loc=c + Vector((0, 1.2, 0)), bevel=0.15)
        gauge(k, 0.45, c + Vector((1.2, -0.9, -1.2)))
        rod(k, c + Vector((0, 0, -2.3)), c + Vector((0, 0, 2.3)), 0.25, k.metal)
    else:
        ball(k, 0.75, k.glow, loc=c)
        ball(k, 1.0, k.armour, loc=c, scale=(1, 0.35, 1))
        halo(k, 2.0, 0.1, k.trim, loc=c, axis="Y", spikes=16, spike=0.55)
        ring(k, 1.5, 0.09, k.trim, loc=c, axis="X")
        ring(k, 1.25, 0.07, k.trim, loc=c, axis="Z")
        rod(k, c + Vector((0, 0.8, -2.4)), c + Vector((0, 0.8, 1.6)), 0.15, k.metal)


def anchor_spikes(k):
    """Two ground spikes in a housing on the thigh, pointing down."""
    if k.C:
        box(k, (3.8, 1.4, 2.0), k.filigree, loc=(0, -0.2, 0.2), bevel=0.2)
        box(k, (4.0, 1.5, 0.3), k.trim, loc=(0, -0.2, 1.3), bevel=0.08)
        for x in (-1.1, 1.1):
            cyl(k, 0.7, 0.6, k.trim, loc=(x, -0.6, -0.9), verts=16)
            # A lance-head spike: fluted, gold-banded, with a fleur at the collar.
            lathe(k, [(0.55, 0), (0.5, -0.5), (0.4, -1.2), (0.3, -2.2), (0.01, -2.3)], k.armour, loc=(x, -0.6, -1.2), segments=8)
            lathe(k, [(0.36, 0), (0.3, -0.3), (0.01, -2.0)], k.trim, loc=(x, -0.6, -3.2), segments=8)
            ring(k, 0.36, 0.06, k.trim, loc=(x, -0.6, -3.2), axis="Z")
            ring(k, 0.5, 0.07, k.trim, loc=(x, -0.6, -1.65), axis="Z")
            for s in (-1, 1):
                cyl(k, 0.12, 0.8, k.trim, loc=(x + s * 0.45, -0.6, -1.3), rot=(0, s * 0.5, 0), verts=6, bevel=0, r2=0.01)
        spire(k, 0.5, 1.4, (0, -0.2, 1.35))
    elif k.F:
        box(k, (4.0, 1.6, 2.2), k.hull, loc=(0, -0.2, 0.2), bevel=0.2)
        rivets(k, (-1.7, -1.02, 1.0), (1.7, -1.02, 1.0), 6)
        rivets(k, (-1.7, -1.02, -0.6), (1.7, -1.02, -0.6), 6)
        stencil(k, (2.2, 0.2, 1.1), loc=(0, -1.05, 0.2))
        for x in (-1.2, 1.2):
            cyl(k, 0.7, 1.4, k.metal, loc=(x, -0.7, -1.4), verts=16)       # hydraulic sleeve
            rod(k, (x, -0.7, -2.0), (x, -0.7, -3.2), 0.38, k.trim)
            lathe(k, [(0.55, 0), (0.55, -0.3), (0.01, -1.4)], k.metal, loc=(x, -0.7, -3.2), segments=6)
            rod(k, (x + 0.6 * (1 if x > 0 else -1), -0.4, 0.6), (x, -0.7, -2.4), 0.13, k.metal)
    else:
        # Bone claws curling down out of a ceramic housing.
        lathe(k, [(0.01, 1.4), (1.0, 1.2), (1.5, 0.3), (1.3, -0.6), (0.01, -0.8)], k.armour, loc=(0, -0.3, 0), segments=24)
        ring(k, 1.45, 0.08, k.trim, loc=(0, -0.3, 0.2), axis="Z")
        for i, x in enumerate((-0.8, 0, 0.8)):
            pts = [Vector((x, -0.6, -0.5))]
            for t in range(1, 9):
                u = t / 8
                pts.append(Vector((x * (1 + u * 0.3), -0.6 - math.sin(u * 1.4) * 1.1, -0.5 - u * 3.2)))
            for j in range(len(pts) - 1):
                r = 0.32 * (1 - j / len(pts)) + 0.03
                cyl(k, r, (pts[j + 1] - pts[j]).length * 1.1, k.armour, loc=(pts[j] + pts[j + 1]) / 2, rot=along(pts[j], pts[j + 1]),
                    verts=10, bevel=0, r2=r * 0.8)
            ring(k, 0.36, 0.06, k.trim, loc=pts[1], axis="Z")
        ball(k, 0.35, k.glow, loc=(0, -1.6, 0.3), scale=(1, 0.5, 1.4))


# ------------------------------------------------------------------ systems

def targeting_array(k):
    """A rangefinder on a short mast (core), looking forward."""
    if k.C:
        cyl(k, 1.1, 0.6, k.trim, loc=(0, 0, 0.3), verts=8)
        cyl(k, 0.35, 1.8, k.metal, loc=(0, 0, 1.4))
        # A lantern scope: a gothic housing round a long gold-banded barrel.
        box(k, (1.8, 2.4, 1.8), k.filigree, loc=(0, 0, 2.9), bevel=0.2)
        lancets(k, 0.6, 1.0, -1.2, (0,), 2.3, depth=0.25)
        cyl(k, 0.55, 3.2, k.armour, loc=(0, -2.3, 3.1), rot=(math.pi / 2, 0, 0))
        for y in (-1.3, -2.5, -3.75):
            cyl(k, 0.65, 0.25, k.trim, loc=(0, y, 3.1), rot=(math.pi / 2, 0, 0))
        cyl(k, 0.42, 0.1, k.glow, loc=(0, -3.92, 3.1), rot=(math.pi / 2, 0, 0), bevel=0)
        spire(k, 0.6, 1.8, (0, 0.2, 3.8))
    elif k.F:
        box(k, (2.6, 1.6, 0.6), k.metal, loc=(0, 0, 0.3), bevel=0.1)
        rod(k, (0, 0, 0.6), (0, 0, 1.9), 0.35, k.metal)
        box(k, (4.2, 1.8, 1.6), k.hull, loc=(0, 0, 2.6), bevel=0.2)       # stereo rangefinder bar
        for x in (-1.6, 1.6):
            cyl(k, 0.62, 0.8, k.trim, loc=(x, -1.1, 2.6), rot=(math.pi / 2, 0, 0))
            cyl(k, 0.45, 0.1, k.glow, loc=(x, -1.52, 2.6), rot=(math.pi / 2, 0, 0), bevel=0)
        cyl(k, 0.5, 1.2, k.armour, loc=(0, -1.0, 2.7), rot=(math.pi / 2, 0, 0))
        rivets(k, (-1.0, -0.92, 3.25), (1.0, -0.92, 3.25), 5)
        rod(k, (1.6, 0.4, 3.4), (2.0, 0.4, 5.0), 0.07, k.metal)            # whip aerial
    else:
        # An eye in a halo on a slender stem.
        cyl(k, 0.9, 0.4, k.trim, loc=(0, 0, 0.2), verts=24)
        lathe(k, [(0.4, 0), (0.22, 1.0), (0.18, 2.2), (0.32, 2.5), (0.01, 2.6)], k.armour, loc=(0, 0, 0.4))
        ball(k, 0.85, k.armour, loc=(0, -0.2, 3.6))
        ball(k, 0.5, k.glow, loc=(0, -0.72, 3.6), scale=(1, 0.6, 1))
        ring(k, 0.58, 0.08, k.trim, loc=(0, -0.95, 3.6))
        halo(k, 1.7, 0.1, k.trim, loc=(0, 0.1, 3.6), spikes=12, spike=0.65)


def coolant_loop(k):
    """A coolant tank wound with radiator coil (core)."""
    def coil(r, z0, z1, turns, mat, rad):
        n = int(turns * 16)
        pts = [Vector((math.cos(2 * math.pi * turns * i / n) * r, math.sin(2 * math.pi * turns * i / n) * r, z0 + (z1 - z0) * i / n)) for i in range(n + 1)]
        shapes.sweep(k.name("coil"), pts, rad, mat, parent=k.root)
    if k.C:
        box(k, (3.4, 3.4, 0.5), k.trim, loc=(0, 0, 0.25), bevel=0.1)
        cyl(k, 1.1, 3.8, k.filigree, loc=(0, 0, 2.4), verts=8)
        for z in (0.8, 2.4, 4.1):
            cyl(k, 1.22, 0.25, k.trim, loc=(0, 0, z), verts=8)
        coil(1.4, 0.7, 4.0, 4, k.metal, 0.17)
        lancets(k, 0.5, 1.0, -1.06, (0,), 1.3, depth=0.2)
        spire(k, 1.0, 2.6, (0, 0, 4.25))
    elif k.F:
        box(k, (3.8, 3.4, 0.6), k.metal, loc=(0, 0, 0.3), bevel=0.12)
        cyl(k, 1.2, 3.6, k.hull, loc=(0, 0, 2.4), verts=24)
        lathe(k, [(1.2, 0), (1.0, 0.5), (0.4, 0.8), (0.01, 0.85)], k.armour, loc=(0, 0, 4.2))
        for z in (0.9, 3.9):
            ring(k, 1.25, 0.12, k.metal, loc=(0, 0, z), axis="Z")
        coil(1.5, 0.8, 3.8, 5, k.trim, 0.17)
        gauge(k, 0.5, (0, -1.32, 2.6))
        cyl(k, 0.3, 0.6, k.trim, loc=(0, 0, 5.2), verts=12)
    else:
        lathe(k, [(0.01, 0), (0.8, 0.1), (1.3, 0.9), (1.35, 2.2), (0.9, 3.4), (0.45, 3.9), (0.6, 4.1), (0.01, 4.2)], k.armour, loc=(0, 0, 0.2))
        coil(1.42, 0.9, 3.0, 3, k.glow, 0.1)
        for z in (0.7, 3.25):
            ring(k, 1.15 if z < 1 else 1.05, 0.08, k.trim, loc=(0, 0, z), axis="Z")
        halo(k, 0.9, 0.07, k.trim, loc=(0, 0.2, 4.8), spikes=10, spike=0.4)


def overcharged_boiler(k):
    """A furnace stack on the back or chest (core)."""
    if k.C:
        cyl(k, 2.0, 0.6, k.trim, loc=(0, 0, 0.3), verts=8)
        cyl(k, 1.7, 4.2, k.filigree, loc=(0, 0, 2.7), verts=8)
        cyl(k, 1.95, 0.4, k.trim, loc=(0, 0, 4.9), verts=8)
        for i in range(4):
            a = i * math.pi / 2
            ob = shapes.lancet(k.name("win"), 0.9, 2.2, 0.3, k.trim, glow=k.glow, parent=k.root,
                               loc=(math.sin(a) * 1.6, -math.cos(a) * 1.6, 1.4))
            ob.rotation_euler = (0, 0, a)
        spire(k, 1.4, 4.6, (0, 0, 5.1))
        for i in range(4):
            a = i * math.pi / 2 + math.pi / 4
            spire(k, 0.45, 1.4, (math.sin(a) * 1.55, -math.cos(a) * 1.55, 5.1))
    elif k.F:
        box(k, (4.0, 3.2, 3.4), k.hull, loc=(0, 0, 1.7), bevel=0.25, panel_lines=1)
        box(k, (2.6, 0.3, 1.8), k.metal, loc=(0, -1.62, 1.5), bevel=0.06)       # firebox door
        for x in (-0.9, -0.3, 0.3, 0.9):
            box(k, (0.22, 0.25, 1.4), k.glow, loc=(x, -1.7, 1.5), bevel=0)
        for x in (-0.6, 0, 0.6):
            box(k, (0.18, 0.4, 1.6), k.metal, loc=(x, -1.8, 1.5), bevel=0.03)
        rivets(k, (-1.8, -1.62, 3.1), (1.8, -1.62, 3.1), 8)
        stencil(k, (1.6, 0.2, 0.9), loc=(-0.8, -1.62, 2.7))
        for x, h in ((-1.1, 3.6), (0.9, 2.6)):                                   # smokestacks
            cyl(k, 0.5, h, k.metal, loc=(x, 0.6, 3.4 + h / 2), verts=20)
            cyl(k, 0.65, 0.35, k.trim, loc=(x, 0.6, 3.4 + h), verts=20)
            ring(k, 0.53, 0.08, k.trim, loc=(x, 0.6, 3.4 + h * 0.4), axis="Z")
        gauge(k, 0.45, (1.2, -1.62, 2.7))
    else:
        lathe(k, [(0.01, 0), (1.9, 0.1), (2.0, 0.6), (1.6, 0.8), (1.7, 3.0), (1.2, 4.2), (0.5, 4.8), (0.01, 5.0)], k.armour, loc=(0, 0, 0), segments=40)
        ring(k, 1.95, 0.1, k.trim, loc=(0, 0, 0.6), axis="Z")
        ring(k, 1.62, 0.08, k.trim, loc=(0, 0, 3.0), axis="Z")
        for i in range(3):
            a = (i - 1) * math.radians(50)
            ob = prism(k, vesica(0.7, 2.0, 10), 0.3, k.glow, y=0, bevel=0.03, loc=(math.sin(a) * 1.68, -math.cos(a) * 1.68, 1.9), stem="win")
            ob.rotation_euler = (0, 0, a)
        sunburst(k, 0.8, 12, -1.1, centre=(0, 3.6), boss=k.glow, thick=0.12)
        halo(k, 1.6, 0.11, k.trim, loc=(0, 0.3, 5.6), spikes=16, spike=0.6)


def spotter_drone(k):
    """A launch post with its drone docked on top (core)."""
    cyl(k, 1.0, 0.6, k.metal if not k.R else k.trim, loc=(0, 0, 0.3), verts=20)
    rod(k, (0, 0, 0.6), (0, 0, 2.4), 0.2, k.metal)
    c = Vector((0, 0, 3.4))
    if k.C:
        # A lantern with gilded wings.
        cyl(k, 0.9, 1.6, k.filigree, loc=c, verts=8)
        lancets(k, 0.45, 0.9, -0.86, (0,), c.z - 0.5, depth=0.15)
        spire(k, 0.9, 1.6, c + Vector((0, 0, 0.8)))
        for s in (-1, 1):
            wing = [(0, 0), (s * 2.8, 0.9), (s * 3.2, 0.3), (s * 2.4, -0.2), (s * 1.6, -0.5), (0, -0.4)]
            w = prism(k, [(x, z) for x, z in wing], 0.12, k.trim, y=0, bevel=0.03, loc=(s * 0.7, 0, c.z + 0.1), stem="wing")
            w.rotation_euler = (0, 0, s * -0.25)
        ball(k, 0.28, k.glow, loc=c + Vector((0, -0.85, 0.2)), scale=(1, 0.5, 1))
    elif k.F:
        box(k, (1.8, 2.2, 1.0), k.hull, loc=c, bevel=0.15)
        for x in (-1, 1):
            for y in (-1, 1):
                p = c + Vector((x * 1.6, y * 1.6, 0.2))
                rod(k, c + Vector((x * 0.7, y * 0.8, 0.2)), p, 0.12, k.metal, verts=8)
                ring(k, 0.75, 0.08, k.metal, loc=p, axis="Z")
                box(k, (1.3, 0.12, 0.05), k.trim, loc=p + Vector((0, 0, 0.1)), rot=(0, 0, x * y * 0.6), bevel=0)
        cyl(k, 0.35, 0.6, k.trim, loc=c + Vector((0, -1.2, -0.1)), rot=(math.pi / 2, 0, 0))
        cyl(k, 0.25, 0.08, k.glow, loc=c + Vector((0, -1.52, -0.1)), rot=(math.pi / 2, 0, 0), bevel=0)
    else:
        ball(k, 0.8, k.armour, loc=c, scale=(1, 1, 1.15))
        ball(k, 0.38, k.glow, loc=c + Vector((0, -0.6, 0)), scale=(1, 0.55, 1))
        halo(k, 1.35, 0.09, k.trim, loc=c, axis="Z", spikes=12, spike=0.5)
        ring(k, 1.05, 0.06, k.trim, loc=c, axis="Y")


def field_repair_rig(k):
    """A folding crane arm with a welding head (core)."""
    base_mat = k.filigree if k.C else k.hull if k.F else k.armour
    cyl(k, 1.1, 0.8, base_mat, loc=(0, 0, 0.4), verts=8 if k.C else 24)
    sh = Vector((0, 0, 1.2))
    el = Vector((0, 0.4, 4.0))
    hd = Vector((0, -3.0, 4.6))
    arm_mat = k.armour if not k.F else k.trim
    rod(k, sh, el, 0.38 if not k.R else 0.26, arm_mat)
    rod(k, el, hd, 0.3 if not k.R else 0.2, arm_mat)
    ball(k, 0.5, k.trim, loc=el)
    ball(k, 0.42, k.metal, loc=sh)
    for a, b in ((sh, el), (el, hd)):
        rod(k, a.lerp(b, 0.15) + Vector((0, 0.5, 0)), a.lerp(b, 0.75) + Vector((0, 0.45, 0)), 0.1, k.metal, verts=8)
    if k.C:
        for t in (0.3, 0.7):
            cyl(k, 0.46, 0.18, k.trim, loc=sh.lerp(el, t), rot=along(sh, el))
        # A censer welding head: a small gilded lantern hung below the arm.
        cyl(k, 0.55, 0.9, k.trim, loc=hd + Vector((0, 0, -0.6)), verts=8)
        ball(k, 0.3, k.glow, loc=hd + Vector((0, 0, -1.2)))
        spire(k, 0.4, 1.0, hd + Vector((0, 0, -0.15)))
    elif k.F:
        lathe(k, [(0.5, 0), (0.6, -0.4), (0.3, -1.0), (0.1, -1.4)], k.metal, loc=hd)
        cyl(k, 0.12, 0.3, k.glow, loc=hd + Vector((0, 0, -1.55)), verts=8, bevel=0)
        shapes.pipe(k.name("hose"), [sh + Vector((0.6, 0, 0)), el + Vector((0.6, 0.3, -0.3)), hd + Vector((0.5, 0.3, 0))], 0.13, k.metal)
        box(k, (1.6, 1.2, 1.0), k.armour, loc=(0.9, 0.6, 1.3), bevel=0.12)     # gas bottle cradle
        cyl(k, 0.45, 2.0, k.trim, loc=(-1.0, 0.5, 1.6), verts=16)
    else:
        for s in (-1, 1):                                                        # fine claw tips
            a = hd + Vector((s * 0.25, 0, 0))
            b = hd + Vector((s * 0.5, -0.4, -1.0))
            cyl(k, 0.12, (b - a).length, k.trim, loc=(a + b) / 2, rot=along(a, b), verts=8, bevel=0, r2=0.02)
        ball(k, 0.3, k.glow, loc=hd + Vector((0, -0.3, -0.6)))
        ring(k, 0.45, 0.06, k.trim, loc=hd, axis="Z")
        halo(k, 0.6, 0.05, k.trim, loc=el + Vector((0, 0.3, 0.2)), spikes=8, spike=0.3)


BUILDERS = {
    "ablative-plating": ablative_plating,
    "reactive-shell": reactive_shell,
    "kinetic-shield": kinetic_shield,
    "smoke-launcher": smoke_launcher,
    "jump-jets": jump_jets,
    "sprint-servos": sprint_servos,
    "gyro-stabilisers": gyro_stabilisers,
    "anchor-spikes": anchor_spikes,
    "targeting-array": targeting_array,
    "coolant-loop": coolant_loop,
    "overcharged-boiler": overcharged_boiler,
    "spotter-drone": spotter_drone,
    "field-repair-rig": field_repair_rig,
}


def build(item, faction, location=(0, 0, 0)):
    root = kit.empty(f"item_{item}@{faction}", location, size=1.0)
    BUILDERS[item](Kit(faction, root))
    return root


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("items", nargs="*", default=list(BUILDERS))
    ap.add_argument("--faction", choices=FACTIONS, action="append")
    ap.add_argument("--render", metavar="DIR", help="review renders only, no publish")
    ap.add_argument("--samples", type=int, default=32)
    ap.add_argument("--size", type=int, default=256, help="baked texture size")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    a = ap.parse_args(argv)
    for item in a.items:
        for faction in a.faction or FACTIONS:
            kit.reset_scene()
            root = build(item, faction)
            if a.render:
                kit.render.studio()
                out = Path(a.render) / f"{item}@{faction}.png"
                kit.render.shot(kit.meshes(root), out, az=30, el=14, samples=a.samples, res=(480, 480), margin=0.9)
                kit.render.post(str(out))
            else:
                kit.publish(root, size=a.size, source=HERE / "blend" / f"item_{item}@{faction}.blend")


if __name__ == "__main__":
    main()
