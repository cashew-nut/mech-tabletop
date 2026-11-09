# Goliath composite parts (Reliquary titan, 2026-11-07)

The Goliath Meshy model (`meshy-sources/goliath/model/`, mesh `01a1b610...`, textured `01a1b612...`) cut into 12 closed parts by the
shared composite pipeline (`MODEL=goliath`, settings in `assets/blender/parts/composite/goliath.py`). Printed at Luke's 1.5x scale:
75 mm to the hood top, about 93 mm to the spire tips. Parts, STLs, game GLBs and the .blend are in the project folder
`models/goliath-composite/`; renders in `renders/goliath-composite/` (JPEG copies here). In the game (see below).

| File | What |
| --- | --- |
| `assembled.jpg` | front, three-quarter, side and back, textured |
| `exploded.jpg` | every part pulled apart, front and back |
| `parts.jpg` | each part alone |
| `pose.jpg` | posed by rotating joints (Arc Cannon raised, legs striding) |
| `items-preview.jpg` | the Seer's kinetic claws and arc spear on the Goliath's wrist in place of the hand (preview only) |

`docs/concept-art/goliath/mesh-vs-turnaround.jpg` is the silhouette check (gate D): the Meshy mesh matched the turnaround in all three views.

## The parts

Pelvis (with the central banner), torso (the reliquary cage), hood, **back** (two spires, the halo ring and the pack: the halo
grows from the spires in the mesh, so it is one part with them), and the left-hand set, mirrored for the right: wing pauldron, upper arm,
forearm, **claw hand**, thigh, shin, foot. The twelfth part is the
**Arc Cannon**: the figure's own forearm, re-seated on the forearm socket like the Sentinel's gun, so it fits either elbow. Every part is
one closed solid (report.json).

The mesh was **mirrored in x once** before cutting (`mesh_orig.npz` keeps the original) so the cannon falls on the figure's right,
where the pipeline expects a gun, and the staff arm is the plain left arm.

**Revision after Luke's review (2026-11-07).** He disliked the long white blades (the staff, which came out on both hands because the hand is
mirrored), and the arm joints. The staff is gone and the hand is a designed gilded claw (a palm and four clawed fingers reaching forward;
the Meshy hand was only a 5 mm blob once the staff was cut away). The Meshy upper arm is a hollow shell, so the shell is dropped and the
upper arm is a gilded rod with two bands between the knuckles (the first fix, a core rod through the shell, showed through as gold slabs).
The shoulder ball is bigger so the shoulder peg has room for a magnet.

**Ball knuckles.** The Reliquary limbs are gaunt (5 to 7 mm at print scale). Following the Seer, every limb joint (neck, shoulder, elbow,
wrist, hip, knee, ankle) has a designed gold ball knuckle in a gilded sleeve, added to the figure before the cut. A first pass at full size
looked like gold top hats, so they are 80% of that.

| Joint | Peg radius | Peg length | Magnet |
| --- | --- | --- | --- |
| thigh into pelvis | 2.2 mm | 2.6 mm | 3 x 2 |
| torso / pelvis | 3.0 | 2.6 | 3 x 2 |
| hood into torso | 1.75 | 3.5 | 2 x 1 |
| back / torso | 3.0 | 3.5 | 3 x 2 |
| pauldron into torso | 1.75 | 3.5 | 2 x 1 |
| arm / torso (shoulder) | 1.75 | 1.5 | 2 x 1 |
| forearm / arm, Arc Cannon / arm | 1.75 | 3.5 | 2 x 1 |
| hand / forearm | 1.75 | 2.6 | 2 x 1 |
| shin into thigh, foot / shin | 2.0 | 2.2 | 2 x 1 |

All pass the strict checks (hole walls inside the part, no break-outs, mirrored side clear).

## Cannon pose and wrist items (2026-11-07, Luke: "gun looks weird, how would the claw or spear fit")

- **Cannon.** The assembled view showed the cannon hanging straight down beside the leg, because the parts are cut with the arm
  hanging. It is now shown held level and forward, as in the concept art (`HOLD` in goliath.py, used by render.py). It is a render pose: the
  gun sits on the elbow's ball knuckle, so the elbow can be turned that way on the table.
- **Claws and spear.** The hand plugs into the forearm at the wrist knuckle (1.75 mm peg, 2 x 1 magnet). Wrist items take the hand's place on
  that same socket, as on the Seer (`seer_wrist.py`): each carries a copy of the hand's half ball and peg and continues the arm.
  `items-preview.jpg` shows the Seer's kinetic claws and arc spear, scaled 1.25x, on the Goliath's wrist.
  **That is a preview only**: they are the Seer's STLs with the Seer's peg, not yet rebuilt with the Goliath hand's peg, and the game has
  no Goliath hardpoints yet (`goliath_items_preview.py` makes the picture).

## Things to know

- **Shoulders are still chunky.** The shoulder knuckle is a gold ball in a barrel sleeve, bigger than the other joints so the peg can take a magnet (a smaller one gave a 1 mm peg with a 1 x 1 magnet). The joint is fine; the look is heavier than the concept.
- **Dropped from the mesh.** The tattered cloth, chains and small lanterns on the wing spars and cannon (about 6 floating bits) are gone, as
  planned in the design note. The central banner stays on the pelvis.
- **Thin parts.** The hood is 6 mm wide (68 mm3), the wing pauldron is a 23 mm blade 8 mm deep, and the claw fingers are 1.3 to 1.6 mm thick
  at the base. They are closed solids but fragile; they will need a test print.
- **Not cut.** There is no staff item any more, and the shoulder plate itself is part of the torso: the Meshy mesh has no separate plate
  under the wing spar.
- **Colour.** The retexture came out pale bone with gold only on the knuckles; the concept art has more aged gold on the limbs. A recolour
  pass (as for the Artillery) would fix it.
- **Not test-printed.** Magnet pockets are 0.1 mm over stock size, as on the other walkers.

## In the game (2026-11-07)

`node scripts/publish-composite.mjs DIR/glb goliath` published 11 kit parts, its own frame (`reliquary_frame_goliath`) and the Arc Cannon
(`item_arc-cannon@goliath`, the re-seated gun forearm on the elbow socket), 3.7 MB compressed. Data is in `data/model-kit.json`:
`frameTunes["reliquary/goliath"]`, `omit.goliath` (cloth, collar), `fit.classes.goliath`, the Arc Cannon class fit, `fit.overrides.goliath`.
`fit-check.mjs goliath` shows 0 flagged over 21 placements; `npm test` passes. Render: `in-game.jpg`.

**Borrowed from the Seer:** `fit.itemModels.goliath = ["seer"]`, so the Kinetic Claws, Spear and the like use the Seer's models on the
Goliath wrist socket. They fit but are not built for the Goliath hand's peg, so they are not magnet-exact for printing.

## Polish pass (2026-11-09)

Luke asked for each Meshy walker to be fine-tuned against its Meshy first pass (the concept, turnaround and part sheet in
`docs/concept-art/goliath/`). The Goliath's rough edges, and what changed:

| File | What |
| --- | --- |
| `polish-assembled-before-after.jpg` | the assembled walker, before and after |
| `polish-game-before-after.jpg` | in the game (reliquary backdrop, showcase loadout), before and after, three angles |
| `polish-vs-concept.jpg` | the approved hero art beside the polished model |
| `polish-parts.jpg`, `polish-exploded.jpg`, `polish-pose.jpg` | each part alone, pulled apart, and posed |

- **Colour.** The retexture was pale bone everywhere; the concept is aged gold and bronze over black, with bone only on the hood,
  chest plates and wings. `reliquary_grade.py` grades Meshy's texture to that (style bible palette), part by part, keeping its carving.
- **Knuckles.** The gold sleeves read as gold top hats and bloomed in the game. Every joint now uses the Seer's polished knuckle (aged
  gold ball with a seam band, deep bronze housing with gold collar and band), so the two Reliquary walkers match.
- **Upper arms and hands.** The fat gold rod is a slimmer bronze rod with three gold ribs; the claw hand has a bronze palm.
- **Light.** The chest cage and the pack's core glow teal in the game, and the hood has two teal eye slits, as in the concept.

Joints after the re-cut (all strict checks pass, every part one closed solid): thigh 2.2 mm with 3 x 2 magnet, torso and back 3.0 mm with
3 x 2, hood, pauldron, shoulder, elbow, wrist 1.75 mm with 2 x 1, knee now 2.0 mm with a 3 x 2 magnet (was 2 x 1), ankle 2.2 mm but only
1.5 mm long (was 2.0 mm, 2.2 long), 2 x 1 magnet. Game parts grew from 3.8 to 5.6 MB (ETC1S, base quality 150). Files: project folder
`models/goliath-polish/` and `renders/goliath-polish/`.

Still bulkier than the concept: the knuckle housings (they hold the pegs and magnets) are heavier than the concept's slim joints, most of all at
the shoulders and hips.

## Not done yet

`parts.json` rows and card faces for the six Goliath body cards, Goliath-specific claw and spear item models (rebuilt on the Goliath hand
peg), a Soul Lantern staff if one is wanted, and a test print of the thin parts. Not checked on a real GPU or the 3D battle board.
