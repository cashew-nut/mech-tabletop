"""The Brute's elbow socket, as the cannon arm cuts it (numpy + manifold3d, no Blender; run with MODEL=brute).

item_cut.py puts every Brute arm item (the Meshy-sculpted claw and rail cannon) on this socket: the same centre, axis,
D-section peg, flat and magnet pocket as `rockets` has, read from the Brute build's report.json (joints.rockets), plus the
collar the gatling carries. Items are modelled for the walker's left; the web mirrors them for the right.
"""
import numpy as np

import manifold3d as mf
from joints import frame, peg_shapes, place   # importing layout reads MODEL: run with MODEL=brute

ELBOW = np.array([14.994, -1.951, 53.626])      # print mm
SOCKET_AXIS = np.array([-0.4996, -0.3185, 0.8056])   # from the peg into the pauldron
SOCKET_AXIS /= np.linalg.norm(SOCKET_AXIS)
PEG_R, PEG_L, MAGNET = 1.5, 3.5, (1.0, 1.0)     # radius, length, (magnet radius, thickness): a 2 x 1 mm disc
BARREL = np.array([0.25031859, -0.70882445, -0.65947593])   # the cannon arm's muzzle direction (principal axis)
BARREL /= np.linalg.norm(BARREL)
SWING = (-15.0, 0.0, 15.0)                      # degrees about the elbow's x axis for the clearance check


def socket():
    """The peg (magnet pocket cut in its tip), the matching hole, and the collar that carries the peg, in world print mm."""
    add, sub = peg_shapes(PEG_R, PEG_L, MAGNET, SOCKET_AXIS, ELBOW)
    R2 = frame(SOCKET_AXIS, np.array([0.0, 0.0, 1.0]))
    collar = place(mf.Manifold.cylinder(3.4, PEG_R + 1.2, -1.0, 48).translate((0, 0, -3.4)), R2, ELBOW)
    return add, sub, collar


def load_stl(path):
    import trimesh
    t = trimesh.load(path)
    t.merge_vertices()
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def check_socket(report):
    """Fail if the Brute's build moved or resized the elbow socket (report is the build's report.json joints.rockets)."""
    assert np.allclose(report["centre"], ELBOW, atol=1e-3) and np.allclose(report["axis"], np.round(SOCKET_AXIS, 4), atol=2e-4), \
        "the Brute's elbow socket has moved: update ELBOW and SOCKET_AXIS from report.json"
    assert (report["peg_radius"], report["peg_length"], report["magnet"]) == (PEG_R, PEG_L, "2 x 1 mm"), report
