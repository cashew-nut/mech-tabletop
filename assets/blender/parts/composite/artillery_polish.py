"""The Artillery's polish pass (2026-11-09): what the Meshy cut got wrong against the part sheet, re-made.

Luke's part sheet (docs/concept-art/artillery/partsheet.jpg, the "exploded first pass") reads as a foundry siege walker:
clawed feet planted on the ground, plated hips, a howitzer over a riveted chest. The cut model kept Meshy's shapes, and
with them Meshy's mistakes:

* **Rubble feet.** Meshy modelled each foot as a pile of rocks with the real foot buried in it. `foot` keeps only the
  ankle stub that meets the shin and builds a clawed foot under it: an ankle drum with brass caps, a riveted instep,
  three splayed toes with red toe plates and steel claws, and a rear spur.
* **The rear slab.** Meshy read the three-quarter view as a third, rear leg. The first cut dropped it with a box that
  only covered x < 0.1, so the pelvis ended in a flat wall on the walker's right and a ragged hip lump on its left.
  `rear_plate` cuts the whole rear level and closes it with an armoured tail plate: an upper and a lower plate in red
  with an iron frame, a brass hatch and rivets.
* **Hanging cable and chains.** A twisted cable hangs under the pauldron and chains hang under the howitzer and the
  shell arm. They are below 1 mm across (they will not print) and read as stray hairs in the game. `STRIP` removes them.
* **A featureless cupola.** The head stand-in is a 4.6 mm ridged hump. `cupola` gives it a commander's cupola: a
  faceted ring, a hatch with a brass rim and hinge, and a vision block with a glowing slit.

Everything is built in print mm (kit axes: x the walker's left, -y forward, z up) and tagged with a paint finish
(paint.code), so the panel paint in artillery.py colours it like the rest. Nothing moves a joint: split.py re-stamps the
voxel grid for the parts changed here, and joints.py fits the pegs and magnets afterwards as before.
"""
import numpy as np

# --- what goes: boxes in print mm ((x0, x1), (y0, y1), (z0, z1)) per part ----------------------------------------
STRIP = {
    "pauldron": [((25.0, 30.5), (17.5, 23.5), (37.0, 49.6))],       # the twisted cable under the side plate
    "forearm": [((29.5, 34.0), (-3.0, 6.5), (21.0, 31.0))],         # the two chain loops under the shell arm's belt
    "torso": [((-3.0, 3.0), (-19.0, -8.0), (48.0, 57.4))],         # the chain under the howitzer's breech
}

REAR_Y = 21.8           # mm: the pelvis ends here; Meshy's third leg (and the ragged hip it left) is behind it


def code(name):
    import paint as PA
    return PA.code(name)


def tag(m, finish):
    c = code(finish)
    return m.set_properties(2, lambda q, old: (c, c))


def cutter(m):
    """A solid used to cut: its faces become cut faces (UV -1, -1)."""
    return m.set_properties(2, lambda q, old: (-1.0, -1.0))


def box(mf, lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return mf.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def hull(mf, pts):
    return mf.Manifold.hull_points(np.asarray(pts, np.float64).tolist())


def chamfer_box(mf, c, half, ch):
    """A box (centre c, half sizes) with every edge chamfered by ch, as a hull."""
    c, h = np.asarray(c, float), np.asarray(half, float)
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                s = np.array([sx, sy, sz], float)
                for ax in range(3):
                    q = h.copy()
                    q[ax] -= ch
                    pts.append(c + s * q)
    return hull(mf, pts)


def rot_z(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])


def place(m, R, t):
    return m.transform(np.concatenate([np.asarray(R, float), np.asarray(t, float)[:, None]], 1).tolist())


def cyl(mf, a, b, r, seg=24, r2=None):
    """Cylinder from a to b (mm)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    v = b - a
    L = float(np.linalg.norm(v))
    ax = v / L
    z = np.array([0.0, 0.0, 1.0])
    w = np.cross(z, ax)
    s, c = np.linalg.norm(w), z @ ax
    if s < 1e-8:
        R = np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    else:
        vx = np.array([[0, -w[2], w[1]], [w[2], 0, -w[0]], [-w[1], w[0], 0]])
        R = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)
    return place(mf.Manifold.cylinder(L, r, r if r2 is None else r2, seg), R, a)


def rivet(mf, p, r=0.42):
    """A domed rivet head at p (mm): a flattened sphere, half sunk."""
    return mf.Manifold.sphere(r, 12).scale([1.0, 1.0, 1.0]).translate(np.asarray(p, float).tolist())


def union(ms):
    ms = [m for m in ms if m is not None and not m.is_empty()]
    import manifold3d as mf
    return mf.Manifold.batch_boolean(ms, mf.OpType.Add) if len(ms) > 1 else ms[0]


# --- feet ----------------------------------------------------------------------------------------------------------
SOLE = 4.5                       # mm: the sole plane (FOOT_Z at print scale)
FOOT_C = np.array([25.4, -8.0])  # mm: the instep's centre (x, y), under the ankle
STUB_Z = 11.2                    # mm: Meshy's ankle stub above this is kept (it meets the shin)
CUT_Z = 13.38                   # mm: the shin / foot cut (artillery.FOOT_TOP at print scale)


def toe(mf, ang, length, width, root_z, claw, root=-3.2):
    """One toe pointing along -y turned `ang` degrees about z, its root `root` mm along y from the instep's centre (the
    front for the three toes, the back for the spur). Returns (iron body, red plate, steel claw, brass knuckle)."""
    R = rot_z(ang)
    o = np.array([FOOT_C[0], FOOT_C[1] + root, 0.0])
    w0, w1 = width / 2, width * 0.36
    body = hull(mf, [R @ p + o for p in (
        (-w0, 0.5, SOLE + 0.4), (w0, 0.5, SOLE + 0.4), (-w0, 0.5, root_z), (w0, 0.5, root_z),
        (-w1, -length, SOLE), (w1, -length, SOLE), (-w1 * 0.9, -length + 0.6, SOLE + 1.9), (w1 * 0.9, -length + 0.6, SOLE + 1.9))])
    # the toe plate: a raised armour plate along the top, stepped in from the edges
    pw0, pw1 = w0 * 0.82, w1 * 0.8
    plate = hull(mf, [R @ p + o for p in (
        (-pw0, -0.4, root_z - 0.35), (pw0, -0.4, root_z - 0.35), (-pw0, -0.4, root_z + 0.55), (pw0, -0.4, root_z + 0.55),
        (-pw1, -length + 1.6, SOLE + 1.75), (pw1, -length + 1.6, SOLE + 1.75), (-pw1, -length + 1.9, SOLE + 2.35),
        (pw1, -length + 1.9, SOLE + 2.35))])
    # the claw: a wedge past the toe's end, down to the ground
    cw = w1 * 0.75
    claw_m = hull(mf, [R @ p + o for p in (
        (-cw, -length + 0.4, SOLE + 0.2), (cw, -length + 0.4, SOLE + 0.2), (-cw, -length + 0.8, SOLE + 1.8),
        (cw, -length + 0.8, SOLE + 1.8), (-0.18, -length - claw, SOLE), (0.18, -length - claw, SOLE))])
    knuckle = cyl(mf, R @ np.array([-w0 - 0.15, -0.9, root_z - 1.4]) + o, R @ np.array([w0 + 0.15, -0.9, root_z - 1.4]) + o, 0.85, 18)
    return body, plate, claw_m, knuckle


def foot(old, shin, mf):
    """The clawed foot under Meshy's ankle stub (see the module docstring)."""
    # the ankle cuff: the shin's own footprint (its convex hull just above the cut), down to the instep, so the foot's
    # top meets the shin face to face; Meshy's rubble round the stub goes
    sec = shin.slice(CUT_Z + 0.25).hull().offset(-0.1, mf.JoinType.Miter)
    stub = tag(mf.Manifold.extrude(sec, CUT_Z + 0.3 - STUB_Z).translate([0.0, 0.0, STUB_Z]), "iron")
    cx, cy = FOOT_C
    iron, red, steel, brass = [], [], [], []
    # instep: a chamfered block from the stub down to the toes, slightly wider at the bottom
    iron.append(hull(mf, [(cx - 4.3, cy - 4.2, SOLE + 0.6), (cx + 4.3, cy - 4.2, SOLE + 0.6), (cx - 4.3, cy + 4.0, SOLE + 0.6),
                          (cx + 4.3, cy + 4.0, SOLE + 0.6), (cx - 3.6, cy - 3.4, 10.4), (cx + 3.6, cy - 3.4, 10.4),
                          (cx - 3.6, cy + 3.3, 10.4), (cx + 3.6, cy + 3.3, 10.4), (cx - 3.0, cy - 2.6, STUB_Z + 0.6),
                          (cx + 3.0, cy - 2.6, STUB_Z + 0.6), (cx - 3.0, cy + 2.8, STUB_Z + 0.6), (cx + 3.0, cy + 2.8, STUB_Z + 0.6)]))
    # ankle drum across the foot, brass caps at both ends
    az = 9.6
    iron.append(cyl(mf, (cx - 4.9, cy + 0.3, az), (cx + 4.9, cy + 0.3, az), 2.15, 28))
    for s in (-1, 1):
        brass.append(cyl(mf, (cx + s * 4.7, cy + 0.3, az), (cx + s * 5.35, cy + 0.3, az), 1.45, 24))
        brass.append(cyl(mf, (cx + s * 5.3, cy + 0.3, az), (cx + s * 5.6, cy + 0.3, az), 0.7, 16))
    # instep armour: a red plate over the front of the instep, riveted
    red.append(hull(mf, [(cx - 3.3, cy - 4.55, SOLE + 1.6), (cx + 3.3, cy - 4.55, SOLE + 1.6), (cx - 3.3, cy - 3.6, SOLE + 1.6),
                         (cx + 3.3, cy - 3.6, SOLE + 1.6), (cx - 2.7, cy - 3.95, 10.0), (cx + 2.7, cy - 3.95, 10.0),
                         (cx - 2.7, cy - 2.9, 10.0), (cx + 2.7, cy - 2.9, 10.0)]))
    for p in ((-2.4, SOLE + 2.3), (2.4, SOLE + 2.3), (-2.0, 9.3), (2.0, 9.3)):
        brass.append(rivet(mf, (cx + p[0], cy - 4.45 + (p[1] - SOLE) * 0.11, p[1]), 0.38))
    # three splayed toes and a rear spur
    for ang, L, w in ((-27.0, 8.6, 3.5), (0.0, 10.4, 4.0), (27.0, 8.6, 3.5)):
        b, p, c, k = toe(mf, ang, L, w, 8.4, 1.7)
        iron.append(b)
        red.append(p)
        steel.append(c)
        brass.append(k)
    b, p, c, k = toe(mf, 180.0, 5.4, 3.6, 7.6, 1.2, root=3.4)
    iron.append(b)
    red.append(p)
    steel.append(c)
    brass.append(k)
    designed = union([tag(union(iron), "iron"), tag(union(red), "red"), tag(union(steel), "steel"), tag(union(brass), "brass")])
    # precedence: later finishes win where solids overlap (the boolean keeps one face per spot)
    new = stub + designed
    new = new - shin
    ps = sorted(new.decompose(), key=lambda m: -m.volume())
    return ps[0] if len(ps) == 1 else union([q for q in ps if q.volume() > 0.5])


# --- the rear of the pelvis ----------------------------------------------------------------------------------------
def rear_plate(pelvis, others, mf):
    """Cut the pelvis level at REAR_Y and close it with a tail plate (iron frame, red plates, brass hatch, rivets)."""
    bb = pelvis.bounding_box()
    cut = cutter(box(mf, (bb[0] - 1, REAR_Y, bb[2] - 1), (bb[3] + 1, bb[4] + 1, bb[5] + 1)))
    pel = pelvis - cut
    ps = sorted(pel.decompose(), key=lambda m: -m.volume())
    pel = union([q for q in ps if q.volume() > 2.0])
    # the cut face's extent, from the slice just in front of it
    P = np.asarray(pel.to_mesh().vert_properties)[:, :3]
    near = P[P[:, 1] > REAR_Y - 0.6]
    xs, zs = near[:, 0], near[:, 2]
    xa, za0, za1 = min(abs(xs.min()), abs(xs.max())), zs.min(), zs.max()
    print(f"  pelvis rear face at y {REAR_Y}: |x| < {xa:.1f}, z {za0:.1f} to {za1:.1f}", flush=True)
    xa = min(max(xa - 1.0, 10.0), 12.5)
    za0 += 1.5
    iron, red, brass = [], [], []
    # backing: a chamfered iron block that closes the cut face and carries the lames
    yb = REAR_Y - 0.4               # starts inside the pelvis so it fuses with it
    iron.append(hull(mf, [(-xa, yb, za0 + 0.8), (xa, yb, za0 + 0.8), (-xa, yb, za1 - 0.4), (xa, yb, za1 - 0.4),
                          (-xa + 1.2, REAR_Y + 2.0, za0 + 1.6), (xa - 1.2, REAR_Y + 2.0, za0 + 1.6),
                          (-xa + 1.2, REAR_Y + 2.0, za1 - 1.2), (xa - 1.2, REAR_Y + 2.0, za1 - 1.2)]))
    # three overlapping lames, each leaning out at its lower edge and narrower than the one above (a tail fauld)
    H = za1 - za0
    lames = ((za1 - 0.6, za1 - 0.42 * H, xa - 0.4, 1.0), (za1 - 0.36 * H, za1 - 0.72 * H, xa - 1.6, 1.5),
             (za1 - 0.66 * H, za0 + 0.6, xa - 3.0, 2.0))
    for i, (zt, zb, xw, lean) in enumerate(lames):
        y0 = REAR_Y + 0.9 + 0.35 * i
        t = 1.7
        lame = hull(mf, [(-xw, y0, zt), (xw, y0, zt), (-xw + 0.5, y0 + lean, zb), (xw - 0.5, y0 + lean, zb),
                         (-xw + 0.35, y0 + t, zt - 0.35), (xw - 0.35, y0 + t, zt - 0.35),
                         (-xw + 0.8, y0 + lean + t, zb + 0.3), (xw - 0.8, y0 + lean + t, zb + 0.3)])
        red.append(lame)
        # rivets along the top edge
        for x in np.linspace(-xw + 1.2, xw - 1.2, 6 - i):
            f = 0.18
            brass.append(rivet(mf, (x, y0 + t + lean * f - 0.05, zt - 0.35 - (zt - zb) * f), 0.36))
    # a brass hatch on the top lame, six bolts round it
    hz = lames[0][0] - 0.5 * (lames[0][0] - lames[0][1])
    hy = REAR_Y + 0.6 + 1.7 + 0.5
    brass.append(cyl(mf, (0, hy - 1.2, hz), (0, hy + 0.35, hz), 2.3, 32))
    iron.append(cyl(mf, (0, hy - 1.0, hz), (0, hy + 0.65, hz), 1.35, 28))
    for i in range(6):
        a = np.radians(30 + 60 * i)
        brass.append(rivet(mf, (1.85 * np.cos(a), hy + 0.3, hz + 1.85 * np.sin(a)), 0.28))
    plate = union([tag(union(iron), "iron"), tag(union(red), "red"), tag(union(brass), "brass")])
    for o in others:
        plate = plate - cutter(o)
    out = pel + plate
    ps = sorted(out.decompose(), key=lambda m: -m.volume())
    return union([q for q in ps if q.volume() > 0.5])


# --- the cupola ----------------------------------------------------------------------------------------------------
def cupola(helm, others, mf):
    """A commander's cupola over Meshy's hump: a faceted ring, a hatch with a brass rim and hinge, and a vision block
    whose slit glows (glow_weight)."""
    bb = helm.bounding_box()
    cx, cy = 0.0, 0.5 * (bb[1] + bb[4]) + 0.4
    z0 = bb[5] - 2.2                     # the ring sits down into the hump's crown
    iron, brass, soot = [], [], []
    ring = mf.Manifold.cylinder(2.6, 4.3, 3.8, 8).rotate([0, 0, 22.5]).translate([cx, cy, z0])
    iron.append(ring)
    brass.append(mf.Manifold.cylinder(0.55, 3.75, 3.75, 32).translate([cx, cy, z0 + 2.45]))
    hatch = mf.Manifold.cylinder(0.75, 3.2, 2.7, 32).translate([cx, cy, z0 + 2.9])
    iron.append(hatch)
    iron.append(cyl(mf, (cx - 1.8, cy + 3.0, z0 + 3.2), (cx + 1.8, cy + 3.0, z0 + 3.2), 0.55, 16))   # hinge
    brass.append(mf.Manifold.cylinder(0.5, 0.75, 0.6, 16).translate([cx + 1.2, cy - 0.9, z0 + 3.55]))  # handle boss
    # vision block on the front: a chamfered visor with a dark slit
    vy = cy - 3.35
    vis = chamfer_box(mf, (cx, vy, z0 + 1.15), (3.0, 1.0, 1.0), 0.35)
    slit = box(mf, (cx - 2.3, vy - 1.4, z0 + 0.95), (cx + 2.3, vy - 0.55, z0 + 1.45))
    iron.append(vis - cutter(slit))
    soot.append(box(mf, (cx - 2.3, vy - 0.62, z0 + 0.95), (cx + 2.3, vy - 0.4, z0 + 1.45)))
    # periscope on the left rear
    iron.append(chamfer_box(mf, (cx + 2.3, cy + 1.6, z0 + 3.3), (0.8, 0.9, 1.0), 0.25))
    soot.append(box(mf, (cx + 1.7, cy + 0.66, z0 + 3.4), (cx + 2.9, cy + 0.74, z0 + 3.9)))
    add = union([tag(union(iron), "iron"), tag(union(brass), "brass"), tag(union(soot), "glow")])
    for o in others:
        add = add - cutter(o)
    out = helm + add
    ps = sorted(out.decompose(), key=lambda m: -m.volume())
    return union([q for q in ps if q.volume() > 0.3])


def design(solid, mf):
    out = dict(solid)
    for k, boxes in STRIP.items():
        if k not in out:
            continue
        v0 = out[k].volume()
        for lo_hi in boxes:
            (x0, x1), (y0, y1), (z0, z1) = lo_hi
            out[k] = out[k] - cutter(box(mf, (x0, y0, z0), (x1, y1, z1)))
        ps = sorted(out[k].decompose(), key=lambda m: -m.volume())
        out[k] = union([q for q in ps if q.volume() > 0.5])      # chain links left loose
        print(f"  {k}: stripped {v0 - out[k].volume():.1f} mm3 (cable, chains)", flush=True)
    if "pelvis" in out:
        v0 = out["pelvis"].volume()
        others = [out[k] for k in ("torso", "back") if k in out]
        others += [out["thigh"], out["thigh"].mirror([1.0, 0.0, 0.0])] if "thigh" in out else []
        out["pelvis"] = rear_plate(out["pelvis"], others, mf)
        print(f"  pelvis: rear plate, {v0:.0f} -> {out['pelvis'].volume():.0f} mm3", flush=True)
    if "foot" in out:
        v0 = out["foot"].volume()
        out["foot"] = foot(out["foot"], out["shin"], mf)
        print(f"  foot: clawed foot, {v0:.0f} -> {out['foot'].volume():.0f} mm3, "
              f"{len(out['foot'].decompose())} piece(s)", flush=True)
    if "helm" in out:
        v0 = out["helm"].volume()
        out["helm"] = cupola(out["helm"], [out[k] for k in ("torso", "back") if k in out], mf)
        print(f"  helm: cupola, {v0:.0f} -> {out['helm'].volume():.0f} mm3", flush=True)
    return out


CHANGED = ("pauldron", "forearm", "torso", "pelvis", "foot", "helm")    # split.py re-stamps these in the voxel grid
