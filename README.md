# Brass Charter

A turn-based war-walker skirmish game. Chartered Companies settle disputes over worlds by
Charter Trial, fielding lances of 3 to 5 custom-built, steam-powered war-walkers on a
100-point budget. Every build trades points, slots and boiler Pressure against each other.

The first target is a browser game against an AI opponent, used to playtest the rules. The
rules are written to work on a physical tabletop too.

## Status

Phase 5 of the plan: balance. Rules are at v0.2; see the [balance report](docs/balance.md).

| Path | What it is |
| --- | --- |
| [`docs/rules.md`](docs/rules.md) | Core rules v0.2 |
| [`data/`](data) | Chassis, equipment, Driver traits, Companies, scenarios and example lances as JSON. The source of truth for the engine, builder, AI and simulator. |
| [`packages/rules`](packages/rules) | TypeScript rules engine: `createGame`, `applyAction`, `legalActions`, `previewAttack`. Pure and deterministic (seeded dice), so the browser game, AI and simulator can share it. |
| [`apps/web`](apps/web) | Browser app with two tabs. **Lance Ledger** builds lances (points, Pressure, armour and expected damage live; save, export, import). **Charter Trial** plays a battle on a hex map against the AI. |
| [`packages/ai`](packages/ai) | Greedy utility AI: `chooseAction(state)` and `playOut(state)` for AI-vs-AI games. |
| [`tools/sim`](tools/sim) | Balance simulator: `npm run sim -- 600 1` plays AI-vs-AI Trials and reports win rates by lance, chassis, item, trait and Company. |
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
5. Headless AI-vs-AI simulator and a balance pass (this phase)
6. 3D builder with Three.js and Blender-made parts, plus STL export for miniatures
7. Polish: art direction, scenarios, printable rules and unit cards, campaign
