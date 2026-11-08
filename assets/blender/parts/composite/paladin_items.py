"""The Paladin's three per-mech items, cut as closed parts that plug into designed hardpoints (numpy + manifold3d, no Blender).

    ~/bvenv/bin/python -I paladin_items.py PARTS OUT --rack RACK_WORK --shield SHIELD_WORK [--pod PALADIN_WORK]

PARTS   models/paladin-composite-1.5x (stl/<part>.stl, report.json): the Paladin the items plug into.
OUT     gets kit/<item>.npz (closed solids with Meshy UVs, the format build.py bakes), stl/ (print copies, plus the two
        host parts that gained hardpoints and, with a native right pauldron, pauldron_r_clear.stl: its cape cleared of the
        right forearm's bracer socket), hosts/ (the sockets for the web), tex_*.jpg per item under work/<item>/, and
        fit.json (the checks below).
*_WORK  a `cut.py extract` folder (mesh.npz + tex_*.jpg): the Meshy generation for that item. --pod is the Paladin's own
        WORK folder after split.py (parts/pod.npz is the shoulder pod cut from the Meshy Paladin).

The items follow the walker's own method (README.md): the shape is Meshy's, the fit is designed here.

  * Missile Rack (`item_missile-rack@paladin`) and Shield (`item_kinetic-shield@paladin`) are Meshy generations (image-to-3D
    from a text-to-image reference in the Paladin's black, gold and red). Each is one closed surface, so it is turned
    into the solid, scaled to print mm, and given a designed mount collar and the D peg with its 2 x 1 mm magnet pocket.
  * Carapace Gun (`item_carapace-gun@paladin`) is the Meshy pod the walker was already cut with. Its old stem had no
    room for a magnet (the pod is a thin-walled lattice: no 3 mm disc fits anywhere in it), so the stem is cut off flat
    and the pod gets the same mount collar and peg as the rack.

Hardpoints (the host parts get a designed socket, so the peg plugs into solid metal with a 0.4 mm wall at least):

  * Shoulder: a gunmetal pedestal on the torso's upper back, 6.8 mm tall, with the hole and a magnet pocket at its bottom.
    It flares into a flange where it meets the torso, has a chamfered seat and two proud gold bands like the item collars'
    own, so the socket and the item on it read as one fitting (a plain cylinder read as a tin can). Left and right
    (mirrored); the right one is trimmed against the native right pauldron. The Carapace Gun and the Missile Rack use the
    same socket, either side.
  * Bracer: the same kind of boss on the forearm's outer face, with a gold rim under its chamfered seat, same hole. The
    Kinetic Shield plugs into it.

The sockets are also written to hosts/<socket>.npz for the web (scripts/publish-composite.mjs merges them into the torso
and forearm): positions P, triangles T, crease-split normals N and a per-triangle finish M (0 gunmetal, 1 gold).

Item frame (mm, origin at the socket centre on the seat plane): +Z is out of the host. Pegs go to -Z. The items are modelled for
the walker's left; the web mirrors them for the right.

Checks written to fit.json (the script exits 1 if one fails): one closed piece; the peg is the socket's peg and fills no solid of
the host (its hole is 0.1 mm bigger); the hole and its 0.4 mm wall lie inside the host; the item touches no other part of
the walker, on either side, at rest and with the forearm bent for the shield.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifold3d as mf  # noqa: E402
from joints import frame, peg_shapes, save as save_npz  # noqa: E402

PEG_R, PEG_L, MAGNET = 1.5, 3.0, (1.0, 1.0)         # radius, length, (magnet radius, thickness): a 2 x 1 mm disc
WALL = 0.4
CLEAR = 0.15                                          # mm of clearance the item keeps from the rest of the walker

SHOULDER = dict(centre=(8.0, 4.0, 77.8), out=(0.0, 0.0, 1.0), boss_z0=71.0)
# socket profiles, item frame (seat at z = 0): (z, radius) stations from the bottom up, and the gold bands (z0, z1), proud 0.15
# mm like the collars' bands. The seat chamfers to the collar's own radius, so collar and socket run on flush.
SHOULDER_BOSS = dict(stations=((-6.8, 4.0), (-5.6, 3.45), (-0.2, 3.1), (0.0, 2.9)), bands=((-5.75, -5.4), (-0.6, -0.3)))
BRACER_BOSS = dict(stations=((-6.0, 3.3), (-0.2, 3.1), (0.0, 2.9)), bands=((-0.6, -0.3),))
# the forearm's outer face slopes inward towards the elbow (about 12 degrees), so the bracer's axis leans with it; the seat is
# 0.5 mm proud of the highest point of the forearm under the collar
BRACER = dict(y=-5.5, z=48.0, tilt_deg=12.0, boss_depth=6.0, proud=0.5)
COLLAR_R = 2.9
RACK_SCALE = 6.5          # print mm per Meshy unit: 12.4 mm long, 8.3 wide, 10.3 tall (the pod it replaces is 15.5 x 9.2 x 11.5)
SHIELD_SCALE = 7.9        # 15 mm tall, 8.7 wide
STANDOFF = 2.6            # mm between the seat and the back of the shield plate

PAINT_CAP, PAINT_GOLD = (-1.0, -1.0), (-2.0, -2.0)   # build.py: UV (-1,-1) bakes gunmetal, (-2,-2) bakes gold


def mark(m, uv):
    return m.set_properties(2, lambda p, old: uv)


def cyl(r, z0, z1, uv=PAINT_CAP, n=64):
    return mark(mf.Manifold.cylinder(z1 - z0, r, r, n).translate((0, 0, z0)), uv)


def load_stl(path):
    import trimesh
    t = trimesh.load(path)
    t.merge_vertices()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def load_meshy(work):
    """The Meshy generation as one manifold with its UVs as vertex properties (UV seams merged by position)."""
    d = np.load(Path(work) / "mesh.npz")
    me = mf.Mesh(vert_properties=np.column_stack([d["V"], d["UV"]]).astype(np.float32), tri_verts=d["F"].astype(np.uint32))
    me.merge()
    m = mf.Manifold(me)
    assert m.status().name == "NoError" and len(m.decompose()) == 1, "the Meshy mesh is not one closed solid"
    return m


def affine(m, R, t):
    """x -> R x + t (R is 3x3, rows are the new axes in the old coordinates)."""
    return m.transform(np.concatenate([np.asarray(R, float), np.asarray(t, float)[:, None]], 1).tolist())


def stl_bytes(m):
    mm = m.to_mesh()
    P, T = np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts)
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    n = np.cross(B - A, C - A)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    rec = np.zeros(len(T), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, np.stack([A, B, C], 1)
    return b"composite paladin item, mm".ljust(80, b" ") + np.uint32(len(T)).tobytes() + rec.tobytes()


def plain(m):
    """The same solid without the UV properties (for the print copy)."""
    mm = m.to_mesh()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(mm.vert_properties)[:, :3].astype(np.float32),
                               tri_verts=np.asarray(mm.tri_verts, np.uint32), merge_from_vert=np.asarray(mm.merge_from_vert, np.uint32),
                               merge_to_vert=np.asarray(mm.merge_to_vert, np.uint32)))


class Socket:
    """A hardpoint: where the peg goes, in world print mm."""

    def __init__(self, centre, out):
        self.c = np.array(centre, float)
        self.out = np.array(out, float) / np.linalg.norm(out)
        axis_in = -self.out
        self.add, self.hole = peg_shapes(PEG_R, PEG_L, MAGNET, axis_in, self.c)
        self.R = frame(self.out, np.array([1.0, 0, 0]) if abs(self.out[0]) < 0.9 else np.array([0.0, 0, 1.0]))   # item frame

    def world(self, m):
        """An item-frame solid to world print mm."""
        return affine(m, self.R, self.c)

    def collar(self, h):
        """The mount collar under an item: a gunmetal cylinder with two gold bands, item frame, seat at z = 0."""
        parts = [cyl(COLLAR_R, 0.0, h), cyl(COLLAR_R + 0.15, 0.45, 0.8, PAINT_GOLD), cyl(COLLAR_R + 0.15, h - 0.9, h - 0.55, PAINT_GOLD)]
        return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def mirror(m):
    return m.mirror((1, 0, 0))


def socket_boss(stations, bands, n=72):
    """A host socket in the item frame (seat at z = 0, out of the host along +z): gunmetal cones through the (z, r) stations,
    with proud gold bands."""
    zs, rs = [z for z, _ in stations], [r for _, r in stations]
    parts = []
    for i, ((z0, r0), (z1, r1)) in enumerate(zip(stations[:-1], stations[1:])):
        # each cone runs 0.02 mm into the next one: cones that only touch at a face can union as separate pieces
        e = 0.02 if i < len(stations) - 2 else 0.0
        parts.append(mark(mf.Manifold.cylinder(z1 + e - z0, r0, r1 + (r1 - r0) * e / (z1 - z0), n).translate((0, 0, z0)), PAINT_CAP))
    for z0, z1 in bands:
        r0, r1 = np.interp(z0, zs, rs) + 0.15, np.interp(z1, zs, rs) + 0.15
        parts.append(mark(mf.Manifold.cylinder(z1 - z0, float(r0), float(r1), n).translate((0, 0, z0)), PAINT_GOLD))
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def host_arrays(m, crease=35.0):
    """A socket mesh for the web: positions P, triangles T, normals N (smooth up to `crease` degrees, split at sharper
    edges) and the finish M per triangle (1 where the solid carries the gold mark, else 0)."""
    mm = m.to_mesh()
    vp = np.asarray(mm.vert_properties, np.float64)
    T = np.asarray(mm.tri_verts, np.int64)
    P = vp[:, :3]
    gold = (np.abs(vp[T, 3:5] + 2.0) < 0.5).all((1, 2)) if vp.shape[1] >= 5 else np.zeros(len(T), bool)
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    fn = np.cross(B - A, C - A)                                   # area weighted
    fu = fn / (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12)
    pid = np.unique(np.round(P, 4), axis=0, return_inverse=True)[1].ravel()
    cv, cf = pid[T].ravel(), np.repeat(np.arange(len(T)), 3)      # corner -> position, face
    order = np.argsort(cv, kind="stable")
    N = np.zeros((len(cv), 3))
    cos = np.cos(np.radians(crease))
    for grp in np.split(order, np.flatnonzero(np.diff(cv[order])) + 1):
        f = cf[grp]
        N[grp] = ((fu[f] @ fu[f].T) > cos) @ fn[f]
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    Pc = P[T].reshape(-1, 3)
    _, first, inv = np.unique(np.column_stack([np.round(Pc, 4), np.round(N, 3)]), axis=0, return_index=True, return_inverse=True)
    return dict(P=Pc[first].astype(np.float32), T=inv.ravel().reshape(-1, 3).astype(np.int32), N=N[first].astype(np.float32),
                M=gold.astype(np.int32))


def host_boss(sock, host, others, r, z_lo, z_hi):
    """A gunmetal boss (cylinder along the socket's out axis from z_lo to z_hi below/above the seat, item frame) fused to the host
    and trimmed where other parts of the walker are."""
    b = sock.world(cyl(r, z_lo, z_hi))
    for o in others:
        b = b - o
    return b


def pieces(m):
    return len(m.decompose())


def check_fit(name, item, host_modified, walker, sock, extra=None):
    """Closed, one piece; peg clear of solid; no clash with the walker; hole and wall in the host."""
    info = {"closed": item.status().name == "NoError", "pieces": pieces(item), "volume_mm3": round(item.volume(), 1),
            "tris": item.num_tri()}
    bb = item.bounding_box()
    info["size_mm"] = [round(bb[3 + i] - bb[i], 1) for i in range(3)]
    clashes = {}
    for k, o in walker.items():
        v = (item ^ o).volume()
        if v > 1e-3:
            clashes[k] = round(v, 3)
    info["clashes_mm3"] = clashes
    # the hole and its wall lie inside the host: a cylinder radius hole+WALL, from the seat down past the magnet pocket
    depth = PEG_L + 0.15 + MAGNET[1] + 0.1
    ring = mf.Manifold.cylinder(depth, PEG_R + 0.1 + WALL, PEG_R + 0.1 + WALL, 48).translate((0, 0, -depth))
    miss = (sock.world(ring) - host_modified - sock.hole).volume()
    info["wall_missing_mm3"] = round(miss, 3)
    info["peg_in_host_mm3"] = round((sock.add ^ host_modified).volume(), 4)
    info["pass"] = bool(info["closed"] and info["pieces"] == 1 and not clashes and miss < 0.02 and info["peg_in_host_mm3"] < 0.01)
    return info


def surface_x(forearm, y, z, r=3.0):
    """The highest x of the forearm within a disc of radius r about (y, z): the bracer seat goes just outside it."""
    for x in np.arange(32, 18, -0.25):
        d = mf.Manifold.cylinder(1.0, r, r, 24).rotate((0, 90, 0)).translate((x, y, z))
        if (forearm ^ d).volume() > 0.002:
            return float(x)
    raise RuntimeError("no forearm at the bracer position")


def shield_frame(work):
    """The Meshy shield's own axes: up (its long axis), side, and the front normal (the shield stands tilted in the Meshy file)."""
    V = np.load(Path(work) / "mesh.npz")["V"].astype(np.float64)
    c = V.mean(0)
    n = np.linalg.svd(V - c, full_matrices=False)[2][2]
    n = -n if n[1] > 0 else n               # the front (boss) faces -y in the Meshy file
    up = np.array([0, 0, 1.0])
    up = up - (up @ n) * n
    up /= np.linalg.norm(up)
    side = np.cross(up, n)
    Rm = np.stack([up, -side, n])           # rows: item X (up), item Y, item Z (front, out of the host): right-handed
    return V, c, Rm


def main(parts_dir, out, rack_work, shield_work, pod_work=None):
    parts_dir, out = Path(parts_dir), Path(out)
    for d in ("kit", "stl", "work", "hosts"):
        (out / d).mkdir(parents=True, exist_ok=True)
    report = {}
    names = ("pelvis", "torso", "helm", "back", "pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot", "blade")
    P = {k: load_stl(parts_dir / "stl" / f"{k}.stl") for k in names}
    SIDED = ("pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot", "blade")
    walker = dict(P)
    for k in SIDED:
        walker[k + "_R"] = mirror(P[k])
    if (parts_dir / "stl" / "pauldron_r.stl").exists():      # the native right pauldron and its long cape (paladin.py)
        walker["pauldron_R"] = load_stl(parts_dir / "stl" / "pauldron_r.stl")

    # ---- shoulder hardpoint on the torso ------------------------------------------------------------------------------
    sock = Socket(SHOULDER["centre"], SHOULDER["out"])
    others = [walker[k] for k in ("back", "helm", "pauldron", "pauldron_R", "arm", "arm_R")]
    assert abs(SHOULDER_BOSS["stations"][0][0] + (SHOULDER["centre"][2] - SHOULDER["boss_z0"])) < 1e-6
    boss_cyl = sock.world(socket_boss(**SHOULDER_BOSS))
    boss_l = boss_cyl
    for o in others:
        boss_l = boss_l - o
    boss_r = mirror(boss_cyl)
    for o in [walker[k] for k in ("back", "helm", "pauldron", "pauldron_R", "arm", "arm_R")]:
        boss_r = boss_r - o
    hole_l, hole_r = sock.hole, mirror(sock.hole)
    torso_mod = (P["torso"] + boss_l + boss_r) - hole_l - hole_r
    torso_mod = mf.Manifold.batch_boolean([p for p in torso_mod.decompose() if p.volume() > 1.0], mf.OpType.Add)
    walker["torso"] = torso_mod
    report["shoulder_hardpoint"] = {"centre": list(SHOULDER["centre"]), "axis_out": list(SHOULDER["out"]),
                                    "peg": f"r {PEG_R} x {PEG_L} mm D, magnet {2 * MAGNET[0]:g} x {MAGNET[1]:g} mm",
                                    "torso_pieces": pieces(torso_mod), "torso_closed": torso_mod.status().name == "NoError"}
    report["shoulder_hardpoint"]["pass"] = report["shoulder_hardpoint"]["torso_pieces"] == 1 and report["shoulder_hardpoint"]["torso_closed"]

    # ---- the items on the shoulder ------------------------------------------------------------------------------------
    def shoulder_item(name, body_item_frame, collar_h):
        item = body_item_frame + sock.collar(collar_h)
        world = sock.world(item) + sock.add
        info = check_fit(name, world, torso_mod, {k: v for k, v in walker.items() if k != "torso"} | {"torso": torso_mod}, sock)
        # the mirrored copy (the web mirrors the item for the right shoulder) against the real right side
        wr = mirror(world)
        info["right_clashes_mm3"] = {k: round((wr ^ v).volume(), 3) for k, v in walker.items() if (wr ^ v).volume() > 1e-3}
        info["pass"] = bool(info["pass"] and not info["right_clashes_mm3"])
        return item, info

    rack = load_meshy(rack_work)
    R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]]) * RACK_SCALE      # barrels to -y (forward)
    m = affine(rack, R, (0, 0, 0))
    bb = m.bounding_box()
    post = m ^ mf.Manifold.cube((40, 40, 1.2)).translate((-20, -20, bb[2]))     # the post's foot
    pb = post.bounding_box()
    collar_h = 2.0
    m = m.translate((-(pb[0] + pb[3]) / 2, -(pb[1] + pb[4]) / 2, collar_h - bb[2] - 0.15))
    rack_item, report["missile-rack"] = shoulder_item("missile-rack", m, collar_h)

    items = {"missile-rack": (rack_item, sock, rack_work, "shoulder")}

    # ---- carapace gun: the Meshy pod on the same socket ---------------------------------------------------------------
    if pod_work:
        from joints import load as load_npz
        pod = load_npz(Path(pod_work) / "parts" / "pod.npz")
        z0 = SHOULDER["centre"][2]
        pod = pod ^ mf.Manifold.cube((60, 60, 40)).translate((-30, -30, z0))
        pod = affine(pod, np.eye(3), (0, 0, 0))
        item_world_body = pod
        # to the item frame (translation only: the shoulder frame is the world frame)
        body = affine(pod, sock.R.T, -sock.R.T @ sock.c)
        collar = sock.collar(collar_h)
        joined = body + collar
        keep = [p for p in joined.decompose() if p.volume() > 4.0]
        joined = mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]
        item = joined
        world = sock.world(item) + sock.add
        info = check_fit("carapace-gun", world, torso_mod, dict(walker), sock)
        wr = mirror(world)
        info["right_clashes_mm3"] = {k: round((wr ^ v).volume(), 3) for k, v in walker.items() if (wr ^ v).volume() > 1e-3}
        info["pass"] = bool(info["pass"] and not info["right_clashes_mm3"])
        report["carapace-gun"] = info
        items["carapace-gun"] = (item, sock, pod_work, "shoulder")

    # ---- bracer hardpoint on the forearm and the shield ---------------------------------------------------------------
    f = P["forearm"]
    xs = surface_x(f, BRACER["y"], BRACER["z"])
    th = np.radians(BRACER["tilt_deg"])
    bs = Socket((xs + BRACER["proud"], BRACER["y"], BRACER["z"]), (np.cos(th), 0, np.sin(th)))
    assert abs(BRACER_BOSS["stations"][0][0] + BRACER["boss_depth"]) < 1e-6
    boss = bs.world(socket_boss(**BRACER_BOSS))
    boss_full = boss.volume()
    for k in ("arm", "hand", "pauldron", "blade", "torso"):
        boss = boss - walker[k]
    forearm_mod = (f + boss) - bs.hole
    forearm_mod = mf.Manifold.batch_boolean([p for p in forearm_mod.decompose() if p.volume() > 1.0], mf.OpType.Add)
    walker["forearm"] = forearm_mod
    walker["forearm_R"] = mirror(forearm_mod)
    # The native right pauldron's long cape hangs past the right forearm and was cut clear of the plain forearm only
    # (joints.py): it gives way to the mirrored bracer socket too, with the walker's clearance, so the right forearm still
    # plugs in. What it loses is hidden inside the forearm.
    cleared = None
    if (parts_dir / "stl" / "pauldron_r.stl").exists():
        wide = dict(BRACER_BOSS, stations=tuple((z, r + CLEAR) for z, r in BRACER_BOSS["stations"]) + ((CLEAR, 2.9 + CLEAR),))
        pr = walker["pauldron_R"] - mirror(bs.world(socket_boss(**wide)))
        keep = sorted(pr.decompose(), key=lambda p: -p.volume())
        cleared = {"trimmed_mm3": round(walker["pauldron_R"].volume() - pr.volume(), 3),
                   "dropped_mm3": round(sum(p.volume() for p in keep[1:]), 3)}
        walker["pauldron_R"] = keep[0]
    Vs, cs, Rm = shield_frame(shield_work)
    shield = load_meshy(shield_work)
    L = (Vs - cs) @ Rm.T
    u0 = 0.10                                   # where on the shield (up, Meshy units) the collar is
    near = np.linalg.norm(L[:, :2] - np.array([u0, 0.0]), axis=1) < 0.35
    zb = L[near, 2].min()
    m = affine(shield, Rm * SHIELD_SCALE, -(Rm @ cs) * SHIELD_SCALE + np.array([-u0 * SHIELD_SCALE, 0, STANDOFF - zb * SHIELD_SCALE]))
    shield_item = m + bs.collar(STANDOFF + 0.7)
    world = bs.world(shield_item) + bs.add
    info = check_fit("kinetic-shield", world, forearm_mod, {k: v for k, v in walker.items() if k != "forearm_R"}, bs)
    wr = mirror(world)
    info["right_clashes_mm3"] = {k: round((wr ^ v).volume(), 3) for k, v in walker.items() if k not in ("forearm",) and (wr ^ v).volume() > 1e-3}
    info["pass"] = bool(info["pass"] and not info["right_clashes_mm3"])
    # the forearm bent at the elbow: the shield must not hit the arm, the pauldron or the body
    from layout import joint
    j = np.array(joint("elbow"))
    bent = {}
    for deg in (-30.0, -45.0):
        w = world.translate(tuple(-j)).rotate((deg, 0, 0)).translate(tuple(j))
        c = {k: round((w ^ walker[k]).volume(), 3) for k in ("arm", "pauldron", "torso", "pelvis", "thigh") if (w ^ walker[k]).volume() > 1e-3}
        bent[f"{deg:+.0f}"] = c
    info["bent_clashes_mm3"] = bent
    report["kinetic-shield"] = info
    report["bracer_hardpoint"] = {"centre": [round(float(v), 3) for v in bs.c], "axis_out": [round(float(v), 4) for v in bs.out],
                                  "peg": f"r {PEG_R} x {PEG_L} mm D, magnet {2 * MAGNET[0]:g} x {MAGNET[1]:g} mm",
                                  "forearm_pieces": pieces(forearm_mod), "forearm_closed": forearm_mod.status().name == "NoError",
                                  "right_cape_cleared": cleared}
    report["bracer_hardpoint"]["pass"] = bool(pieces(forearm_mod) == 1 and forearm_mod.status().name == "NoError"
                                              and (not cleared or pieces(walker["pauldron_R"]) == 1))
    items["kinetic-shield"] = (shield_item, bs, shield_work, "bracer")

    # ---- write ------------------------------------------------------------------------------------------------------
    for name, (item, s, work, _) in items.items():
        wd = out / "work" / name
        (wd / "kit").mkdir(parents=True, exist_ok=True)
        # build.py reads the item in world print mm with the peg in place (UV props: Meshy's, (-1,-1) caps, (-2,-2) gold)
        solid = s.world(item) + s.add
        save_npz(solid, wd / "kit" / f"{name}.npz")
        for i in range(3):
            tex = Path(work) / f"tex_{i}.jpg"
            (wd / f"tex_{i}.jpg").write_bytes(tex.read_bytes())
    hosts = [("torso_hardpoints", torso_mod), ("forearm_bracer", forearm_mod)]
    if cleared:
        hosts.append(("pauldron_r_clear", walker["pauldron_R"]))     # the right pauldron for a forearm with the bracer socket
    for name, m in hosts:
        (out / "stl" / f"{name}.stl").write_bytes(stl_bytes(plain(m).simplify(0.015)))
    # the host sockets, for the blend: only the part outside the host, with the hole cut
    vis = {"shoulder_L": (boss_l - P["torso"]) - hole_l, "shoulder_R": (boss_r - P["torso"]) - hole_r, "bracer_L": (boss - f) - bs.hole}
    for k, m in vis.items():
        np.savez(out / "hosts" / f"{k}.npz", **host_arrays(m))
    # how much of each socket other parts of the walker took (trimmed away where they sit), and its visible pieces
    trims = {"shoulder_L": boss_cyl.volume() - boss_l.volume(), "shoulder_R": boss_cyl.volume() - boss_r.volume(),
             "bracer_L": boss_full - boss.volume()}
    report["sockets"] = {k: {"tris": int(len(m.to_mesh().tri_verts)), "pieces": pieces(m), "trimmed_mm3": round(trims[k], 2)}
                         for k, m in vis.items()}
    ok = all(v.get("pass", True) for v in report.values() if isinstance(v, dict))
    (out / "fit.json").write_text(json.dumps(report, indent=1))
    for k, v in report.items():
        print(k, json.dumps(v), flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k: a[a.index(k) + 1] if k in a else None
    main(a[0], a[1], opt("--rack"), opt("--shield"), opt("--pod"))
