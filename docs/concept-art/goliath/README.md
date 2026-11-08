# Goliath concept art (Reliquary titan, 2026-11-07)

Gate B done: Luke picked hero roll 3 (2026-11-07). Turnaround and part sheet made from it, and Luke said "Build it" (gate C). The 3D model is built (see below and `docs/goliath-composite/`).

Made with Meshy image-to-image (nano-banana, 3 credits each, 9 in all, balance 97 to 88) from `docs/style-bible/reliquary.md`
through `tools/meshy/prompts.py goliath hero --variant 0|1|2`. References: the Reliquary hero, Goliath and Seer tiles from
`three-factions-board.png` and a crop of the approved Seer render. Originals and `source.json` per task are in the project folder
`meshy-sources/goliath/hero/`; ledger rows are in `meshy-sources/ledger.json`.

| File | What |
| --- | --- |
| `rolls.jpg` | the three rolls side by side |
| `hero-roll1.jpg` | stocky and hunched, teal reliquary-cage chest, two spires, hanging lanterns, arc cannon left, spear right |
| `hero-roll2.jpg` | the closest to the board hero: thin, a long glaive, moonlit. Least printable limbs |
| `hero-roll3.jpg` | **picked.** Symmetrical, big wing spars, hooded, hooked lantern staff, heavy arc cannon on the right |
| `turnaround-front/side/back.png` | one multi-view task (6 credits with the part sheet), black background |
| `partsheet.jpg` | the walker taken apart: spires and wing spars, halo helm, torso cage, arms, Arc Cannon, lantern staff, legs |
| `concept-sheet.jpg` | hero, front, side, back and part sheet on one page |

## Design note for approval

**Why the Goliath.** The missing walkers are Lancer, Scavenger, Wraith and Goliath. The faction identity (`data/factions.json`)
is "frail, fast or strange walkers around one towering Goliath", so it is the Reliquary's flagship and the tallest walker in the
game (titan, 75 mm printed at 1.5x). It also gives the Reliquary a second walker and a style bible of its own.

**Lessons applied.**

- *Magnetic closed parts*: cut as closed parts with keyed pegs and 3 x 2 mm magnets on the body joints, 2 x 1 mm on limbs
  (`joints.py`, STRICT). Gold ball knuckles in gilded sleeves (the Seer's standard) are in the brief from the start, not added after.
- *One faction*: Reliquary only. Never list in the bible keeps out boxy plate, stencils, hazard stripes, rust and smokestacks.
- *Colour*: bone and aged gold plate, dark frame, teal glow only at the eye slits, cage and lanterns, a little dark crimson cloth
  (as on the Seer and the board). The Brute's iron, red plate and brass scheme is Foundries, so it is not used here.
- *One item per arm*: right forearm carries the Arc Cannon, left wrist carries the Soul Lantern staff. Both are swappable items on
  the standard wrist/elbow socket, not part of the arm. The default arms are bare clawed hands.
- *1.5x print scale*: 75 mm tall. Limbs at least 7% of body height (5 mm) so the peg and magnet fit, which is why the brief says
  "gaunt but chunky". Roll 1 and 3 are closest to that, roll 2 is the thinnest.

**Original recommendation was roll 1; Luke chose roll 3.** Chunkiest limbs, deepest chest, the spires and lanterns give the back and card art plenty to read, and
the teal cage makes a clear core. Roll 3 is a close second and the easiest to model symmetrically.

**Known risks for the 3D step.** Hanging chains and cloth tatters will not survive Meshy or printing (drop them or fuse them to
plate, as with the Sentinel banner). The halo crown is a thin ring and needs a thick printed rim and a peg through the hood.
Spires and wing spars are fragile and should be separate pegged parts.

## Gate C check (turnaround and part sheet)

Cost 6 credits, balance 88 to 82. Meshy returned back, side, front in that order (front goes first into the 3D call).

- Design is unchanged from the hero: same hood, halo, wing spars, teal cage, Arc Cannon right, hooked lantern staff left.
- Colours drifted slightly toward bronze; the hero is the colour reference and retexture can use it.
- The side view shows the cannon pointing left and the legs overlapping; the stance and spires read clearly.
- The part sheet separates the six card groups: spires and wing spars, helm with halo, torso cage, arms, legs, plus the Arc Cannon and
  lantern staff as separate items. Left and right arms appear once, not as a pair.
- Not carried into 3D: hanging chains, small lanterns and cloth tatters (they would not print or survive Meshy), the halo ring will be
  thickened, and the wing spars and spires are cut as their own pegged parts.
- Legs are the thinnest part. The cut map plans ball knuckles at hip, knee and ankle and checks the 7% limb rule on the mesh.

**Next after approval.** Turnaround and part sheet (6 credits), then mesh (20) and retexture (10): about 36 more credits, balance
88 to about 52. Nothing 3D runs until approval.

## 3D model (2026-11-07)

One whole-body model from the three views (front first): mesh only (multi-image-to-3d, 20 credits, 2.2M triangles), silhouette checked
against the turnaround (`mesh-vs-turnaround.jpg`: wing spars, spires, halo, cannon, staff and stance all match), then retexture from the
same three views (meshy-7, 10 credits). Files: project folder `meshy-sources/goliath/model/` (mesh task `01a1b610...`, textured `01a1b612...`).
Total for the Goliath: 45 credits (15 for the 2D art, 30 for the model), balance 52. The composite cut is in `docs/goliath-composite/`.
