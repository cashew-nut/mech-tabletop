# Goliath concept art (Reliquary titan, 2026-11-07)

Gate B: three hero rolls, waiting for Luke to pick one (or ask for another roll). No 3D credits spent, no turnaround yet.

Made with Meshy image-to-image (nano-banana, 3 credits each, 9 in all, balance 97 to 88) from `docs/style-bible/reliquary.md`
through `tools/meshy/prompts.py goliath hero --variant 0|1|2`. References: the Reliquary hero, Goliath and Seer tiles from
`three-factions-board.png` and a crop of the approved Seer render. Originals and `source.json` per task are in the project folder
`meshy-sources/goliath/hero/`; ledger rows are in `meshy-sources/ledger.json`.

| File | What |
| --- | --- |
| `rolls.jpg` | the three rolls side by side |
| `hero-roll1.jpg` | stocky and hunched, teal reliquary-cage chest, two spires, hanging lanterns, arc cannon left, spear right |
| `hero-roll2.jpg` | the closest to the board hero: thin, a long glaive, moonlit. Least printable limbs |
| `hero-roll3.jpg` | symmetrical, big wing spars, hooded, hooked lantern staff, heavy arc cannon on the right |

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

**Recommendation: roll 1.** Chunkiest limbs, deepest chest, the spires and lanterns give the back and card art plenty to read, and
the teal cage makes a clear core. Roll 3 is a close second and the easiest to model symmetrically.

**Known risks for the 3D step.** Hanging chains and cloth tatters will not survive Meshy or printing (drop them or fuse them to
plate, as with the Sentinel banner). The halo crown is a thin ring and needs a thick printed rim and a peg through the hood.
Spires and wing spars are fragile and should be separate pegged parts.

**Next after approval.** Turnaround and part sheet (6 credits), then mesh (20) and retexture (10): about 36 more credits, balance
88 to about 52. Nothing 3D runs until approval.
