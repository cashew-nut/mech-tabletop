"""Package 8b: shared equipment built per faction. Only the Kinetic Shield is left here: the other shared items are
card-only or cut (data/equipment.json, docs/rules.md) and have no model.

Every shared item gets one part per faction, `item_<id>@<faction>`, because
the baked textures carry the faction's materials (blackened iron and gold,
rusted red plate and brass, bone ceramic and pale gold). The forms change too:
Covenant gear is gothic (lancet windows, spires, crosses, sunbursts), Foundries
gear is riveted, stencilled and blunt, Reliquary gear is slender ceramic with
gold rings, halos and teal light.

Items are built at Scout scale (the web scales them by frame) with the origin
at the attachment point, Z up and the front facing -Y.

    ~/bvenv/bin/python assets/blender/parts/equipment/items.py                 # publish the 3 faction versions
    ~/bvenv/bin/python assets/blender/parts/equipment/items.py kinetic-shield  # one item, three factions
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


# ------------------------------------------------------------------ mobility

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


# ------------------------------------------------------------------ systems

BUILDERS = {
    "kinetic-shield": kinetic_shield,
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
