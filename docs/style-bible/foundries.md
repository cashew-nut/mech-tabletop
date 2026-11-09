# Style bible: Ashen Foundries

Status: **draft for gate A** (2026-11-04). Written from the faction board's Foundries column and the approved Brute.
The machine-readable copy is `data/style-bible.json`; `tools/meshy/prompts.py` builds every prompt from it, so edit the
JSON and this page together.

Reference images (up to five go with every Foundries prompt):

- `docs/concept-art/three-factions-board.png`, middle column: hero shot, the Brute, Artillery and Scavenger tiles, close-ups.
- The approved Brute (project folder `renders/meshy-brute/`, GLB in `models/brute-viewer/brute.glb`): the canonical 3D look.

## The feel

Industrial warbands. Brutal, hunched and functional, mass-produced and soot-stained. Plate is welded, patched and
painted in a hurry, then stencilled with a unit number. It looks built to win, not to inspire: a Foundries walker should
read as a machine first, never a knight.

## Palette

| Role | Colour | Hex |
| --- | --- | --- |
| Main plate (rust red lacquer) | | `#8d2912` |
| Panels, hazard edges | orange lacquer | `#be6a35` |
| Frame, guns, undercarriage | blackened iron | `#34322f` |
| Fittings, collars, sleeves | worn brass | `#6e4d2f` |
| Glow | orange furnace light from vents and cores | |

## Motifs

Riveted hull plates with stencilled white unit numbers. Hazard stripes on plate edges. Twin smokestacks. Glowing furnace
cores behind grilles. Hydraulic pistons, ammunition belts and chains, welded patch plates, exposed pipes.

## Silhouette

Low, wide and hunched, with heavy forearms and guns and big boxy shoulders.

## Joints (for the print)

Chunky riveted collars and brass-sleeved hydraulic pistons, thick ball-and-socket hips and shoulders. Every joint has a
collar that can hide a peg and a 3 x 2 mm magnet.

## Never

Gold filigree, cloth banners, tabards, halos, cathedral spires, teal, thin skeletal limbs, upright elegant poses.

## Class brief: Artillery (first Foundries walker under this bible)

Role: long range. Frame: bulwark (size 3, 63 mm printed at 1.5x). Stride 1, boiler 7, slots 3 / 3 / 2 / 1.

- **Silhouette**: a walking gun platform. Squat hull much wider than tall, deep boxy torso, short thick legs set wide for
  the recoil, a small armoured head sunk between heavy shoulders. Distinct from the Brute by its gun-over-shoulder profile.
- **Weapon**: a very long howitzer (riveted tube, recoil sleeve, muzzle brake) slung over the right shoulder on a gimbal
  cradle, and a heavy clamp hand on each arm, the left carrying an artillery shell.
- **Back**: the howitzer cradle, a belt-fed ammunition drum and two smokestacks.
- **Limbs**: chunky, at least 7% of the body height.

## Class brief: Scavenger (last Foundries walker, 2026-11-09)

Role: utility and recon. Frame: scout (size 1, 42 mm printed at 1.5x). Stride 3, boiler 4, slots 1 / 1 / 2 / 1.

- **Silhouette**: a lean scrap-runner. Hunched forward hull, long digitigrade hind legs of thick hydraulic pistons with brass
  collars and wide clamp feet, a low wide head with one glowing lens eye and a small sensor dish, patched welded scrap plate.
  The lightest Foundries walker but still a machine, never a knight.
- **Weapons**: an industrial salvage claw on one arm and a short autocannon on the other, one item per arm.
- **Back**: a bundle of welded scrap plates, one short smokestack and a folded radar mast. No hanging chains.
- **Limbs**: chunky, at least 10% of the body height (scout frame).
