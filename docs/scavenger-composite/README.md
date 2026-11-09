# Scavenger composite parts (Ashen Foundries scout, 2026-11-09)

The Scavenger Meshy model (`meshy-sources/scavenger/model/`, mesh `01a1c03a...`, textured `01a1c03b...`) cut into 12 closed parts by the
shared composite pipeline (`MODEL=scavenger`, settings in `assets/blender/parts/composite/scavenger.py`). It is the scout frame, 28 kit mm
to the hull roof, so at Luke's 1.5x it prints about 45 mm to the hull roof and about 54 mm to the top of the exhaust. Parts, STLs, game
GLBs and the .blend are in the project folder `models/scavenger-composite/`; renders in `renders/scavenger-composite/` (JPEG copies here).
In the game (see below).

| File | What |
| --- | --- |
| `assembled.jpg` | front, three-quarter, side and back, textured |
| `exploded.jpg` | every part pulled apart, front and back |
| `parts.jpg` | each part alone |
| `pose.jpg` | posed by rotating joints (claw arm raised, legs striding) |
| `in-game.jpg` | in the game, default loadout (autocannon right, claw left), three angles |
| `in-game-loadouts.jpg` | in the game: default, rail cannon + rocket pod, twin autocannon + shield, shell arm + claw |

`docs/concept-art/scavenger/mesh-vs-turnaround.jpg` is the silhouette check (gate D).

## The parts

Pelvis, torso, **hull canopy + lens** (the low red canopy with the single eye and jaw tusks under it), **stacks + exhaust** (the vented
stacks, the rear pack and the bent exhaust), and the left-hand set, mirrored for the right: pauldron, upper arm, forearm, **salvage claw**,
thigh, **shin + hock** (the digitigrade leg's rear joint), foot. The twelfth part is the **autocannon**: the figure's own right forearm,
re-seated on the forearm socket like the Sentinel's gun, so it fits either elbow. With it fitted on the right, the right forearm and claw
are spares. Every part is one closed solid (report.json).

The loose chains under the pelvis and the gun are dropped, as planned at gate B (they would not print at this size).

**Foundries knuckles.** At 1.5x the Meshy elbows, knees and ankles are only 3 to 4 mm across, so shoulder, elbow, knee and ankle have a
designed knuckle added before the cut: a blackened iron ball split by one worn brass seam band, in an iron collar housing with a brass band
at its top. The first bake had four brass rings per joint and the knees read as striped cans, so they are down to two.

| Joint | Peg radius | Peg length | Magnet |
| --- | --- | --- | --- |
| thigh into pelvis | 2.0 mm | 3.0 mm | 3 x 2 |
| torso / pelvis (waist) | 3.0 | 1.8 | 2 x 1 |
| hull canopy into torso | 3.0 | 3.5 | 3 x 2 |
| stacks / torso | 3.0 | 3.5 | 3 x 2 |
| upper arm into torso (shoulder knuckle) | 1.5 | 1.8 | 2 x 1 |
| pauldron / upper arm | 0.85 | 1.2 | none (a press fit) |
| forearm / arm, autocannon / arm (elbow knuckle) | 1.3 | 1.8 | 2 x 1 |
| claw / forearm | 1.5 | 1.5 | 2 x 1 |
| shin into thigh (knee knuckle) | 1.3 | 1.5 | 2 x 1 |
| foot / shin (ankle knuckle) | 1.75 | 1.5 | 2 x 1 |

All pass the strict checks (hole walls inside the part, no break-outs, mirrored side clear).

**Assembly check (2026-11-09).** `assembly_check.py` (in the composite folder) puts the STLs together and checks that the parts go
together, not only that each peg fits its hole: no two parts overlap (with the claw arm and again with the autocannon), every part
slides straight off its peg (and so straight on), and every part meets its parent round the peg. The first run found two hooks: a
flange of the upper arm curled over the torso's shoulder block, and a tongue of the thigh hung down behind the shin's knuckle, so
neither the arm nor the shin could be pushed straight onto its peg. The cut there is now the knuckle's plane out to a wider radius
(`WIDE_CUT` in scavenger.py), and the check passes: 0 overlaps, all 11 joints slide on, every joint touches. The thigh comes off
cleanly over its whole 3 mm peg; pulled a further 1 mm it would brush the claw, so fit the legs before the arms.

## Finish

Meshy's retexture came out dusty: pinkish plates on a beige-grey body, all half-metal, so the walker read pale grey. The settings grade
each texel toward the Foundries bible by its Meshy colour: rust-red lacquer, orange lacquer panels, worn brass, blackened iron and cream
unit stencils, keeping 30% of Meshy's own grime. Metal and roughness come from the Brute's paint, brass and iron. The single lens eye under
the canopy glows furnace orange.

## Known limits

- **Pauldron.** Meshy's shoulder cap is a 0.6 mm sheet; an iron backing plate makes it a 1.5 mm plate, but it is still only 5 x 7 mm and
  takes a 0.85 mm peg with no magnet (a press fit; a drop of glue if it is loose).
- **Elbows and knees.** 1.3 mm pegs with 2 x 1 magnets: enough to hold, but the scout limbs leave no room for 3 x 2.
- **Chains.** Dropped; a printed chain or a wire loop could be added by hand.
- **No 3D re-roll.** The Meshy balance is 7 credits, so any further change is Blender work on this mesh.

## In the game (2026-11-09)

`node scripts/publish-composite.mjs DIR/glb scavenger` publishes the 11 kit parts as `kit/foundries_<part>_scavenger.glb`, its own frame
(`foundries_frame_scavenger`, a copy of the scout frame on the joints the parts were cut on) and two arm weapons, both whole forearms on
the elbow socket: `item_autocannon@scavenger` (the re-seated gun) and `item_industrial-claw@scavenger` (its own forearm and salvage claw
merged, so the claw arm it stands with is the same model as the item). Data in `data/model-kit.json`: `frameTunes["foundries/scavenger"]`
(shifted 1.19 mm in y so the feet stand near the hex centre), `omit.scavenger` (cloth, collar), `fit.classes.scavenger`,
`fit.overrides.scavenger` (the Artillery's), and the class fit of the autocannon, industrial claw, rail cannon and rocket pod
(`forearm-gun`, which hides the forearm and hand). The rail cannon and rocket pod borrow the Brute's models (`fit.itemModels.scavenger`).
Compressed with `KTX2_NORMAL=etc1s KTX2_BASE_Q=150` (4.3 MB in all). `fit-check.mjs scavenger` shows 0 flagged; `npm test` passes; `scripts/fit-sets.json` has four Scavenger review loadouts.
