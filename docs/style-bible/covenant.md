# Style bible: Iron Covenant

Status: **draft for gate A** (2026-11-04). Written from the faction boards and the approved Paladin. The machine-readable
copy is `data/style-bible.json`; `tools/meshy/prompts.py` builds every prompt from it, so edit the JSON and this page together.

Reference images (always sent with a Covenant prompt, up to five):

- `docs/concept-art/three-factions-board.png`, left column: hero shot, the Paladin, Sentinel and Lancer, the helm, hand, chest and pauldron close-ups.
- `docs/concept-art/iron-covenant-board.png`: the hero shot, helm close-up, variant B (artillery platform) and the orthographic turnaround.
- The approved Paladin (project folder `models/paladin-assembled.glb`, turnaround in `renders/meshy-paladin/assembled-vs-original.png`): the canonical 3D look.

## The feel

Cathedral knights. Noble, upright, ornate, heavy with ceremony. Black enamel plate trimmed in gold filigree, crimson
cloth, a slit visor with a warm amber glow, spires and a sunburst. Functional beauty: it looks hand-forged and blessed,
never mass-produced. A Covenant walker should read as a knight first and a machine second.

## Palette

| Role | Colour | Hex |
| --- | --- | --- |
| Main plate (black enamel) | blackened gunmetal, glossy | `#262527` |
| Trim, filigree, spires | aged gold | `#805830` (highlights up to `#c9a050`) |
| Cloth, banners, tabards, pauldron inserts | crimson | `#800d14` |
| Accent, tabards, heraldry | bone / ivory | `#d2c5bb` |
| Glow | amber furnace light, only at the visor and chest | `#ffb347` |

Black is about 70% of any walker, gold 20%, crimson 8%, bone 2%.

## Motifs

Gold filigree trim along every plate edge. Sunburst pauldrons. Cross and eagle heraldry on cloth. Tabards hanging from
the pelvis and long banners from the back. Cathedral spires and pinnacles on the back and shoulders. A glowing furnace
chest behind a gothic window. A slit visor under a pointed gothic helm. Armoured, ornamented hands.

## Silhouette

Tall and upright, broad shoulders, straight legs, a narrow waist under heavy shoulders. The Paladin is the tallest and
most elegant; the Sentinel is the same knight in a heavier, wider frame, built to stand in a doorway.

## Joints (for the print)

Armoured and broad: gauntlet cuffs, knee and elbow cops, a gorget at the neck, a belt at the waist. Every joint has a
plate collar that can hide a peg and a 3 x 2 mm magnet. No bare thin rods at joints.

## Never

Rust, stencilled numbers, exposed pipes and chains, teal, halos, hunched or low silhouettes, bare skeletal limbs.

## Prompt wording

Short phrases the prompt script uses (kept here so the page and the JSON agree):

- `feel`: cathedral knights, noble, upright and ornate
- `look`: black enamel plate with gold filigree trim and crimson cloth
- `never`: rust, stencilled numbers, exposed pipes, teal, halos, hunched poses

## Class brief: Sentinel (first walker under this bible)

Role: defence and support. Frame: bulwark (size 3, 42 kit units tall, 63 mm printed at 1.5x). Stride 2, boiler 6,
slots 1 / 1 / 4 / 1 (core slots are the highest in the faction: it is the Covenant's platform for gear).

- **Silhouette**: a gatehouse knight. Broader and lower than the Paladin, with a deep chest, big sunburst pauldrons,
  thick armoured legs and a wide stance. Slab-like shield-plates over the shoulders.
- **Weapons**: the Carapace Gun (a heavy rotary barrel on the right forearm, gilded barrel shroud and crimson ammunition drum),
  and an empty armoured left gauntlet that can carry the Targe (the Covenant tower shield).
- **Back**: a tall banner standard rising from the back, with a crimson banner and a gold cross finial, between two cathedral spires.
- **Chest**: a glowing furnace chest behind a gothic window, a gilded sunburst plate on the front, a tabard hanging from the belt.
- **Limbs**: chunky. Every limb at least 7% of the body height thick (a printed limb needs about 4 mm for the peg and magnet).

Variant B (the artillery platform on the Covenant board) shows the right hull weight and is a reference for the legs
and shoulders; its cannon and crab-like legs are not used.
