# Scavenger concept art (Ashen Foundries scout, 2026-11-09)

Gate B: three hero rolls for the last Ashen Foundries walker. Luke picked roll 3 (2026-11-09); gates C and D and the 3D model
follow below.

Made with Meshy image-to-image (nano-banana, 3 credits each, 9 in all, balance 52 to 43) from `docs/style-bible/foundries.md`
through `tools/meshy/prompts.py scavenger hero --variant 0|1|2`. References: the Foundries hero, class and close-up strips from
`three-factions-board.png` and the approved Artillery hero (`docs/concept-art/artillery/hero-roll3.jpg`). Originals and `source.json`
per task are in the project folder `meshy-sources/scavenger/hero/`; ledger rows are in `meshy-sources/ledger.json`.

| File | What |
| --- | --- |
| `rolls.jpg` | the three rolls side by side |
| `hero-roll1.jpg` | wide canopy plate over the shoulders, twin stacks, dish, big salvage claw left, autocannon right |
| `hero-roll2.jpg` | the most symmetrical and readable head: big lens eye, hazard-striped wing plates, claw right, cannon left. Wing plates are thin and fragile |
| `hero-roll3.jpg` | **recommended.** Compact boxy hull, chunkiest legs and collars, one stack and a dish, cannon left, claw right |

## Design note

**Why the Scavenger.** The Foundries have three classes (Scavenger, Brute, Artillery). The Brute and Artillery are built; the
Scavenger is the last one, and the only Foundries class on the scout frame (42 mm printed at 1.5x).

**Brief.** A lean scrap-runner: the lightest Foundries walker, still brutal and functional. Hunched hull, thick piston
hind legs with brass collars, one glowing lens eye and a small sensor dish, patched rust-red and orange plate over blackened
iron. An industrial salvage claw on one arm and a short autocannon on the other (both swappable items later, so the default
arm is a clamp hand). Chains from the board are dropped in 3D.

**Lessons applied.** Magnetic closed parts, one faction (Never list keeps out gold, cloth, halos and teal), colours from the
bible, one item per arm, 1.5x print scale. Scout limbs must be at least 10% of height (4 mm) to carry a peg and a magnet,
so the brief says "all limbs chunky". The board's Scavenger tile is thin and spindly, so it was used as a silhouette hint only.

**Why roll 3.** Chunkiest limbs and collars, the deepest hull, and nothing thin sticking out, so it cuts into closed parts
with the fewest weak joints. Roll 2 has the strongest face but its wing plates would be fragile at 42 mm. Roll 1's canopy
is wide and would need its own peg.

**Known risks for 3D.** Hanging chains do not survive Meshy or printing. The hind legs overlap in a three-quarter view, so
the turnaround must show them apart. Small sensor dish and stack need to be pegged parts.

**Next after approval.** Turnaround and part sheet (6 credits), mesh (20), retexture (10): 36 credits, balance 43 to 7. That
leaves no room for a 3D re-roll, so the silhouette check before texturing matters.

## Gate C: turnaround and part sheet (Luke picked roll 3)

Meshy multi-view and part sheet from `hero-roll3.jpg` (3 credits each). Originals in `meshy-sources/scavenger/turnaround/` and
`meshy-sources/scavenger/partsheet/`.

| File | What |
| --- | --- |
| `turnaround-front.png`, `turnaround-side.png`, `turnaround-back.png` | the three views fed to the mesh call |
| `partsheet.jpg` | the parts laid out apart: shoulder plates, joint collars, torso with the lens, pelvis plate, legs, claw arm, autocannon |

## Gate D: mesh and silhouette check

One multi-image-to-3D call (mesh only, 20 credits) from the three turnaround views, then `tools/meshy/silhouette.py`:
`mesh-vs-turnaround.jpg` overlays the mesh on each view. The silhouette matched, so it went to one retexture (10 credits). Mesh and
textured model are in `meshy-sources/scavenger/model/`.

Credits for the Scavenger: 9 (hero rolls) + 6 (turnaround and part sheet) + 20 (mesh) + 10 (retexture) = 45, balance 7. The composite
cut is in `docs/scavenger-composite/`.
