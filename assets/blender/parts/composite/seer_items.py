"""The Seer's Hellfire Missiles, cut as a closed part that plugs into a designed shoulder hardpoint (numpy + manifold3d, no Blender).

    MODEL=seer ~/bvenv/bin/python -I seer_items.py PARTS OUT --hellfire HELLFIRE_WORK [--length 17]

PARTS          the Seer the launcher plugs into: a work folder (kit/<part>.npz, joints.json; seer_elbow.py's BENT since the
               2026-11-08 polish), or a build's output (stl/<part>.stl, joints.json; models/seer-composite-v2 before). v1 (native
               right arm) works too, but then only the left shoulder is checked.
OUT            gets work/hellfire-missiles/ (kit/<item>.npz in world print mm with its peg, the format build.py bakes, and the
               Meshy textures), hosts/ (the hardpoint sleeve and the right pauldron's clearance cutter, for the blend),
               stl/arm_hardpoints.stl (the arm with its socket), stl/pauldron_r_cleared.stl and fit.json (the checks below).
               From a work folder also kit/arm.npz: the kit arm with the socket fused on, for build.py (copy it over the work
               folder's arm before the build). The script exits 1 if a check fails.
HELLFIRE_WORK  a `cut.py extract` folder of the Meshy Hellfire generation (task 01a1938a-a9f8-7753-968d-3d86a411c7a7, made
               2026-10-31 for the first Meshy weapons pass; the source GLB is in the project folder, meshy-sources/hellfire/).

The method is the Paladin items' (paladin_items.py): the shape is Meshy's, the fit is designed here.

  * The launcher is the Meshy sculpt: two stacked missiles with curved blade tips and serrated fins, on a shared housing.
    It is one closed surface, so it is turned so the blades point forward (-y), scaled to --length print mm, and stood on a
    gunmetal mount collar with two gold bands under the back of its housing. The collar carries the D peg (r 1.3 x 2.2 mm)
    with a 2 x 1 mm magnet.
  * Shoulder hardpoint: a boss in the Seer's own joint style (since the 2026-11-08 polish: a bronze body narrowing
    to a rounded foot, a gilded lip round the seat and a gold band, like seer.py's knuckle housings) sunk into the shoulder
    drum of the `arm` part, with the D hole and a magnet pocket at its bottom. The drum is a
    2.2 mm half ball, too small to hold the hole on its own, so the sleeve carries the wall. The Seer's right arm is the
    mirror of the left (seer-composite-v2), so the same socket is on both shoulders and the one launcher fits either side
    (the D flat faces forward, so the mirrored socket keys it the same way). The socket rides on the arm, so the launcher
    swings with the shoulder; fit.json checks it at rest and swung.
  * The right pauldron is not the mirror of the left: its plate lies over the right shoulder drum. It gets a clearance cut
    for the sleeve and the collar (a few mm3), so the mirrored arm's sleeve comes up through it.
  * The socket position, sleeve depth and launcher offset are searched (shallowest sleeve first): the first spot where the
    launcher clears the halo, helm, pauldrons and back spires on both sides, the sleeve keeps the hole's 0.4 mm wall, and the
    peg fills none of the arm. A torso mount was tried first and fails: the shoulder plate is too thin for the hole's wall,
    and on the right the back spires are in the way.

Item frame (mm, origin at the socket centre on the seat plane): +Z out of the host (up), -Y forward (the blades), X outboard on
the left. The item is modelled for the walker's left; the web and the blend mirror it for the right.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import manifold3d as mf  # noqa: E402
import paladin_items as pi  # noqa: E402  (Socket, collar, check_fit, loaders: shared with the Paladin's items)
from joints import load as load_npz, save as save_npz  # noqa: E402

# The Seer's own joints are 1.0 to 1.3 mm pegs (its limbs are thin); the launcher takes the forearm's girth, r 1.3 mm D with a
# 2 x 1 mm magnet, but 2.2 mm long: the shoulder sleeve is a 2.2 mm radius drum, and a longer hole would break out of its bottom. paladin_items reads these module values when it builds the socket and checks the wall.
pi.PEG_R, pi.PEG_L, pi.MAGNET = 1.3, 2.2, (1.0, 1.0)
pi.COLLAR_R = 1.8                # slimmer than the Paladin's 2.9: on the right shoulder the back spire and the wing spike sit
                                 # 2 mm behind the socket
BOSS_R = 2.2                     # the boss round the hole: hole r 1.4 + 0.4 mm wall + 0.4 spare
BOSS_DEPTHS = (3.2, 4.0, 4.8, 5.6)   # mm below the seat; the shallowest that keeps the hole's wall wins (the shoulder drum is a
                                     # 2.2 mm radius half ball: nothing shallower than 3.2 holds a 0.4 mm wall round the hole)
OFFSETS = (0.0, 0.75)            # mm the launcher may sit outboard of its collar, to clear the halo while the hole stays in metal
HOST = "arm"                     # the part that carries the hardpoint ("torso" works with the same code but fails, see above)
SEARCH_X = {"torso": (3.5, 7.6), "arm": (8.5, 10.0)}
SEARCH_Y = {"torso": (2.0, 9.6), "arm": (3.0, 6.6)}
CANDIDATES = 32
PROUD = 0.5                      # the seat stands this far above the highest metal of the orb under the boss
COLLAR_H = 1.1                   # seat to the underside of the launcher
EMBED = 0.35                     # the collar runs this far up into the launcher, so the two fuse
MOUNT_AT = 0.9                   # where the collar sits along the launcher, 0 = blade tips, 1 = rear of the housing: under the
                                 # back of the housing, so the launcher reaches forward and clears the back spires
SWING = (-15.0, 15.0)            # degrees about the shoulder axis, for the swung check

ITEM = "hellfire-missiles"
SIDED = ("thigh", "shin", "foot")     # mirrored for the right in every version of the Seer
RAW = ("spear",)                      # kit pieces that are not on the walker (seer_wrist.py cuts the spear into a wrist weapon)


def load_walker(parts):
    if (parts / "kit").is_dir():     # a work folder (split.py, joints.py, seer_elbow.py): the kit at print tolerance
        P = {f.stem: pi.plain(load_npz(f)).simplify(0.015) for f in sorted((parts / "kit").glob("*.npz"))
             if f.stem not in RAW}
    else:                            # a build's print copies
        P = {f.stem: pi.load_stl(f) for f in sorted((parts / "stl").glob("*.stl"))}
    walker = dict(P)
    for k in SIDED:
        walker[k + "_R"] = pi.mirror(P[k])
    native_right = "arm_r" in P            # seer-composite (v1) has a native right arm; v2 mirrors the left one
    if not native_right:
        for k in ("arm", "forearm", "hand"):
            if k in P:
                walker[k + "_R"] = pi.mirror(P[k])
    if "pauldron" in P and "pauldron_r" not in P:     # since 2026-11-02 the right pauldron is the left one mirrored too
        walker["pauldron_R"] = pi.mirror(P["pauldron"])
    return P, walker, native_right


def launcher(work, length):
    """The Meshy launcher in the item frame: blades to -y, housing at +y, the collar's axis on z, launcher underside at COLLAR_H."""
    m = pi.load_meshy(work)
    bb = m.bounding_box()
    s = length / (bb[3] - bb[0])
    # Meshy: long axis x with the blades at -x, the two missiles stacked in z. Item: x -> y (blades to -y), y -> -x.
    m = pi.affine(m, np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]]) * s, (0, 0, 0))
    bb = m.bounding_box()
    yc = bb[1] + MOUNT_AT * (bb[4] - bb[1])
    # the underside at the collar: the lowest metal within the collar's footprint
    foot = m ^ mf.Manifold.cylinder(bb[5] - bb[2] + 2, pi.COLLAR_R, pi.COLLAR_R, 48).translate((0, yc, bb[2] - 1))
    zb = foot.bounding_box()[2]
    return m.translate((0, -yc, COLLAR_H - zb)), s


FRAME = (-3.0, -3.0)            # build.py: the knuckle housings' bronze (seer.py FRAME_UV, FRAME_FINISH)
TAPER = 0.95                     # the boss narrows to this x BOSS_R at its foot, like the knuckle housings
LIP = (0.4, 0.1, 0.15)           # the gilded lip: height, overhang past the body, chamfer in from BOSS_R at the seat


def sleeve(depth):
    """The hardpoint boss in the Seer's own joint language (seer.py's knuckle housings), item frame (seat at z = 0): a bronze
    body (frame UV) narrowing a little down to a rounded foot, a chamfered gold lip round the seat (the launcher's collar
    stands inside it) and a gold band above the foot. Until the 2026-11-08 polish it was a straight bright-gold can that the
    game drew as a separate flat-gold mesh; empty, it read as a flower pot on each shoulder."""
    gold = pi.PAINT_GOLD
    r = BOSS_R
    if depth <= r:
        return pi.cyl(r, -depth, 0.0, FRAME)
    rd = r * TAPER
    zc = -depth + rd                                   # the foot's centre
    zt = -LIP[0] + 0.02                                # the body runs a little into the lip, so the two fuse
    rad = lambda z: rd + (r - rd) * (z - zc) / (zt - zc)
    parts = [pi.mark(mf.Manifold.cylinder(zt - zc, rd, r, 64).translate((0, 0, zc)), FRAME),
             pi.mark((mf.Manifold.sphere(rd, 64) ^ mf.Manifold.cube((3 * rd, 3 * rd, rd + 0.02), True).translate(
                 (0, 0, -rd / 2 + 0.01))).translate((0, 0, zc)), FRAME),        # the lower half: a shallow boss stays below its seat
             pi.mark(mf.Manifold.cylinder(LIP[0], r + LIP[1], r - LIP[2], 64).translate((0, 0, -LIP[0])), gold)]
    if depth > r + 1.2:
        z0, z1 = zc + 0.15, zc + 0.5
        parts.append(pi.mark(mf.Manifold.cylinder(z1 - z0, rad(z0) + 0.12, rad(z1) + 0.12, 64).translate((0, 0, z0)), gold))
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add)


def with_uv(m, uv):
    """The solid with every vertex's two UV properties set to `uv` (a paint tag; numpy, fast on whole parts)."""
    mm = m.to_mesh()
    vp = np.asarray(mm.vert_properties)[:, :3]
    vp = np.column_stack([vp, np.tile(np.asarray(uv, np.float32), (len(vp), 1))]).astype(np.float32)
    return mf.Manifold(mf.Mesh(vert_properties=vp, tri_verts=np.asarray(mm.tri_verts, np.uint32),
                               merge_from_vert=np.asarray(mm.merge_from_vert, np.uint32),
                               merge_to_vert=np.asarray(mm.merge_to_vert, np.uint32)))


def top_of(host, x, y, r):
    """The highest z of a part within a disc of radius r about (x, y), or None."""
    col = mf.Manifold.cylinder(80, r, r, 32).translate((x, y, 0))
    hit = host ^ col
    if hit.is_empty():
        return None
    return hit.bounding_box()[5]


TRIM = ("torso", "arm", "pauldron", "crown", "helm", "back", "arm_r", "pauldron_r", "arm_R")


def place(item_frame, P, walker, host, x, y, depth, offset, right=False):
    """Socket, boss and fitted item for a socket centre at (x, y) on top of `host`, a boss `depth` mm deep below the seat and the
    launcher `offset` mm outboard (+x) of its collar. With `right`, the torso also gets the mirrored socket and the mirrored
    launcher is checked against the walker's own right side. Returns (info, parts) or None."""
    base = P[host]
    top = top_of(base, x, y, BOSS_R)
    if top is None:
        return None
    sock = pi.Socket((x, y, top + PROUD), (0.0, 0.0, 1.0))
    trim = [walker[k] for k in TRIM if k in walker and k != host]
    if right and host != "torso":       # one arm serves both shoulders: its sleeve also keeps clear of the right side's own
        trim += [pi.mirror(walker[k]) for k in ("back", "torso", "crown", "helm") if k in walker]   # parts (not the right
        # pauldron: it lies over the right shoulder drum, so it gets a clearance cut for the sleeve and collar instead, below)
    boss = sock.world(sleeve(depth))
    for o in trim:
        boss = boss - o
    host_mod = (base + boss) - sock.hole
    boss_r = None
    if right and host == "torso":
        boss_r = pi.mirror(sock.world(sleeve(depth)))
        for o in trim:
            boss_r = boss_r - o
        host_mod = (host_mod + boss_r) - pi.mirror(sock.hole)
    host_mod = mf.Manifold.batch_boolean([p for p in host_mod.decompose() if p.volume() > 1.0], mf.OpType.Add)
    body = item_frame.translate((offset, 0, 0)) + sock.collar(COLLAR_H + EMBED)
    keep = [p for p in body.decompose() if p.volume() > 0.5]
    body = mf.Manifold.batch_boolean(keep, mf.OpType.Add) if len(keep) > 1 else keep[0]
    world = sock.world(body) + sock.add
    others = {k: v for k, v in walker.items() if k != host} | {host: host_mod}
    info = pi.check_fit(ITEM, world, host_mod, others, sock)
    pr_mod = cutter = None
    if right and host != "torso":      # the mirrored arm carries the mirrored socket: check the launcher on the real right side
        if "pauldron_r" in others:     # the right pauldron plate covers the drum: cut it clear of the sleeve and the collar
            clear = boss + sock.world(pi.cyl(pi.COLLAR_R + 0.3, -0.05, COLLAR_H + EMBED + 0.3))
            cutter = pi.mirror(clear)
            pr_mod = others["pauldron_r"] - cutter
            pr_mod = mf.Manifold.batch_boolean([p for p in pr_mod.decompose() if p.volume() > 0.5], mf.OpType.Add)
            others = others | {"pauldron_r": pr_mod}
            info["pauldron_r_cut_mm3"] = round(walker["pauldron_r"].volume() - pr_mod.volume(), 2)
            info["pauldron_r_pieces"] = pi.pieces(pr_mod)
        wr = pi.mirror(world)
        info["right_clashes_mm3"] = {k: round((wr ^ v).volume(), 3) for k, v in others.items()
                                     if k not in ("arm_R", host) and (wr ^ v).volume() > 1e-3}
        rb = pi.mirror(boss)               # the mirrored arm's sleeve against the right side's own parts
        for k, v in others.items():
            if k not in ("arm_R", host) and (rb ^ v).volume() > 1e-3:
                info["right_clashes_mm3"][f"{k} (sleeve)"] = round((rb ^ v).volume(), 3)
        info["pass"] = bool(info["pass"] and not info["right_clashes_mm3"])
    elif right:
        wr = pi.mirror(world)
        info["right_clashes_mm3"] = {k: round((wr ^ v).volume(), 3) for k, v in others.items() if (wr ^ v).volume() > 1e-3}
        rs = pi.Socket(tuple(np.array(sock.c) * [-1, 1, 1]), (0.0, 0.0, 1.0))
        ring_depth = pi.PEG_L + 0.15 + pi.MAGNET[1] + 0.1
        ring = mf.Manifold.cylinder(ring_depth, pi.PEG_R + 0.1 + pi.WALL, pi.PEG_R + 0.1 + pi.WALL, 48).translate((0, 0, -ring_depth))
        info["right_wall_missing_mm3"] = round((rs.world(ring) - host_mod - pi.mirror(sock.hole)).volume(), 3)
        info["pass"] = bool(info["pass"] and not info["right_clashes_mm3"] and info["right_wall_missing_mm3"] < 0.02)
    return info, dict(sock=sock, boss=boss, boss_r=boss_r, host_mod=host_mod, body=body, world=world, pauldron_r=pr_mod,
                            cutter=cutter, trim=trim, depth=depth)


def swung(world, walker, P, centre, axis=(1.0, 0.0, 0.0)):
    """The launcher (riding on the arm) swung about the shoulder: clashes with the parts that do not move with the arm."""
    out = {}
    for deg in SWING:
        w = world.translate(tuple(-np.asarray(centre))).rotate(tuple(np.asarray(axis) * deg)).translate(tuple(centre))
        c = {k: round((w ^ walker[k]).volume(), 3) for k in ("torso", "pauldron", "crown", "helm", "back")
             if k in walker and (w ^ walker[k]).volume() > 1e-3}
        out[f"{deg:+.0f}"] = c
    return out


def main(parts, out, work, length):
    parts, out = Path(parts), Path(out)
    for d in ("stl", "hosts"):
        (out / d).mkdir(parents=True, exist_ok=True)
    P, walker, native_right = load_walker(parts)
    item_frame, scale = launcher(work, length)
    shoulder = json.loads((parts / "joints.json").read_text())["arm"] if (parts / "joints.json").exists() else None
    centre = np.array(shoulder["centre"]) if shoulder else np.array([7.527, 4.979, 48.946])

    # search: the shallowest boss, then the smallest outboard offset, then the spot nearest the crown of the host. The search runs
    # on a simplified launcher (seconds per try); the winner is re-checked with the full-detail one.
    host = HOST
    right = host == "torso" or not native_right      # the torso carries both sockets; a mirrored arm carries its own
    xs = np.arange(*SEARCH_X[host], 0.5)
    ys = np.arange(*SEARCH_Y[host], 0.5)
    cands = []
    for x in xs:
        for y in ys:
            t = top_of(P[host], x, y, 0.6)
            if t is not None:
                cands.append((-t, float(x), float(y)))
    cands.sort()
    cands = cands[:CANDIDATES]
    rough = item_frame.simplify(0.02)
    tried, found = [], None
    for depth in BOSS_DEPTHS:
        for off in OFFSETS:
            for _, x, y in cands:
                r = place(rough, P, walker, host, x, y, depth, off, right)
                if r is None:
                    continue
                info, got = r
                tried.append({"xy": [round(x, 2), round(y, 2)], "depth": depth, "offset": off, "pass": info["pass"],
                              "clashes": info["clashes_mm3"], "right_clashes": info.get("right_clashes_mm3"),
                              "wall_missing_mm3": info["wall_missing_mm3"], "right_wall": info.get("right_wall_missing_mm3")})
                if info["pass"]:
                    full = place(item_frame, P, walker, host, x, y, depth, off, right)
                    if full and full[0]["pass"]:
                        found = (x, y, full[0], full[1])
                        break
            if found:
                break
        if found:
            break
    report = {"item": ITEM, "length_mm": length, "meshy_to_mm": round(scale, 3),
              "peg": f"r {pi.PEG_R} x {pi.PEG_L} mm D, magnet {2 * pi.MAGNET[0]:g} x {pi.MAGNET[1]:g} mm",
              "parts": str(parts), "right_arm": "native (v1: right side not checked)" if native_right else "mirror of the left"}
    if not found:
        report["tried"] = tried
        (out / "fit.json").write_text(json.dumps(report, indent=1))
        print(json.dumps(report, indent=1))
        sys.exit(1)
    x, y, info, got = found
    info["boss_depth_mm"], info["launcher_offset_mm"] = depth, off
    sock, world = got["sock"], got["world"]
    if host == "arm":
        info["swung_clashes_mm3"] = swung(world, walker, P, centre)
    report["shoulder_hardpoint"] = {"host": host, "centre": [round(float(v), 3) for v in sock.c], "axis_out": [0.0, 0.0, 1.0],
                                    "both_sides": bool(right), "boss_r": BOSS_R,
                                    "host_pieces": pi.pieces(got["host_mod"]), "host_closed": got["host_mod"].status().name == "NoError"}
    report[ITEM] = info
    report["candidates_tried"] = len(tried)

    # ---- write ----------------------------------------------------------------------------------------------------
    wd = out / "work" / ITEM
    (wd / "kit").mkdir(parents=True, exist_ok=True)
    save_npz(world, wd / "kit" / f"{ITEM}.npz")       # world print mm with the peg in place (build.py's input)
    for i in range(3):
        (wd / f"tex_{i}.jpg").write_bytes((Path(work) / f"tex_{i}.jpg").read_bytes())
    (out / "stl" / f"{host}_hardpoints.stl").write_bytes(pi.stl_bytes(pi.plain(got["host_mod"]).simplify(0.015)))
    if got["pauldron_r"] is not None:
        (out / "stl" / "pauldron_r_cleared.stl").write_bytes(pi.stl_bytes(pi.plain(got["pauldron_r"]).simplify(0.015)))
        mm = pi.plain(got["cutter"]).to_mesh()       # the blend cuts the baked right pauldron with this (keeps its UVs)
        np.savez(out / "hosts" / "pauldron_r_cut.npz", P=np.asarray(mm.vert_properties)[:, :3], T=np.asarray(mm.tri_verts))
    if (parts / "kit").is_dir():
        # the host with its socket for build.py: the boss (tagged frame metal and gold, its trimmed faces frame metal) fused
        # onto the kit part (Meshy UVs), the hole cut (tagged as a cut face). The game and the blend then carry the socket in
        # the arm's own baked textures instead of as a separate flat-gold mesh.
        boss = sock.world(sleeve(got["depth"]))
        for o in got["trim"]:
            boss = boss - with_uv(o, FRAME)
        kit = (load_npz(parts / "kit" / f"{host}.npz") + boss) - sock.hole
        kit = mf.Manifold.batch_boolean([p for p in kit.decompose() if p.volume() > 1.0], mf.OpType.Add)
        (out / "kit").mkdir(exist_ok=True)
        save_npz(kit, out / "kit" / f"{host}.npz")
        report["shoulder_hardpoint"]["kit"] = {"part": f"kit/{host}.npz", "pieces": pi.pieces(kit),
                                               "closed": kit.status().name == "NoError", "volume_mm3": round(kit.volume(), 1)}
    # the hardpoints for the blend: only the part outside the host, with the hole cut
    vis = {"shoulder_L": (got["boss"] - P[host]) - sock.hole}
    if got["boss_r"] is not None:
        vis["shoulder_R"] = (got["boss_r"] - P[host]) - pi.mirror(sock.hole)
    for k, m in vis.items():
        mm = pi.plain(m).to_mesh()
        np.savez(out / "hosts" / f"{k}.npz", P=np.asarray(mm.vert_properties)[:, :3], T=np.asarray(mm.tri_verts))
    (out / "fit.json").write_text(json.dumps(report, indent=1))
    for k, v in report.items():
        print(k, json.dumps(v), flush=True)
    sys.exit(0 if info["pass"] else 1)


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    main(a[0], a[1], opt("--hellfire"), float(opt("--length", "17")))
