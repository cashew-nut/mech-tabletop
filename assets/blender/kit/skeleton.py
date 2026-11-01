"""The four frames every walker is hung on, with joints, sockets and spare mounts.

    sk = Skeleton("covenant", "titan")     # pure maths, no Blender objects
    sk.joint("elbow", "L")                 # world position of joint_elbow_L
    sk.length("shoulder", "elbow")         # upper-arm length in mm
    sk.H                                   # nominal height to the top of the head

    root = build_frame("covenant", "titan")  # covenant_frame_titan, with stand-ins

A frame is an empty named `<faction>_frame_<frame>` holding a tree of joint
empties (`joint_<name>` or `joint_<name>_L/_R`), the mount empties weapons
snap to (`mount_<location>_<slot>`, with spares so any class's slot counts
fit) and a rough stand-in mesh for every component (`standin_<component>`),
which the web hides once a real part covers it. Joints all keep the world
axes at rest (Z up, facing -Y), so a part is modelled in its joint's space:
place it where it sits on the walker and call `to_joint(part, component)`.

The walker's left is +X. Sided parts are modelled for the left and mirrored.
Faction proportions come from data/model-kit.json: Reliquary limbs are
longer and thinner, Foundries frames squatter and wider.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from .core import empty, parent_keep
from .materials import PALETTES
from . import shapes

KIT = json.loads((Path(__file__).resolve().parents[3] / "data" / "model-kit.json").read_text())
FRAMES = tuple(KIT["frames"])
COMPONENTS = {c["id"]: c for c in KIT["components"]}
BASE_THICKNESS = 3.0

# Parent of each joint. Sided joints exist once per side.
TREE = {
    "root": None, "pelvis": "root", "spine": "pelvis", "chest": "spine", "neck": "chest", "head": "neck",
    "shoulder": "chest", "elbow": "shoulder", "wrist": "elbow", "hip": "pelvis", "knee": "hip", "ankle": "knee",
}
SIDED = {"shoulder", "elbow", "wrist", "hip", "knee", "ankle"}


def joint_name(joint, side=None):
    return f"joint_{joint}" + (f"_{side}" if joint in SIDED else "")


class Skeleton:
    """Joint positions (mm, world space, left side) for one faction's frame."""

    def __init__(self, faction, frame):
        self.faction, self.frame = faction, frame
        p = KIT["factions"][faction]["proportions"]
        f = KIT["frames"][frame]
        self.H = H = f["height"] * p["height"]
        self.W = W = f["width"] * p["width"]
        self.L = L = p["limbLength"]
        self.G = p["limbGirth"] * math.sqrt(W)
        self.base = f["base"]
        ankle_z = BASE_THICKNESS + 0.05 * H
        knee_z = ankle_z + 0.22 * H * L
        hip_z = knee_z + 0.22 * H * L
        pelvis_z = hip_z + 0.02 * H
        spine_z = pelvis_z + 0.07 * H
        chest_z = spine_z + 0.13 * H
        neck_z = chest_z + 0.13 * H
        sh = Vector((0.19 * H * W, 0.0, chest_z + 0.07 * H))
        el = sh + Vector((0.03 * H * W, 0.01 * H, -0.19 * H * L))
        wr = el + Vector((0.0, -0.06 * H, -0.17 * H * L))
        self._j = {
            "root": Vector((0, 0, 0)),
            "pelvis": Vector((0, 0, pelvis_z)),
            "spine": Vector((0, 0, spine_z)),
            "chest": Vector((0, 0, chest_z)),
            "neck": Vector((0, 0, neck_z)),
            "head": Vector((0, -0.01 * H, neck_z + 0.05 * H)),
            "shoulder": sh, "elbow": el, "wrist": wr,
            "hip": Vector((0.07 * H * W, 0, hip_z)),
            "knee": Vector((0.085 * H * W, -0.02 * H, knee_z)),
            "ankle": Vector((0.10 * H * W, 0.0, ankle_z)),
        }
        # A class's own model can pin the joints and mounts to its proportions (frameTunes in model-kit.json).
        self.tune = KIT.get("frameTunes", {}).get(f"{faction}/{frame}", {})
        for name, pos in self.tune.get("joints", {}).items():
            self._j[name] = Vector(pos)

    def joint(self, name, side="L"):
        """World position of a joint; side "R" mirrors X."""
        v = self._j[name].copy()
        if name in SIDED and side == "R":
            own = self.tune.get("jointsRight", {}).get(name)    # an asymmetric model's own right-hand joint
            if own:
                return Vector(own)
            v.x = -v.x
        return v

    def length(self, a, b):
        return (self._j[b] - self._j[a]).length

    def radius(self, part):
        """Nominal stand-in radius of a limb segment, a guide for real parts."""
        k = {"arm": 0.05, "forearm": 0.045, "thigh": 0.065, "shin": 0.055}[part]
        return k * self.H * self.G

    def socket(self, component, side="L"):
        """World position of the joint a component hangs on."""
        return self.joint(COMPONENTS[component]["joint"], side)

    def mounts(self):
        """(name, joint, side, local offset, z-rotation) for every mount, spares included."""
        H, sp = self.H, KIT["spareMounts"]
        out = []
        for loc, side, sx in (("armLeft", "L", 1), ("armRight", "R", -1)):
            spots = [
                ("wrist", Vector((sx * 0.03 * H, -0.03 * H, -0.02 * H))),
                ("elbow", Vector((sx * 0.07 * H, -0.02 * H, -0.06 * H))),
                ("shoulder", Vector((sx * 0.03 * H, 0.0, 0.07 * H))),
            ]
            for i in range(sp[loc]):
                j, off = spots[min(i, len(spots) - 1)]
                tuned = self.tune.get("mounts", {}).get(f"mount_{loc}_{i}")
                if tuned:
                    off = Vector(tuned[1])
                out.append((f"mount_{loc}_{i}", j, side, off, 0.0))
        core = [
            (Vector((0.10 * H * self.W, 0.02 * H, 0.15 * H)), 0.0),
            (Vector((-0.10 * H * self.W, 0.02 * H, 0.15 * H)), 0.0),
            (Vector((0.0, 0.11 * H, 0.06 * H)), math.pi),
            (Vector((0.0, -0.09 * H, 0.03 * H)), 0.0),
        ]
        for i in range(sp["core"]):
            off, rz = core[min(i, len(core) - 1)]
            tuned = self.tune.get("mounts", {}).get(f"mount_core_{i}")
            if tuned:
                off = Vector(tuned[1])
            out.append((f"mount_core_{i}", "chest", None, off, rz))
        for i in range(sp["legs"]):
            side, sx = ("L", 1) if i % 2 == 0 else ("R", -1)
            out.append((f"mount_legs_{i}", "hip", side, Vector((sx * 0.06 * H, 0.0, -0.06 * H)), 0.0))
        return out


# ------------------------------------------------------------------ building in Blender

def _standin_materials(faction):
    """Plain-colour materials for stand-ins: small files, no textures."""
    pal = PALETTES[faction]
    out = {}
    for role, colour, metal, rough in (
        ("armour", pal["armour"]["base"][1], pal["armour"]["metal"], 0.55),
        ("metal", pal["metal"]["base"][1], 0.8, 0.6),
        ("trim", pal["trim"]["base"][1], 1.0, 0.35),
    ):
        name = f"standin_{role}_{faction}"
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*colour, 1)
        b.inputs["Metallic"].default_value = metal
        b.inputs["Roughness"].default_value = rough
        m["bake"] = False
        out[role] = m
    name = f"hull_standin_{faction}"
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*pal["hull"]["paint"], 1)
    b.inputs["Roughness"].default_value = 0.5
    m["bake"] = False
    out["hull"] = m
    glow = pal["glow"]
    name = f"glow_standin_{faction}"
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    b.inputs["Emission Color"].default_value = (*glow["emit"], 1)
    b.inputs["Emission Strength"].default_value = glow["strength"]
    m["bake"] = False
    out["glow"] = m
    return out


def _limb(name, a, b, r, mat, r2=None):
    d = b - a
    ob = shapes.cylinder(name, r, d.length, mat, loc=(a + b) / 2, verts=16, bevel=r * 0.15, r2=r2)
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    return ob


def _standins(sk, faction, joints):
    """A rough body: enough to judge proportions and see where each component goes."""
    m = _standin_materials(faction)
    H, W = sk.H, sk.W
    made = []

    def put(ob, component, side=None):
        ob.name = f"standin_{component}" + (f"_{side}" if side else "")
        ob["standin"] = component
        if side:
            ob["side"] = side
        parent_keep(ob, joints[joint_name(COMPONENTS[component]["joint"], side)])
        made.append(ob)

    put(shapes.cylinder("b", sk.base / 2, BASE_THICKNESS, m["armour"], loc=(0, 0, BASE_THICKNESS / 2), verts=48, bevel=0.6), "base")
    pz = sk.joint("pelvis").z
    put(shapes.box_plate("p", (0.2 * H * W, 0.12 * H, 0.08 * H), m["armour"], bevel=0.4, loc=(0, 0, pz)), "pelvis")
    sz, cz = sk.joint("spine").z, sk.joint("chest").z
    torso = shapes.box_plate("t", (0.3 * H * W, 0.17 * H, 0.26 * H), m["armour"], bevel=0.6, loc=(0, 0, (sz + cz) / 2 + 0.04 * H), taper=-0.25)
    parent_keep(shapes.box_plate("tp", (0.16 * H * W, 0.02 * H, 0.12 * H), m["hull"], bevel=0.2, loc=(0, -0.09 * H, cz)), torso)
    put(torso, "torso")
    hz = sk.joint("head")
    helm = shapes.sphere("h", 0.055 * H, m["armour"], loc=hz + Vector((0, 0, 0.03 * H)), scale=(0.85, 1.0, 1.1))
    parent_keep(shapes.box_plate("hv", (0.06 * H, 0.01 * H, 0.012 * H), m["glow"], bevel=0, loc=hz + Vector((0, -0.055 * H, 0.035 * H))), helm)
    put(helm, "helm")
    for side in ("L", "R"):
        sx = 1 if side == "L" else -1
        sh, el, wr = sk.joint("shoulder", side), sk.joint("elbow", side), sk.joint("wrist", side)
        put(shapes.sphere("pa", 0.085 * H * sk.G, m["armour"], loc=sh + Vector((sx * 0.01 * H, 0, 0.02 * H)), scale=(1.0, 1.0, 0.75)), "pauldron", side)
        put(_limb("a", sh, el, sk.radius("arm"), m["metal"]), "arm", side)
        put(_limb("f", el, wr, sk.radius("forearm"), m["armour"], sk.radius("forearm") * 1.2), "forearm", side)
        put(shapes.box_plate("hd", (0.05 * H, 0.06 * H, 0.07 * H), m["metal"], bevel=0.3, loc=wr + Vector((0, -0.01 * H, -0.04 * H))), "hand", side)
        hp, kn, an = sk.joint("hip", side), sk.joint("knee", side), sk.joint("ankle", side)
        put(_limb("th", hp, kn, sk.radius("thigh"), m["armour"]), "thigh", side)
        put(_limb("sh", kn, an, sk.radius("shin"), m["armour"], sk.radius("shin") * 1.15), "shin", side)
        put(shapes.box_plate("ft", (0.08 * H, 0.16 * H, 0.05 * H), m["metal"], bevel=0.4, loc=an + Vector((0, -0.03 * H, -0.025 * H)), taper=0.3), "foot", side)
    return made


def build_frame(faction, frame, standins=True, location=(0, 0, 0)):
    """Make `<faction>_frame_<frame>`: joints, spare mounts and stand-ins."""
    sk = Skeleton(faction, frame)
    # Built at the origin (stand-ins are placed in world space), then moved.
    root = empty(f"{faction}_frame_{frame}", (0, 0, 0), size=sk.base / 2, kind="CIRCLE")
    root["kit_faction"] = faction
    root["kit_frame"] = frame
    joints = {}

    def make(joint, side):
        name = joint_name(joint, side)
        if name in joints:
            return joints[name]
        parent = TREE[joint]
        par = root if parent is None else make(parent, side)
        world = sk.joint(joint, side or "L")
        ob = empty(name, world - (sk.joint(parent, side or "L") if parent else Vector()), parent=par, size=0.04 * sk.H, kind="SPHERE")
        ob["joint"] = name
        joints[name] = ob
        return ob
    for j in TREE:
        for side in (("L", "R") if j in SIDED else (None,)):
            make(j, side)
    for name, joint, side, off, rz in sk.mounts():
        m = empty(name, off, parent=joints[joint_name(joint, side)], size=0.03 * sk.H)
        m.rotation_euler = (0, 0, rz)
        m["mount"] = name
    bpy.context.view_layer.update()
    if standins:
        _standins(sk, faction, joints)
    root.location = location
    bpy.context.view_layer.update()
    return root


def to_joint(part, faction, frame, component, side="L"):
    """Move a part modelled in place on the walker into its joint's space, so
    its origin is the joint (that is how the web and STL builder attach it)."""
    # Move the children, not the root: export_glb() writes the root at the
    # origin, so an offset on the root itself would be lost.
    off = Skeleton(faction, frame).socket(component, side)
    bpy.context.view_layer.update()
    for c in part.children:
        c.matrix_world = Matrix.Translation(-off) @ c.matrix_world
    return part
