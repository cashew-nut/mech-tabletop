# Goliath composite parts (Reliquary titan, 2026-11-07)

The Goliath Meshy model (`meshy-sources/goliath/model/`, mesh `01a1b610...`, textured `01a1b612...`) cut into 12 closed parts by the
shared composite pipeline (`MODEL=goliath`, settings in `assets/blender/parts/composite/goliath.py`). Printed at Luke's 1.5x scale:
75 mm to the hood top, about 93 mm to the spire tips. Parts, STLs, game GLBs and the .blend are in the project folder
`models/goliath-composite/`; renders in `renders/goliath-composite/` (JPEG copies here). Not in the game yet.

| File | What |
| --- | --- |
| `assembled.jpg` | front, three-quarter, side and back, textured |
| `exploded.jpg` | every part pulled apart, front and back |
| `parts.jpg` | each part alone |
| `pose.jpg` | posed by rotating joints (Arc Cannon raised, legs striding) |

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

## Not done yet

Game publish (`publish-composite.mjs`, a `reliquary/titan` frame tune and fit class), `parts.json` rows and card faces for the six Goliath
body cards, the Arc Cannon item model for the game, and a Soul Lantern staff if one is wanted (it would be a new model).
