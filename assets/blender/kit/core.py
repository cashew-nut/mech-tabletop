"""Scene, object and naming helpers every kit module and part script uses.

Units are millimetres, Z is up and the walker faces -Y (see ../common.py).
"""
import math
import re

import bpy  # noqa: F401  (bpy must load before bmesh)
import bmesh
from mathutils import Matrix, Vector

# ------------------------------------------------------------------ names
#
# Kit parts are named <faction>_<component>_<class>, falling back to
# <faction>_<component>_<frame>. Skeletons are <faction>_frame_<frame>.
# A sided component (arm, pauldron, ...) is modelled for the walker's LEFT
# side (+X) and mirrored for the right; an asymmetric right-hand version can
# be named <faction>_<component>-right_<class or frame>.

NAME_RE = re.compile(r"^(covenant|foundries|reliquary)_([a-z]+(?:-right)?)_([a-z]+)$")


def part_name(faction, component, variant, right=False):
    """`variant` is a class id (paladin) or a frame id (titan)."""
    return f"{faction}_{component}{'-right' if right else ''}_{variant}"


def frame_name(faction, frame):
    return part_name(faction, "frame", frame)


def parse_name(name):
    """(faction, component, variant, right) for a kit part name, else None."""
    m = NAME_RE.match(name.split(".")[0])
    if not m:
        return None
    comp = m.group(2)
    return m.group(1), comp.removesuffix("-right"), m.group(3), comp.endswith("-right")


# ------------------------------------------------------------------ scene

def reset_scene():
    """Empty factory scene in millimetres."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 0.001
    s.unit_settings.length_unit = "MILLIMETERS"
    return s


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def empty(name, loc=(0, 0, 0), parent=None, size=1.0, kind="ARROWS"):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = kind
    obj.empty_display_size = size
    obj.location = loc
    link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def parent_keep(child, parent):
    """Parent without moving the child in world space."""
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = mw
    return child


def mesh_obj(name, bm, mat=None, smooth=True, parent=None):
    """Turn a bmesh into a linked object. The bmesh is freed."""
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    if mat is not None:
        ob.data.materials.append(mat)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    if parent is not None:
        ob.parent = parent
    return ob


def mod(ob, kind, **kw):
    """Add a modifier: mod(ob, "BEVEL", width=0.2, segments=2)."""
    m = ob.modifiers.new(kind.lower(), kind)
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def apply_all(ob):
    """Apply an object's modifiers (curves become meshes)."""
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    if ob.type == "CURVE":
        bpy.ops.object.convert(target="MESH")
        return bpy.context.view_layer.objects.active
    for m in list(ob.modifiers):
        bpy.ops.object.modifier_apply(modifier=m.name)
    return ob


def subtree(obj):
    return [obj, *obj.children_recursive]


def meshes(root):
    return [o for o in subtree(root) if o.type in {"MESH", "CURVE"}]


def direction(az_deg, el_deg):
    """Unit vector. Azimuth 0 faces -Y (the walker's front), elevation up from the horizon."""
    a, e = math.radians(az_deg), math.radians(el_deg)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


def look_at(obj, target, up="Y"):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", up).to_euler()


def bounds(objs):
    """World-space (min, max) corners of a set of objects, modifiers included."""
    dg = bpy.context.evaluated_depsgraph_get()
    lo = Vector((math.inf,) * 3)
    hi = Vector((-math.inf,) * 3)
    for o in objs:
        ev = o.evaluated_get(dg)
        if not hasattr(ev, "bound_box") or o.type not in {"MESH", "CURVE"}:
            continue
        for c in ev.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


__all__ = [
    "Matrix", "Vector", "bmesh", "part_name", "frame_name", "parse_name", "reset_scene", "link", "empty",
    "parent_keep", "mesh_obj", "mod", "apply_all", "subtree", "meshes", "direction", "look_at", "bounds",
]
