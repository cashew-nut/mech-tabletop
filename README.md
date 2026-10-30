# Brass Charter

A turn-based war-walker skirmish game. Chartered Companies settle disputes over worlds by
Charter Trial, fielding lances of 3 to 5 custom-built, steam-powered war-walkers on a
100-point budget. Every build trades points, slots and boiler Pressure against each other.

The first target is a browser game against an AI opponent, used to playtest the rules. The
rules are written to work on a physical tabletop too.

## Status

Phase 2 of the plan: the rules engine.

| Path | What it is |
| --- | --- |
| [`docs/rules.md`](docs/rules.md) | Core rules v0.1 |
| [`data/`](data) | Chassis, equipment, Driver traits, Companies, scenarios and example lances as JSON. The source of truth for the engine, builder, AI and simulator. |
| [`packages/rules`](packages/rules) | TypeScript rules engine: `createGame`, `applyAction`, `legalActions`, `previewAttack`. Pure and deterministic (seeded dice), so the browser game, AI and simulator can share it. |
| [`scripts/validate-data.mjs`](scripts/validate-data.mjs) | Checks the data and that every example lance is legal. |

```sh
npm install
npm run check   # validate data, typecheck, run tests
```

## Roadmap

1. Rules and data (done)
2. Rules engine in TypeScript, with tests (this phase)
3. 2D lance builder in the browser
4. Playable battle against an AI on a hex map
5. Headless AI-vs-AI simulator and a balance pass
6. 3D builder with Three.js and Blender-made parts, plus STL export for miniatures
7. Polish: art direction, scenarios, printable rules and unit cards, campaign
