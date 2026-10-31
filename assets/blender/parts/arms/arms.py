"""Package 4: upper arms, forearms and hands for all three factions.

    ~/bvenv/bin/python parts/arms/arms.py                    # publish every arm, forearm and hand in PARTS
    ~/bvenv/bin/python parts/arms/arms.py covenant_hand_titan  # publish one part
    ~/bvenv/bin/python parts/arms/arms.py --review OUT       # review renders beside the art, no publish

Parts are built in place on the walker's left side (+X) from the frame's
joints, then moved into joint space. Each limb segment is laid out in its own
frame: origin at the upper joint, local -Z down the limb, +X outward (the
back of the hand), -Y forward (the thumb side).

  Iron Covenant  black iron lames edged in gold, a fanned elbow cop, a filigree
                 vambrace plate and articulated three-segment gauntlet fingers.
  Ashen Foundries  riveted red hull plate over greasy iron, brass-collared
                 hydraulic rams, a drum elbow and a heavy three-finger fist with
                 hydraulic lines to every knuckle.
  Reliquary      long bone-white ceramic shells caged in gold ribs, a teal glow
                 seam, an exposed relic spine and skeletal gold talons.

Hands come posed: `open`, `grip` or `fist` (POSES). Each frame gets its
faction's default pose; classes listed in CLASS_HANDS get their own.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # assets/blender
import kit  # noqa: E402
from kit import shapes  # noqa: E402
from kit.core import apply_all, parent_keep  # noqa: E402
from kit.skeleton import Skeleton  # noqa: E402

# Frames each faction's classes use (data/chassis.json).
FRAMES = {
    "covenant": ("striker", "bulwark", "titan"),
    "foundries": ("scout", "bulwark"),
    "reliquary": ("scout", "striker", "titan"),
}
DEFAULT_POSE = {"covenant": "open", "foundries": "grip", "reliquary": "open"}
# Class-specific hands: (faction, frame, pose).
CLASS_HANDS = {
    "lancer": ("covenant", "striker", "grip"),
    "brute": ("foundries", "bulwark", "fist"),
    "goliath": ("reliquary", "titan", "grip"),
    "paladin": ("covenant", "titan", "grip"),
}
# Class hands cocked at the wrist (degrees about X, the fist's grip turning
# from level to point down and forward): the Paladin holds its swords
# point-down as in the north-star render.
HAND_PITCH = {"paladin": 52}
# Curl per finger joint (degrees, towards the palm), thumb curl, finger splay.
POSES = {
    "open": {"curl": (10, 14, 10), "thumb": (5, 12, 10), "splay": 7},
    "grip": {"curl": (58, 72, 48), "thumb": (28, 30, 24), "splay": 2},
    "fist": {"curl": (86, 96, 74), "thumb": (48, 44, 40), "splay": 0},
}
# Thinnest finger or rod radius, so Scout hands still print (mm).
MIN_R = 0.3
# Filigree and tread tile size on these small parts (mm).
DECAL_MM = 2.5

COMPONENTS = ("arm", "forearm", "hand")


# ------------------------------------------------------------------ placement helpers

def axis(a, b):
    """A frame at `a` with local -Z pointing at `b` and +X outward; and the length."""
    d = b - a
    z = -d.normalized()
    y = Vector((0, 1, 0))
    y = (y - y.dot(z) * z).normalized()
    x = y.cross(z)
    rot = Matrix((x, y, z)).transposed().to_4x4()
    return Matrix.Translation(a) @ rot, d.length


def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def R(x=0.0, y=0.0, z=0.0):
    """Rotation in degrees."""
    return Euler((math.radians(x), math.radians(y), math.radians(z))).to_matrix().to_4x4()


class Builder:
    """Collects the pieces of one part so they can be joined under its root."""

    def __init__(self, faction):
        self.faction = faction
        self.m = kit.materials.library(faction)
        self.pieces = []

    def put(self, ob, M):
        ob.matrix_world = M @ ob.matrix_basis
        self.pieces.append(ob)
        return ob

    def pts(self, M, local):
        return [M @ Vector(p) for p in local]

    # Shapes in a local frame.
    def box(self, name, M, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), **kw):
        ob = shapes.box_plate(name, size, mat, **kw)
        return self.put(ob, M @ T(*loc) @ R(*rot))

    def cyl(self, name, M, r, depth, mat, loc=(0, 0, 0), rot=(0, 0, 0), **kw):
        kw.setdefault("bevel", r * 0.12)
        ob = shapes.cylinder(name, r, depth, mat, **kw)
        return self.put(ob, M @ T(*loc) @ R(*rot))

    def ball(self, name, M, r, mat, loc=(0, 0, 0), scale=(1, 1, 1)):
        ob = shapes.sphere(name, r, mat, scale=scale, segments=14)
        return self.put(ob, M @ T(*loc))

    def sweep(self, name, M, local, r, mat, **kw):
        ob = shapes.sweep(name, self.pts(M, local), r, mat, **kw)
        self.pieces.append(ob)
        return ob

    def rod(self, name, M, a, b, r, mat, r2=None, verts=10):
        """A cylinder between two local points."""
        a, b = Vector(a), Vector(b)
        d = b - a
        ob = shapes.cylinder(name, r, d.length, mat, verts=verts, bevel=r * 0.15, r2=r2)
        q = d.to_track_quat("Z", "Y")
        return self.put(ob, M @ T(*((a + b) / 2)) @ q.to_matrix().to_4x4())

    def rivets(self, name, M, a, b, n, r, mat, normal):
        nrm = (M.to_3x3() @ Vector(normal)).normalized()
        ob = shapes.rivet_row(name, M @ Vector(a), M @ Vector(b), n, r, mat, normal=nrm)
        self.pieces.append(ob)
        return ob

    def shell(self, name, M, profile, a0, a1, mat, thick, trim=None, trim_r=0.0, edges=("top", "bottom", "sides"), segments=40, fit_uv=False):
        """A curved armour plate turned round local Z between two azimuths
        (0 = front, 90 = outward), with raised trim on its edges. `fit_uv`
        stretches one copy of the decal over the plate, for stencils."""
        ob = shapes.lathe(name, profile, mat, a0=a0, a1=a1, segments=segments)
        if fit_uv:
            uv = ob.data.uv_layers["Decal"].data
            us, vs = [d.uv[0] for d in uv], [d.uv[1] for d in uv]
            for d in uv:
                d.uv = ((d.uv[0] - min(us)) / (max(us) - min(us)), 1 - (d.uv[1] - min(vs)) / (max(vs) - min(vs)))
        kit.mod(ob, "SOLIDIFY", thickness=thick, offset=0)
        kit.mod(ob, "BEVEL", width=thick * 0.3, segments=2, limit_method="ANGLE")
        self.put(ob, M)
        if trim is not None and trim_r:
            lift = thick * 0.5 + trim_r * 0.4

            def ring(r, z, n=32):
                return [(math.sin(math.radians(a0 + (a1 - a0) * i / n)) * (r + lift),
                         -math.cos(math.radians(a0 + (a1 - a0) * i / n)) * (r + lift), z) for i in range(n + 1)]
            if "top" in edges:
                self.sweep(name + "_trim_top", M, ring(*profile[0]), trim_r, trim)
            if "bottom" in edges:
                self.sweep(name + "_trim_bot", M, ring(*profile[-1]), trim_r, trim)
            if "sides" in edges:
                for k, a in enumerate((a0, a1)):
                    s, c = math.sin(math.radians(a)), -math.cos(math.radians(a))
                    self.sweep(f"{name}_trim_side{k}", M, [(s * (r + lift), c * (r + lift), z) for r, z in profile], trim_r * 0.8, trim)
        return ob

    def ribs(self, name, M, profile, azimuths, r, mat, lift):
        """Raised ribs running down a turned profile at the given azimuths."""
        for a in azimuths:
            s, c = math.sin(math.radians(a)), -math.cos(math.radians(a))
            self.sweep(f"{name}_{a:g}", M, [(s * (pr + lift), c * (pr + lift), z) for pr, z in profile], r, mat)

    def hoop(self, name, M, rad, z, r, mat, a0=0.0, a1=360.0, n=36):
        pts = [(math.sin(math.radians(a0 + (a1 - a0) * i / n)) * rad, -math.cos(math.radians(a0 + (a1 - a0) * i / n)) * rad, z) for i in range(n + 1)]
        return self.sweep(name, M, pts, r, mat, cyclic=(a1 - a0) >= 360)

    def finish(self, root):
        """Apply every modifier, join the pieces into one mesh under `root`."""
        objs = [apply_all(o) for o in self.pieces]
        for o in objs:
            shapes.decal_uv(o, DECAL_MM)  # pieces that have no layout of their own
        objs = [o for o in objs if o.type == "MESH" and len(o.data.polygons)]
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = root.name + "_mesh"
        ob.data.name = ob.name
        parent_keep(ob, root)
        return ob


def profile(z0, z1, r0, r1, bulge=0.0, n=10, lip=0.0):
    """(radius, z) from z0 to z1, tapering r0 to r1 with a belly and a flared lip."""
    out = []
    for i in range(n + 1):
        t = i / n
        r = r0 + (r1 - r0) * t + bulge * math.sin(math.pi * t) + lip * max(0.0, (t - 0.8) / 0.2) ** 2
        out.append((r, z0 + (z1 - z0) * t))
    return out


# ------------------------------------------------------------------ upper arms (joint: shoulder)

def arm(b, sk):
    sh, el = sk.joint("shoulder"), sk.joint("elbow")
    M, L = axis(sh, el)
    r = sk.radius("arm")
    m = b.m
    f = b.faction
    # Shoulder ball (under the pauldron) and the elbow hinge axle.
    b.ball("socket", M, r * 0.95, m["metal"])
    b.cyl("axle", M, r * 0.42, r * 2.1, m["metal"], loc=(0, 0, -L), rot=(0, 90, 0), verts=20)
    for sx in (-1, 1):
        b.box(f"yoke{sx}", M, (r * 0.22, r * 1.15, r * 1.3), m["metal"], loc=(sx * r * 0.82, 0, -L + r * 0.35), bevel=r * 0.05)
        b.cyl(f"axle_cap{sx}", M, r * 0.34, r * 0.12, m["metal"], loc=(sx * r * 1.0, 0, -L), rot=(0, 90, 0), verts=20)

    if f == "covenant":
        b.cyl("core", M, r * 0.62, L * 0.9, m["metal"], loc=(0, 0, -L * 0.5), verts=20)
        # Three overlapping lames, each flared and edged in gold; the middle one carries the filigree.
        bands = [(-0.16, -0.40), (-0.36, -0.62), (-0.58, -0.84)]
        for k, (z0, z1) in enumerate(bands):
            rr = r * (1.0 + 0.07 * k)
            prof = profile(z0 * L, z1 * L, rr, rr * 1.06, bulge=r * 0.05, lip=r * 0.12)
            mat = m["filigree"] if k == 1 else m["armour"]
            b.shell(f"lame{k}", M, prof, -70, 250, mat, r * 0.14, trim=m["trim"], trim_r=r * 0.06, edges=("bottom", "sides"))
        # Studs along the lame edges.
        for k, (_, z1) in enumerate(bands):
            rr = r * (1.0 + 0.07 * k) * 1.06 + r * 0.14
            for a in (-40, 20, 160, 220):
                s, c = math.sin(math.radians(a)), -math.cos(math.radians(a))
                b.ball(f"stud{k}_{a}", M, r * 0.06, m["trim"], loc=(s * rr, c * rr, z1 * L + r * 0.12))
        # Piston and cables down the inside, where the lames leave the arm open.
        b.rod("piston", M, (-r * 0.75, r * 0.15, -L * 0.1), (-r * 0.7, r * 0.1, -L * 0.88), r * 0.13, m["metal"])
        b.rod("piston_rod", M, (-r * 0.72, r * 0.12, -L * 0.6), (-r * 0.7, r * 0.1, -L * 0.95), r * 0.08, m["trim"])
        for k, (y, z) in enumerate(((-r * 0.35, -L * 0.3), (-r * 0.35, -L * 0.7))):
            b.cyl(f"collar{k}", M, r * 0.66, r * 0.12, m["trim"], loc=(0, 0, z), verts=24)

    elif f == "foundries":
        b.cyl("core", M, r * 0.7, L * 0.92, m["metal"], loc=(0, 0, -L * 0.5), verts=16)
        # A heavy riveted hull plate wrapped round the outside, a stencilled number panel on it.
        prof = profile(-L * 0.12, -L * 0.82, r * 1.12, r * 1.18, bulge=r * 0.03, n=6)
        b.shell("plate", M, prof, -40, 200, m["armour"], r * 0.2, segments=12)
        b.shell("hullplate", M, profile(-L * 0.2, -L * 0.74, r * 1.29, r * 1.33, n=4), 45, 135, m["hull"], r * 0.08, segments=8)
        b.shell("number", M, profile(-L * 0.32, -L * 0.6, r * 1.36, r * 1.37, n=3), 62, 118, m["stencil"], r * 0.04, segments=6, fit_uv=True)
        for a in (-35, 50, 130, 195):
            s, c = math.sin(math.radians(a)), -math.cos(math.radians(a))
            rr = r * 1.31
            b.rivets(f"rivets{a}", M, (s * rr, c * rr, -L * 0.15), (s * rr, c * rr, -L * 0.79), 6, r * 0.07, m["metal"], (s, c, 0))
        for z in (-0.14, -0.8):
            b.hoop(f"band{z}", M, r * 1.3, z * L, r * 0.08, m["metal"], -40, 200, n=14)
        # The hydraulic ram on the front: housing, brass collars and a bright rod.
        b.rod("ram", M, (0, -r * 1.15, -L * 0.05), (0, -r * 1.25, -L * 0.62), r * 0.28, m["metal"], verts=16)
        b.rod("ram_rod", M, (0, -r * 1.25, -L * 0.6), (0, -r * 1.2, -L * 1.0), r * 0.15, m["trim"], verts=12)
        for k, t in enumerate((0.12, 0.55)):
            b.rod(f"ram_collar{k}", M, (0, -r * (1.15 + 0.1 * t), -L * (t - 0.025)), (0, -r * (1.15 + 0.1 * t), -L * (t + 0.025)), r * 0.34, m["trim"], verts=16)
        # Fat hoses round the back.
        b.sweep("hose", M, [(-r * 0.4, r * 0.9, -L * 0.02), (-r * 0.2, r * 1.3, -L * 0.35), (-r * 0.3, r * 1.25, -L * 0.7), (-r * 0.5, r * 0.8, -L * 0.95)], r * 0.14, m["metal"])

    else:  # reliquary
        # A relic spine of stacked vertebrae down the inside, the ceramic shell over the outside.
        b.cyl("core", M, r * 0.5, L * 0.92, m["metal"], loc=(0, 0, -L * 0.5), verts=16)
        for k in range(7):
            z = -L * (0.12 + 0.11 * k)
            b.cyl(f"vertebra{k}", M, r * 0.68, r * 0.16, m["metal"], loc=(-r * 0.1, 0, z), verts=16)
        prof = profile(-L * 0.08, -L * 0.86, r * 0.95, r * 0.88, bulge=r * 0.16, n=12, lip=r * 0.08)
        b.shell("shell", M, prof, -60, 230, m["armour"], r * 0.12, trim=m["trim"], trim_r=r * 0.05)
        b.ribs("rib", M, prof[1:-1], (40, 140), r * 0.045, m["trim"], r * 0.1)
        b.hoop("cage", M, prof[3][0] + r * 0.1, prof[3][1], r * 0.04, m["trim"], -60, 230)
        # The teal seam down the outside.
        b.sweep("seam", M, [(pr2 + r * 0.06, 0, z) for pr2, z in prof[1:-1]], r * 0.035, m["glow"])


# ------------------------------------------------------------------ forearms (joint: elbow)

def forearm(b, sk):
    el, wr = sk.joint("elbow"), sk.joint("wrist")
    M, L = axis(el, wr)
    r = sk.radius("forearm")
    m = b.m
    f = b.faction
    b.cyl("knuckle", M, r * 0.62, r * 1.6, m["metal"], rot=(0, 90, 0), verts=20)
    b.ball("wristball", M, r * 0.5, m["metal"], loc=(0, 0, -L))

    if f == "covenant":
        b.cyl("core", M, r * 0.62, L * 0.92, m["metal"], loc=(0, 0, -L * 0.5), verts=20)
        # Couter: a domed elbow cop with a gold rim and a swept-back fan.
        cop = (r * 0.35, r * 0.55, r * 0.1)
        b.ball("cop", M, r * 0.85, m["armour"], loc=cop, scale=(0.75, 0.55, 0.9))
        b.hoop("cop_rim", M @ T(*cop) @ R(70, 0, 15), r * 0.72, 0, r * 0.07, m["trim"])
        b.box("cop_fan", M, (r * 0.1, r * 0.9, r * 1.1), m["armour"], loc=(r * 0.62, r * 0.7, r * 0.05), rot=(-30, 0, 12), taper=0.8, bevel=r * 0.04)
        # Vambrace: flared towards the wrist, edged in gold, a filigree plate on the outside.
        prof = profile(-L * 0.14, -L * 0.9, r * 0.98, r * 1.2, bulge=r * 0.05, n=12, lip=r * 0.16)
        b.shell("vambrace", M, prof, -80, 260, m["armour"], r * 0.15, trim=m["trim"], trim_r=r * 0.065)
        inlay = [(pr + r * 0.1, z) for pr, z in prof if -L * 0.74 <= z <= -L * 0.28]
        b.shell("inlay", M, inlay, 58, 122, m["filigree"], r * 0.05, trim=m["trim"], trim_r=r * 0.05, segments=12)
        b.ribs("ridge", M, prof[1:-1], (20,), r * 0.06, m["trim"], r * 0.12)
        for k, z in enumerate((-0.92, -0.97)):
            b.cyl(f"cuff{k}", M, r * (0.85 - 0.08 * k), r * 0.1, m["trim"] if k == 0 else m["metal"], loc=(0, 0, z * L), verts=28)
        b.rod("tendon", M, (-r * 0.6, r * 0.3, -L * 0.12), (-r * 0.55, r * 0.25, -L * 0.88), r * 0.1, m["metal"])
        b.rod("tendon2", M, (-r * 0.6, -r * 0.3, -L * 0.12), (-r * 0.55, -r * 0.25, -L * 0.88), r * 0.1, m["metal"])

    elif f == "foundries":
        # The piston arm: a banded iron barrel with two rams and a riveted cuff.
        b.cyl("barrel", M, r * 1.0, L * 0.78, m["armour"], loc=(0, 0, -L * 0.48), r2=r * 1.12, verts=24, bevel=r * 0.08)
        for k, t in enumerate((0.16, 0.42, 0.68)):
            b.cyl(f"collar{k}", M, r * (1.17 + 0.05 * t), r * 0.2, m["trim"], loc=(0, 0, -L * t), verts=28)
            b.rivets(f"collar_rivets{k}", M, (r * 1.16, 0, -L * t), (r * 1.16, 0, -L * t), 1, r * 0.06, m["metal"], (1, 0, 0))
        prof = profile(-L * 0.2, -L * 0.62, r * 1.16, r * 1.2, n=4)
        b.shell("hullplate", M, prof, 35, 145, m["hull"], r * 0.14, segments=8)
        for a in (40, 140):
            s, c = math.sin(math.radians(a)), -math.cos(math.radians(a))
            b.rivets(f"plate_rivets{a}", M, (s * r * 1.27, c * r * 1.27, -L * 0.22), (s * r * 1.27, c * r * 1.27, -L * 0.6), 4, r * 0.06, m["metal"], (s, c, 0))
        for k, (x, y) in enumerate(((-r * 0.75, -r * 0.85), (-r * 0.75, r * 0.85))):
            b.rod(f"ram{k}", M, (x, y, -L * 0.02), (x * 1.05, y * 1.05, -L * 0.55), r * 0.24, m["metal"], verts=16)
            b.rod(f"ram{k}_rod", M, (x * 1.05, y * 1.05, -L * 0.5), (x * 1.1, y * 1.1, -L * 0.92), r * 0.13, m["trim"], verts=12)
            b.rod(f"ram{k}_collar", M, (x, y, -L * 0.08), (x, y, -L * 0.14), r * 0.3, m["trim"], verts=16)
            b.rod(f"ram{k}_eye", M, (x * 1.1 - r * 0.15, y * 1.1, -L * 0.93), (x * 1.1 + r * 0.15, y * 1.1, -L * 0.93), r * 0.16, m["metal"], verts=12)
        # Heavy cuff: four riveted blocks round the wrist.
        for k, a in enumerate((0, 90, 180, 270)):
            s, c = math.sin(math.radians(a)), -math.cos(math.radians(a))
            b.box(f"cuff{k}", M, (r * 0.95, r * 0.35, r * 0.55), m["armour"], loc=(s * r * 1.02, c * r * 1.02, -L * 0.88), rot=(0, 0, -a), bevel=r * 0.06)
            b.rivets(f"cuff_rivets{k}", M, (s * r * 1.2 - c * r * 0.3, c * r * 1.2 + s * r * 0.3, -L * 0.88), (s * r * 1.2 + c * r * 0.3, c * r * 1.2 - s * r * 0.3, -L * 0.88), 2, r * 0.06, m["metal"], (s, c, 0))
        # A drum guard on the elbow.
        b.cyl("drum", M, r * 0.85, r * 0.6, m["armour"], loc=(r * 0.75, 0, 0), rot=(0, 90, 0), verts=20)
        b.cyl("drum_rim", M, r * 0.9, r * 0.12, m["metal"], loc=(r * 1.05, 0, 0), rot=(0, 90, 0), verts=24)
        b.sweep("hose", M, [(-r * 0.3, r * 1.0, r * 0.2), (-r * 0.2, r * 1.35, -L * 0.3), (-r * 0.4, r * 1.2, -L * 0.75), (-r * 0.5, r * 0.6, -L * 0.98)], r * 0.13, m["metal"])

    else:  # reliquary
        # Two exposed bones under a long ceramic vambrace caged in gold.
        for k, y in enumerate((-r * 0.28, r * 0.28)):
            b.rod(f"bone{k}", M, (-r * 0.15, y, -L * 0.05), (-r * 0.2, y * 0.8, -L * 0.95), max(MIN_R, r * 0.2), m["metal"], verts=12)
        b.ball("elbow_cop", M, r * 0.75, m["armour"], loc=(r * 0.2, r * 0.45, 0), scale=(0.8, 0.7, 1.0))
        b.hoop("cop_ring", M @ T(r * 0.2, r * 0.45, 0) @ R(80, 0, 0), r * 0.6, 0, r * 0.05, m["trim"])
        prof = profile(-L * 0.12, -L * 0.92, r * 1.08, r * 0.7, bulge=r * 0.1, n=14, lip=r * 0.1)
        b.shell("vambrace", M, prof, -50, 220, m["armour"], r * 0.12, trim=m["trim"], trim_r=r * 0.055)
        b.ribs("rib", M, prof[1:-1], (35, 145), r * 0.045, m["trim"], r * 0.1)
        # Gold tracery: two pointed arches meeting on the outside, like the board's vambrace.
        for k, z0 in enumerate((-0.3, -0.62)):
            pts = []
            for a in range(35, 146, 5):
                z = L * (z0 + 0.12 * (1 - abs(a - 90) / 55))
                pr = min(prof, key=lambda p: abs(p[1] - z))[0] + r * 0.1
                pts.append((math.sin(math.radians(a)) * pr, -math.cos(math.radians(a)) * pr, z))
            b.sweep(f"tracery{k}", M, pts, r * 0.04, m["trim"])
        b.sweep("seam", M, [(pr2 + r * 0.06, 0, z) for pr2, z in prof[2:-2]], r * 0.035, m["glow"])
        b.cyl("wrist_ring", M, r * 0.72, r * 0.14, m["trim"], loc=(0, 0, -L * 0.95), verts=28)
        b.cyl("wrist_glow", M, r * 0.66, r * 0.06, m["glow"], loc=(0, 0, -L * 0.99), verts=28, bevel=0)


# ------------------------------------------------------------------ hands (joint: wrist)

def finger(b, name, M, segs, r, pose_curl, style):
    """A chain of jointed segments from M down local -Z, curling towards -X (the palm)."""
    m = b.m
    for k, (ln, curl) in enumerate(zip(segs, pose_curl)):
        M = M @ R(0, curl, 0)
        last = k == len(segs) - 1
        if style == "covenant":
            b.cyl(f"{name}_k{k}", M, r * 0.9, r * 2.0, m["metal"], rot=(90, 0, 0), verts=10)
            b.cyl(f"{name}_s{k}", M, r * 0.7, ln * 0.9, m["metal"], loc=(0, 0, -ln * 0.5), verts=8, r2=r * (0.55 if last else 0.66))
            # Back plate on each segment, gold-edged on the first two, pointed at the tip.
            plate = (r * 0.5, r * 1.75, ln * (0.98 if last else 0.82))
            b.box(f"{name}_p{k}", M, plate, m["armour"], loc=(r * 0.62, 0, -ln * 0.5), taper=-0.55 if last else -0.1, bevel=r * 0.12)
            if not last:
                b.box(f"{name}_g{k}", M, (r * 0.54, r * 1.8, r * 0.28), m["trim"], loc=(r * 0.64, 0, -ln * 0.88), bevel=r * 0.08)
            else:
                b.ball(f"{name}_tip", M, r * 0.55, m["armour"], loc=(-r * 0.05, 0, -ln * 0.95), scale=(1, 1, 1.4))
        elif style == "foundries":
            b.cyl(f"{name}_k{k}", M, r * 0.95, r * 2.2, m["metal"], rot=(90, 0, 0), verts=12)
            b.cyl(f"{name}_kc{k}", M, r * 0.6, r * 2.35, m["trim"], rot=(90, 0, 0), verts=12)
            b.box(f"{name}_s{k}", M, (r * 1.7, r * 1.9, ln * 0.92), m["armour"], loc=(r * 0.05, 0, -ln * 0.5), taper=-0.15 if last else 0.0, bevel=r * 0.18)
            b.rivets(f"{name}_r{k}", M, (r * 0.92, 0, -ln * 0.3), (r * 0.92, 0, -ln * 0.7), 2, r * 0.14, m["metal"], (1, 0, 0))
        else:  # reliquary talons
            b.ball(f"{name}_k{k}", M, r * 1.1, m["trim"], scale=(1, 1, 1.2))
            if last:
                # A curved talon: two tapering pieces bending further in.
                b.rod(f"{name}_t0", M, (0, 0, 0), (-r * 0.2, 0, -ln * 0.55), r * 0.85, m["trim"], r2=r * 0.6)
                b.rod(f"{name}_t1", M, (-r * 0.2, 0, -ln * 0.55), (-r * 1.0, 0, -ln * 1.05), r * 0.62, m["trim"], r2=r * 0.4)
                b.rod(f"{name}_t2", M, (-r * 1.0, 0, -ln * 1.05), (-r * 2.4, 0, -ln * 1.45), r * 0.4, m["trim"], r2=0.02)
            else:
                b.rod(f"{name}_s{k}", M, (0, 0, -r * 0.6), (0, 0, -ln + r * 0.6), r * 0.75, m["trim"], r2=r * 0.85)
                b.cyl(f"{name}_band{k}", M, r * 0.95, r * 0.4, m["metal"], loc=(0, 0, -ln * 0.5), verts=10)
        M = M @ T(0, 0, -ln)
    return M


def hand_frame(sk, pitch=0.0):
    """The hand's frame at the wrist: local -Z down the palm, +X the back of the hand."""
    el, wr = sk.joint("elbow"), sk.joint("wrist")
    # The hand carries on along the forearm, tipped a little back towards vertical.
    d = (wr - el).normalized().lerp(Vector((0, 0, -1)), 0.5)
    M, _ = axis(wr, wr + d)
    if pitch:
        M = T(*wr) @ R(pitch, 0, 0) @ T(*(-wr)) @ M
    return M


def grip_point(sk, pitch=0.0):
    """Where a gripping Covenant fist closes, in world space (left side): the
    point a held weapon's grip should pass through."""
    rf = sk.radius("forearm")
    pt, pl, flen = rf * 0.72, rf * 1.45, rf * 2.7
    return hand_frame(sk, pitch) @ Vector((-pt * 0.5 - flen * 0.3, 0.0, -pl - flen * 0.15))


def hand(b, sk, pose, pitch=0.0):
    wr = sk.joint("wrist")
    rf = sk.radius("forearm")
    M = hand_frame(sk, pitch)
    m = b.m
    f = b.faction
    P = POSES[pose]
    curl, tcurl, splay = P["curl"], P["thumb"], P["splay"]

    if f == "covenant":
        hw, pl, pt = rf * 1.9, rf * 1.45, rf * 0.72
        fr = max(MIN_R, hw / 7.6)
        flen = rf * 2.7
        b.ball("wrist", M, rf * 0.5, m["metal"])
        b.box("palm", M, (pt, hw * 0.94, pl), m["metal"], loc=(0, 0, -pl * 0.55), bevel=rf * 0.08)
        # Two curved gauntlet plates over the back of the hand, the upper one
        # carrying the filigree, both edged in gold; then a plate per knuckle.
        R0 = hw * 0.85
        half = math.degrees(math.asin(min(0.95, hw * 0.55 / R0)))
        C = M @ T(pt * 0.5 - R0, 0, 0) @ R(0, 0, 0)
        b.shell("back0", C, profile(rf * 0.25, -pl * 0.55, R0 + rf * 0.05, R0 + rf * 0.14, bulge=rf * 0.06, n=6),
                90 - half, 90 + half, m["filigree"], rf * 0.12, trim=m["trim"], trim_r=rf * 0.055, segments=16)
        b.shell("back1", C, profile(-pl * 0.45, -pl * 0.98, R0 + rf * 0.12, R0 + rf * 0.1, bulge=rf * 0.03, n=4, lip=rf * 0.06),
                90 - half * 0.92, 90 + half * 0.92, m["armour"], rf * 0.12, trim=m["trim"], trim_r=rf * 0.05, segments=16)
        b.ball("boss", M, rf * 0.16, m["trim"], loc=(pt * 0.5 + rf * 0.22, 0, -pl * 0.18), scale=(0.6, 1, 1))
        lengths = (0.95, 1.0, 0.95, 0.8)
        seg = (0.42, 0.32, 0.26)
        n = 4
    elif f == "foundries":
        hw, pl, pt = rf * 2.2, rf * 1.7, rf * 1.15
        fr = max(MIN_R, hw / 6.4)
        flen = rf * 1.75
        b.ball("wrist", M, rf * 0.6, m["metal"])
        b.box("palm", M, (pt, hw, pl), m["armour"], loc=(0, 0, -pl * 0.55), bevel=rf * 0.12)
        b.box("back", M, (pt * 0.3, hw * 1.02, pl * 0.82), m["armour"], loc=(pt * 0.6, 0, -pl * 0.5), bevel=rf * 0.08)
        b.box("back_panel", M, (pt * 0.1, hw * 0.55, pl * 0.32), m["hull"], loc=(pt * 0.77, 0, -pl * 0.3), bevel=rf * 0.03)
        for y in (-hw * 0.42, hw * 0.42):
            b.rivets(f"back_rivets{y:.2f}", M, (pt * 0.77, y, -pl * 0.18), (pt * 0.77, y, -pl * 0.82), 3, rf * 0.07, m["metal"], (1, 0, 0))
        lengths = (1.0, 1.0, 0.9)
        seg = (0.45, 0.33, 0.27)
        n = 3
    else:
        hw, pl, pt = rf * 1.7, rf * 1.6, rf * 0.55
        fr = max(MIN_R, rf * 0.13)
        flen = rf * 3.3
        b.ball("wrist", M, rf * 0.5, m["trim"])
        # A narrow ceramic back plate over skeletal metacarpals.
        R0 = hw * 0.8
        half = math.degrees(math.asin(min(0.95, hw * 0.4 / R0)))
        C = M @ T(pt * 0.5 - R0, 0, 0)
        b.shell("back", C, profile(rf * 0.1, -pl * 0.7, R0 + rf * 0.02, R0 + rf * 0.08, bulge=rf * 0.08, n=6),
                90 - half, 90 + half, m["armour"], rf * 0.1, trim=m["trim"], trim_r=rf * 0.04, segments=12)
        b.ball("back_gem", M, rf * 0.13, m["glow"], loc=(pt * 0.5 + rf * 0.16, 0, -pl * 0.3))
        lengths = (0.95, 1.0, 0.95, 0.82)
        seg = (0.4, 0.33, 0.27)
        n = 4

    # Fingers: index at the front (-Y), fanned by the pose's splay.
    for i in range(n):
        y = (-0.5 + (i + 0.5) / n) * hw * 0.92
        spread = (i - (n - 1) / 2) * splay
        base = M @ T(0, y, -pl) @ R(spread, 0, 0)
        if f == "reliquary":
            # Metacarpal bones from the wrist to each knuckle.
            b.rod(f"meta{i}", M, (0, y * 0.35, -pl * 0.05), (0, y, -pl), max(MIN_R, fr * 0.8), m["trim"])
        segs = [flen * lengths[i] * s for s in seg]
        finger(b, f"f{i}", base, segs, fr, curl, f)
        if f == "foundries":
            # A hydraulic line from the wrist to every knuckle.
            b.sweep(f"line{i}", M, [(pt * 0.85, y * 0.4, -pl * 0.05), (pt * 0.95, y * 0.85, -pl * 0.6), (pt * 0.75, y, -pl * 0.98)], max(MIN_R * 0.7, fr * 0.14), m["metal"])
            b.cyl(f"line{i}_fit", M, max(MIN_R, fr * 0.26), fr * 0.4, m["trim"], loc=(pt * 0.75, y, -pl * 0.98), rot=(0, 90, 0), verts=10)

    # Thumb: from the front of the palm, angled forward and across.
    tb = M @ T(-pt * 0.15, -hw * 0.5, -pl * (0.55 if f == "reliquary" else 0.35)) @ R(-28, 0, 0) @ R(0, 0, -20)
    if f == "foundries":
        b.cyl("thumb_ram", tb, fr * 0.5, flen * 0.5, m["metal"], loc=(fr * 0.9, 0, -flen * 0.2))
    tsegs = [flen * s * (0.7 if f == "reliquary" else 1.0) for s in ((0.4, 0.32, 0.28) if f != "foundries" else (0.42, 0.34, 0.3))]
    finger(b, "thumb", tb, tsegs, fr * (1.1 if f != "reliquary" else 1.0), tcurl, f)


# ------------------------------------------------------------------ publishing

def part_list():
    """(name, faction, frame, component, pose) for every part this package owns."""
    out = []
    for faction, frames in FRAMES.items():
        for frame in frames:
            for comp in COMPONENTS:
                out.append((f"{faction}_{comp}_{frame}", faction, frame, comp, DEFAULT_POSE[faction]))
    for cls, (faction, frame, pose) in CLASS_HANDS.items():
        out.append((f"{faction}_hand_{cls}", faction, frame, "hand", pose))
    return out


def build(name, faction, frame, comp, pose):
    sk = Skeleton(faction, frame)
    root = kit.empty(name)
    b = Builder(faction)
    if comp == "arm":
        arm(b, sk)
    elif comp == "forearm":
        forearm(b, sk)
    else:
        hand(b, sk, pose, HAND_PITCH.get(name.rsplit("_", 1)[-1], 0.0))
    b.finish(root)
    root["kit_pose"] = pose if comp == "hand" else ""
    return root


def publish(only=None):
    todo = [p for p in part_list() if only is None or p[0] in only]
    for name, faction, frame, comp, pose in todo:
        kit.reset_scene()
        root = build(name, faction, frame, comp, pose)
        kit.skeleton.to_joint(root, faction, frame, comp)
        # Small parts: 512 px sets keep a class's arms near 1.5 MB once compressed.
        kit.publish(root, size=512)


def review(out_dir, factions=None, poses=False):
    """Render each faction's arm assembled on its showcase frame, and its hand close up, beside the art."""
    out = Path(out_dir)
    show = {"covenant": ("titan", "covenant_gauntlet", "detail_covenant_gauntlet"),
            "foundries": ("bulwark", "detail_foundries_piston_arm", None),
            "reliquary": ("titan", "detail_reliquary_arm", "detail_reliquary_claw")}
    for faction, (frame, arm_art, hand_art) in show.items():
        if factions and faction not in factions:
            continue
        kit.reset_scene()
        kit.render.studio()
        roots = [build(f"{faction}_{c}_{frame}", faction, frame, c, DEFAULT_POSE[faction]) for c in COMPONENTS]
        objs = [o for r in roots for o in kit.meshes(r)]
        shots = []
        for az, el in ((60, 8), (115, 14)):
            p = out / f"{faction}-arm-{az}.png"
            kit.render.shot(objs, p, az=az, el=el, samples=40, res=(560, 900), margin=0.72)
            kit.render.post(p)
            shots.append(p)
        kit.render.compare(shots, arm_art, out / f"{faction}-arm-compare.png", title=f"{faction} arm, {frame} frame")
        hand_objs = kit.meshes(roots[2])
        hs = []
        for az, el in ((70, 10), (20, 25)):
            p = out / f"{faction}-hand-{az}.png"
            kit.render.shot(hand_objs, p, az=az, el=el, samples=40, res=(700, 700), margin=0.75)
            kit.render.post(p)
            hs.append(p)
        kit.render.compare(hs, hand_art or arm_art, out / f"{faction}-hand-compare.png", title=f"{faction} hand ({DEFAULT_POSE[faction]})")
        if poses:
            ps = []
            for pose in POSES:
                kit.reset_scene()
                kit.render.studio()
                r = build(f"{faction}_hand_{frame}", faction, frame, "hand", pose)
                p = out / f"{faction}-pose-{pose}.png"
                kit.render.shot(kit.meshes(r), p, az=25, el=15, samples=32, res=(520, 600), margin=0.8)
                kit.render.post(p)
                ps.append(p)
            kit.render.compare(ps, None, out / f"{faction}-poses.png", labels=list(POSES), title=f"{faction} hand poses")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    if args and args[0] == "--review":
        review(args[1], factions=args[2:] or None, poses=True)
    else:
        publish(set(args) or None)
