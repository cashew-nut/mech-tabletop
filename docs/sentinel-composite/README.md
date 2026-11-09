# Sentinel composite parts (gate E, 2026-11-04)

The Sentinel Meshy model (`meshy-sources/sentinel/model/`) cut into 12 closed parts by the shared composite pipeline
(`MODEL=sentinel`, settings in `assets/blender/parts/composite/sentinel.py`). Printed at Luke's 1.5x scale: about 67 mm to
the helm top, 79 mm to the spire tips. Parts, STLs, game GLBs and the .blend are in the project folder
`models/sentinel-polish/` (the polished build, 2026-11-09; the first cut is in `models/sentinel-composite/`); renders in
`renders/sentinel-polish/` (JPEG copies here).

| File | What |
| --- | --- |
| `assembled.jpg` | front, three-quarter, side and back, textured |
| `exploded.jpg` | every part pulled apart, front and back |
| `parts.jpg` | each part alone |
| `pose.jpg` | posed by rotating joints (left arm raised, head turned, legs striding) |
| `polish-assembled-before-after.jpg` | the polish pass (2026-11-09): Blender renders, before on top |
| `polish-game-before-after.jpg` | the same in the game, before on top |

## The parts

Pelvis (with the tabard), torso (with the gorget), helm, back (two spires and the pack), and the left-hand set, mirrored for
the right: pauldron, upper arm, forearm, gauntlet, thigh, greave, sabaton. The twelfth part is the **Carapace Gun**: the figure's
right forearm is the gun, so it is cut from the right, mirrored and re-seated on the forearm's socket (the Brute's gatling
trick), so it fits either elbow in place of forearm and gauntlet. It keeps the level pose Meshy sculpted (see the polish pass
below). Every part is one closed solid (report.json).

| Joint | Peg across | Magnet |
| --- | --- | --- |
| thigh into pelvis | 4.4 mm | 3 x 2 |
| torso / pelvis | 6.0 mm | 2 x 1 |
| helm into torso | 5.5 mm | 3 x 2 |
| back (spires) / torso | 6.0 mm | 2 x 1 |
| pauldron into torso | 5.0 mm | 3 x 2 |
| arm / pauldron | 4.0 mm | 2 x 1 |
| forearm / arm | 2.0 mm | 1 x 1 |
| gun / arm (same socket) | 2.0 mm | 1 x 1 |
| gauntlet into forearm | 3.0 mm | none |
| greave into thigh | 3.5 mm | 2 x 1 |
| sabaton / greave | 2.6 mm | 2 x 1 |

All pass the strict checks (hole walls inside the part, no break-outs, mirrored side clear).

## Things to know

- **Mesh repair.** Meshy's mesh had 160 open edges and 14 three-way edges, so manifold3d refused it. `repair_mesh.py` drops the
  faulty faces and fan-fills the holes (76 faces net). Run it after `cut.py extract`, before `split.py`.
- **Weak joints.** The elbow (forearm, gun) has only a 2 mm peg with a 1 x 1 magnet because the upper arm is a small part (7 x 7 x 10 mm).
  The gauntlet has no magnet. A knuckle (as on the Seer) would fix both.
- **Helm.** The Meshy helm is a thin hood, so the helm part is only 273 mm3.
- **Missing from the model.** The banner pole and flag (and the part sheet's pennants on the spires) did not come out of
  Meshy (too thin). Add them by hand if wanted.

## Polish pass (2026-11-09)

Luke asked for each Meshy walker to be gone over by eye against its concept art and Meshy's part sheets. For the Sentinel:

- **The gun is level.** The re-seat used to turn the Carapace Gun 66 degrees onto the forearm's line, so it hung barrel-down
  to the ground (in Blender and in the game). It now keeps the pose Meshy sculpted, level and pointing forward as in the
  concept, on the same elbow socket (2 mm peg, 1 x 1 magnet). It still pulls straight off its peg, and it clears the thigh.
- **Covenant colours.** Meshy's retexture came out dusty: khaki trim at roughness 0.63, brick-pink cloth, warm grey-brown
  plate. The concept, the part sheets and the Paladin are black enamel, bright worn gold and crimson, so the textures are
  graded to the Paladin's baked values before the bake (gold, red and dark plate each keep their own shading and wear).
- **Eyes and furnace light.** The concept's amber eyes and lit chest grille were painted by Meshy as cream texels, so they
  read as pale paint. They now glow amber (emissive maps on the helm and torso, strength 3 like the Brute's furnace),
  and the game's bloom picks them up.

Nothing moved at the joints except the gun's pose; every part is still one closed solid and passes the strict checks.
Outputs: project folder `models/sentinel-polish/` (glb, stl, the .blend, report.json); the pre-polish build stays in
`models/sentinel-composite/`.

## In the game

Published (`node scripts/publish-composite.mjs models/sentinel-polish/glb sentinel`, then `compress-parts.mjs` with
`KTX2_NORMAL=etc1s KTX2_BASE_Q=150`): the eleven body parts as `kit/covenant_<part>_sentinel.glb` (left side only, the web
mirrors the right) and the class frame `covenant_frame_sentinel.glb`, 3.6 MB in all. `data/model-kit.json` has the Sentinel's
joints (`frameTunes["covenant/sentinel"]`, shifted 5.5 mm in y so the feet stand near the hex centre), `omit.sentinel`
(collar, cloth) and a `fit` class with the Paladin's overrides. `game.jpg` is the in-game render.
The script strips the ".002" Blender suffix that every node in `covenant_frame_bulwark` carried (its joints were not found).

The Carapace Gun forearm is published as `item_carapace-gun@sentinel.glb` and hangs on the right elbow in place of the
forearm and hand (`fit.items.carapace-gun.classes.sentinel`); `scripts/fit-check.mjs sentinel` flags nothing (2026-11-09).
Card faces and `parts.json` rows were already in the repo (the Sentinel cards exist); their art is still the old render.
- **Not test-printed.** Magnet pockets are 0.1 mm over stock size, as on the other walkers.
