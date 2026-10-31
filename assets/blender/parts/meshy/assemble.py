"""Assemble the published Paladin kit parts at rest, in Blender, and render or export them.

    ~/bvenv/bin/python assemble.py OUT_PREFIX [--viewer FILE.glb] [--size 512]

Imports apps/web/public/parts/kit/covenant_*_paladin.glb (before KTX2 compression: Blender can't read KTX2),
puts each part at its frame joint (using frameTunes) and the two items at their mounts, then renders
front, side and back views. `--viewer` also writes one GLB (JPEG textures scaled to --size) for a web viewer.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import bpy  # noqa: E402
import kit  # noqa: E402
from kit.skeleton import Skeleton  # noqa: E402
from kit.export import PARTS_DIR  # noqa: E402
from mathutils import Vector  # noqa: E402

SIDED = {"pauldron", "arm", "forearm", "hand", "thigh", "shin", "foot"}
JOINT_OF = {c["id"]: c["joint"] for c in kit.skeleton.KIT["components"]}
ITEM_SCALE = 1.7


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    root = kit.empty(path.stem)
    for r in roots:
        r.parent = root
    return root, new


def main(args):
    out = args[0]
    kit.reset_scene()
    sk = Skeleton("covenant", "titan")
    everything = []
    d = PARTS_DIR / "kit"
    for comp in JOINT_OF:
        for side in (("L", "R") if comp in SIDED else (None,)):
            name = f"covenant_{comp}{'-right' if side == 'R' else ''}_paladin"
            f = d / f"{name}.glb"
            if not f.exists() and side == "R":
                f = d / f"covenant_{comp}_paladin.glb"   # a left part, mirrored
            if not f.exists():
                continue
            root, objs = load(f)
            root.location = sk.joint(JOINT_OF[comp], side or "L")
            root.scale = (0.001, 0.001, 0.001)   # the GLB holds mm as metres; the importer scales by 1000
            if side == "R" and "-right" not in f.name:
                root.scale.x = -0.001
            everything += objs
    for mount, item, sx in (("mount_armLeft_0", "item_lance@paladin", 1), ("mount_armRight_0", "item_lance@paladin", -1),
                            ("mount_core_0", "item_carapace-gun@paladin", 1), ("mount_core_1", "item_carapace-gun@paladin", -1)):
        f = PARTS_DIR / f"{item}.glb"
        if not f.exists():
            continue
        # mounts() lists (name, joint, side, offset, rz); items sit at the mount, scaled for the titan frame.
        m = next(m for m in sk.mounts() if m[0] == mount)
        root, objs = load(f)
        root.location = sk.joint(m[1], m[2] or "L") + m[3]
        root.scale = (sx * ITEM_SCALE * 0.001, ITEM_SCALE * 0.001, ITEM_SCALE * 0.001)
        everything += objs
    bpy.context.view_layer.update()
    meshes = [o for o in everything if o.type == "MESH"]
    print("meshes", len(meshes), "tris", sum(len(o.data.polygons) for o in meshes))
    if "--viewer" in args:
        path = Path(args[args.index("--viewer") + 1])
        bpy.ops.object.select_all(action="DESELECT")
        for o in everything:
            o.select_set(True)
        for o in meshes:
            for s in o.material_slots:
                pass
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True, export_image_format="JPEG",
                                  export_jpeg_quality=int(__import__("os").environ.get("JPEG_Q", 85)))
        print("viewer", path, path.stat().st_size // 1024, "KB")
    if "--no-render" in args:
        return
    if "--ortho" in args:
        import math
        sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        sc.cycles.samples = 12
        w = bpy.data.worlds.new("flat")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[1].default_value = 1.6
        sc.world = w
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 2
        sun.rotation_euler = (0.8, 0.2, 0.5)
        sc.collection.objects.link(sun)
        sc.render.resolution_x, sc.render.resolution_y = 900, 1000
        cam = bpy.data.objects.new("c", bpy.data.cameras.new("c"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 2.1 * 50 / 1.5          # same framing as the Meshy original: 2.1 units over the image height
        zc = (0 + 0.9) * 50 / 1.5 + 3
        for name, loc, rot in (("front", (0, -500, zc), (90, 0, 0)), ("side", (500, 0, zc), (90, 0, 90)), ("back", (0, 500, zc), (90, 0, 180))):
            cam.location = loc
            cam.rotation_euler = [math.radians(r) for r in rot]
            sc.render.filepath = f"{out}-{name}.png"
            bpy.ops.render.render(write_still=True)
        return
    if "--flat" in args:
        sc = bpy.context.scene
        sc.render.engine = "CYCLES"
        w = bpy.data.worlds.new("flat")
        w.use_nodes = True
        w.node_tree.nodes["Background"].inputs[1].default_value = 1.4
        w.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.55, 1)
        sc.world = w
        sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
        sun.data.energy = 3
        sun.rotation_euler = (0.9, 0.2, -0.6)
        sc.collection.objects.link(sun)
    else:
        kit.render.studio(strength=2.5)
    for name, az, el in (("front", 0, 6), ("side", 90, 6), ("back", 180, 6), ("three-quarter", 35, 10)):
        kit.render.shot(meshes, f"{out}-{name}.png", az=az, el=el, samples=24, res=(700, 900))


if __name__ == "__main__":
    main(sys.argv[1:])
