# Code audit plan (2026-11-02)

A module-by-module tidy of the code on `main` after PR #64. The goal is simpler code with the same behaviour:
remove dead code, merge duplicated logic, and split the few files that hold several jobs. Each group below is one
small PR. Every PR runs `npm run check` (data validation, typecheck, 162 tests) and `npm run build`. A PR that
touches 3D code also renders before-and-after frames in headless Chromium (SwiftShader, so no GPU) and compares
them pixel for pixel.

Out of scope: model files (GLB, STL, blend), the Blender scripts in `assets/blender` (every script there is
documented in a README, and none is dead), and anything that calls Meshy.

## Module map

| Module | Lines | Owns | Imports |
| --- | --- | --- | --- |
| `packages/rules` | 2,900 | Data loading, hex maths, lance rules, builder stats, the game engine, map generation | `data/*.json` |
| `packages/ai` | 370 | Greedy utility AI | rules |
| `apps/web/src` (App, WalkerEditor, Cards, storage) | 1,030 | Tabs, the Lance Ledger, unit cards, saved lances | rules, model (lazy), battle |
| `apps/web/src/model` | 3,600 | Procedural parts, the kit assembler, hardpoint fit, the stage, the part view, exporters, the dev pages (render, place) | rules, `data/model-kit.json`, `data/item-bounds.json` |
| `apps/web/src/battle` | 2,800 | Battle UI, the 2D and 3D boards, board art and kit, the combat replay | rules, ai, model (assemble, chassis) |
| `scripts` | 1,500 | Data validation, GLB publishing and compression, headless renders | gltf-transform, Playwright |
| `tools` | 450 | Balance simulator and map-generation tuning tools | rules, ai |

The layering is sound: rules has no app imports, ai depends only on rules, and the web app depends on both. There is
one layering smell. `rules/mapgen` imports `passable`, `stepCost` and `lineOfSight` from the whole engine, when it
only needs the read-only queries.

## Findings and proposed changes

### PR 1: dead code and stale exports (all packages)

- `kit.ts` `rivetRing`, `kitparts.ts` `KIT_FACTIONS` and the test helper `fillers` are never used. Delete them.
- `mapgen/validate.ts` `RULE_NAMES` is never read. It is the only place the hard rules are named, so the names move
  into the doc comment on `RuleId`.
- `parts.ts` re-exports `BASE_MM` and `frameOf`, and nothing imports either one. Drop the re-exports.
- `Battle.tsx` `PLAYABLE_SCENARIOS` is only an alias of `SCENARIOS`. Use `SCENARIOS` directly.
- Eleven web values are exported but only used inside their own file, such as `collectParts`, `BACKDROPS`, `kindOf`
  and `BASE_RADIUS`. Remove the `export`, so each module's surface shows what other modules use. The rules package
  keeps everything `index.ts` re-exports, since that is its public API. The `kit.ts` shape library (`gauge`, `gear`)
  also keeps its exports.

### PR 2: builder 3D model (`apps/web/src/model`)

- The sided-joint list is written twice: `SIDED_JOINTS` in `kitparts.ts` and an inline array in
  `assemble.ts placeAtHardpoint`. Use `jointName()` in both places.
- `Side` is declared in both `fit.ts` and `kitparts.ts`. Keep one.
- The kit node name regex `^kit_([a-z]+)(?:_([LR]))?$` is repeated in `explode.ts`, `partview.ts` (twice) and
  `preview.ts`. Add one `parseKitNode()` in `kitparts.ts`.
- `explode.ts SIDED` restates the `sided` flags of `data/model-kit.json` components. Derive it from `COMPONENTS`.
- The joint lookup `userData.joint ?? (name starts with joint_)` is repeated in `assemble.ts` and `preview.ts`. Add
  one helper.
- The degrees-to-Euler conversion is written out three times in `assemble.ts`. Add one helper.
- `fit.ts nudgeOf` repeats the identity test that `isQuiet` already does.
- The seeded Park-Miller random is written three times (`kit.ts` twice, `stage.ts` once). Export one `seeded()`.
- The "dispose every mesh under a node" loop appears twice in `stage.ts`. Add one helper.
- `WalkerModel.tsx` repeats the `partsOn && KIT_CHASSIS.includes(...)` test three times. Compute it once. The
  `KIT_CHASSIS` list stays written out: it matches `fit.classes` today, but it means something different (classes
  with closed composite parts).
- `parts.ts` also re-exports `kit.ts` and `chassis.ts` symbols, so callers reach the palette and the chassis through
  the item file. Import them from where they live, and drop the re-exports.

### PR 3: battle UI and app shell (`apps/web/src/battle`, `App.tsx`)

- The zone labels (Core, Core (rear), Left arm and so on) are the same in `Battle.tsx ZONE_NAMES` and
  `CombatReplay.tsx ZONES`. Share one table.
- The hex size (26) is defined in `HexMap.tsx`, `BoardHud.tsx`, and as `UNIT = 1 / 26` in `Board3D.tsx`. Export it
  once from `HexMap.tsx`.
- The sine-hash random is written in both `boardArt.ts rndFrom` and `Board3D.tsx rnd01`, and they are the same
  function. Keep one.
- `Battle.tsx` (670 lines) holds six components. Move `Setup`, `ActivationPanel` and `WalkerCard` into their own
  files. `Trial`, `Log` and the escort helper stay in `Battle.tsx`.
- `boardWalkers.ts WalkerLibrary` keeps a `renderer` field it never reads. Keep it as a plain constructor argument.
- `App.tsx` holds the whole Lance Ledger (`Builder`, 250 lines) beside the tab shell. Move it to `Builder.tsx`, and
  render the three tab buttons from one list.
- Found but not changed here: `Board3D` does not dispose its scene geometries, materials or PMREM environment on
  unmount, so switching tabs back and forth leaks GPU memory. That fix changes behaviour, so it is listed as a
  follow-up.

### PR 4: rules engine and AI (`packages/rules`, `packages/ai`)

- The target number table by range band is written three times. `engine.ts` has the modifiers (0, 0, 1, 2) on top
  of a base TN of 4, while `builder.ts` and `ai/index.ts` each spell out the totals (4, 4, 5, 6). Export `BASE_TN`
  and the band modifiers once, and build the other two from them. `BANDS` in `builder.ts` repeats `BAND_ORDER` in
  `engine.ts`.
- The hit rule (a 6 always hits, a 1 always misses) is written in both `engine.ts rollAttack` and
  `web/battle/replayExchanges.ts isHit`. Export `isHit` from rules and use it in both.
- `engine.ts` is 1,190 lines. Split out `queries.ts` (walker and hex lookups, movement, reach, line of sight, range
  bands, `previewAttack`, deployment zones), which are pure reads. Mutations stay in `engine.ts`, and `mapgen` imports
  from `queries.ts`. `index.ts` re-exports the same query names as before by name, so the engine's internal helpers
  stay private. The only additions are `BASE_TN`, `BAND_TN`, `BAND_ORDER` and `isHit`.
- `ai.test.ts` and `game.test.ts` each define the same small test random. They are in different packages, and a
  test importing across packages would cost more than the two lines it saves, so they stay as they are.

### PR 5: scripts and tools

- Five Playwright scripts (`render-walkers`, `fit-check`, `fit-sheets`, `render-battle`, `render-card-art`) each
  copy the same block: start Vite on a port, wait for it, launch SwiftShader Chromium, and kill the server. Move it
  into `scripts/lib/viewer.mjs`. (`build-card-sheet` uses Chromium without Vite, so it keeps its own launch.)
- `scripts/seed-parts.mjs` is a one-off seeding script, and its own header says not to run it again because it
  overwrites the hand-tuned `data/parts.json`. Delete it (it stays in git history) and update `docs/cards.md`.
- `apps/web/test` and `tools/` are not typechecked, since `tsconfig` only includes `src`. Give each its own
  `tsconfig.json` with Node types (`@types/node` becomes a dev dependency, so browser code still sees no Node globals),
  and add both to `npm run typecheck`. Both typecheck clean already.

## Order

PR 1 goes first, because the later PRs touch the same files. PRs 2 to 5 do not overlap, so they can be reviewed in
any order. Each one is cut from `main` after the PR before it merges, so no PR needs a rebase.
