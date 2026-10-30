"""Material test plates: one armour panel per faction using every role in its
material library, baked, rendered and laid beside the faction's swatches.

    bvenv/bin/python assets/blender/test_plates.py [faction ...] [--samples 48] [--out renders/foundation]
    bvenv/bin/python assets/blender/test_plates.py covenant --publish   # also export kit/covenant_testplate_kit.glb

The plate is a kit-built panel with a curved pauldron dome, gold or brass
trim, rivets, a filigree band, a painted hull panel, a lit lancet, a pipe
and a hanging strip of cloth. It renders twice: with the live node
materials, and after baking with the baked textures, so the bake can be
judged against the source.
"""
import math
import sys
from pathlib import Path

import bpy  # noqa: F401

sys.path.insert(0, str(Path(__file__).parent))
import kit  # noqa: E402
from common import REPO, script_args  # noqa: E402
from kit import shapes  # noqa: E402
from kit.core import Vector, bmesh, empty, mesh_obj, mod  # noqa: E402

DETAIL = {"covenant": "detail_covenant_helm", "foundries": "detail_foundries_hull_07", "reliquary": "detail_reliquary_helm"}


def cloth_strip(name, w, h, mat, loc, parent):
    """A hanging banner: a rippled, torn-hemmed sheet."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("Decal")
    nu, nv = 12, 20
    grid = []
    for j in range(nv + 1):
        row = []
        for i in range(nu + 1):
            u, v = i / nu, j / nv
            # The hem is ragged: the lowest rows are pulled up unevenly.
            tear = 0.12 * (1 - v) ** 6 * (0.5 + 0.5 * math.sin(u * 37.0)) if j == 0 else 0
            z = -h * (1 - v) + h * tear
            y = 0.35 * math.sin(u * math.pi * 3 + v * 2) * (1 - v * 0.7)
            row.append(bm.verts.new((loc[0] + (u - 0.5) * w, loc[1] + y, loc[2] + z)))
        grid.append(row)
    shapes._grid_faces(bm, grid, uv, (1, 2))
    ob = mesh_obj(name, bm, mat, parent=parent)
    mod(ob, "SOLIDIFY", thickness=0.15)
    return ob


def build(faction):
    m = kit.materials.library(faction)
    root = empty(f"{faction}_testplate_kit", size=4)
    base = shapes.box_plate("plate", (16, 1.4, 12), m["armour"], bevel=0.35, loc=(0, 0, 6), panel_lines=2, parent=root)
    # Gold edging round the front face, as on the art's plates.
    hw, hh, y = 8.05, 6.05, -0.75
    shapes.sweep("plate_trim", [(-hw, y, 6 - hh), (hw, y, 6 - hh), (hw, y, 6 + hh), (-hw, y, 6 + hh)], 0.22, m["trim"], cyclic=True, parent=root, profile="square")
    shapes.rivet_row("rivets_top", (-7.2, -0.85, 11.2), (7.2, -0.85, 11.2), 13, 0.2, m["trim"], parent=root)
    shapes.rivet_row("rivets_bot", (-7.2, -0.85, 0.8), (7.2, -0.85, 0.8), 13, 0.2, m["trim"], parent=root)
    # A filigree band along the bottom.
    band = shapes.box_plate("filigree_band", (14, 0.5, 2.2), m["filigree"], bevel=0.12, loc=(0, -0.9, 2.2), parent=root)
    shapes.decal_uv(band, tile_mm=2.2)
    # The paintable hull panel, with a stencil for the Foundries.
    shapes.box_plate("hull_panel", (5.5, 0.5, 5.0), m["stencil" if faction == "foundries" else "hull"], bevel=0.15, loc=(4.2, -0.95, 6.6), parent=root)
    if faction == "foundries":
        # Re-lay the decal UVs so one stencil spans the panel.
        p = bpy.data.objects["hull_panel"]
        me = p.data
        me.uv_layers.remove(me.uv_layers["Decal"])
        p.location = (4.2, -0.95, 6.6)
        bpy.context.view_layer.update()
        shapes.decal_uv(p, tile_mm=5.2)
        for lp in me.uv_layers["Decal"].data:
            lp.uv = (lp.uv[0] - (4.2 - 2.6) / 5.2, lp.uv[1] - (6.6 - 2.6) / 5.2)
    # A pauldron dome with stacked lames laid on a Shell.
    dome = shapes.sphere("dome", 3.4, m["armour"], loc=(-4.0, -0.7, 7.2), scale=(1.0, 0.7, 0.85), parent=root, segments=48)
    bpy.context.view_layer.update()
    shell = shapes.Shell(dome, centre=(-4.0, 1.0, 7.2))
    shell.lames("dome_lame", -60, 60, [(-30, -8), (-10, 12)], m["armour"], trim_mat=m["trim"], lift=0.08, step=0.1, thick=0.2, lip=0.2, parent=root, trim=0.1)
    shell.trim("dome_ring", [(a, 22) for a in range(-80, 81, 4)], 0.16, m["trim"], parent=root)
    shell.studs("dome_studs", [(a, 30) for a in range(-50, 51, 20)], 0.18, m["trim"], parent=root)
    # A lit lancet window and a banded pipe.
    shapes.lancet("lancet", 1.6, 3.6, 0.8, m["metal"], glow=m["glow"], loc=(0.4, -1.0, 4.6), parent=root)
    shapes.pipe("pipe", [(-7.5, -1.6, 9.6), (-2, -1.9, 10.2), (3, -1.9, 10.2), (7.5, -1.6, 9.8)], 0.35, m["metal"], parent=root, bands=(0.2, 0.5, 0.8), band_mat=m["trim"])
    cloth_strip("cloth", 3.2, 9, m["cloth"], (-6.2, -1.4, 10.5), root)
    return root


def main():
    args = script_args()
    samples = int(args[args.index("--samples") + 1]) if "--samples" in args else 48
    out = Path(args[args.index("--out") + 1]) if "--out" in args else REPO / "renders" / "foundation"
    flags = {"--samples", "--out"}
    factions = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in flags)] or list(kit.materials.FACTIONS)
    publish = "--publish" in args
    for faction in factions:
        kit.reset_scene()
        kit.render.studio()
        root = build(faction)
        objs = kit.meshes(root)
        live = kit.render.shot(objs, out / f"testplate-{faction}-live.png", az=28, el=10, samples=samples, res=(900, 760))
        if publish:
            path = kit.publish(root, size=1024)
            print("published", path)
        else:
            kit.bake.bake_part(root, size=1024, out_dir=kit.export.BAKE_DIR / root.name)
        objs = kit.meshes(root)
        baked = kit.render.shot(objs, out / f"testplate-{faction}-baked.png", az=28, el=10, samples=samples, res=(900, 760))
        for p in (live, baked):
            kit.render.post(p)
        kit.render.compare([live, baked], f"swatches_{faction}", out / f"testplate-{faction}.png", height=520,
                           labels=["node materials (Cycles)", "baked textures (what the web gets)"], title=f"{faction} test plate")
        kit.render.compare([baked], DETAIL[faction], out / f"testplate-{faction}-detail.png", height=520,
                           labels=["baked test plate"], title=f"{faction} test plate beside a detail tile")
        print("wrote", out / f"testplate-{faction}.png")


main()
