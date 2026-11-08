"""Preview: the Seer's wrist items (kinetic claws, arc spear) on the Goliath's wrist, in place of the hand. Render only."""
import math, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Vector, Euler
sys.path.insert(0, "/home/user/mech-tabletop/assets/blender/parts/composite")
sys.path.insert(0, "/home/user/mech-tabletop/assets/blender")
import kit
from kit.render import studio, shot, post
OUT = Path(sys.argv[sys.argv.index("--") + 1])
SW = Vector((14.811, -2.691, 25.972)); SA = Vector((0.2456, -0.6189, -0.746))     # Seer wrist, blade axis (from fit.json)
SCALE = 1.25
bpy.ops.wm.open_mainfile(filepath=str(OUT / "goliath_composite.blend"))
studio()
obs = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
bpy.data.objects["gun_R"].rotation_euler = Euler((math.radians(-90), 0, 0))
bpy.context.view_layer.update()
def wpos(o): return o.matrix_world.translation.copy()
def item(name, stl, mat_col):
    bpy.ops.wm.stl_import(filepath=stl)
    o = bpy.context.selected_objects[0]
    elbow, wrist = wpos(obs["forearm_L"]), wpos(obs["hand_L"])
    out = (wrist - elbow).normalized()
    rot = SA.rotation_difference(out).to_matrix().to_4x4()
    M = Matrix.Translation(wrist) @ rot @ Matrix.Scale(SCALE, 4) @ Matrix.Translation(-SW)
    o.data.transform(M); o.name = name
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = mat_col; b.inputs["Metallic"].default_value = 1.0; b.inputs["Roughness"].default_value = 0.35
    o.data.materials.append(m)
    return o
claws = item("claws", "/mnt/project-files/models/seer-wrist/stl/kinetic-claws.stl", (0.62, 0.45, 0.2, 1))
spear = item("spear", "/mnt/project-files/models/seer-wrist/stl/arc-cannon.stl", (0.62, 0.45, 0.2, 1))
for o in obs.values():
    if o.get("spare"): o.hide_render = True
paths = []
for label, it, other in (("claws", claws, spear), ("spear", spear, claws)):
    other.hide_render = True; it.hide_render = False
    obs["hand_L"].hide_render = True
    for az in (20, 60, 100):
        p = OUT / f"_i_{label}_{az}.png"
        shot([it, obs["forearm_L"], obs["arm_L"]], p, az=az, el=8, samples=48, res=(700, 800), margin=1.1)
        post(p); paths.append(p)
from PIL import Image, ImageDraw
ims = [Image.open(p).convert("RGB") for p in paths]
w, h = ims[0].size
S = Image.new("RGB", (w * 3, h * 2 + 30), (12, 12, 14)); d = ImageDraw.Draw(S)
for i, im in enumerate(ims): S.paste(im, ((i % 3) * w, (i // 3) * h + 30))
d.text((10, 8), "Kinetic claws (top) and arc spear (bottom) on the Goliath's wrist, in place of the hand (preview: Seer parts, 1.25x)", fill=(225, 210, 170))
S.save(OUT / "items-preview.png")
for p in paths: p.unlink()
