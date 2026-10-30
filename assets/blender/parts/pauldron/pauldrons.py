"""Package 3: pauldrons and collars for all three factions.

    bvenv/bin/python assets/blender/parts/pauldron/pauldrons.py [faction ...] [--frame titan] [--render OUT] [--publish]

One build per faction and frame, named `<faction>_pauldron_<frame>` (left,
+X, mirrored for the right) and `<faction>_collar_<frame>`:

* Iron Covenant: a tilted dome with a raised gold sunburst on its outer face,
  overlapping lames hanging round the arm, and a filigree haute-piece rising
  beside the helm. The collar is a high fluted gorget, low at the front and
  pointed at the back.
* Ashen Foundries: stacked slabs of riveted plate, a red hull drop plate in a
  brass frame, a vent grille and hex bolts. The collar is a squat octagonal
  ring with a raised back plate.
* Reliquary: swept, ragged-edged ceramic blades rising off a small domed cap
  ringed in gold. The collar is a tall narrow gorget with points.

Everything is sized from the frame's skeleton, so one script covers every
frame. `--render` draws the parts on the frame's stand-ins (node materials,
no bake) beside the matching concept art crop; `--publish` bakes and exports.
"""
import math
import sys
from pathlib import Path

import bpy  # noqa: F401  (before bmesh)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import kit  # noqa: E402
from common import script_args  # noqa: E402
from kit import shapes  # noqa: E402
from kit.core import Vector, bmesh, empty, mesh_obj, mod  # noqa: E402

HERE = Path(__file__).resolve().parent
FRAMES = {"covenant": ("striker", "bulwark", "titan"), "foundries": ("scout", "bulwark"), "reliquary": ("scout", "striker", "titan")}
SIZE = {"scout": 0, "striker": 1, "bulwark": 2, "titan": 3}
ART = {"covenant": "covenant_pauldron", "foundries": "class_brute", "reliquary": "class_goliath"}
rad = math.radians

# ------------------------------------------------------------------ helpers


def surface(name, fn, nu, nv, mat, thick, parent=None, cyclic=False, tile=(1.0, 1.0), bevel=0.3):
    """A plate from a parametric surface fn(u, v) -> Vector, u and v in [0, 1],
    given thickness either side. `cyclic` closes it round u."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("Decal")
    cols = nu if cyclic else nu + 1
    grid = [[bm.verts.new(fn(i / nu, j / nv)) for i in range(cols)] for j in range(nv + 1)]
    if cyclic:
        grid = [row + [row[0]] for row in grid]
    shapes._grid_faces(bm, grid, uv, tile)
    ob = mesh_obj(name, bm, mat, parent=parent)
    mod(ob, "SOLIDIFY", thickness=thick, offset=0)
    if bevel:
        mod(ob, "BEVEL", width=thick * bevel, segments=2, limit_method="ANGLE")
    return ob


def tapered(name, pts, r0, r1, mat, parent=None):
    """A swept bar thinning from r0 to r1: sunburst rays, blade spines."""
    ob = shapes.sweep(name, pts, 1.0, mat, parent=parent, resolution=2)
    sp = ob.data.splines[0]
    for k, p in enumerate(sp.points):
        t = k / max(1, len(sp.points) - 1)
        p.radius = r0 + (r1 - r0) * t
    return ob


def studs(name, spots, radius, mat, parent=None):
    """Domed studs at (point, normal) pairs, joined into one object."""
    bm = bmesh.new()
    for p, n in spots:
        rot = Vector(n).normalized().to_track_quat("Z", "Y").to_matrix()
        geom = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=radius)
        for v in geom["verts"]:
            v.co = Vector(p) + rot @ Vector((v.co.x, v.co.y, max(v.co.z, -radius * 0.2) * 0.8))
    ob = mesh_obj(name, bm, mat, parent=parent)
    shapes.decal_uv(ob)
    return ob


def outline_plate(name, pts, normal, thick, mat, parent=None, bevel=0.3, tile_mm=2.0):
    """A flat plate cut to an outline (3D points in one plane), `thick` deep along `normal`."""
    n = Vector(normal).normalized() * (thick / 2)
    bm = bmesh.new()
    front = [bm.verts.new(Vector(p) - n) for p in pts]
    back = [bm.verts.new(Vector(p) + n) for p in pts]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        bm.faces.new((front[j], front[i], back[i], back[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = mesh_obj(name, bm, mat, smooth=False, parent=parent)
    if bevel:
        mod(ob, "BEVEL", width=thick * bevel, segments=2, limit_method="ANGLE")
        mod(ob, "WEIGHTED_NORMAL", keep_sharp=True)
    shapes.decal_uv(ob, tile_mm)
    return ob


def hexbolt(name, r, loc, normal, mat, parent=None):
    ob = shapes.cylinder(name, r, r * 0.7, mat, loc=loc, parent=parent, verts=6, bevel=r * 0.12)
    ob.rotation_euler = Vector(normal).to_track_quat("Z", "Y").to_euler()
    return ob


def ring_pts(fn, n=72):
    return [fn(i / n) for i in range(n)]

# ------------------------------------------------------------------ Iron Covenant


def covenant_pauldron(sk, m, frame, root):
    n = SIZE[frame]
    R = 0.105 * sk.H * sk.G
    zs = 0.8
    tilt = rad(22)
    sh = sk.joint("shoulder")
    centre = sh + Vector((0.12 * R, 0, 0.1 * R))
    piv = empty("pauldron_cap", loc=centre, parent=root, size=R * 0.3)
    piv.rotation_euler = (0, tilt, 0)

    def ell(d, lift=0.0):
        """Point and normal on the cap's ellipsoid along local direction d."""
        d = Vector(d).normalized()
        k = R / math.sqrt(d.x ** 2 + d.y ** 2 + (d.z / zs) ** 2)
        p = d * k
        nrm = Vector((p.x, p.y, p.z / (zs * zs))).normalized()
        return p + nrm * lift, nrm

    def sph(az, phi):
        a, p = rad(az), rad(phi)
        return Vector((math.sin(a) * math.sin(p), -math.cos(a) * math.sin(p), math.cos(p)))

    rim = 84
    surface("cap", lambda u, v: ell(sph(u * 360, 2 + v * (rim - 2)))[0], 64, 18, m["armour"], 0.07 * R, parent=piv, cyclic=True, tile=(6, 2))
    shapes.sweep("cap_rim", ring_pts(lambda t: ell(sph(t * 360, rim - 1), 0.03 * R)[0]), 0.05 * R, m["trim"], cyclic=True, parent=piv)
    shapes.sweep("cap_rim_bead", ring_pts(lambda t: ell(sph(t * 360, rim - 8), 0.02 * R)[0]), 0.022 * R, m["trim"], cyclic=True, parent=piv)
    # Gold seams over the crown, front and back, framing the sunburst panel.
    for k, az in enumerate((-8, 188, 50, 130)):
        lo = 12 if k < 2 else 70
        shapes.sweep(f"cap_seam{k}", [ell(sph(az, lo + (rim - 9 - lo) * i / 16), 0.03 * R)[0] for i in range(17)], 0.032 * R, m["trim"], parent=piv)
    studs("cap_studs", [ell(sph(a, rim - 4.5), 0.0) for a in range(0, 360, 15)], 0.035 * R, m["trim"], parent=piv)

    # The sunburst: a boss on the outer face with alternating straight and
    # flame-like rays, as on the board's pauldron close-up.
    c = sph(90, 52)
    e1 = c.cross(Vector((0, 1, 0))).normalized()
    e2 = c.cross(e1).normalized()
    boss, bn = ell(c, 0.0)
    shapes.sphere("sun_boss", 0.12 * R, m["trim"], loc=boss, scale=(1, 1, 0.55), parent=piv).rotation_euler = bn.to_track_quat("Z", "Y").to_euler()
    shapes.sweep("sun_ring", ring_pts(lambda t: ell(c * math.cos(0.2) + (e1 * math.cos(t * 6.283) + e2 * math.sin(t * 6.283)) * math.sin(0.2), 0.03 * R)[0], 40),
                 0.025 * R, m["trim"], cyclic=True, parent=piv)
    rays = 16 if n >= 2 else 12
    tips = []
    for i in range(rays):
        t = 2 * math.pi * i / rays
        long = i % 2 == 0
        reach = 0.95 if long else 0.62
        pts = []
        for s in range(13):
            ang = 0.22 + (reach - 0.22) * s / 12
            wob = 0.0 if long else 0.09 * math.sin(s * 1.1) * (s / 12)
            d = c * math.cos(ang) + (e1 * math.cos(t + wob) + e2 * math.sin(t + wob)) * math.sin(ang)
            pts.append(ell(d, 0.03 * R)[0])
        tapered(f"sun_ray{i}", pts, (0.045 if long else 0.032) * R, 0.008 * R, m["trim"], parent=piv)
        if long:
            d = c * math.cos(reach + 0.05) + (e1 * math.cos(t) + e2 * math.sin(t)) * math.sin(reach + 0.05)
            tips.append(ell(d, 0.0))
    studs("sun_tips", tips, 0.03 * R, m["trim"], parent=piv)

    # Lames: overlapping bands wrapping the outer side of the arm, below the
    # cap's rim, each a little wider and flared at its lower edge.
    def rim_z(az):
        # Height of the tilted cap's rim above the cap centre at this azimuth.
        return R * (0.1 - 0.34 * math.sin(rad(az)))
    count = 2 if n <= 1 else 3
    top_off, depth = 0.16 * R, 0.5 * R
    for k in range(count):
        span = 118 - 14 * k
        rk = R * (0.97 + 0.07 * k)

        def lame(u, v, k=k, span=span, rk=rk):
            az = 90 + span * (2 * u - 1)
            s = abs(2 * u - 1)
            env = 0.35 + 0.65 * math.sqrt(max(0.0, math.cos(s * math.pi / 2)))
            z0 = rim_z(az) + top_off - k * depth * 0.62
            z = z0 - depth * env * v
            r = rk * (1 + 0.1 * v * v)
            return centre + Vector((math.sin(rad(az)) * r, -math.cos(rad(az)) * r, z))
        surface(f"lame{k}", lame, 40, 6, m["filigree"] if k == count - 1 else m["armour"], 0.07 * R, parent=root, tile=(8, 1))
        edge = [lame(i / 40, 1.0) + (lame(i / 40, 1.0) - centre).normalized() * 0.0 for i in range(41)]
        edge = [p + Vector((p.x - centre.x, p.y - centre.y, 0)).normalized() * 0.04 * R for p in edge]
        shapes.sweep(f"lame{k}_trim", edge, 0.04 * R, m["trim"], parent=root)
        spots = []
        for i in range(4, 37, 4):
            p = lame(i / 40, 0.55)
            nn = Vector((p.x - centre.x, p.y - centre.y, 0)).normalized()
            spots.append((p + nn * 0.04 * R, nn))
        studs(f"lame{k}_rivets", spots, 0.03 * R, m["trim"], parent=root)

    # The haute-piece: a gothic flange rising on the inner edge, beside the helm.
    hx = centre.x - 0.5 * R
    hz = centre.z + 0.35 * R
    hh = (0.6 + 0.08 * n) * R
    hw = 0.6 * R
    prof = [(-hw, 0.0)]
    for i in range(9):
        a = i / 8
        prof.append((-hw + hw * 0.25 * a, hh * 0.55 * a))
    for i in range(1, 9):
        a = i / 8
        prof.append((-hw * 0.75 * (1 - a) ** 1.4, hh * (0.55 + 0.45 * math.sin(a * math.pi / 2))))
    prof += [(-y, z) for y, z in reversed(prof[1:-1])]
    prof.append((hw, 0.0))
    lean = rad(12)

    def hp(y, z, x=0.0):
        return Vector((hx + x + z * math.sin(lean), y, hz + z * math.cos(lean)))
    outline_plate("haute_piece", [hp(y, z) for y, z in prof], (math.cos(lean), 0, -math.sin(lean)), 0.08 * R, m["filigree"], parent=root, tile_mm=R * 1.4)
    shapes.sweep("haute_trim", [hp(y * 0.97, z * 0.98 + 0.01 * R, 0.06 * R) for y, z in prof], 0.035 * R, m["trim"], cyclic=True, parent=root)
    shapes.sphere("haute_finial", 0.06 * R, m["trim"], loc=hp(0, hh + 0.05 * R), parent=root)


def covenant_collar(sk, m, frame, root):
    H = sk.H
    nk = sk.joint("neck")
    r0, r1 = 0.07 * H, 0.088 * H
    zb = nk.z - 0.035 * H

    def top(az):
        back = (1 - math.cos(rad(az))) / 2           # 0 at the front, 1 at the back
        h = 0.02 * H + 0.06 * H * back ** 1.5
        # Three gothic points across the back.
        if back > 0.55:
            h += 0.012 * H * abs(math.cos(rad(az) * 3)) ** 4 * (back - 0.55) / 0.45
        return h

    def col(u, v):
        az = u * 360
        z = zb + (nk.z - zb + top(az)) * v
        r = r0 + (r1 - r0) * v ** 1.6
        return Vector((math.sin(rad(az)) * r, -math.cos(rad(az)) * r, z))
    surface("collar", col, 72, 10, m["armour"], 0.0045 * H, parent=root, cyclic=True, tile=(8, 1))
    out = 0.004 * H

    def at(az, v, lift=out):
        p = col(az / 360 % 1.0, v)
        nn = Vector((p.x, p.y, 0)).normalized()
        return p + nn * lift
    shapes.sweep("collar_rim", ring_pts(lambda t: at(t * 360, 1.0)), 0.0035 * H, m["trim"], cyclic=True, parent=root)
    shapes.sweep("collar_base", ring_pts(lambda t: at(t * 360, 0.0)), 0.003 * H, m["trim"], cyclic=True, parent=root)
    for az in range(45, 316, 30):
        shapes.sweep(f"collar_flute{az}", [at(az, v / 10) for v in range(1, 10)], 0.0025 * H, m["trim"], parent=root)
    # A filigree band round the middle, and studs below the rim.
    band = surface("collar_band", lambda u, v: at(u * 360, 0.25 + 0.2 * v, 0.0025 * H), 72, 2, m["filigree"], 0.002 * H, parent=root, cyclic=True, tile=(14, 1), bevel=0)
    band.name = "collar_band"
    studs("collar_studs", [(at(a, 0.88, 0.0), Vector((math.sin(rad(a)), -math.cos(rad(a)), 0))) for a in range(-150, 151, 15) if abs(a) > 20],
          0.0028 * H, m["trim"], parent=root)

# ------------------------------------------------------------------ Ashen Foundries


def foundries_pauldron(sk, m, frame, root):
    n = SIZE[frame]
    R = 0.1 * sk.H * sk.G * (0.85 if n == 0 else 1.0)
    sh = sk.joint("shoulder")
    slope = rad(16)
    c = sh + Vector((0.3 * R, 0, 0.75 * R))
    # The main slab, sloping down and out, with a second slab stepped under it.
    top = shapes.box_plate("slab", (2.3 * R, 2.4 * R, 0.42 * R), m["armour"], bevel=0.12 * R, loc=c, rot=(0, slope, 0), parent=root, panel_lines=2, taper=0.06)
    shapes.box_plate("slab_step", (1.5 * R, 1.9 * R, 0.22 * R), m["armour"], bevel=0.06 * R, loc=c + Vector((-0.35 * R, 0, 0.3 * R)), rot=(0, slope, 0), parent=root)
    shapes.decal_uv(top, R * 0.6)
    shapes.box_plate("slab_under", (2.1 * R, 2.2 * R, 0.4 * R), m["metal"], bevel=0.05 * R, loc=c + Vector((0.25 * R, 0, -0.42 * R)), rot=(0, slope, 0), parent=root)
    # A brass edge on the slab's front and back.
    for s, nm in ((-1, "front"), (1, "back")):
        p = c + Vector((0, s * 1.21 * R, 0.02 * R))
        shapes.box_plate(f"slab_edge_{nm}", (2.32 * R, 0.08 * R, 0.24 * R), m["trim"], bevel=0.02 * R, loc=p, rot=(0, slope, 0), parent=root)
    # Hex bolts at the slab's corners.
    up = Vector((math.sin(slope), 0, math.cos(slope)))
    side = Vector((math.cos(slope), 0, -math.sin(slope)))
    for i, (a, b) in enumerate(((-0.95, -1.0), (0.95, -1.0), (-0.95, 1.0), (0.95, 1.0))):
        hexbolt(f"slab_bolt{i}", 0.1 * R, c + side * a * R + Vector((0, b * R, 0)) + up * 0.27 * R, up, m["trim"], parent=root)
    # A vent grille set into the slab top.
    g = c + side * -0.35 * R + up * 0.43 * R
    shapes.box_plate("vent", (0.8 * R, 0.9 * R, 0.08 * R), m["metal"], bevel=0.01 * R, loc=g, rot=(0, slope, 0), parent=root)
    for i in range(5):
        shapes.box_plate(f"vent_slat{i}", (0.7 * R, 0.07 * R, 0.1 * R), m["armour"], bevel=0.01 * R,
                         loc=g + Vector((0, (-0.34 + 0.17 * i) * R, 0)) + up * 0.05 * R, rot=(0, slope, 0), parent=root)

    # The red drop plate on the outer side, framed in brass and riveted.
    dz = 1.6 * R if n else 1.2 * R
    dp = c + side * 1.18 * R + Vector((0, 0, -0.55 * R - dz / 2 + 0.35 * R))
    lean = rad(-14)
    shapes.box_plate("drop", (0.32 * R, 2.2 * R, dz), m["hull"], bevel=0.05 * R, loc=dp, rot=(0, lean, 0), parent=root, panel_lines=0)
    out = Vector((math.cos(lean), 0, -math.sin(lean)))
    dn = Vector((math.sin(lean), 0, math.cos(lean)))
    f = dp + out * 0.18 * R
    hw, hd = 1.05 * R, dz / 2 - 0.05 * R
    frame_pts = [f + Vector((0, y, 0)) + dn * z for y, z in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]
    shapes.sweep("drop_frame", frame_pts, 0.06 * R, m["trim"], cyclic=True, parent=root, profile="square")
    spots = []
    for z in (-hd + 0.14 * R, hd - 0.14 * R):
        for k in range(7):
            spots.append((f + Vector((0, -hw + 0.15 * R + (2 * hw - 0.3 * R) * k / 6, 0)) + dn * z + out * 0.02 * R, out))
    studs("drop_rivets", spots, 0.055 * R, m["metal"], parent=root)
    # Hazard bar across the drop plate.
    shapes.box_plate("drop_bar", (0.08 * R, 1.9 * R, 0.08 * R), m["metal"], bevel=0.02 * R, loc=f + dn * (0.1 * R), rot=(0, lean, 0), parent=root)
    if n:
        # A lower lame below the drop plate, stepped out.
        lp = dp + dn * (-dz / 2 - 0.25 * R) + out * 0.1 * R
        shapes.box_plate("drop_lame", (0.3 * R, 1.9 * R, 0.5 * R), m["armour"], bevel=0.05 * R, loc=lp, rot=(0, lean - rad(8), 0), parent=root)
        shapes.rivet_row("drop_lame_rivets", lp + out * 0.17 * R + Vector((0, -0.8 * R, 0)), lp + out * 0.17 * R + Vector((0, 0.8 * R, 0)), 6, 0.05 * R,
                         m["trim"], parent=root, normal=out)
    # The pivot drum the slabs hang on, visible under the front edge.
    drum = shapes.cylinder("pivot_drum", 0.45 * R, 1.2 * R, m["metal"], loc=sh + Vector((0.2 * R, 0, 0.15 * R)), rot=(math.pi / 2, 0, 0), parent=root, verts=24, bevel=0.03 * R)
    drum.name = "pivot_drum"
    for s in (-1, 1):
        shapes.cylinder(f"pivot_cap{s}", 0.3 * R, 0.12 * R, m["trim"], loc=sh + Vector((0.2 * R, s * 0.62 * R, 0.15 * R)), rot=(math.pi / 2, 0, 0), parent=root, verts=6, bevel=0.02 * R)


def foundries_collar(sk, m, frame, root):
    H = sk.H
    nk = sk.joint("neck")
    r0, r1 = 0.075 * H, 0.095 * H
    zb, zt = nk.z - 0.03 * H, nk.z + 0.02 * H
    prof = [(r1, zb), (r1 * 1.02, zb + (zt - zb) * 0.55), (r0 * 1.05, zt), (r0 * 0.9, zt)]
    ring = shapes.lathe("collar", prof, m["armour"], segments=8, parent=root)
    ring.rotation_euler = (0, 0, math.pi / 8)
    mod(ring, "SOLIDIFY", thickness=0.006 * H, offset=-1)
    mod(ring, "BEVEL", width=0.0015 * H, segments=2, limit_method="ANGLE")
    shapes.decal_uv(ring, 0.05 * H)
    band = shapes.lathe("collar_band", [(r1 * 1.035, zb + 0.004 * H), (r1 * 1.035, zb + 0.014 * H)], m["trim"], segments=8, parent=root)
    band.rotation_euler = (0, 0, math.pi / 8)
    mod(band, "SOLIDIFY", thickness=0.003 * H, offset=1)
    spots = []
    for i in range(8):
        a = math.pi / 8 + 2 * math.pi * i / 8 + math.pi / 8
        nn = Vector((math.sin(a), -math.cos(a), 0))
        for z in (zb + 0.022 * H,):
            spots.append((nn * r1 * 1.02 * math.cos(math.pi / 8) + Vector((0, 0, z)), nn))
    studs("collar_rivets", spots, 0.004 * H, m["metal"], parent=root)
    # A raised back plate guarding the helm, with a brass cap.
    bp = Vector((0, 0.085 * H, nk.z + 0.03 * H))
    shapes.box_plate("collar_back", (0.11 * H, 0.012 * H, 0.08 * H), m["hull"], bevel=0.002 * H, loc=bp, rot=(rad(-10), 0, 0), parent=root, taper=0.18)
    shapes.box_plate("collar_back_cap", (0.1 * H, 0.016 * H, 0.008 * H), m["trim"], bevel=0.0015 * H, loc=bp + Vector((0, -0.007 * H, 0.04 * H)), rot=(rad(-10), 0, 0), parent=root)
    shapes.rivet_row("collar_back_rivets", bp + Vector((-0.045 * H, -0.008 * H, -0.03 * H)), bp + Vector((0.045 * H, -0.008 * H, -0.03 * H)), 5, 0.0035 * H,
                     m["metal"], parent=root, normal=(0, -1, 0))
    # Cable runs from the collar into the back plate.
    for s in (-1, 1):
        shapes.pipe(f"collar_hose{s}", [(s * 0.06 * H, 0.05 * H, zt - 0.005 * H), (s * 0.05 * H, 0.075 * H, zt + 0.01 * H), (s * 0.035 * H, 0.08 * H, zt + 0.03 * H)],
                    0.005 * H, m["metal"], parent=root, bands=(0.5,), band_mat=m["trim"])

# ------------------------------------------------------------------ Reliquary


def blade(name, base, along, up, length, width, mat, trim, root, ragged=5, curl=0.18, sweep_back=0.25):
    """A swept ceramic blade: `along` is its spine direction, `up` the
    leading edge's side. The trailing edge is scalloped, the tip a point,
    and the face cupped back."""
    along = Vector(along).normalized()
    up = (Vector(up) - along * Vector(up).dot(along)).normalized()
    face = along.cross(up).normalized()

    def spine(u):
        # A gentle upward arc and backward sweep.
        return base + along * length * u + up * length * 0.12 * math.sin(u * math.pi) * u + Vector((0, 1, 0)) * length * sweep_back * u * u

    def half_width(u, leading):
        if leading:
            return width * 0.35 * (1 - u) ** 0.9 * (0.5 + 0.5 * math.sin(min(1.0, u * 3) * math.pi / 2))
        w = width * (1 - u) ** 0.75 * (0.45 + 0.55 * math.sin(min(1.0, u * 2.2) * math.pi / 2))
        return w * (1 - 0.22 * abs(math.sin(u * math.pi * ragged)) ** 0.6) if u > 0.12 else w

    def pt(u, v):
        s = 2 * v - 1                                     # -1 trailing edge, +1 leading edge
        return spine(u) + up * half_width(u, s >= 0) * s + face * curl * width * s * s

    ob = surface(name, pt, 36, 8, mat, 0.06 * width, parent=root, tile=(4, 1))
    shapes.sweep(name + "_lead", [pt(i / 36, 1.0) + up * 0.02 * width for i in range(36)] + [spine(1.0)], 0.035 * width, trim, parent=root)
    tapered(name + "_spine", [spine(i / 30) - face * 0.04 * width for i in range(28)], 0.05 * width, 0.01 * width, trim, parent=root)
    return ob, spine, face


def reliquary_pauldron(sk, m, frame, root):
    n = SIZE[frame]
    R = 0.09 * sk.H * sk.G * 1.25
    sh = sk.joint("shoulder")
    c = sh + Vector((0.15 * R, 0.05 * R, 0.25 * R))
    cap = empty("pauldron_cap", loc=c, parent=root, size=R * 0.3)
    cap.rotation_euler = (0, rad(28), 0)
    zs = 0.75

    def sph(az, phi, r=R, lift=0.0):
        a, p = rad(az), rad(phi)
        return Vector((math.sin(a) * math.sin(p) * (r + lift), -math.cos(a) * math.sin(p) * (r + lift), math.cos(p) * (r + lift) * zs))
    surface("cap", lambda u, v: sph(u * 360, 2 + v * 78), 48, 14, m["filigree"], 0.06 * R, parent=cap, cyclic=True, tile=(5, 2))
    shapes.sweep("cap_ring", ring_pts(lambda t: sph(t * 360, 79, lift=0.03 * R)), 0.05 * R, m["trim"], cyclic=True, parent=cap)
    shapes.sweep("cap_ring2", ring_pts(lambda t: sph(t * 360, 40, lift=0.03 * R)), 0.03 * R, m["trim"], cyclic=True, parent=cap)
    shapes.sphere("cap_gem", 0.13 * R, m["glow"], loc=sph(90, 22, lift=0.02 * R), parent=cap)
    shapes.sweep("cap_gem_ring", ring_pts(lambda t: sph(90 + 30 * math.cos(t * 6.283), 22 + 13 * math.sin(t * 6.283), lift=0.03 * R), 32),
                 0.025 * R, m["trim"], cyclic=True, parent=cap)
    # A hanging under-plate wrapping the arm.
    def under(u, v):
        az = 30 + 120 * u
        r = R * (0.95 + 0.12 * v)
        return c + Vector((math.sin(rad(az)) * r, -math.cos(rad(az)) * r, -0.15 * R - 0.55 * R * v * (0.5 + 0.5 * math.sin(u * math.pi))))
    surface("under", under, 24, 5, m["armour"], 0.06 * R, parent=root, tile=(4, 1))
    shapes.sweep("under_trim", [under(i / 24, 1.0) + (under(i / 24, 1.0) - c).normalized() * 0.03 * R for i in range(25)], 0.03 * R, m["trim"], parent=root)

    # The blades: a main one swept up and out, one or two smaller below it.
    scale = (0.8, 1.0, 1.0, 1.25)[n]
    base = c + Vector((0.35 * R, 0.25 * R, 0.35 * R))
    blade("blade_main", base, (0.8, 0.15, 0.9), (-0.6, -0.3, 0.6), 3.0 * R * scale, 1.0 * R * scale, m["armour"], m["trim"], root, ragged=4)
    if n >= 1:
        blade("blade_second", base + Vector((0.2 * R, 0.3 * R, -0.35 * R)), (1.0, 0.35, 0.35), (-0.3, -0.2, 1.0), 2.3 * R * scale, 0.65 * R * scale, m["trim"], m["trim"], root, ragged=3)
    if n >= 3:
        blade("blade_third", base + Vector((0.2 * R, 0.45 * R, -0.75 * R)), (1.0, 0.55, -0.1), (-0.1, -0.1, 1.0), 1.7 * R * scale, 0.35 * R * scale, m["armour"], m["trim"], root, ragged=3)


def reliquary_collar(sk, m, frame, root):
    H = sk.H
    nk = sk.joint("neck")
    r0, r1 = 0.058 * H, 0.072 * H
    zb = nk.z - 0.03 * H

    def top(az):
        a = rad(az)
        back = (1 - math.cos(a)) / 2
        h = 0.035 * H + 0.04 * H * back
        # Two tall points either side of the face and one at the back.
        for c, k, w in ((28, 0.045, 14), (-28, 0.045, 14), (180, 0.03, 22)):
            d = (az - c + 180) % 360 - 180
            h += k * H * max(0.0, 1 - abs(d) / w) ** 1.5
        return h

    def col(u, v):
        az = u * 360
        z = zb + (nk.z - zb + top(az)) * v
        r = r0 + (r1 - r0) * math.sin(v * math.pi * 0.8) - 0.008 * H * v ** 3
        return Vector((math.sin(rad(az)) * r, -math.cos(rad(az)) * r, z))
    surface("collar", col, 96, 12, m["armour"], 0.004 * H, parent=root, cyclic=True, tile=(8, 1))

    def at(az, v, lift=0.004 * H):
        p = col(az / 360 % 1.0, v)
        return p + Vector((p.x, p.y, 0)).normalized() * lift
    shapes.sweep("collar_rim", ring_pts(lambda t: at(t * 360, 1.0), 120), 0.0026 * H, m["trim"], cyclic=True, parent=root)
    shapes.sweep("collar_base", ring_pts(lambda t: at(t * 360, 0.0)), 0.0024 * H, m["trim"], cyclic=True, parent=root)
    surface("collar_glyphs", lambda u, v: at(u * 360, 0.3 + 0.12 * v, 0.003 * H), 72, 2, m["filigree"], 0.0015 * H, parent=root, cyclic=True, tile=(16, 1), bevel=0)
    shapes.sweep("collar_glow", ring_pts(lambda t: at(t * 360, 0.5, 0.0035 * H)), 0.0012 * H, m["glow"], cyclic=True, parent=root)
    for az in (28, -28, 180):
        shapes.sweep(f"collar_rib{az}", [at(az, v / 12, 0.004 * H) for v in range(1, 13)], 0.002 * H, m["trim"], parent=root)


BUILDERS = {
    "covenant": (covenant_pauldron, covenant_collar),
    "foundries": (foundries_pauldron, foundries_collar),
    "reliquary": (reliquary_pauldron, reliquary_collar),
}

# ------------------------------------------------------------------ build, render, publish


def build(faction, frame, component):
    """Build one part in place on the walker; returns its root (still in world space)."""
    m = kit.materials.library(faction)
    sk = kit.skeleton.Skeleton(faction, frame)
    root = empty(kit.part_name(faction, component, frame), size=sk.H * 0.02)
    fn = BUILDERS[faction][0 if component == "pauldron" else 1]
    fn(sk, m, frame, root)
    bpy.context.view_layer.update()
    return root


def render(faction, frame, out, samples):
    """The parts on the frame's stand-ins, front three-quarter and close up, beside the art."""
    kit.reset_scene()
    kit.render.studio()
    fr = kit.skeleton.build_frame(faction, frame)
    for o in fr.children_recursive:
        if o.get("standin") == "pauldron":
            o.hide_render = True
    left = build(faction, frame, "pauldron")
    collar = build(faction, frame, "collar")
    # The right pauldron: the same build under a mirroring empty, as the web does it.
    mirror = empty("mirror_R")
    mirror.scale = (-1, 1, 1)
    right = build(faction, frame, "pauldron")
    right.parent = mirror
    bpy.context.view_layer.update()
    ours = kit.meshes(left) + kit.meshes(right) + kit.meshes(collar)
    upper = [o for o in kit.meshes(fr) if o.get("standin") in ("torso", "helm", "arm") and not o.hide_render]
    shots = []
    for az, el, nm, objs in ((32, 14, "front", ours + upper), (68, 22, "side", kit.meshes(left) + kit.meshes(collar))):
        p = kit.render.shot(objs, Path(out) / f"{faction}_{frame}_{nm}.png", az=az, el=el, samples=samples, res=(720, 760), margin=0.85)
        kit.render.post(p)
        shots.append(p)
    kit.render.compare(shots, ART[faction], Path(out) / f"{faction}_{frame}_compare.png", height=560,
                       labels=[f"{faction} {frame}: pauldrons and collar", "left pauldron close up"], title=f"{faction} pauldrons and collar ({frame})")
    print("wrote", Path(out) / f"{faction}_{frame}_compare.png")


def publish(faction, frame, components=("pauldron", "collar")):
    for component in components:
        kit.reset_scene()
        root = build(faction, frame, component)
        kit.skeleton.to_joint(root, faction, frame, component)
        # The collar is small on the walker: half-size textures keep a class under budget.
        kit.publish(root, size=1024 if component == "pauldron" else 512, source=HERE / f"{root.name}.blend")


def main():
    args = script_args()
    opts = {"--frame", "--render", "--samples", "--only"}
    val = {a: args[i + 1] for i, a in enumerate(args) if a in opts and i + 1 < len(args)}
    factions = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in opts)] or list(FRAMES)
    samples = int(val.get("--samples", 48))
    for faction in factions:
        frames = [val["--frame"]] if "--frame" in val else FRAMES[faction]
        for frame in frames:
            if "--render" in val:
                render(faction, frame, val["--render"], samples)
            if "--publish" in args:
                publish(faction, frame, [val["--only"]] if "--only" in val else ("pauldron", "collar"))


main()
