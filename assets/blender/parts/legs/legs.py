"""Package 5: legs and feet (thigh, shin and foot) for every faction and frame.

    bvenv/bin/python assets/blender/parts/legs/legs.py [faction ...] [--frames titan striker]
        [--publish] [--render DIR] [--samples 48] [--size 1024]

With no factions it builds every faction on the frames its classes use
(data/chassis.json). Parts are named `<faction>_<component>_<frame>`, so every
class on a frame shares them, and are modelled for the walker's left (+X).

* Iron Covenant: gothic plate. A keeled cuisse with a pointed hem, a winged
  knee cop, a fluted greave over twin calf pistons and a sabaton of
  overlapping lames ending in a pointed toe, all edged in gold with
  filigree inlays.
* Ashen Foundries: industrial. Box-section thighs between exposed hydraulic
  rams, a hub-and-bolt knee drum, a riveted red shin block over a big rear
  ram and hoses, and a flat three-toed tread foot.
* Reliquary: long, thin digitigrade legs. Ceramic plates on a dark teal
  skeleton, bound with gold rings; the shin breaks backwards at a glowing
  hock with a gold spur, and the foot is a gold-clawed talon.

`--render DIR` puts the legs on the faction's frame (stand-ins for the rest,
both sides) and writes a full-height shot, a leg close-up and a sheet
beside the matching crop of the concept art (legs_<faction> in crops.json).
`--publish` bakes each part and exports it to apps/web/public/parts/kit/.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))  # assets/blender
import kit  # noqa: E402
from kit import shapes  # noqa: E402
from kit.core import bmesh, mesh_obj, mod  # noqa: E402
from kit.skeleton import BASE_THICKNESS, Skeleton, build_frame  # noqa: E402
from common import chassis_frames, load, script_args  # noqa: E402

COMPONENTS = ("thigh", "shin", "foot")


# ------------------------------------------------------------------ helpers


def _f(v):
    return v if callable(v) else (lambda *_a, v=v: v)


def wrap(name, rad, az0, az1, z0, z1, mat, parent, thick=0.3, nu=20, nv=10, trim=None, tr=0.1, inlay=None, margin=0.16, bevel=True, warp=None):
    """A curved armour plate round a limb's local Z axis, between two azimuths
    (0 = front, -Y; positive towards +X). `rad(az, z)` is the outer radius;
    `z0` and `z1` may be functions of azimuth, so hems can come to a point.
    `trim` edges it with a swept bead, `inlay` lays a filigree sheet inside
    the edge."""
    lo, hi, rf = _f(z0), _f(z1), rad

    def pt(az, z, lift=0.0):
        a = math.radians(az)
        r = rf(az, z) + lift
        v = Vector((math.sin(a) * r, -math.cos(a) * r, z))
        return warp(v) if warp else v

    def grid_pts(u0, u1, v0, v1, lift):
        rows = []
        for j in range(nv + 1):
            v = v0 + (v1 - v0) * j / nv
            row = []
            for i in range(nu + 1):
                az = az0 + (az1 - az0) * (u0 + (u1 - u0) * i / nu)
                row.append(pt(az, lo(az) + (hi(az) - lo(az)) * v, lift))
            rows.append(row)
        return rows

    def sheet(nm, rows, m, t, solid=True):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("Decal")
        g = [[bm.verts.new(p) for p in row] for row in rows]
        span = abs(math.radians(az1 - az0)) * rf(0.5 * (az0 + az1), 0.5 * (lo(0) + hi(0)))
        height = abs(hi(0) - lo(0))
        shapes._grid_faces(bm, g, uv, (max(1.0, span / 2.5), max(1.0, height / 2.5)))
        ob = mesh_obj(nm, bm, m, parent=parent)
        if solid:
            mod(ob, "SOLIDIFY", thickness=t, offset=-1)
            if bevel:
                mod(ob, "BEVEL", width=t * 0.3, segments=1, limit_method="ANGLE")
        return ob

    ob = sheet(name, grid_pts(0, 1, 0, 1, 0.0), mat, thick)
    if trim is not None:
        edge = [(az0 + (az1 - az0) * i / nu, 0.0) for i in range(nu + 1)]
        edge += [(az1, j / nv) for j in range(1, nv + 1)]
        edge += [(az1 - (az1 - az0) * i / nu, 1.0) for i in range(1, nu + 1)]
        edge += [(az0, 1 - j / nv) for j in range(1, nv)]
        pts = [pt(a, lo(a) + (hi(a) - lo(a)) * v, tr * 0.4) for a, v in edge[::2]]
        shapes.sweep(name + "_trim", pts, tr, trim, cyclic=True, parent=parent, resolution=1)
    if inlay is not None:
        # A single raised sheet: the filigree is in the texture, so it needs no thickness.
        sheet(name + "_inlay", grid_pts(margin, 1 - margin, margin * 1.2, 1 - margin * 1.2, 0.04), inlay, 0.0, solid=False)
    return ob


def along(name, a, b, r, mat, parent, r2=None, verts=20, bevel=None):
    """A cylinder from point a to point b (parent space)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    ob = shapes.cylinder(name, r, d.length, mat, loc=(a + b) / 2, parent=parent, verts=verts,
                         bevel=r * 0.12 if bevel is None else bevel, r2=r2)
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return ob


def axle(name, centre, r, length, mat, parent, verts=24, bevel=None):
    """A cylinder along X (hinges, drums)."""
    return shapes.cylinder(name, r, length, mat, loc=centre, rot=(0, math.pi / 2, 0), parent=parent, verts=verts,
                           bevel=r * 0.1 if bevel is None else bevel)


def piston(name, a, b, r, barrel, rod, parent, collar=None):
    """A hydraulic ram: barrel from a, polished rod to b, eyes at both ends."""
    a, b = Vector(a), Vector(b)
    out = [along(name, a, a.lerp(b, 0.6), r, barrel, parent),
           along(name + "_rod", a.lerp(b, 0.5), b, r * 0.55, rod, parent, verts=16)]
    out.append(shapes.sphere(name + "_eye0", r * 1.05, barrel, loc=a, parent=parent, segments=16))
    out.append(shapes.sphere(name + "_eye1", r * 0.8, barrel, loc=b, parent=parent, segments=16))
    if collar is not None:
        for k, t in enumerate((0.05, 0.58)):
            out.append(along(f"{name}_collar{k}", a.lerp(b, t), a.lerp(b, t + 0.05), r * 1.25, collar, parent, verts=20))
    return out


def ring(name, z, r, tube, mat, parent, centre=(0, 0), n=24, squash=(1.0, 1.0)):
    pts = [(centre[0] + math.sin(2 * math.pi * i / n) * r * squash[0], centre[1] - math.cos(2 * math.pi * i / n) * r * squash[1], z)
           for i in range(n)]
    return shapes.sweep(name, pts, tube, mat, cyclic=True, parent=parent, resolution=1)


def bone(root, a, b):
    """An empty at joint a whose local -Z runs to b: limb pieces are laid out
    in it with z from 0 (a) down to -length (b)."""
    e = kit.empty(root.name + "_bone", a, parent=root, size=1)
    # The shortest turn from straight up, so the limb's front stays facing -Y.
    e.rotation_euler = Vector((0, 0, 1)).rotation_difference(Vector(a) - Vector(b)).to_euler()
    return e, (Vector(b) - Vector(a)).length


def forward(root, origin=(0, 0, 0)):
    """An empty whose local Z points forward (-Y) and local +Y up, for
    plates wrapped round the length of a foot: azimuth 180 is the top."""
    e = kit.empty(root.name + "_fwd", origin, parent=root, size=1)
    e.rotation_euler = Euler((math.radians(90), 0, 0))
    return e


def gear(name, centre, r, length, mat, tooth_mat, parent, teeth=12):
    """A drum along X with a toothed ring round its middle."""
    c = Vector(centre)
    out = [axle(name, c, r, length, mat, parent)]
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        t = shapes.box_plate(f"{name}_tooth{k}", (length * 0.35, r * 0.22, r * 0.22), tooth_mat, bevel=r * 0.03,
                             loc=c + Vector((0, math.sin(a) * r * 1.05, math.cos(a) * r * 1.05)), parent=parent)
        t.rotation_euler = (-a, 0, 0)
        out.append(t)
    return out


def bolts(name, centre, r, n, size, mat, parent, side):
    """A ring of bolt heads on a hub facing +X (side 1) or -X (side -1)."""
    c = Vector(centre)
    bm = bmesh.new()
    for k in range(n):
        a = 2 * math.pi * k / n
        geom = bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=size, radius2=size, depth=size)
        for v in geom["verts"]:
            v.co = c + Vector((side * (v.co.z + size * 0.5), v.co.x + math.sin(a) * r, v.co.y + math.cos(a) * r))
    ob = mesh_obj(name, bm, mat, smooth=False, parent=parent)
    shapes.decal_uv(ob)
    return ob


def square(az, n):
    """Superellipse factor: >1 at the corners, so a round plate reads as a squared box section."""
    a = math.radians(az)
    return 1.0 / (abs(math.sin(a)) ** n + abs(math.cos(a)) ** n) ** (1.0 / n)


def bump(az, at, width):
    return math.exp(-((az - at) / width) ** 2)


class Leg:
    """The three parts of one faction's leg on one frame, built in place on
    the walker's left side, then moved into joint space."""

    def __init__(self, faction, frame):
        self.faction, self.frame = faction, frame
        self.sk = sk = Skeleton(faction, frame)
        self.m = kit.materials.library(faction)
        self.hip, self.knee, self.ankle = sk.joint("hip"), sk.joint("knee"), sk.joint("ankle")
        self.H = sk.H
        self.rt, self.rs = sk.radius("thigh"), sk.radius("shin")
        # Detail sizes follow the frame's height so a Scout's trim is not a Titan's.
        self.u = sk.H / 50.0
        self.ground = BASE_THICKNESS

    def build(self):
        parts = {}
        for comp in COMPONENTS:
            # Pieces are placed in world space round a root at the origin, so
            # the part stands in place on the walker; kit.skeleton.to_joint()
            # moves them into the joint's space before publishing.
            root = kit.empty(kit.part_name(self.faction, comp, self.frame), (0, 0, 0), size=self.u * 2)
            root["kit_component"] = comp
            getattr(self, f"{self.faction}_{comp}")(root)
            parts[comp] = root
        bpy.context.view_layer.update()
        return parts

    # -------------------------------------------------------------- Iron Covenant

    def covenant_thigh(self, root):
        m, u, r = self.m, self.u, self.rt
        g, L = bone(root, self.hip, self.knee)
        # The steel underneath: a ball at the hip, a tapered core and a rear ram.
        shapes.sphere("hip_ball", r * 0.62, m["metal"], parent=g, segments=24)
        ring("hip_ring", -r * 0.1, r * 0.64, 0.1 * u, m["trim"], g)
        along("core", (0, 0, -0.1 * L), (0, 0, -0.97 * L), r * 0.58, m["metal"], g, r2=r * 0.5)
        piston("ram", (0, r * 0.7, -0.12 * L), (0, r * 0.55, -0.9 * L), r * 0.2, m["metal"], m["trim"], g)
        for k, az in enumerate((-120, 130)):
            a = math.radians(az)
            piston(f"strut{k}", (math.sin(a) * r * 0.6, -math.cos(a) * r * 0.6, -0.15 * L),
                   (math.sin(a) * r * 0.5, -math.cos(a) * r * 0.5, -0.85 * L), r * 0.11, m["metal"], m["metal"], g)

        # The cuisse: a squared, keeled front plate with a pointed hem...
        def cuisse_r(az, z):
            t = -z / L
            return r * (1.02 - 0.12 * t) * square(az, 3.2) * (1 + 0.06 * bump(az, 0, 14))
        wrap("cuisse", cuisse_r, -80, 86, lambda az: -0.8 * L - 0.14 * L * bump(az, 4, 40), lambda az: -0.03 * L + 0.05 * L * bump(az, 60, 30),
             m["armour"], g, thick=0.32 * u, trim=m["trim"], tr=0.1 * u)
        # ...a raised centre plate over it, gold-edged, with a filigree field...
        mid = lambda az, z: cuisse_r(az, z) + 0.32 * u  # noqa: E731
        wrap("cuisse_panel", mid, -34, 34, lambda az: -0.68 * L - 0.12 * L * bump(az, 0, 18), lambda az: -0.12 * L + 0.04 * L * bump(az, 0, 15),
             m["armour"], g, thick=0.28 * u, trim=m["trim"], tr=0.1 * u, inlay=m["filigree"], margin=0.14, nu=18)
        # ...a keel bead, gold studs along the top and a gothic cross boss.
        shapes.sweep("cuisse_keel", [(0, -mid(0, z) - 0.36 * u, z) for z in (-0.16 * L, -0.42 * L, -0.66 * L)], 0.08 * u, m["trim"], parent=g)
        shapes.rivet_row("cuisse_studs", (-0.62 * r, -cuisse_r(-38, -0.07 * L) - 0.08 * u, -0.07 * L),
                         (0.62 * r, -cuisse_r(38, -0.07 * L) - 0.08 * u, -0.07 * L), 7, 0.09 * u, m["trim"], parent=g)
        cz, cy = -0.34 * L, -mid(0, -0.34 * L) - 0.38 * u
        shapes.box_plate("cross_v", (0.18 * u, 0.12 * u, 0.36 * L), m["trim"], bevel=0.04 * u, loc=(0, cy, cz), parent=g)
        shapes.box_plate("cross_h", (0.9 * r, 0.12 * u, 0.18 * u), m["trim"], bevel=0.04 * u, loc=(0, cy, cz + 0.06 * L), parent=g)
        # Outer tasset: a flared plate over the hip, overlapping the cuisse.
        wrap("tasset", lambda az, z: r * 1.14 * square(az, 3.2) + 0.15 * u * (z / L), 56, 150, lambda az: -0.55 * L - 0.1 * L * bump(az, 100, 25),
             0.1 * L, m["armour"], g, thick=0.3 * u, trim=m["trim"], tr=0.1 * u, inlay=m["filigree"], margin=0.2)
        shapes.rivet_row("tasset_studs", (r * 1.2, -r * 0.2, 0.02 * L), (r * 1.2, -r * 0.2, -0.45 * L), 4, 0.09 * u, m["trim"], parent=g,
                         normal=(1, 0, 0))
        # Rear and inner lames over the ram.
        for k in range(3):
            z1 = -0.1 * L - k * 0.24 * L
            wrap(f"rear_lame{k}", lambda az, z, k=k: r * (0.98 + 0.04 * k), 150, 250, z1 - 0.28 * L, z1, m["armour"], g,
                 thick=0.22 * u, nu=16, nv=4, trim=m["trim"], tr=0.06 * u)
        wrap("inner_plate", lambda az, z: r * 0.92, -150, -84, -0.7 * L, -0.12 * L, m["metal"], g, thick=0.2 * u, nu=12, nv=6)

    def covenant_shin(self, root):
        m, u, r = self.m, self.u, self.rs
        g, L = bone(root, self.knee, self.ankle)
        # Knee hinge and the poleyn: a pointed cop with a spiked boss and a fan on the outside.
        axle("knee_hinge", (0, 0, 0), r * 0.68, r * 1.9, m["metal"], g)
        for s in (-1, 1):
            axle(f"knee_boss{s}", (s * r * 0.97, 0, 0), r * 0.42, r * 0.12, m["trim"], g)

        def cop_r(az, z):
            k = max(0.05, 1 - (z / (r * 1.15)) ** 2)
            return r * (0.5 + 0.62 * math.sqrt(k)) * (1 + 0.16 * bump(az, 0, 12))
        wrap("poleyn", cop_r, -66, 66, lambda az: -r * 0.95 - r * 0.25 * bump(az, 0, 22), lambda az: r * 0.8 + r * 0.45 * bump(az, 0, 18),
             m["armour"], g, thick=0.3 * u, trim=m["trim"], tr=0.1 * u, inlay=m["filigree"], margin=0.24, nv=12)
        shapes.cylinder("poleyn_spike", r * 0.2, r * 0.55, m["trim"], loc=(0, -cop_r(0, 0) - r * 0.2, 0), rot=(math.radians(90), 0, 0),
                        parent=g, verts=8, bevel=0, r2=0.01)
        shapes.sphere("poleyn_boss", r * 0.22, m["trim"], loc=(0, -cop_r(0, 0) - 0.05 * u, 0), parent=g, scale=(1, 0.6, 1), segments=16)
        # The fan: a pointed wing on the outer side of the knee, sweeping up and back.
        wrap("knee_fan", lambda az, z: r * 1.1 + 0.3 * u * bump(z, 0, r), 58, 140, lambda az: -r * 0.75 + r * 0.5 * bump(az, 140, 20),
             lambda az: r * 0.7 + r * 1.3 * bump(az, 118, 12), m["armour"], g, thick=0.25 * u, trim=m["trim"], tr=0.09 * u, nv=8, nu=22)
        # Calf: a tapered core and twin pistons behind it.
        along("core", (0, 0, -0.1 * L), (0, 0, -0.98 * L), r * 0.55, m["metal"], g, r2=r * 0.42)
        for k, x in enumerate((-0.38, 0.38)):
            piston(f"calf{k}", (x * r, r * 0.75, -0.12 * L), (x * r * 0.8, r * 0.5, -0.88 * L), r * 0.17, m["metal"], m["trim"], g, collar=m["trim"])

        # The greave: squared and keeled, narrowing then flaring over the ankle, pointed at both ends.
        def greave_r(az, z):
            t = -z / L
            return r * (1.0 - 0.14 * t + 0.3 * t ** 8) * square(az, 3.0) * (1 + 0.08 * bump(az, 0, 12))
        wrap("greave", greave_r, -84, 84, lambda az: -0.98 * L - 0.08 * L * bump(az, 0, 30), lambda az: -0.22 * L + 0.12 * L * bump(az, 0, 28),
             m["armour"], g, thick=0.32 * u, trim=m["trim"], tr=0.1 * u, nv=12)
        mid = lambda az, z: greave_r(az, z) + 0.3 * u  # noqa: E731
        wrap("greave_panel", mid, -30, 30, lambda az: -0.86 * L - 0.08 * L * bump(az, 0, 14), lambda az: -0.3 * L + 0.08 * L * bump(az, 0, 14),
             m["armour"], g, thick=0.26 * u, trim=m["trim"], tr=0.09 * u, inlay=m["filigree"], margin=0.14, nu=14, nv=12)
        shapes.sweep("greave_keel", [(0, -mid(0, z) - 0.33 * u, z) for z in (-0.34 * L, -0.6 * L, -0.84 * L)], 0.08 * u, m["trim"], parent=g)
        for k, az in enumerate((-56, 56)):
            pts = [(az, -(0.3 + 0.6 * j / 10) * L) for j in range(11)]
            shapes.sweep(f"greave_rib{k}", [Vector((math.sin(math.radians(a)) * (greave_r(a, z) + 0.1 * u),
                                                    -math.cos(math.radians(a)) * (greave_r(a, z) + 0.1 * u), z)) for a, z in pts],
                         0.07 * u, m["trim"], parent=g)
        # Side splints and a rear calf guard.
        for k, az in enumerate((98, -98)):
            wrap(f"splint{k}", lambda a, z: r * 1.04, az - 14, az + 14, -0.85 * L, -0.28 * L, m["armour"], g, thick=0.22 * u, nu=8, nv=10,
                 trim=m["trim"], tr=0.07 * u)
        wrap("calf_guard", lambda az, z: r * 1.05, 140, 220, -0.7 * L, -0.25 * L, m["armour"], g, thick=0.22 * u,
             nu=14, nv=8, trim=m["trim"], tr=0.07 * u)
        for k in range(4):
            ring(f"calf_band{k}", -(0.3 + 0.13 * k) * L, r * 0.62, 0.05 * u, m["trim"], g, centre=(0, r * 0.62))

    def covenant_foot(self, root):
        m, u, r = self.m, self.u, self.rs
        a, gz = self.ankle, self.ground
        h = a.z - gz
        fl, fw = 0.19 * self.H, 0.095 * self.H  # foot length and width
        shapes.sphere("ankle_ball", r * 0.5, m["metal"], loc=a, parent=root, segments=20)
        ring("ankle_ring", a.z - r * 0.1, r * 0.5, 0.08 * u, m["trim"], root, centre=(a.x, a.y))
        # Sole and heel.
        shapes.box_plate("sole", (fw * 0.92, fl * 0.86, 0.32 * h), m["metal"], bevel=0.12 * u, loc=(a.x, a.y - fl * 0.12, gz + 0.16 * h), parent=root)
        shapes.box_plate("heel", (fw * 0.7, fl * 0.26, 0.7 * h), m["armour"], bevel=0.16 * u, loc=(a.x, a.y + fl * 0.22, gz + 0.35 * h),
                         parent=root, taper=0.25)
        shapes.cylinder("heel_spur", 0.2 * fw, fl * 0.2, m["trim"], loc=(a.x, a.y + fl * 0.4, gz + 0.3 * h), rot=(-math.radians(80), 0, 0),
                        parent=root, verts=6, bevel=0, r2=0.01)
        # Sabaton: overlapping lames riding down to a pointed toe.
        f = forward(root, (a.x, a.y, gz))
        n = 4
        for k in range(n):
            z0 = -fl * 0.1 + k * fl * 0.13
            sy = h * (1.3 - 0.2 * k) / (fw * 0.5)
            wrap(f"lame{k}", lambda az, z, k=k: fw * 0.5 * (1.0 - 0.04 * k), 100, 260, z0, z0 + fl * 0.19, m["armour"], f,
                 thick=0.25 * u, nu=18, nv=4, trim=m["trim"], tr=0.07 * u, warp=lambda v, sy=sy: Vector((v.x, v.y * sy, v.z)))
        # The toe: a pointed gothic cap with a gold ridge, and two side claws.
        toe_y = a.y - fl * 0.1 - n * fl * 0.13 - fl * 0.04
        cap = shapes.cylinder("toe_cap", fw * 0.42, fl * 0.24, m["armour"], loc=(a.x, toe_y - fl * 0.08, gz + 0.32 * h),
                              rot=(math.radians(90), 0, 0), parent=root, verts=6, bevel=0.08 * u, r2=fw * 0.05)
        cap.scale = (1.0, 0.55, 1.0)
        shapes.sweep("toe_ridge", [(a.x, toe_y + fl * 0.06, gz + 0.62 * h), (a.x, toe_y - fl * 0.2, gz + 0.32 * h)], 0.08 * u, m["trim"], parent=root)
        for s in (-1, 1):
            shapes.cylinder(f"claw{s}", fw * 0.09, fl * 0.2, m["trim"], loc=(a.x + s * fw * 0.42, toe_y + fl * 0.02, gz + 0.15 * h),
                            rot=(math.radians(96), 0, s * math.radians(18)), parent=root, verts=6, bevel=0, r2=0.01)

    # -------------------------------------------------------------- Ashen Foundries

    def foundries_thigh(self, root):
        m, u, r = self.m, self.u, self.rt
        g, L = bone(root, self.hip, self.knee)
        # A geared hip drum, a box-section frame and two exposed rams.
        gear("hip_drum", (0, 0, 0), r * 0.62, r * 1.6, m["metal"], m["armour"], g, teeth=14)
        for s in (-1, 1):
            axle(f"hip_hub{s}", (s * r * 0.84, 0, 0), r * 0.42, r * 0.14, m["trim"], g)
            bolts(f"hip_bolts{s}", (s * r * 0.92, 0, 0), r * 0.3, 6, 0.08 * u, m["metal"], g, s)
        shapes.box_plate("frame", (r * 1.2, r * 0.95, 0.86 * L), m["metal"], bevel=0.1 * u, loc=(0, 0, -0.5 * L), parent=g, panel_lines=2)
        for k, x in enumerate((-0.82, 0.82)):
            piston(f"ram{k}", (x * r, -r * 0.15, -0.06 * L), (x * r * 0.9, -r * 0.2, -0.94 * L), r * 0.2, m["metal"], m["trim"], g, collar=m["armour"])
        # Layered front armour: a rusted iron slab, a red panel let into it and riveted straps.
        front = shapes.box_plate("front_plate", (r * 1.6, r * 0.4, 0.72 * L), m["armour"], bevel=0.1 * u, loc=(0, -r * 0.7, -0.46 * L),
                                 parent=g, taper=-0.12)
        front.rotation_euler = (math.radians(-4), 0, 0)
        panel = shapes.box_plate("front_panel", (r * 1.05, r * 0.2, 0.4 * L), m["hull"], bevel=0.06 * u, loc=(0, -r * 0.92, -0.4 * L), parent=g,
                                 panel_lines=1)
        panel.rotation_euler = (math.radians(-4), 0, 0)
        for k, z in enumerate((-0.15 * L, -0.7 * L)):
            shapes.box_plate(f"strap{k}", (r * 1.7, r * 0.12, 0.08 * L), m["metal"], bevel=0.03 * u, loc=(0, -r * 0.93 - 0.02 * z, z), parent=g)
            shapes.rivet_row(f"strap_rivets{k}", (-r * 0.7, -r * 1.0 - 0.02 * z, z), (r * 0.7, -r * 1.0 - 0.02 * z, z), 6, 0.08 * u, m["trim"], parent=g)
        shapes.box_plate("side_plate", (r * 0.3, r * 1.2, 0.62 * L), m["armour"], bevel=0.08 * u, loc=(r * 0.92, 0.05 * r, -0.44 * L), parent=g,
                         panel_lines=1)
        shapes.rivet_row("side_rivets", (r * 1.08, -r * 0.45, -0.18 * L), (r * 1.08, -r * 0.45, -0.7 * L), 5, 0.08 * u, m["trim"], parent=g,
                         normal=(1, 0, 0))
        for k in range(3):
            shapes.box_plate(f"side_vent{k}", (r * 0.06, r * 0.5, 0.04 * L), m["glow"], bevel=0, loc=(r * 1.07, r * 0.25, -(0.35 + 0.08 * k) * L), parent=g)
        shapes.box_plate("rear_plate", (r * 1.15, r * 0.28, 0.5 * L), m["armour"], bevel=0.08 * u, loc=(0, r * 0.6, -0.4 * L), parent=g)
        shapes.pipe("hose", [(-r * 0.6, r * 0.5, -0.05 * L), (-r * 1.1, r * 0.2, -0.35 * L), (-r * 0.9, -r * 0.1, -0.85 * L)], r * 0.09,
                    m["metal"], parent=g, bands=(0.3, 0.7), band_mat=m["trim"])

    def foundries_shin(self, root):
        m, u, r = self.m, self.u, self.rs
        g, L = bone(root, self.knee, self.ankle)
        # The knee: a geared drum with bolted brass hubs.
        gear("knee_drum", (0, 0, 0), r * 0.7, r * 1.7, m["metal"], m["armour"], g, teeth=16)
        for s in (-1, 1):
            axle(f"knee_hub{s}", (s * r * 0.9, 0, 0), r * 0.48, r * 0.16, m["trim"], g)
            bolts(f"knee_bolts{s}", (s * r * 0.98, 0, 0), r * 0.33, 6, 0.08 * u, m["metal"], g, s)
        guard = shapes.box_plate("knee_guard", (r * 1.5, r * 0.45, r * 1.25), m["armour"], bevel=0.1 * u, loc=(0, -r * 0.88, r * 0.05), parent=g,
                                 taper=0.25)
        guard.rotation_euler = (math.radians(-10), 0, 0)
        shapes.rivet_row("knee_rivets", (-r * 0.55, -r * 1.12, r * 0.45), (r * 0.55, -r * 1.12, r * 0.45), 4, 0.08 * u, m["trim"], parent=g)
        # The shin block, flaring to the ankle, with layered plates, straps and a red panel.
        shapes.box_plate("shin_block", (r * 1.45, r * 1.35, 0.82 * L), m["metal"], bevel=0.12 * u, loc=(0, 0, -0.55 * L), parent=g, taper=-0.22,
                         panel_lines=2)
        plate = shapes.box_plate("shin_plate", (r * 1.5, r * 0.32, 0.66 * L), m["armour"], bevel=0.1 * u, loc=(0, -r * 0.8, -0.54 * L),
                                 parent=g, taper=-0.2)
        plate.rotation_euler = (math.radians(3), 0, 0)
        panel = shapes.box_plate("shin_panel", (r * 0.95, r * 0.18, 0.3 * L), m["hull"], bevel=0.05 * u, loc=(0, -r * 0.98, -0.42 * L), parent=g,
                                 panel_lines=1)
        panel.rotation_euler = (math.radians(3), 0, 0)
        for k, z in enumerate((-0.24 * L, -0.66 * L, -0.86 * L)):
            w = r * (0.68 + 0.1 * k)
            shapes.box_plate(f"strap{k}", (w * 2.25, r * 0.1, 0.06 * L), m["metal"], bevel=0.03 * u, loc=(0, -r * 0.98 + 0.03 * z, z), parent=g)
            shapes.rivet_row(f"plate_rivets{k}", (-w, -r * 1.04 + 0.03 * z, z), (w, -r * 1.04 + 0.03 * z, z), 5, 0.075 * u, m["trim"], parent=g)
        # A big rear ram, side hoses, a glowing vent grille and a brass gauge.
        piston("calf_ram", (0, r * 0.92, -0.02 * L), (0, r * 0.78, -0.9 * L), r * 0.28, m["metal"], m["trim"], g, collar=m["armour"])
        for s in (-1, 1):
            shapes.pipe(f"hose{s}", [(s * r * 0.8, r * 0.6, -0.1 * L), (s * r * 1.02, r * 0.2, -0.45 * L), (s * r * 0.88, -r * 0.1, -0.9 * L)],
                        r * 0.09, m["metal"], parent=g, bands=(0.5,), band_mat=m["trim"])
        shapes.box_plate("vent_glow", (r * 0.04, r * 0.85, 0.28 * L), m["glow"], bevel=0, loc=(r * 0.76, -r * 0.05, -0.55 * L), parent=g)
        for k in range(5):
            shapes.box_plate(f"vent{k}", (r * 0.1, r * 0.06, 0.32 * L), m["metal"], bevel=0.01 * u,
                             loc=(r * 0.8, -r * 0.4 + k * r * 0.18, -0.55 * L), parent=g)
        shapes.gauge("gauge", r * 0.2, m["trim"], m["armour"], m["metal"], loc=(-r * 0.75, -r * 0.6, -0.3 * L), rot=(0, 0, -1.2), parent=g)

    def foundries_foot(self, root):
        m, u, r = self.m, self.u, self.rs
        a, gz = self.ankle, self.ground
        h = a.z - gz
        fl, fw = 0.19 * self.H, 0.11 * self.H
        gear("ankle_drum", (a.x, a.y, a.z), r * 0.5, r * 1.4, m["metal"], m["armour"], root, teeth=12)
        for s in (-1, 1):
            axle(f"ankle_hub{s}", (a.x + s * r * 0.75, a.y, a.z), r * 0.35, r * 0.14, m["trim"], root)
        # A wide deck, three blunt toes and a heel block, all on a tread sole.
        shapes.box_plate("deck", (fw * 0.8, fl * 0.55, h * 0.7), m["armour"], bevel=0.12 * u, loc=(a.x, a.y - fl * 0.02, gz + h * 0.4), parent=root,
                         taper=0.2)
        shapes.box_plate("deck_plate", (fw * 0.6, fl * 0.35, h * 0.12), m["hull"], bevel=0.05 * u, loc=(a.x, a.y - fl * 0.12, gz + h * 0.78),
                         parent=root)
        for k, x in enumerate((-0.33, 0.0, 0.33)):
            toe = shapes.box_plate(f"toe{k}", (fw * 0.3, fl * 0.32, h * 0.6), m["armour"], bevel=0.1 * u,
                                   loc=(a.x + x * fw, a.y - fl * 0.42, gz + h * 0.3), parent=root, taper=0.35)
            toe.rotation_euler = (math.radians(-6), 0, 0)
            shapes.box_plate(f"toe{k}_sole", (fw * 0.3, fl * 0.32, h * 0.18), m["metal"], bevel=0.04 * u, loc=(a.x + x * fw, a.y - fl * 0.42, gz + h * 0.09),
                             parent=root, panel_lines=0)
            shapes.rivet_row(f"toe{k}_rivets", (a.x + x * fw, a.y - fl * 0.32, gz + h * 0.62), (a.x + x * fw, a.y - fl * 0.52, gz + h * 0.5),
                             2, 0.08 * u, m["trim"], parent=root, normal=(0, -0.3, 1))
        shapes.box_plate("heel", (fw * 0.6, fl * 0.25, h * 0.75), m["armour"], bevel=0.1 * u, loc=(a.x, a.y + fl * 0.3, gz + h * 0.37), parent=root)
        shapes.box_plate("sole", (fw * 0.85, fl * 0.75, h * 0.22), m["metal"], bevel=0.05 * u, loc=(a.x, a.y + fl * 0.02, gz + h * 0.11), parent=root,
                         panel_lines=5)
        piston("heel_ram", (a.x, a.y + r * 0.4, a.z), (a.x, a.y + fl * 0.32, gz + h * 0.75), r * 0.16, m["metal"], m["trim"], root)

    # -------------------------------------------------------------- Reliquary

    def reliquary_thigh(self, root):
        m, u, r = self.m, self.u, self.rt
        g, L = bone(root, self.hip, self.knee)
        shapes.sphere("hip_ball", r * 0.7, m["metal"], parent=g, segments=20)
        ring("hip_ring", 0, r * 0.74, 0.08 * u, m["trim"], g)
        # A dark skeleton: a spine rod and two struts, bound with gold rings.
        along("spine", (0, 0, -0.05 * L), (0, 0, -0.98 * L), r * 0.32, m["metal"], g)
        for k, az in enumerate((-125, 125)):
            a_ = math.radians(az)
            along(f"strut{k}", (math.sin(a_) * r * 0.55, -math.cos(a_) * r * 0.55, -0.12 * L),
                  (math.sin(a_) * r * 0.35, -math.cos(a_) * r * 0.35, -0.9 * L), r * 0.12, m["trim"], g, verts=12)
        for k, z in enumerate((-0.12, -0.5, -0.86)):
            ring(f"band{k}", z * L, r * 0.6 * (1 - 0.2 * abs(z)), 0.07 * u, m["trim"], g)
        # A long ceramic plate down the front, narrow and pointed at the knee.
        def plate_r(az, z):
            return r * (0.92 - 0.2 * (-z / L)) * (1 + 0.12 * bump(az, 0, 12))
        wrap("cuisse", plate_r, -55, 60, lambda az: -0.8 * L - 0.14 * L * bump(az, 0, 22), lambda az: -0.08 * L + 0.06 * L * bump(az, 40, 20),
             m["armour"], g, thick=0.22 * u, trim=m["trim"], tr=0.07 * u, nu=18, nv=12, inlay=m["filigree"], margin=0.2)
        shapes.sweep("glyph_line", [(0, -plate_r(0, z) - 0.06 * u, z) for z in (-0.2 * L, -0.5 * L, -0.78 * L)], 0.05 * u, m["trim"], parent=g)
        # Ribs behind, like a reliquary's bones.
        for k in range(5):
            z = -(0.2 + 0.14 * k) * L
            wrap(f"rib{k}", lambda az, zz: r * 0.62, 120, 240, z - 0.045 * L, z, m["armour"], g, thick=0.15 * u, nu=12, nv=2)

    def reliquary_shin(self, root):
        m, u, r = self.m, self.u, self.rs
        k0, an = self.knee, self.ankle
        L = (an - k0).length
        # Digitigrade: the shin runs back and down to a hock, then down to the ankle.
        hock = k0.lerp(an, 0.55) + Vector((0, 0.32 * L, 0))
        shapes.sphere("knee_ball", r * 0.6, m["metal"], loc=k0, parent=root, segments=18)
        ring("knee_ring", k0.z, r * 0.62, 0.07 * u, m["trim"], root, centre=(k0.x, k0.y))
        upper, ul = bone(root, k0, hock)
        # Upper shank: a ceramic sheath over a dark rod, gold at both ends.
        along("shank_rod", (0, 0, -0.05 * ul), (0, 0, -0.95 * ul), r * 0.3, m["metal"], upper)
        wrap("shank_plate", lambda az, z: r * (0.75 - 0.18 * (-z / ul)) * (1 + 0.15 * bump(az, 0, 14)), -70, 70, -0.88 * ul,
             lambda az: -0.02 * ul + 0.12 * ul * bump(az, 0, 20), m["armour"], upper, thick=0.2 * u, trim=m["trim"], tr=0.06 * u, nu=16, nv=10,
             inlay=m["filigree"], margin=0.2)
        wrap("shank_back", lambda az, z: r * 0.5, 110, 250, -0.8 * ul, -0.15 * ul, m["armour"], upper, thick=0.15 * u, nu=12, nv=6)
        for k, t in enumerate((0.2, 0.92)):
            ring(f"shank_band{k}", -t * ul, r * 0.42, 0.06 * u, m["trim"], upper)
        # The hock: a gold joint with a teal lamp and a backward spur.
        shapes.sphere("hock", r * 0.42, m["trim"], loc=hock, parent=root, segments=16)
        shapes.sphere("hock_lamp", r * 0.18, m["glow"], loc=hock + Vector((r * 0.33, 0, 0)), parent=root, segments=12)
        along("spur", hock + Vector((0, r * 0.2, 0)), hock + Vector((0, 0.35 * L, 0.12 * L)), r * 0.2, m["trim"], root, r2=0.01, verts=8, bevel=0)
        # Lower shank: a slender rod with a ceramic splint and a sprung tendon behind.
        lower, ll = bone(root, hock, an)
        along("cannon", (0, 0, -0.02 * ll), (0, 0, -0.98 * ll), r * 0.24, m["metal"], lower)
        wrap("cannon_plate", lambda az, z: r * 0.42 * (1 + 0.15 * bump(az, 0, 14)), -60, 60, -0.85 * ll, -0.12 * ll, m["armour"], lower,
             thick=0.16 * u, trim=m["trim"], tr=0.05 * u, nu=14, nv=10)
        along("tendon", Vector((0, r * 0.4, -0.05 * ll)), Vector((0, r * 0.35, -0.9 * ll)), r * 0.08, m["trim"], lower, verts=8)
        for k, t in enumerate((0.1, 0.92)):
            ring(f"cannon_band{k}", -t * ll, r * 0.32, 0.05 * u, m["trim"], lower)

    def reliquary_foot(self, root):
        m, u, r = self.m, self.u, self.rs
        a, gz = self.ankle, self.ground
        h = a.z - gz
        fl = 0.17 * self.H
        shapes.sphere("ankle_ball", r * 0.45, m["metal"], loc=a, parent=root, segments=16)
        ring("ankle_ring", a.z, r * 0.47, 0.05 * u, m["trim"], root, centre=(a.x, a.y))
        palm = Vector((a.x, a.y - 0.04 * fl, gz + 0.45 * h))
        shapes.sphere("palm", r * 0.55, m["armour"], loc=palm, parent=root, scale=(1.1, 1.3, 0.6), segments=16)
        # Three long toes splayed forward, each with a ceramic knuckle and a gold claw.
        for k, ang in enumerate((-26, 0, 26)):
            d = Vector((math.sin(math.radians(ang)), -math.cos(math.radians(ang)), 0))
            k1 = palm + d * 0.32 * fl + Vector((0, 0, 0.05 * h))
            k2 = k1 + d * 0.22 * fl - Vector((0, 0, 0.3 * h))
            along(f"toe{k}_a", palm, k1, r * 0.2, m["metal"], root, r2=r * 0.16, verts=10)
            shapes.sphere(f"toe{k}_knuckle", r * 0.22, m["armour"], loc=k1, parent=root, segments=12)
            along(f"toe{k}_b", k1, k2, r * 0.15, m["metal"], root, r2=r * 0.12, verts=10)
            tip = k2 + d * 0.16 * fl - Vector((0, 0, max(0.0, k2.z - gz) * 0.9))
            along(f"toe{k}_claw", k2, tip, r * 0.16, m["trim"], root, r2=0.01, verts=8, bevel=0)
        # A rear spur and a hallux claw on the inside.
        along("rear_toe", palm, palm + Vector((0, 0.32 * fl, -0.35 * h)), r * 0.16, m["metal"], root, r2=r * 0.1, verts=10)
        along("rear_claw", palm + Vector((0, 0.3 * fl, -0.33 * h)), palm + Vector((0, 0.42 * fl, -0.42 * h)), r * 0.13, m["trim"], root,
              r2=0.01, verts=8, bevel=0)
        # A pale gold collar where the cannon meets the foot.
        wrap("ankle_cuff", lambda az, z: r * 0.5, -120, 120, -r * 0.4, r * 0.3, m["trim"],
             kit.empty("ankle_up", a, parent=root, size=1), thick=0.12 * u, nu=16, nv=4)


# ------------------------------------------------------------------ run


def wanted(args):
    frames_by_faction = {}
    for c in load("chassis.json")["chassis"]:
        frames_by_faction.setdefault(c["faction"], set()).add(c["frame"])
    order = ("scout", "striker", "bulwark", "titan")
    factions = [a for a in args if a in frames_by_faction] or list(kit.materials.FACTIONS)
    only = None
    if "--frames" in args:
        i = args.index("--frames")
        only = [a for a in args[i + 1:] if a in order]
    return [(f, fr) for f in factions for fr in order if fr in frames_by_faction[f] and (only is None or fr in only)]


def review(faction, frame, parts, out, samples):
    """Hang the legs (and a mirrored copy) on the frame with its stand-ins, render, compare."""
    sk = Skeleton(faction, frame)
    frame_root = build_frame(faction, frame)
    for o in list(frame_root.children_recursive):
        if o.get("standin") in COMPONENTS:
            o.hide_render = o.hide_viewport = True
    leg = Leg(faction, frame)
    right = leg.build()
    for comp, root in right.items():
        root.name = root.name + "_R"
        root.scale.x = -1
    bpy.context.view_layer.update()
    objs = [o for r in (*parts.values(), *right.values()) for o in kit.meshes(r)]
    body = objs + [o for o in kit.meshes(frame_root) if not o.hide_render]
    kit.render.studio()
    shots = []
    name = f"legs_{faction}_{frame}"
    p = kit.render.shot(body, out / f"{name}-full.png", az=30, el=6, samples=samples, res=(720, 900))
    kit.render.post(p)
    shots.append(p)
    left = [o for r in parts.values() for o in kit.meshes(r)]
    hidden = [o for o in body if o not in left]
    for o in hidden:
        o.hide_render = True
    for az in (0, 40, 95):
        p = kit.render.shot(left, out / f"{name}-{az}.png", az=az, el=8, samples=samples, res=(480, 900), margin=0.95)
        kit.render.post(p)
        shots.append(p)
    foot = kit.meshes(parts["foot"])
    p = kit.render.shot(foot, out / f"{name}-foot.png", az=40, el=25, samples=samples, res=(480, 900), margin=1.1)
    kit.render.post(p)
    shots.append(p)
    for o in hidden:
        o.hide_render = False
    crop = f"legs_{faction}"
    art = crop if crop in kit.render.crops() else None
    return kit.render.compare(shots, art, out / f"{name}-compare.png", labels=["on the frame", "front", "40°", "side", "foot"],
                              title=f"{faction} legs, {frame} frame")


def main():
    args = script_args()
    out = Path(args[args.index("--render") + 1]) if "--render" in args else None
    samples = int(args[args.index("--samples") + 1]) if "--samples" in args else 48
    size = int(args[args.index("--size") + 1]) if "--size" in args else 1024
    for faction, frame in wanted(args):
        kit.reset_scene()
        leg = Leg(faction, frame)
        parts = leg.build()
        if out is not None:
            print("wrote", review(faction, frame, parts, out, samples))
        if "--publish" in args:
            kit.reset_scene()
            parts = Leg(faction, frame).build()
            for comp, root in parts.items():
                kit.skeleton.to_joint(root, faction, frame, comp)
            bpy.context.view_layer.update()
            src = HERE / f"legs_{faction}_{frame}.blend"
            for comp, root in parts.items():
                kit.publish(root, size=size, source=src if comp == "thigh" else None)


main()
