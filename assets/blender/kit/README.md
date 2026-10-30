# The war-walker kit

Scripted, headless Blender building blocks for the walker models, and the
pipeline that carries them into the web game. Every component package
(helms, torsos, pauldrons, arms, legs, spires, cloth, weapons) builds on
this. The plan is the "War-walker model rebuild plan" doc.

## Setup

Blender 5.2 as a Python module, no Blender install needed:

```sh
python3.13 -m venv ~/bvenv && ~/bvenv/bin/pip install bpy pillow numpy   # bpy wheel ~400 MB
npm install && npm i --no-save basisu                                       # KTX2 encoder for compress-parts
```

Every script also runs inside a full Blender: `blender --background --python script.py -- args`.

## The pipeline

```
part script (Python, bpy + kit)
  -> kit.publish(root)          bake node materials to base colour, ORM and normal PNGs,
                                export apps/web/public/parts/kit/<name>.glb, list it in manifest.json
  -> node scripts/compress-parts.mjs    PNG textures in the GLBs -> KTX2
  -> the web game               assemble.ts hangs the parts on the class's frame
  -> build_walker.py / STL button       the same parts, assembled for printing
```

Review renders: `kit.render.shot()` then `kit.render.compare()` against a
named crop of the concept art (`assets/art/crops.json`). Post them to the
project's `renders/<package>/` folder before opening a pull request.

## Names

| Root object | What it is | Example |
| --- | --- | --- |
| `<faction>_frame_<frame>` | A skeleton: joints, mounts, stand-ins. Built by `build_frames.py`. | `covenant_frame_titan` |
| `<faction>_<component>_<class>` | A kit part for one class. | `covenant_helm_paladin` |
| `<faction>_<component>_<frame>` | The faction's part for every class on that frame. Used when the class has none. | `foundries_torso_bulwark` |
| `<faction>_<component>-right_<class or frame>` | Optional right-hand version of a sided part. Without one, the left part is mirrored. | `reliquary_hand-right_goliath` |
| `item_<id>` | Equipment, ids from `data/equipment.json`. | `item_lance` |
| `item_<id>@<faction>` | A faction's version of shared equipment. | `item_jump-jets@foundries` |

Factions are `covenant`, `foundries` and `reliquary`. Frames are `scout`,
`striker`, `bulwark` and `titan`. Classes and the frame each uses are in
`data/chassis.json`.

## Components and joints

`data/model-kit.json` lists them, and the web reads the same file. A part's
origin is its joint, and it is modelled in that joint's space at rest (Z up,
facing -Y, joints keep world axes). The easiest way is to build the part in
place on the walker and then call `kit.skeleton.to_joint(root, faction, frame, component)`.

| Component | Joint | Sided | Required | Package |
| --- | --- | --- | --- | --- |
| base | root | | | 9 or 10 |
| pelvis | pelvis | | yes | 2 (waist and hip armour) |
| torso | spine | | yes | 2 |
| back | chest | | | 6 (spires, stacks) |
| cloth | chest | | | 7 |
| collar | neck | | | 3 |
| helm | head | | yes | 1 |
| crown | head | | | 6 (halos) |
| pauldron | shoulder | yes | | 3 |
| arm | shoulder | yes | yes | 4 (upper arm) |
| forearm | elbow | yes | yes | 4 |
| hand | wrist | yes | yes | 4 |
| thigh | hip | yes | yes | 5 |
| shin | knee | yes | yes | 5 |
| foot | ankle | yes | yes | 5 |

Sided parts are modelled for the walker's **left, +X**.

The web uses a class's kit body only once every required component has a
part, and falls back to the procedural chassis until then, so packages can
merge in any order without players seeing a half-built walker. To see a kit
body with gaps (stand-ins fill them), open
`render.html?chassis=paladin&kit=force`. To see one part on its own, open
`render.html?part=covenant_helm_titan`.

## Frames

`kit.skeleton.Skeleton(faction, frame)` gives joint positions without
building anything: `sk.joint("elbow", "L")`, `sk.length("shoulder", "elbow")`,
`sk.radius("forearm")` (the stand-in's girth, a guide) and `sk.H` (nominal
height). Faction proportions scale the frames: Reliquary limbs are 20% longer
and thinner, Foundries frames 15% squatter and wider.

Each frame has spare mounts, more than any class needs: 3 per arm, 4 core, 2
legs. Mount positions: arm 0 at the wrist, arm 1 on the forearm, arm 2 on the
shoulder; core 0 and 1 high on the chest, left and right, core 2 on the back
(facing backwards), core 3 on the chest front; legs 0 and 1 on the outer
thighs. Items snap to them as before and are scaled ×1, ×1.2, ×1.4, ×1.7 by
frame.

## Materials

`kit.materials.get(faction, role)`, or `library(faction)` for all of them.

| Role | Covenant | Foundries | Reliquary |
| --- | --- | --- | --- |
| armour | blackened iron | rust-blotched iron plate | bone-white ceramic, crazed glaze |
| trim | aged gold | oxidised brass | pale gold |
| filigree | iron with raised gold scrollwork | plate with raised tread | ceramic with gold ring glyphs |
| metal | dark steel | greasy dark iron | dark teal-black metal |
| hull (paintable) | crimson enamel over iron | red enamel over iron | teal enamel over metal |
| cloth (paintable) | crimson cloth | red tarp | grey-white shroud |
| glow | amber | furnace orange | teal |
| stencil (fixed colour) | crimson enamel with a sprayed 07 | red enamel with a sprayed 07 | teal enamel with a sprayed 07 |

All materials share wear masks in world millimetres (chipped edges, grime in
recesses, dust on upward faces), so a 4 mm helm and a 20 mm torso age alike.
Relief roles read the `Decal` UV map; shapes lay it out, `shapes.decal_uv(ob, tile_mm)`
re-projects it. `hull*` materials are recoloured by the livery: the bake sets
their `paint` node to white, and the web multiplies the livery into the baked
texture, so wear survives repainting.

Tune colours in `PALETTES` and check them with
`~/bvenv/bin/python assets/blender/test_plates.py [faction]`, which renders a
test plate in every role beside the board's swatches, before and after baking.

## Shapes

`kit.shapes`, all in millimetres, each returning the new object:

- `box_plate(name, (w, d, h), mat, bevel, panel_lines, taper)`: bevelled plates with grooves
- `cylinder`, `sphere`, `lathe(profile)`: bevelled primitives and turned shapes
- `sweep(name, pts, radius, mat, profile="round"|"square")`: trim, cables, ribs
- `pipe(name, pts, r, mat, bands, band_mat)`, `gauge`, `rivet_row`
- `spire(name, width, height, mat, trim, crockets, glow)`, `lancet(name, w, h, depth, mat, glow)`
- `boolean(ob, cutter)`: a live boolean; the cutter is dropped at bake time
- `Shell(ob, centre)`: lay armour on a curved surface by azimuth (0 = front, positive to +X) and elevation:
  `patch` (a plate with trim, a filigree inlay and a flared lip), `lames` (stacked overlapping bands),
  `trim`, `flutes` and `studs`. This is the helm proof of concept's method.

## A part script

```python
import sys; from pathlib import Path
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # assets/blender
import kit
from kit import shapes

kit.reset_scene()
m = kit.materials.library("covenant")
sk = kit.skeleton.Skeleton("covenant", "titan")
root = kit.empty("covenant_forearm_titan")
el, wr = sk.joint("elbow"), sk.joint("wrist")
r = sk.radius("forearm")
shapes.cylinder("vambrace", r * 1.2, (wr - el).length, m["armour"], loc=(el + wr) / 2, parent=root) \
    .rotation_euler = (wr - el).to_track_quat("Z", "Y").to_euler()
kit.skeleton.to_joint(root, "covenant", "titan", "forearm")
kit.publish(root, source=Path(__file__).with_suffix(".blend"))
```

Keep each package's scripts and `.blend` sources in `assets/blender/parts/<package>/`.

## Budgets

1024 px texture sets per part by default (`publish(root, size=...)`); aim
for under 4 MB per class once compressed. Raised trim, crests and spires are
geometry and print; filigree lives only in the textures, so the STL stays
printable. Keep walls at least 1 mm thick at Scout scale.
