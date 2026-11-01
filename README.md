# Brass Charter

A turn-based war-walker skirmish game. Three factions, the Iron Covenant, the Ashen Foundries
and the Reliquary, settle disputes over worlds by Charter Trial, fielding lances of 3 to 5
custom-built, steam-powered war-walkers on a 100-point budget. Every build trades points, slots and boiler Pressure against each other.

The first target is a browser game against an AI opponent, used to playtest the rules. The
rules are written to work on a physical tabletop too.

## Status

Phase 7 of the plan: polish. Rules are at v0.5; see the [balance report](docs/balance.md).

| Path | What it is |
| --- | --- |
| [`docs/rules.md`](docs/rules.md) | Core rules v0.5 |
| [`data/`](data) | Factions, classes (chassis), equipment, Driver traits, scenarios and example lances as JSON. The source of truth for the engine, builder, AI and simulator. |
| [`packages/rules`](packages/rules) | TypeScript rules engine: `createGame`, `applyAction`, `legalActions`, `previewAttack`. Pure and deterministic (seeded dice), so the browser game, AI and simulator can share it. |
| [`apps/web`](apps/web) | Browser app with three tabs. **Lance Ledger** builds lances (points, Pressure, armour and expected damage live; save, export, import) and shows each war-walker as a paintable 3D model with STL and GLB export. **Unit Cards** prints the lance as cards with tick boxes for armour, ammo and Overpressure. **Charter Trial** plays a battle on a hex map against the AI, with alternating deployment and all four scenarios. |
| [`packages/ai`](packages/ai) | Greedy utility AI: `chooseAction(state)` and `playOut(state)` for AI-vs-AI games. |
| [`tools/sim`](tools/sim) | Balance simulator: `npm run sim -- 600 1` plays AI-vs-AI Trials and reports win rates by lance, faction, faction matchup, class, item and trait. |
| [`assets/blender`](assets/blender) | Blender scripts: a starter parts file, part export to the web builder, and lance-to-STL assembly. |
| [`scripts/render-walkers.mjs`](scripts/render-walkers.mjs) | `npm run render -- renders` saves preview images of each class with a showcase loadout, using headless Chromium (needs Playwright installed globally). |
| [`docs/cards.md`](docs/cards.md) | Collectible cards: `data/parts.json` splits each class into six body part cards, `data/cards.json` holds the printable card records, `cards/` has the Paladin art and the 63 x 88 mm sheet. |
| [`scripts/validate-data.mjs`](scripts/validate-data.mjs) | Checks the data and that every example lance is legal. |

```sh
npm install
npm run check   # validate data, typecheck, run tests
npm run dev     # the game at http://localhost:5173
```

## Roadmap

1. Rules and data (done)
2. Rules engine in TypeScript, with tests (done)
3. 2D lance builder in the browser (done)
4. Playable battle against an AI on a hex map (done)
5. Headless AI-vs-AI simulator and a balance pass (done)
6. 3D builder with Three.js and Blender-made parts, plus STL export for miniatures (done)
7. Polish: art direction, scenarios, printable rules and unit cards, campaign (this phase)
