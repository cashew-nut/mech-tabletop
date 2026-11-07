# Artillery composite parts (Ashen Foundries, 2026-11-04)

The Artillery Meshy model (`meshy-sources/artillery/model/`, mesh `01a1a802...`, textured `01a1a804...`) cut into 11 closed parts by
the shared composite pipeline (`MODEL=artillery`, settings in `assets/blender/parts/composite/artillery.py`). Printed at Luke's 1.5x
scale: about 78 mm to the smokestack tops, 80 mm from the muzzle to the pack. Parts, STLs, game GLBs and the .blend are in the
project folder `models/artillery-composite/`; renders in `renders/artillery-composite/` (JPEG copies here).

| File | What |
| --- | --- |
| `assembled.jpg` | front, three-quarter, side and back, textured |
| `exploded.jpg` | every part pulled apart, front and back |
| `parts.jpg` | each part alone |
| `pose.jpg` | posed by rotating joints |
| `game.jpg` | in the game (Foundries paint, showcase loadout of autocannons) |

## The parts

Pelvis, **torso with the howitzer** (cradle and barrel are one solid with it), a **cupola** (the head: the mesh has none, so the
armoured dome on the roof stands in), **stacks and ammo pack** (the two smokestacks, the rear drums and the roof plates), and the
left-hand set, mirrored for the right: pauldron, upper arm, shell arm, clamp with its shell, thigh, shin, foot. Every part is one
closed solid (report.json).

| Joint | Peg across | Magnet |
| --- | --- | --- |
| thigh into pelvis | 6.0 mm | 3 x 2 |
| torso / pelvis | 6.0 mm | 3 x 2 |
| back / torso | 4.0 mm | 3 x 2 |
| cupola / back | 2.3 mm | 1 x 1 |
| pauldron into torso | 5.5 mm | 3 x 2 |
| arm / pauldron | 6.0 mm | 3 x 2 |
| forearm / arm | 5.0 mm | 3 x 2 |
| clamp / forearm | 5.0 mm | 3 x 2 |
| shin into thigh | 6.0 mm | 2 x 1 |
| foot / shin | 5.0 mm | 3 x 2 |

All pass the strict checks (hole walls inside the part, no break-outs, mirrored side clear).

## Things to know

- **Third leg dropped.** Meshy read the three-quarter "side" view as a third, rear leg. The cut keeps the two front legs
  (left cut, mirrored for the right); the rear pelvis carries a flat cap where the third hip was.
- **Colour (recoloured 2026-11-07).** The Meshy retexture came out ochre and brown, nothing like the Brute. The base-colour textures are
  now recoloured to the Brute's scheme (blackened iron, red lacquer plate, worn brass; `tools/recolour/foundry_palette.py`, run per part
  by `scripts/recolour-foundry-parts.mjs`) and the game's livery shader repaints the red as on the Brute (`colour-before-after.jpg`: top
  row before with the Brute at right, bottom row after). Recoloured GLBs are in the project folder `models/artillery-composite/glb-brute-palette/`;
  `glb/` still has the original brown bake. Plate versus brass versus iron is picked by brightness and warmth of the Meshy bake, not by
  part, so a few panels land differently from the concept art.
- **Weak joints.** The back is a 4 mm peg under the stacks and pack, and the cupola has a 2.3 mm peg with a 1 x 1 magnet: both
  are the least that fit. The 80 mm howitzer overhangs the torso's front by 37 mm and is the likeliest part to droop.
- **Right arm not cut.** The figure's own right arm is a heavy autocannon-like block hanging from the elbow. It is not a part (the
  mirrored left arm stands in); cutting it as a swappable weapon forearm, as for the Sentinel's gun, is a follow-up.
- **Not test-printed.** Magnet pockets are 0.1 mm over stock size, as on the other walkers.

## In the game

Published with `node scripts/publish-composite.mjs models/artillery-composite/glb artillery`, then `compress-parts.mjs` with
`KTX2_NORMAL=etc1s KTX2_BASE_Q=150`: the eleven body parts as `kit/foundries_<part>_artillery.glb` (left side only, the web mirrors the
right) and the class frame `foundries_frame_artillery.glb` (a copy of the Foundries bulwark frame), 3.6 MB in all.
`data/model-kit.json` has `frameTunes["foundries/artillery"]` (joints shifted 4.35 mm in y), `omit.artillery` and a `fit` class with
the Sentinel's overrides. 
## Shell arm as a weapon (2026-11-07)

The shell arm (forearm and clamp with its shell) is no longer a body part: it is the **Shell Arm** weapon, an optional item on the
elbow socket, and every other arm weapon sits on the same socket in its place (`shell-arm.jpg`: shells on both arms, a gun and a
shell, two guns, empty arms). An Artillery arm holds one item (`armItemLimit: 1`), so a gun no longer hangs from a shell.

- The shell arm item is built from the recoloured parts (`models/artillery-composite/glb-brute-palette/`). `forearm` and `hand` leave the kit (`omit.artillery` in `data/model-kit.json`; `foundries_forearm_artillery` and
  `foundries_hand_artillery` are gone) and come back as one item, `item_shell-arm@artillery.glb` (merged by
  `node scripts/publish-composite.mjs models/artillery-composite/glb-brute-palette artillery --items`, then `compress-parts.mjs`), origin on the elbow.
  The printed parts are unchanged: forearm and clamp are still two parts with a 5 mm peg between them.
- The Artillery borrows the Brute's gun forearms (`fit.itemModels.artillery = ["brute"]`: `item_autocannon@brute` and the other three), seated on
  the elbow at 1.3x, turned level and a little inward by a placement row (`fit.placements.artillery["forearm-gun"]`). These are the Brute's
  models and textures (the Artillery is now in the Brute's colours too); no Artillery-specific gun forearms exist yet.
- The Shell Arm is Artillery-only gear (`chassis` in `data/equipment.json`), 6 points, a first-pass stat line that has not been simulated.
- Not changed: the Artillery's body card art (`AF-ART-ARM-T1`) and the printable parts.
