"""The Sentinel's second polish pass (2026-11-09): the banner, the spire pennants and a heavy elbow, designed in print mm.

    split.py calls sentinel.design (this module's `design`) after the cut; nothing here runs on its own.

Luke asked for the three things the first polish left open (docs/sentinel-composite/README.md):

* **The banner.** The concept's hero and back view carry a crimson banner on a gold staff that rises behind the left
  pauldron, above the spires, with a cross at its tip; the flag streams out to the walker's left and a little back. Meshy
  did not make it (too thin), so it is built here: a gold staff seated in the cap of the pack's left rear tower, a gold
  ball and cross finial, gold rings above and below the hoist, and a rippled swallowtail flag in crimson with a raised gold
  cross and a gold hem. It is part of the back (the spires and pack), so it comes off with the pack.
* **The spire pennants.** The part sheet flies a small crimson pennant from each spire, streaming outward. Each is a
  rippled swallowtail with a gold hem, held to the spire by two gold rings.
* **A heavy elbow.** The upper arm is a 7 mm column and the elbow was a 2 mm peg with a 1 x 1 magnet under a 2.1 cm3 gun.
  The elbow is now a ball knuckle 8.6 mm across: a blackened steel ball with a gold bearing band on the seam, a narrower
  steel housing with a gold band up the upper arm (the arm's half), and the lower half ball with a gold collar on the
  forearm and on the Carapace Gun (both take the same socket). The ball's flat seam is the cut, square to the upper arm's
  bone, so joints.py (sentinel.KNUCKLES) puts a much bigger peg and magnet down that bone.

Printability (resin, 1.5x): flags are 1.1 mm thick before the ripple (at least 0.9 mm through the steepest fold), the
pennants 0.95 mm, the staff 1.7 mm across, every designed piece is fused into its part and the parts stay closed solids.
Finishes are UV codes build.py knows: gold (-2), black frame metal (-3), crimson cloth (-4).
"""
import numpy as np

GOLD_UV, FRAME_UV, CLOTH_UV = (-2.0, -2.0), (-3.0, -3.0), (-4.0, -4.0)

# --- the elbow -------------------------------------------------------------------------------------------------------
ELBOW_R = 4.3                 # mm, the ball (8.6 mm across; the upper arm is 7.3 mm, the gun 10.3 mm)
# housing up the upper arm, as fractions of ELBOW_R: start, top, top radius, foot radius; then the cone into the limb
HOUSING = dict(start=0.40, top=1.30, r0=0.82, r1=0.76, cone=0.30, cone_to=0.55)
BAND = 0.11                   # gold band at the housing's top (x R)
SEAM = (0.12, 1.065)          # gold bearing band on the seam: half height, radius (x R)
CHILD_COLLAR = (-1.04, -0.80, 0.62)   # the forearm's collar where it leaves the ball: from, to, radius (x R)

# --- the banner (print mm, kit axes: x the walker's left, -y forward, z up) -----------------------------------------
TOWER = (5.8, 17.0, 69.2)     # the cap of the pack's left rear tower, where the staff is seated
STAFF_R = 0.85
STAFF_TOP = 89.2
FLY_DIR = 20.0                # degrees back from the walker's left (the flag streams left and a little behind)
FLAG_TOP = 88.2
FLAG_T = 1.25
FLAG_H = 9.0
# outline in the flag's plane: u along the fly from the staff's axis, v up from the flag's top edge
FLAG = [(0.0, 0.0), (12.0, 0.0), (22.0, -1.3), (15.4, -4.5), (21.0, -7.7), (11.0, -9.0), (0.0, -9.0)]
FLAG_RIPPLE = dict(amp=1.3, wave=8.5, phase=0.6, tilt=0.18, droop=1.8)
CROSS = dict(c=(5.7, -4.5), arm=(5.2, 6.6), w=1.15, bar=(2.1, 0.85))   # centre, across x tall, stroke, end bars
HEM = 0.55
# --- the pennants (one per spire, mirrored) ---------------------------------------------------------------------------
SPIRE = (5.2, 8.62)           # the left spire's axis (x, y)
SPIRE_R = 1.55                # its radius over the pennant's hoist (z 69 to 73)
PENNANT_TOP = 73.2
PENNANT_T = 0.95
PENNANT = [(0.0, 0.0), (5.4, -0.45), (9.0, -1.0), (6.3, -2.0), (8.4, -3.3), (4.8, -3.55), (0.0, -3.6)]
PENNANT_RIPPLE = dict(amp=0.55, wave=4.6, phase=1.4, tilt=0.25, droop=0.5)
PENNANT_DIR = -12.0           # degrees: a little forward of straight out


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _align(zc, ax):
    w = np.cross(zc, ax)
    s, c = np.linalg.norm(w), zc @ ax
    if s < 1e-8:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    K = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
    return np.eye(3) + K + K @ K * ((1 - c) / s ** 2)


def _place(m, R, t):
    return m.transform(np.concatenate([np.asarray(R, float), np.asarray(t, float)[:, None]], 1).tolist())


def _orient(m, axis, c):
    """A solid built along local +z, turned so +z runs along `axis` and moved to c."""
    return _place(m, _align(np.array([0.0, 0.0, 1.0]), _unit(axis)), c)


def _tag(m, uv):
    return m.set_properties(2, lambda p, old: uv)


def _mirror(m):
    return m.transform([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])


def _add(mf, ms):
    ms = [m for m in ms if not m.is_empty()]
    return mf.Manifold.batch_boolean(ms, mf.OpType.Add) if len(ms) > 1 else ms[0]


# --- the elbow knuckle -------------------------------------------------------------------------------------------------
def elbow_axis():
    """The upper arm's bone at the elbow, from the elbow towards the shoulder (into the parent), print mm."""
    from layout import joint
    return _unit(np.array(joint("shoulder")) - np.array(joint("elbow")))


def elbow_knuckle(mf):
    """(parent half, child half, centre, axis) of the left elbow's knuckle, print mm, tagged. The parent's half is the ball
    above the seam plane with the housing; the child's the ball below it with its collar. The seam band is split with them."""
    from layout import joint
    c, a, R = np.array(joint("elbow")), elbow_axis(), ELBOW_R
    h = HOUSING
    n = 72
    up = [_tag(mf.Manifold.cylinder((h["top"] - h["start"]) * R, h["r0"] * R, h["r1"] * R, n).translate((0, 0, h["start"] * R)),
               FRAME_UV),
          _tag(mf.Manifold.cylinder(h["cone"] * R, h["r1"] * R, h["cone_to"] * R, n).translate((0, 0, h["top"] * R)),
               FRAME_UV),
          _tag(mf.Manifold.cylinder(BAND * R, h["r1"] * R * 1.06, h["r1"] * R * 1.06, n)
               .translate((0, 0, (h["top"] - BAND) * R)), GOLD_UV)]
    lo, hi, cr = CHILD_COLLAR
    down = [_tag(mf.Manifold.cylinder((hi - lo) * R, cr * R, cr * R, 56).translate((0, 0, lo * R)), GOLD_UV)]
    ball = _tag(mf.Manifold.sphere(R, 96), FRAME_UV)
    sh, sr = SEAM
    seam = _tag(mf.Manifold.cylinder(2 * sh * R, sr * R, sr * R, n).translate((0, 0, -sh * R)), GOLD_UV)
    whole = _add(mf, [ball, seam])
    # each half is the knuckle cut by a box, so the seam's flat face is cut-face metal (UV -1, -1): joints.py finds it
    # as the interface between the two parts
    box = lambda above: _tag(mf.Manifold.cube((4 * R, 4 * R, 2 * R), True).translate((0, 0, R if above else -R)),
                             (-1.0, -1.0))
    top, bot = whole ^ box(True), whole ^ box(False)
    parent = _orient(_add(mf, [top] + up), a, c)
    child = _orient(_add(mf, [bot] + down), a, c)
    return parent, child, c, a


def half_space(mf, c, a, above, size=400.0):
    box = mf.Manifold.cube((size, size, size), True).translate((0, 0, size / 2 if above else -size / 2))
    return _orient(box, a, c)


def heavy_elbow(solid, mf):
    """Give the upper arm the knuckle's top half and housing, and the forearm and the gun its bottom half. The gun is still
    on the figure's right here (joints.py mirrors it onto the left elbow), so it takes the mirrored knuckle."""
    parent, child, c, a = elbow_knuckle(mf)
    R = ELBOW_R
    # keep the knuckle out of the walker's other parts (the pauldron's rim over the housing, the torso's side)
    others = [solid[k] for k in ("pauldron", "torso", "pelvis", "thigh") if k in solid]
    block = _add(mf, others)
    parent, child = parent - block, child - block
    # the ball's own space: everything of the arm below the seam inside the ball goes, and of the forearm above it
    # the space the arm's half takes, plus clearance for a straight pull: the seam band's ring, then the ball's width up
    # the bone (the housing is narrower). Meshy's elbow medallion outside it stays, tucked behind the ball.
    h = HOUSING
    zone = _orient(_add(mf, [mf.Manifold.cylinder(1.3 * R, SEAM[1] * R + 0.05, SEAM[1] * R + 0.05, 72).translate((0, 0, -1.3 * R)),
                             mf.Manifold.cylinder(SEAM[0] * R + 0.1, SEAM[1] * R + 0.05, SEAM[1] * R + 0.05, 72),
                             mf.Manifold.cylinder((h["top"] + h["cone"]) * R + 1.0, R + 0.05, R + 0.05, 72)]), a, c)
    below, above = half_space(mf, c, a, False), half_space(mf, c, a, True)
    if "arm" in solid:
        solid["arm"] = (solid["arm"] - (zone ^ below)) + parent
    if "forearm" in solid:
        solid["forearm"] = (solid["forearm"] - (zone ^ above)) + child
    if "gun" in solid:
        solid["gun"] = (solid["gun"] - _mirror(zone ^ above)) + _mirror(child)
    for k in ("arm", "forearm", "gun"):
        if k in solid:
            ps = sorted(solid[k].decompose(), key=lambda p: -p.volume())
            lost = sum(p.volume() for p in ps[1:])
            if lost > 0.05:
                print(f"  elbow: {k} dropped {lost:.2f} mm3 of loose bits", flush=True)
            solid[k] = ps[0]
    print(f"  elbow: knuckle r {R} mm at {np.round(c, 2).tolist()}, axis {np.round(a, 3).tolist()}", flush=True)
    return solid


# --- flags -------------------------------------------------------------------------------------------------------------
def _ripple(rp, length):
    """Warp for a flag built flat in (u, v, w): w gains a travelling wave that grows from the hoist, v droops at the fly."""
    def f(P):
        P = np.array(P, float)
        u, v = P[:, 0], P[:, 1]
        s = np.clip(u / length, 0, None)
        P[:, 2] += rp["amp"] * s ** 1.1 * np.sin(2 * np.pi * u / rp["wave"] + rp["phase"] + rp["tilt"] * v)
        P[:, 1] -= rp["droop"] * s ** 2
        return P
    return f


def _slab(mf, polys, t, ripple, step=0.45):
    """Polygons in the (u, v) plane extruded t thick about w = 0, refined and rippled."""
    cs = mf.CrossSection(polys) if not isinstance(polys, mf.CrossSection) else polys
    m = mf.Manifold.extrude(cs, t).translate((0, 0, -t / 2))
    return m.refine_to_length(step).warp_batch(ripple)


def _cross(mf, k):
    (cx, cy), (aw, ah), w, (bl, bw) = k["c"], k["arm"], k["w"], k["bar"]
    sq = lambda x0, y0, x1, y1: mf.CrossSection.square((x1 - x0, y1 - y0)).translate((x0, y0))
    parts = [sq(cx - w / 2, cy - ah / 2, cx + w / 2, cy + ah / 2),            # upright
             sq(cx - aw / 2, cy + ah * 0.12 - w / 2, cx + aw / 2, cy + ah * 0.12 + w / 2)]   # cross arm, a little high
    # end bars (a cross crosslet): across the top and both arm ends
    parts += [sq(cx - bl / 2, cy + ah / 2 - bw, cx + bl / 2, cy + ah / 2),
              sq(cx - aw / 2, cy + ah * 0.12 - bl / 2, cx - aw / 2 + bw, cy + ah * 0.12 + bl / 2),
              sq(cx + aw / 2 - bw, cy + ah * 0.12 - bl / 2, cx + aw / 2, cy + ah * 0.12 + bl / 2)]
    return mf.CrossSection.batch_boolean(parts, mf.OpType.Add)


def flag(mf, outline, t, rp, hem=None, cross=None):
    """A cloth flag in its own frame (u along the fly, v up, w its normal): crimson, with a raised gold hem and cross."""
    length = max(p[0] for p in outline)
    ripple = _ripple(rp, length)
    pts = np.asarray(outline, float)
    if np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1]) < 0:
        pts = pts[::-1]                 # counter-clockwise, or the cross section is empty
    cs = mf.CrossSection([pts.tolist()])
    out = [_tag(_slab(mf, cs, t, ripple), CLOTH_UV)]
    if hem:
        ring = cs - cs.offset(-hem, mf.JoinType.Miter)
        # the hoist edge runs into the sleeve: no hem along it
        ring = ring - mf.CrossSection.square((hem * 2.2, 40.0)).translate((-hem * 1.1, -20.0))
        out.append(_tag(_slab(mf, ring, t + 0.26, ripple), GOLD_UV))
    if cross:
        out.append(_tag(_slab(mf, _cross(mf, cross), t + 0.34, ripple), GOLD_UV))
    return _add(mf, out)


def _flag_frame(deg, mirror=False):
    """Columns: the fly direction, up, the flag's normal (kit axes)."""
    a = np.radians(deg)
    u = np.array([np.cos(a), np.sin(a), 0.0])
    if mirror:
        u[0] = -u[0]
    v = np.array([0.0, 0.0, 1.0])
    return np.stack([u, v, np.cross(u, v)], 1)


def banner(mf):
    """The staff, its finial and rings, and the flag, print mm."""
    x, y, z0 = TOWER
    staff = _tag(mf.Manifold.cylinder(STAFF_TOP - z0 + 1.5, STAFF_R, STAFF_R, 40).translate((x, y, z0 - 1.5)), GOLD_UV)
    knob = _tag(mf.Manifold.sphere(1.15, 40).translate((x, y, STAFF_TOP + 0.6)), GOLD_UV)
    fin = [mf.Manifold.cube((0.75, 0.75, 3.4)).translate((x - 0.375, y - 0.375, STAFF_TOP + 1.3)),
           mf.Manifold.cube((2.5, 0.75, 0.75)).translate((x - 1.25, y - 0.375, STAFF_TOP + 3.0))]
    fin = [_tag(f, GOLD_UV) for f in fin]
    # a collar where the staff is seated in the tower, and rings above and below the hoist
    rings = [_tag(mf.Manifold.cylinder(0.9, 1.35, 1.2, 40).translate((x, y, z0 - 0.3)), GOLD_UV),
             _tag(mf.Manifold.cylinder(0.75, 1.25, 1.25, 40).translate((x, y, FLAG_TOP + 0.05)), GOLD_UV),
             _tag(mf.Manifold.cylinder(0.75, 1.25, 1.25, 40).translate((x, y, FLAG_TOP - FLAG_H - 0.8)), GOLD_UV)]
    sleeve = _tag(mf.Manifold.cylinder(FLAG_H, 1.12, 1.12, 40).translate((x, y, FLAG_TOP - FLAG_H)), CLOTH_UV)
    f = flag(mf, FLAG, FLAG_T, FLAG_RIPPLE, hem=HEM, cross=CROSS)
    f = _place(f, _flag_frame(FLY_DIR), (x, y, FLAG_TOP))
    return _add(mf, [staff, knob, *fin, *rings, sleeve, f])


def pennants(mf):
    """A pennant on each spire, streaming outward, held by two gold rings."""
    x, y = SPIRE
    out = []
    for side in (1, -1):
        f = flag(mf, PENNANT, PENNANT_T, PENNANT_RIPPLE, hem=0.42)
        f = f.translate((SPIRE_R * 0.55, 0, 0))     # its hoist edge sits in the spire
        f = _place(f, _flag_frame(PENNANT_DIR, mirror=side < 0), (side * x, y, PENNANT_TOP))
        rings = [_tag(mf.Manifold.cylinder(0.6, SPIRE_R + 0.35, SPIRE_R + 0.35, 40).translate((side * x, y, z)), GOLD_UV)
                 for z in (PENNANT_TOP - 0.2, PENNANT_TOP - 3.6 - 0.45)]
        out += [f, *rings]
    return _add(mf, out)


def design(solid, mf):
    solid = heavy_elbow(solid, mf)
    if "back" in solid:
        before = solid["back"].volume()
        add = banner(mf) + pennants(mf)
        # keep clear of the parts next to the pack (the left pauldron, the torso)
        others = [solid[k] for k in ("pauldron", "torso", "helm") if k in solid]
        add = add - _add(mf, others)
        solid["back"] = solid["back"] + add
        ps = solid["back"].decompose()
        print(f"  back: banner and pennants +{solid['back'].volume() - before:.1f} mm3, {len(ps)} piece(s)", flush=True)
    return solid
