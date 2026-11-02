"""The Brute's two designed arm items, as closed parts on the elbow socket (numpy + manifold3d, no Blender).

    MODEL=brute ~/bvenv/bin/python -I brute_items.py PARTS OUT

PARTS is the folder the Brute composite build wrote (models/brute-composite: stl/<part>.stl and report.json); OUT gets
solids/<item>.npz (manifold meshes with a colour id per triangle), stl/<item>.stl (the print copy), fit.json (the
checks below) and nothing else. `brute_items_build.py` turns the solids into the game GLBs, the .blend and the renders.

Industrial Claw (`item_industrial-claw@brute`) and Rail Cannon (`item_rail-cannon@brute`) are not cut from the Meshy
figure: the Meshy Brute has no claw and no rail gun, so they are modelled here, in print mm, to the same pattern as the
cannon arm and the gatling arm. Each is a whole forearm with its origin on the elbow, and each plugs into the pauldron's
elbow socket with the exact peg `rockets` has (same centre, axis, D-section, flat and magnet pocket, read from the build's
report.json), so a claw, a rail cannon, a cannon or a gatling fit either elbow. Items are modelled for the walker's left;
the web mirrors them for the right.

Item frame (mm, origin at the socket centre): +X along the barrel, forward and down; +Y outward; +Z up from the barrel.
The socket axis points up, back and in (the pauldron is up and behind), and the boss runs down from it into the body.

Checks written to fit.json (all must hold, and the script exits 1 if one does not):
  * one closed piece, positive volume, no solid inside the pauldron's hole except the peg;
  * the part touches no other part of the walker (the rest pose and the arm swung 15 degrees either way);
  * the peg is the cannon arm's peg: it fills the same volume, to 0.01 mm3.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifold3d as mf  # noqa: E402
from joints import frame, peg_shapes, place  # noqa: E402   (importing layout reads MODEL: run with MODEL=brute)

# Colour ids -> (name, base colour sRGB, roughness, metallic). The Brute's livery is red; the web tints red texels with
# the walker's own hull colour. Everything else keeps its colour.
PAINT = {
    "livery": ((0.50, 0.10, 0.055), 0.6, 0.3),
    "iron": ((0.06, 0.06, 0.065), 0.42, 1.0),
    "steel": ((0.34, 0.35, 0.37), 0.32, 1.0),
    "brass": ((0.62, 0.42, 0.16), 0.30, 1.0),
}
NAMES = list(PAINT)

ELBOW = np.array([14.994, -1.951, 53.626])      # the cannon arm's socket (report.json joints.rockets), print mm
SOCKET_AXIS = np.array([-0.4996, -0.3185, 0.8056])
SOCKET_AXIS /= np.linalg.norm(SOCKET_AXIS)
PEG_R, PEG_L, MAGNET = 1.5, 3.5, (1.0, 1.0)     # radius, length, (magnet radius, thickness): 2 x 1 mm disc
BARREL = np.array([0.25031859, -0.70882445, -0.65947593])   # the cannon arm's muzzle direction (principal axis, to the muzzle)
BARREL /= np.linalg.norm(BARREL)
SWING = (-15.0, 0.0, 15.0)                       # degrees about the elbow's x axis for the clearance check


def item_frame():
    """Rotation whose columns are the item frame's X (barrel), Y (outward), Z (up), in the world."""
    s = np.array([1.0, 0, 0])
    s = s - (s @ BARREL) * BARREL
    s /= np.linalg.norm(s)
    return np.stack([BARREL, s, np.cross(BARREL, s)], 1)


RW = item_frame()


# ---- tagged solids ------------------------------------------------------------------------------------------------

ID_PAINT = {}


def tag(m, paint):
    m = m.as_original()
    ID_PAINT[m.original_id()] = NAMES.index(paint)
    return m


def box(x0, x1, y0, y1, z0, z1, paint, ch=0.0):
    """A box with 45 degree chamfered edges (hull of an inset cross)."""
    if ch <= 0:
        return tag(mf.Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0)), paint)
    pts = []
    for dx in (x0, x1):
        for dy in (y0, y1):
            for dz in (z0, z1):
                sx, sy, sz = (1 if dx == x0 else -1), (1 if dy == y0 else -1), (1 if dz == z0 else -1)
                pts += [(dx + sx * ch, dy, dz), (dx, dy + sy * ch, dz), (dx, dy, dz + sz * ch),
                        (dx + sx * ch, dy + sy * ch, dz), (dx + sx * ch, dy, dz + sz * ch), (dx, dy + sy * ch, dz + sz * ch)]
    return tag(mf.Manifold.hull_points(np.array(pts)), paint)


def cyl_x(x0, x1, y, z, r, paint, r1=None, n=40):
    """A cylinder along X from x0 to x1 (radius r at x0, r1 at x1)."""
    c = mf.Manifold.cylinder(x1 - x0, r, r if r1 is None else r1, n)
    return tag(c.rotate((0, 90, 0)).translate((x0, y, z)), paint)


def cyl_y(y0, y1, x, z, r, paint, n=40):
    c = mf.Manifold.cylinder(y1 - y0, r, r, n)
    return tag(c.rotate((-90, 0, 0)).translate((x, y0, z)), paint)


def tine(path, y0, y1, paint):
    """A claw finger: hulls between boxes centred on path points (x, z, thickness), y0..y1 wide, tapering along the path."""
    segs = []
    for (xa, za, ta), (xb, zb, tb) in zip(path[:-1], path[1:]):
        pts = []
        for x, z, t in ((xa, za, ta), (xb, zb, tb)):
            for y in (y0, y1):
                for dx, dz in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                    pts.append((x + dx * t * 0.5, y, z + dz * t * 0.5))
        segs.append(mf.Manifold.hull_points(np.array(pts)))
    return tag(mf.Manifold.batch_boolean(segs, mf.OpType.Add), paint)


def rot_path(path, pivot, deg):
    """Turn a tine's path about the pivot (in the XZ plane); positive lifts the tip."""
    a = np.radians(deg)
    out = []
    for x, z, t in path:
        dx, dz = x - pivot[0], z - pivot[1]
        out.append((pivot[0] + dx * np.cos(a) - dz * np.sin(a), pivot[1] + dx * np.sin(a) + dz * np.cos(a), t))
    return out


def rivets_y(xs, z, y, out, paint="steel", r=0.42, h=0.35):
    """A row of round rivet heads on a face whose normal is +Y (out=+1) or -Y (out=-1): bumps 0.35 mm high."""
    heads = []
    for x in xs:
        c = mf.Manifold.cylinder(h + 0.2, r, r * 0.8, 16).rotate((-90 if out > 0 else 90, 0, 0)).translate((x, y - 0.2 * out, z))
        heads.append(tag(c, paint))
    return heads


def slots_y(xs, z0, z1, y, out, w=1.0, depth=0.9):
    """Vent slots cut into a face whose normal is +Y (out=+1) or -Y: dark pockets."""
    return [box(x - w / 2, x + w / 2, min(y, y - depth * out), max(y, y - depth * out), z0, z1, "iron") for x in xs]


def union(parts):
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


# ---- the two items (item frame, mm) --------------------------------------------------------------------------------

def claw():
    """Industrial Claw: a hydraulic wrist block on the socket and a two-jaw pincer, jaws open about 30 degrees."""
    pivot = (13.2, -5.4)
    body = [
        box(0.2, 11.0, -1.6, 6.6, -9.6, -1.0, "livery", ch=1.3),            # armoured wrist block
        box(0.9, 2.4, -1.9, 6.9, -9.0, -1.4, "iron", ch=0.5),               # rear guard plate
        box(8.6, 10.2, -1.9, 6.9, -9.2, -1.0, "iron", ch=0.4),              # front collar
        cyl_x(3.2, 9.2, 2.5, -0.4, 1.35, "steel"),                          # hydraulic ram on top
        cyl_x(2.6, 5.4, 2.5, -0.4, 1.75, "brass"),                          # its cylinder housing
        box(5.4, 8.4, 0.6, 4.4, -1.2, 0.2, "iron", ch=0.3),                 # ram clevis
        cyl_y(-1.9, 6.9, pivot[0], pivot[1], 2.1, "brass"),                 # pivot barrel through both jaws
    ]
    # lower jaw: one broad hook, fixed to the block, tip curling up
    low = [(*pivot, 3.8), (18.6, -8.2, 3.3), (23.6, -8.9, 2.8), (27.2, -7.0, 2.3), (28.9, -4.4, 1.8)]
    # upper jaw: two tines on the pivot, turned open
    up = rot_path([(*pivot, 3.6), (18.8, -2.6, 3.0), (23.8, -2.4, 2.6), (27.4, -4.4, 2.2), (28.2, -7.0, 1.8)], pivot, 30)
    jaws = [
        tine(low, 0.5, 4.5, "steel"),
        tine(up, -1.4, 0.7, "steel"),
        tine(up, 4.3, 6.4, "steel"),
        box(9.4, 14.0, 0.2, 4.8, -10.2, -7.6, "livery", ch=0.7),            # knuckle plate over the lower jaw root
        box(10.6, 15.2, -1.6, 0.9, -8.4, -2.6, "livery", ch=0.7),           # upper jaw root plates
        box(10.6, 15.2, 4.1, 6.6, -8.4, -2.6, "livery", ch=0.7),
    ]
    rv = rivets_y([2.2, 5.0, 7.8, 10.2], -2.6, 6.6, 1) + rivets_y([2.2, 5.0, 7.8, 10.2], -8.0, 6.6, 1)
    rv += rivets_y([2.2, 5.0, 7.8, 10.2], -2.6, -1.6, -1) + rivets_y([2.2, 5.0, 7.8, 10.2], -8.0, -1.6, -1)
    claw_solid = union(body + jaws) - union(slots_y([3.6, 5.2, 6.8], -7.0, -3.6, 6.6, 1, w=0.9))
    return union([claw_solid] + rv)


def rail():
    """Rail Cannon: a breech block with capacitor drums, twin rails on coil clamps, a muzzle brace."""
    parts = [
        box(0.2, 10.2, -1.6, 7.0, -8.8, -1.0, "livery", ch=1.3),            # breech block
        box(0.6, 2.0, -2.0, 7.4, -8.4, -1.5, "iron", ch=0.4),               # rear plate
        cyl_x(1.6, 9.4, 7.5, -4.6, 1.9, "iron"),                            # capacitor drum, outboard
        cyl_x(8.4, 10.0, 7.5, -4.6, 2.2, "brass"),                          # its brass cap
        box(4.6, 6.0, 0.4, 5.6, -1.1, 0.5, "iron", ch=0.3),                 # heat fins on the roof
        box(7.0, 8.4, 0.4, 5.6, -1.1, 0.5, "iron", ch=0.3),
        cyl_x(9.0, 22.0, 3.2, -7.0, 1.15, "brass"),                         # power conduit under the rails
    ]
    for y in (1.2, 4.9):                                                    # the rails
        parts.append(box(8.6, 33.0, y - 1.0, y + 1.0, -4.9, -2.5, "steel", ch=0.3))
    for x0 in (12.4, 18.4, 24.4):                                           # coil clamps around both rails
        parts.append(box(x0, x0 + 2.6, -0.6, 7.0, -6.4, -1.0, "livery", ch=0.5))
        parts.append(box(x0 + 0.5, x0 + 2.1, -0.9, 7.3, -5.8, -1.6, "iron", ch=0.3))
    parts.append(box(29.4, 33.4, -0.8, 7.2, -6.2, -1.2, "iron", ch=0.6))    # muzzle brace
    # the conduit meets the clamps through short brass links
    for x0 in (12.4, 18.4):
        parts.append(box(x0 + 0.5, x0 + 2.1, 2.2, 4.2, -7.6, -5.4, "brass", ch=0.2))
    for x0 in (12.4, 18.4, 24.4):
        parts += rivets_y([x0 + 0.7, x0 + 1.9], -2.0, 7.0, 1) + rivets_y([x0 + 0.7, x0 + 1.9], -2.0, -0.6, -1)
    parts += rivets_y([1.8, 4.2, 6.6, 8.8], -2.4, 7.0, 1) + rivets_y([1.8, 4.2, 6.6, 8.8], -7.4, 7.0, 1)
    rail_solid = union(parts) - union(slots_y([3.2, 4.8, 6.4], -6.6, -3.4, 7.0, 1, w=0.9) + slots_y([3.2, 4.8, 6.4], -6.6, -3.4, -1.6, -1, w=0.9))
    return rail_solid


ITEMS = {"claw": (claw, "industrial-claw"), "rail": (rail, "rail-cannon")}


# ---- placing on the socket, checks ---------------------------------------------------------------------------------

def socket():
    """The elbow peg and the collar that carries it, in world print mm: the cannon arm's own peg."""
    R = frame(SOCKET_AXIS, np.array([0.0, -1.0, 0.0]))
    add, sub = peg_shapes(PEG_R, PEG_L, MAGNET, SOCKET_AXIS, ELBOW)
    R2 = frame(SOCKET_AXIS, np.array([0.0, 0.0, 1.0]))
    collar = place(mf.Manifold.cylinder(3.4, PEG_R + 1.2, -1.0, 48).translate((0, 0, -3.4)), R2, ELBOW)
    return add, sub, collar


def to_world(m, deg=0.0, about=None):
    M = np.concatenate([RW, ELBOW[:, None]], 1)
    w = m.transform(M.tolist())
    if deg:
        a = np.radians(deg)
        c, s = np.cos(a), np.sin(a)
        Rx = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        o = np.asarray(about if about is not None else ELBOW)
        w = w.transform(np.concatenate([Rx, (o - Rx @ o)[:, None]], 1).tolist())
    return w


def load_stl(path):
    import trimesh
    t = trimesh.load(path)
    t.merge_vertices()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def stl_bytes(m):
    mm = m.to_mesh()
    P, T = np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts)
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    n = np.cross(B - A, C - A)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    rec = np.zeros(len(T), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, np.stack([A, B, C], 1)
    return b"\0" * 80 + np.uint32(len(T)).tobytes() + rec.tobytes()


def paint_ids(m):
    """The paint index of every triangle of a solid (cut faces and anything untagged read as iron)."""
    mm = m.to_mesh()
    ri = np.asarray(mm.run_index)
    ids = np.full(len(mm.tri_verts), NAMES.index("iron"), np.int16)
    for i, oid in enumerate(mm.run_original_id):
        ids[ri[i] // 3: ri[i + 1] // 3] = ID_PAINT.get(int(oid), NAMES.index("iron"))
    return mm, ids


def main(parts_dir, out):
    parts_dir, out = Path(parts_dir), Path(out)
    (out / "solids").mkdir(parents=True, exist_ok=True)
    (out / "stl").mkdir(exist_ok=True)
    report = json.loads((parts_dir / "report.json").read_text())["joints"]["rockets"]
    assert np.allclose(report["centre"], ELBOW, atol=1e-3) and np.allclose(report["axis"], np.round(SOCKET_AXIS, 4), atol=2e-4), \
        "the Brute's elbow socket has moved: update ELBOW and SOCKET_AXIS from report.json"
    assert (report["peg_radius"], report["peg_length"], report["magnet"]) == (PEG_R, PEG_L, "2 x 1 mm"), report
    others = {k: load_stl(parts_dir / "stl" / f"{k}.stl") for k in ("pelvis", "torso", "helm", "back", "pauldron", "thigh", "shin", "foot")}
    cannon = load_stl(parts_dir / "stl" / "rockets.stl")
    host = others["pauldron"]
    add, _, collar = socket()
    fit = {"socket": {"centre": ELBOW.tolist(), "axis": SOCKET_AXIS.round(4).tolist(),
                      "peg": f"r {PEG_R} x {PEG_L} mm D-section, magnet 2 x 1 mm"}}
    ok = True
    for key, (build, item_id) in ITEMS.items():
        body = build()
        world = (to_world(body) + collar) + add
        info = {"item": item_id, "closed": world.status().name == "NoError", "pieces": len(world.decompose()),
                "volume_mm3": round(world.volume(), 1), "tris": world.num_tri()}
        bb = world.bounding_box()
        info["size_mm"] = [round(bb[3 + i] - bb[i], 1) for i in range(3)]
        # the body (and collar) may touch nothing of the walker, at rest or with the arm swung either way; the collar
        # sits on the pauldron's face and the peg goes into the hole, so only they are allowed near the pauldron
        clashes = {}
        for deg in SWING:
            for name, o in others.items():
                v = (to_world(body, deg) ^ o).volume()
                if v > 1e-3:
                    clashes[f"{name}@{deg:+.0f}"] = round(v, 3)
        info["clashes_mm3"] = clashes
        info["collar_in_pauldron_mm3"] = round((collar ^ host).volume(), 3)
        info["peg_in_pauldron_solid_mm3"] = round((add ^ host).volume(), 4)
        info["peg_vs_cannon_arm_mm3"] = round(abs((add ^ cannon).volume() - add.volume()), 4)
        info["pass"] = bool(info["closed"] and info["pieces"] == 1 and not clashes and info["collar_in_pauldron_mm3"] < 0.01
                            and info["peg_in_pauldron_solid_mm3"] < 0.01 and info["peg_vs_cannon_arm_mm3"] < 0.05)
        ok &= info["pass"]
        fit[key] = info
        mm, ids = paint_ids(world)
        np.savez(out / "solids" / f"{key}.npz", P=np.asarray(mm.vert_properties)[:, :3], T=np.asarray(mm.tri_verts), paint=ids)
        (out / "stl" / f"{key}.stl").write_bytes(stl_bytes(world))
        print(key, json.dumps(info), flush=True)
    (out / "fit.json").write_text(json.dumps(fit, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
