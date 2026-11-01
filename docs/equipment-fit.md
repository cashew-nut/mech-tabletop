# Equipment fit

Where weapons and equipment sit on a walker. Only the classes with full models use it so far:
**Paladin, Brute, Seer** (`fit.classes` in `data/model-kit.json`). Every other class keeps the numbered
mounts (`mount_core_0`, ...) exactly as before.

## How it works

- **Hardpoints** (`fit.hardpoints`): a kit joint plus an offset in fractions of body height (the head joint's
  height), in the joint's own axes (x outward, y up, z forward). `grip-native` is the one exception: it reuses the
  tuned numbered wrist mount, for items cut for it (`lance@paladin`, `autocannon@brute`, `arc-cannon@seer`).
- **Items** (`fit.items`): per location kind (`arm`, `core`, `legs`) an ordered list of hardpoints. The first free one
  wins, so a loadout fills the ladder in order (grip, forearm-top, shoulder-top for arms). `pose` gives the contact
  face (`back`, `bottom`, `top`, `center`) that touches the hardpoint, an extra rotation and a scale per hardpoint.
- **Contact faces** come from each GLB's bounds, `data/item-bounds.json`. Regenerate with
  `node scripts/item-bounds.mjs` after changing a part.
- **Per-class tuning** (`fit.overrides.<class>.<hardpoint>`): replaces fields of a hardpoint for that body. The Meshy
  bodies are not proportioned like the frames, so most tuning goes here. `fit.classes.<class>.scale` scales every item.
- **Placements** (`fit.placements.<class>.<hardpoint>.<item or *>`): the hand-adjustment table, see below.
- Pair hardpoints (`calf-back`, `knee-outer`, `heel`, `shin-front`) put one item on both legs from one slot.
- Right-hand anchors are mirrored, so poses are written for the left.
- An item with no entry, or a body without joints (the procedural chassis), falls back to the numbered mounts.

## Placement table and sliders

`fit.placements` stores, per class, per hardpoint, per item (or `*` for every item at that hardpoint), a nudge:
`offset` (fractions of body height, along the hardpoint's axes: x out, y up, z forward), `rot` (degrees, pitch/turn/roll)
and `scale` (a multiplier). Fields left out mean no change, an item row wins over the `*` row field by field, and a
hardpoint with no row is placed exactly as before. The nudge sits between the hardpoint and the item, so turn and scale
pivot on the item's contact point, and the right side mirrors the left (write values for the left).
`overrides` still moves a hardpoint for a whole body; placements are for one item at one hardpoint.

Tune it live in a browser (dev server, not part of the build):

```sh
npm run place                    # opens /place.html; ?chassis=seer&set=heavy picks a class and a loadout from scripts/fit-sets.json
```

Pick a class, a preset (or type equipment ids per location), click an item in the list, and drag the sliders. The
yellow box and the red/green/blue arrows mark the item and its hardpoint. "This item here" writes a row for that item,
"every item at this hardpoint" writes the `*` row. Unsaved work is kept in the browser, with a banner on reload.
To save it, use Copy JSON (or Download), then:

```sh
node scripts/merge-placements.mjs placements.json    # replaces each class in the file, drops rows that change nothing
npm run validate && npm run fit
```

## Review

```sh
node scripts/fit-sheets.mjs renders/fit/after            # the sets in scripts/fit-sets.json, two angles each
FIT=off node scripts/fit-sheets.mjs renders/fit/before   # the same with the old numbered mounts
node scripts/fit-check.mjs [class]                       # npm run fit: flags HEAD, GROUND, FLOAT, MISSING
```

`render.html?chassis=seer&lo={"core":["soul-lantern"]}&zoom=2&fy=0.5&fit=off` renders any loadout, close up.
Needs Playwright and headless Chromium; run by hand, not in CI.
