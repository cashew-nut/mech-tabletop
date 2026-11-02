"""Bake the Seer's wrist weapons (arc spear, kinetic claws), fit them on the walker in Blender and render the review shots
(needs bpy).

    MODEL=seer ~/bvenv/bin/python -I seer_wrist_build.py PARTS WRIST [--bend BEND.json] [--samples 32] [--size 1024]
                                                          [--no-render]

PARTS  models/seer-composite-v2 (needs seer_composite.blend: the assembled walker, right arm the mirror of the left)
WRIST  seer_wrist.py's output folder (work/<item>/kit/<item>.npz and that item's textures; fit.json). Writes into it:

  glb/<item>.glb       the game part: kit mm (print mm / 1.5), origin on the wrist joint, Blender axes like every kit part
  with --bend (seer_elbow.py's bend.json) PARTS's hands are turned with the bent forearm; the game hand is turned without a
  rebake by scripts/turn-part.mjs
  stl/<item>.stl       the print copy (closed, the hand's half ball and peg in place)
  textures/            the baked colour, orm and normal maps
  seer_wrist.blend     the walker with the spear on the left wrist and the claws on the right, in place of the hands (the
                       other pairing is in the file too, hidden); every weapon is parented to its forearm
  renders/items.png    the two weapons on their own
  renders/loadout.png  the walker: spear both sides, claws both sides, one of each
  renders/socket.png   each weapon pulled off its wrist socket along the peg axis, and seated

build.py does the baking (the same code as every other composite part): the Meshy surface is the bake source, the half
ball, sleeve and struts bake as the knuckles' gold, cut faces and the peg as gunmetal.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
import kit  # noqa: E402
import build  # noqa: E402
from kit.render import shot, post  # noqa: E402
from layout import PS, joint  # noqa: E402
from paladin_items_build import parent_keep  # noqa: E402

ITEMS = {"arc-cannon": (7000, 1024), "kinetic-claws": (7000, 1024)}     # triangles, texture px
LABEL = {"arc-cannon": "Arc spear", "kinetic-claws": "Kinetic claws"}


def bake_item(item, wrist, size_override):
    build.TREE[item] = (None, "wrist", None)       # origin on the wrist joint
    build.BUDGET[item] = (ITEMS[item][0], size_override or ITEMS[item][1])
    work = wrist / "work" / item
    imgs = {}
    for k, nm, cs in ((0, "base", "sRGB"), (1, "mr", "Non-Color"), (2, "nrm", "Non-Color")):
        im = bpy.data.images.load(str(work / f"tex_{k}.jpg"))
        im.colorspace_settings.name = cs
        imgs[nm] = im
    mats = build.high_materials(imgs)
    ob, info = build.build_part(item, work, wrist, mats, size_override, True)
    for m in [m for m in bpy.data.materials if m.name.startswith(("high_", "lo_"))]:
        bpy.data.materials.remove(m)
    # origin on the wrist (seer_wrist.py's fit.json: the bent wrist when the elbow is bent) instead of the unbent joint
    c = Vector(json.loads((wrist / "fit.json").read_text())["origin"]["print_mm"])
    ob.data.transform(Matrix.Translation(ob.location - c))
    ob.location = c
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    ob.location = (0, 0, 0)
    ob.data.transform(Matrix.Scale(1 / PS, 4))
    (wrist / "glb").mkdir(exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(wrist / "glb" / f"{item}.glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_apply=True)
    ob.data.transform(Matrix.Scale(PS, 4))
    ob.location = c
    return ob, info


def main(a):
    parts, wrist = Path(a[0]), Path(a[1])
    samples = int(a[a.index("--samples") + 1]) if "--samples" in a else 32
    size = int(a[a.index("--size") + 1]) if "--size" in a else None
    bpy.ops.wm.open_mainfile(filepath=str(parts / "seer_composite.blend"))
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 1
    obj = bpy.data.objects
    made, report = {}, {}
    for item in ITEMS:
        made[item], report[item] = bake_item(item, wrist, size)
    json.dump(report, open(wrist / "build_report.json", "w"), indent=1)

    # on the walker: a copy of each weapon on each forearm (the right one mirrored), parented so it swings with the arm
    placed = {}
    for item, ob in made.items():
        ob.name = f"{item}_L"
        parent_keep(ob, obj["forearm_L"])
        r = bpy.data.objects.new(f"{item}_R", ob.data)
        scene.collection.objects.link(r)
        r.matrix_world = Matrix.Scale(-1, 4, (1, 0, 0)) @ ob.matrix_world
        parent_keep(r, obj["forearm_R"])
        placed[item] = {"L": ob, "R": r}
    hands = {"L": obj["hand_L"], "R": obj["hand_R"]}
    if "--bend" in a:       # the elbow is bent (seer_elbow.py): turn the hands about the elbow
        b = json.loads(Path(a[a.index("--bend") + 1]).read_text())
        Rb = Matrix([list(r) for r in b["R"]]).to_4x4()
        cb = Vector(b["centre"])
        turn = Matrix.Translation(cb) @ Rb @ Matrix.Translation(-cb)
        flip = Matrix.Scale(-1, 4, (1, 0, 0))
        for s, h in hands.items():
            h.matrix_world = (turn if s == "L" else flip @ turn @ flip) @ h.matrix_world
        bpy.context.view_layer.update()
    # the spare spear bore in the fist stays: the fist still works with the old held spear

    def fit(left, right):
        """Show `left` on the left wrist and `right` on the right one (None: the hand), hide the rest."""
        for item, sides in placed.items():
            for s, o in sides.items():
                on = (left if s == "L" else right) == item
                o.hide_render = not on
                o.hide_set(not on)
        for s, h in hands.items():
            show = (left if s == "L" else right) is None
            h.hide_render = not show
            h.hide_set(not show)
        bpy.context.view_layer.update()

    fit("arc-cannon", "kinetic-claws")
    for im in bpy.data.images:
        if im.filepath and not im.packed_file and im.source == "FILE":
            try:
                im.pack()
            except RuntimeError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=str((wrist / "seer_wrist.blend").resolve()))
    if "--no-render" in a:
        return

    from render import sheet
    kit.render.studio()
    rd = wrist / "renders"
    rd.mkdir(exist_ok=True)
    allm = [o for o in bpy.data.objects if o.type == "MESH" and not o.get("retired") and not o.get("spare")]

    # 1. the weapons alone
    paths, labels = [], []
    for item, sides in placed.items():
        ob = sides["L"]
        for o in allm:
            o.hide_render = o is not ob
        for az, el, tag in ((300, 14, "front"), (90, 6, "side")):
            p = rd / f"_alone_{item}_{az}.png"
            shot([ob], p, az=az, el=el, samples=samples, res=(500, 700), margin=0.85)
            post(p)
            paths.append(p)
            labels.append(f"{LABEL[item]}, {tag}")
    sheet(paths, rd / "items.png", 4, labels)

    # 2. the walker
    paths, labels = [], []
    for left, right, tag in ((None, None, "hands (no weapon)"), ("arc-cannon", "arc-cannon", "arc spear, both"),
                             ("kinetic-claws", "kinetic-claws", "kinetic claws, both"),
                             ("arc-cannon", "kinetic-claws", "spear left, claws right")):
        fit(left, right)
        vis = [o for o in allm if not o.hide_get()]
        for o in allm:
            o.hide_render = o not in vis
        for az, el in ((20, 8), (75, 6)):
            p = rd / f"_load_{tag[:5]}_{az}.png"
            shot(vis, p, az=az, el=el, samples=samples, res=(700, 900), margin=0.8)
            post(p)
            paths.append(p)
            labels.append(f"{tag}, {az} deg")
    sheet(paths, rd / "loadout.png", 4, labels)

    # 3. the socket: each weapon pulled off its wrist along the peg axis, and seated
    fit("arc-cannon", "kinetic-claws")
    fit_json = json.loads((wrist / "fit.json").read_text())
    axis = Vector(fit_json["socket"]["axis_into_forearm"])
    near = [obj[n] for n in ("forearm_L", "arm_L") if n in obj]
    paths, labels = [], []
    for item in ITEMS:
        ob = placed[item]["L"]
        loc = ob.location.copy()
        mw = ob.matrix_world.copy()
        for gap, tag in ((6.0, "pulled off"), (0.0, "seated")):
            ob.matrix_world = Matrix.Translation(-axis * gap) @ mw
            bpy.context.view_layer.update()
            for o in allm:
                o.hide_render = o not in near + [ob]
            ob.hide_render = False
            p = rd / f"_sock_{item}_{tag[:4]}.png"
            shot(near + [ob], p, az=60, el=12, samples=samples, res=(600, 800), margin=0.9)
            post(p)
            paths.append(p)
            labels.append(f"{LABEL[item]} {tag}")
        ob.matrix_world = mw
        ob.location = loc
    sheet(paths, rd / "socket.png", 4, labels)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
