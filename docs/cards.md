# Collectible cards: the Paladin milestone

First milestone of the collectible plan: every class splits into body part cards, and the Paladin's parts and four of its items are printable as 63 x 88 mm cards. Packs, accounts, payments, tier balance and rules-engine changes are not part of this.

## Body part cards (`data/parts.json`)

Each class in `chassis.json` splits into six parts: **legs, torso + pelvis, helm, pauldrons, arms, crown / back**. The parts' stats add up to the class's stats exactly, so the nine classes are the starter builds. `packages/rules/test/parts.test.ts` fails if they drift.

| Stat | Lives on |
| --- | --- |
| stride, `armour.legs`, `slots.legs` | legs |
| `slots.core`, `structure.core` | torso |
| `boiler` | crown / back |
| `slots.armLeft`, `slots.armRight`, `structure.other` | arms |
| `armour.coreFront` | torso 60%, helm 20%, pauldrons 20% |
| `armour.coreRear` | torso 50%, crown / back 50% |
| `armour.arm` | arms 60%, pauldrons 40% |
| `points` | spread 25/30/10/10/15/10 across the parts in the order above, at least 1 each when the class has 6 or more points |

`frameSize` (the class's `size`: 1 scout, 2 striker, 3 bulwark, 4 titan) is the same on all six parts and is checked for equality, not summed. `structure.other` is a per-location value in the rules; here it sits on the arms card only, so a future build that swaps legs does not change it. That is a placeholder choice.

`scripts/seed-parts.mjs` made the first split. Do not rerun it once numbers are tuned by hand.

## Card records (`data/cards.json`)

| Field | Meaning |
| --- | --- |
| `printId` | Prints on the card: faction code, class, slot, tier, e.g. `CV-PAL-LEG-T3`. Equipment: `CV-EQ-LANCE-T1`. Account-linked instance ids come later. |
| `kind` | `body` or `equipment` |
| `partId` / `itemId` | The part in `parts.json` or the item in `equipment.json` |
| `faction`, `frame`, `frameSize` | Equipment has no frame, so those two are `null`. Shared gear prints with the Covenant art. |
| `tier` | 1 Stamped, 2 Riveted, 3 Guild-forged, 4 Masterwork, 5 Legendary Relic (`tiers`) |
| `stats` | Same shape as the part's stats (equipment: the `equipment.json` fields) |
| `statsPlaceholder` | `true` for tiers 2 to 5 |
| `printRun` | Relics only; placeholder number for the numbered run |
| `art` | File in `cards/art/` |

Three example parts, Paladin legs, torso and arms, exist at all five tiers. Tier 1 equals the part. Tiers 2 to 5 add 1 to the primary stat and 1 point per step; this is only so the cards differ, not balance. The other three Paladin parts and four items (Siege Blade, Carapace Gun, Gyro Stabilisers, Targeting Array) exist at tier 1. Gyro Stabilisers and Targeting Array are card-only items (no model), so their art is kept as rendered and the art script no longer redraws it.

## Art, faces and the sheet

```sh
node scripts/render-card-art.mjs            # cards/art/*.jpg from the kit and item GLBs, no Meshy
node scripts/build-card-sheet.mjs [facesDir] # cards/sheet.html, cards/paladin-cards.pdf, optional PNG faces at 300 dpi
```

`render-card-art.mjs` uses the headless renderer (`apps/web/render.html`) with options in `preview.ts`: `show=` picks the named kit components, `side=L` keeps one side, `solo=1` drops everything else, and `plain=1` drops the floor and skyline. Since the Paladin became closed composite parts (`assets/blender/parts/composite`, published into the game), each body card shows its own parts alone, with the pegs where they plug in. Without `solo=1` the rest of the body is dimmed instead (`dim=`). The art is framed by the shown parts' bounding box, so tall parts (torso with its banner, arm) sit a little left of centre.

The PDF is A4, nine cards per page with crop marks. Cards have no bleed yet; print at 100%.
