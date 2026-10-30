# Blender part pipeline

The Lance Ledger draws each war-walker from swappable parts: one chassis plus
one part per fitted item. By default these are procedural models built in
code: `apps/web/src/model/chassis.ts` for the four chassis and `parts.ts` for
the items, from the building blocks in `kit.ts` (bevelled plates, banded
boilers, rivets, pipes, gauges, pistons and the brass, iron and hull
materials). These scripts let you replace them one part at a time with models
made in Blender, and turn any lance into a printable STL.

Tested with Blender 5.2 (the `bpy` module). Every script runs headless:

```sh
# 1. Make a starter file: a blocky version of every chassis and item,
#    with all mount points in place. Open it and start sculpting.
blender --background --python assets/blender/starter_parts.py -- assets/blender/parts.blend

# 2. Export every part in the file to apps/web/public/parts/ and update
#    manifest.json. The web builder uses them on the next reload.
blender assets/blender/parts.blend --background --python assets/blender/export_parts.py
#    ...or only some parts:
blender assets/blender/parts.blend --background --python assets/blender/export_parts.py -- --only titan rail-cannon

# 3. Assemble a walker from a lance file (exported from the Lance Ledger)
#    and save an STL, plus a .blend if you want to pose it before printing.
blender --background --python assets/blender/build_walker.py -- \
    data/lances/examples.json Lamplighter lamplighter.stl --blend lamplighter.blend
```

The Lance Ledger's **STL** button does the same assembly in the browser, so
step 3 is only needed when you want to work on the result in Blender.

## Modelling conventions

These match the web builder, so a part made here drops straight in.

| Rule | Detail |
| --- | --- |
| Units | 1 Blender unit = 1 mm. Bases are 25 / 32 / 40 / 50 mm for Scout / Striker / Bulwark / Titan. |
| Axes | Z up, the walker faces **-Y** (what Blender's Front view shows). The glTF export turns this into the web's Y-up, +Z-forward. |
| Chassis | A root object (an empty is easiest) named `chassis_<id>`, for example `chassis_bulwark`, with everything else parented under it. The base sits on Z = 0. |
| Mount points | Empties under the chassis named `mount_<location>_<slot>`, where location is `armLeft`, `armRight`, `core` or `legs` and slot counts from 0. Each chassis needs one per slot in `data/chassis.json`. The exporter warns about any that are missing. Blender's `.001` suffixes are fine. |
| Items | A root object named `item_<id>` (ids from `data/equipment.json`), with its origin at the point where it attaches and its business end pointing -Y. |
| Item scale | Model items at Scout scale. They are scaled ×1.2, ×1.4 and ×1.7 on the Striker, Bulwark and Titan. |
| Multi-slot items | Snap to the mount of their first slot, so a 2-slot item in slots 0-1 sits on `mount_<location>_0`. |
| Paint | Any material whose name starts with `hull` is recoloured with the faction livery or the walker's paint. Name brass, iron and glowing parts anything else. |
| Printing | Keep walls at least 1 mm thick and barrels at least 1.5 mm across at Scout scale, and keep each part a closed mesh. |

## Files

- `common.py`: shared paths, data loading and the scale table.
- `starter_parts.py`: writes a starter `parts.blend` from `data/`.
- `export_parts.py`: exports `chassis_*` and `item_*` roots as GLB and updates the manifest.
- `build_walker.py`: assembles one walker from the exported GLBs and saves an STL.

Parts you have not modelled yet keep using the procedural web parts, so the
manifest can grow one entry at a time. Commit the `.blend` and the exported GLBs
together.
