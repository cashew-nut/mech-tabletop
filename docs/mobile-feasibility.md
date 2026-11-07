# Could Mech Charter be a mobile game? Feasibility report

Written 2026-11-07. This is a read-through of the repo at that date: no build was run, no phone was tested and no Meshy credits were spent. Numbers marked **measured** come from the files in the repo; numbers marked **estimate** are my judgement and need a real phone to confirm.

## Short answer

Yes. The game is already a web app, so the cheapest route is to make the existing web app work well on phones and install it from the browser (a PWA). That is roughly **3 to 5 working days of Sonnet threads plus your time testing on a real phone**. It does not need a new engine. The real work is not "porting"; it is a phone-sized layout, a lighter graphics setting, and a download strategy for the 3D parts.

Getting into the App Store or Google Play is a second, optional step (wrap the same app with Capacitor), about **1 to 2 more days**, but it brings store rules about selling digital packs that you should read before choosing it (see "Packs and accounts").

I would not rewrite in Unity, Godot or React Native. The rules engine, AI, data and Three.js scene would all have to be redone for no gain at this scale.

## What runs on a phone today

| Piece | Stack | Phone verdict |
| --- | --- | --- |
| Rules, AI, data | Pure TypeScript in `packages/rules`, `packages/ai`, `data/*.json` (83 KB of JSON). No DOM, no Node-only code. | Runs as is. Only open question is AI speed (below). |
| UI | React 18 + Vite, plain CSS (`apps/web/src/styles.css`), `base: './'` so it can be hosted from any path. | Runs. Layout needs a phone pass. |
| Battle board | Three.js 0.169 (`apps/web/src/battle/Board3D.tsx`) with a flat SVG fallback (`HexMap.tsx`) already behind a "Flat map" toggle. | 3D needs a mobile quality tier. The flat map is a ready-made safety net. |
| Saves | `localStorage` only (`storage.ts`), guarded for blocked storage. | Works. Fine for a PWA; in a store app move it to the app's own storage. |
| Fonts | Cinzel and Source Sans loaded from Google Fonts in `index.html`. | Works online only. Self-host them for offline play. |

Nothing in the repo is mobile-hostile at the language or tooling level: no server, no Node APIs in the browser bundle, no desktop-only libraries.

## 3D assets and performance

### What is in the repo (measured)

- `apps/web/public` is **134 MB**: parts 126 MB (of which `parts/kit` 115 MB, 163 GLB files), board scenery 8.2 MB.
- The files are already well prepared for phones: **KTX2 (Basis) textures** with the Basis transcoder shipped in `public/basis`, and **mesh quantization** on the newer classes. KTX2 is the right format, because the phone's GPU gets compressed textures directly (ASTC or ETC2) instead of holding full-size images.
- The five composite walkers (Paladin, Seer, Brute, Sentinel, Artillery) are about **3.1 to 3.7 MB each** on disk and about **55,000 to 73,000 triangles** each, split across 9 to 12 closed parts with 24 to 36 small textures (256 to 1024 px).
- The older frame-based classes are heavier: the Scout frame parts are about **109,000 triangles** in two files, and each of the older frame sets (scout, striker, bulwark, titan) is 21 to 25 MB across the three factions, so roughly 7 to 8 MB per faction.
- Parts are fetched per class, only when a walker of that class is on the board (`ensureKitParts` in `boardWalkers.ts`), so a game does not download the whole 134 MB.
- Board scenery already has three levels of detail (`*_lod1`, `*_lod2`). **Walkers have no level of detail.**

### Where the time goes (estimate)

A six-to-ten walker battle is about **0.4 to 0.7 million triangles of walkers**, plus the board. The board's render settings are the larger risk than the models:

| Setting in `Board3D.tsx` | Cost on a phone | Mobile change |
| --- | --- | --- |
| `EffectComposer` with a half-float target and **4x MSAA**, then `UnrealBloomPass` | The single most expensive item. Many phone GPUs handle half-float MSAA poorly and bloom is several full-screen passes. | Drop the composer on phones. Draw straight to the screen. Keep a cheap fake glow (the sprite "bloom" markers already exist). |
| `sun.shadow` 2048 x 2048, `PCFSoftShadowMap`, every walker casts and receives | Draws all walker triangles a second time, plus a big shadow map. | 1024 map or shadows for walkers only, or a blob shadow under each plinth. |
| `RoomEnvironment` + PMREM, `MeshStandardMaterial` on every part | Acceptable once, but PBR on 0.5M triangles is heavy for low-end devices. | Keep for high tier; use Lambert/unlit-ish materials on a low tier. |
| Canvas is sized by CSS pixels and never uses `devicePixelRatio` (`PIXEL` = 1) | This is good for speed but looks soft on a phone that has DPR 3. | Cap DPR at 1.5 to 2 on phones, and let the quality tier choose. |
| Walker triangles (55 to 110k each) | Fine for one walker, heavy for ten. | Add a walker level of detail: full model near the camera, a baked low-poly proxy when zoomed out. A phone view is almost always zoomed out, so this wins most of the budget back. |
| GPU memory | **Estimate** 15 to 25 MB of compressed textures per walker class, shared between walkers of the same class. Six classes on a board is about 100 to 150 MB, which is tight on older 3 GB phones. | Cap texture size at 512 px on a low tier (the transcoder can skip the top mip), or build a smaller texture set for the board. |

My expectation, to be checked on a real device, is that a mid-range phone from the last four years runs the current scene at a slideshow rate with bloom and MSAA on, and at a steady 30 fps once composer, shadow size and texture size are cut, with walker level of detail needed only for 8+ walker battles. I cannot measure that from this container; it needs a phone and a few minutes with a frame counter.

### AI speed (unmeasured)

`Battle.tsx` runs the AI on the main thread inside `setTimeout`, and `legalActions` works by trial-applying actions to a cloned state (noted in earlier project memory as slow). A desktop does not notice. A phone CPU is several times slower, so the page may freeze for a moment on the AI's turn. Two cheap safeguards: time `chooseAction` on a phone (add a log line), and move it into a Web Worker, which is a small change because the AI is pure TypeScript.

## Touch controls for turn-based play

What already works:

- `OrbitControls` handles touch natively: one finger orbits, two fingers pinch to zoom. Pan is off, which is fine.
- Picking is a pointer-down/pointer-up pair with a 5 px drag threshold, which works for touch. The board has `touch-action: none` so the page does not scroll under the canvas.
- Hex and walker clicks are separate, and invisible cylinder proxies make walkers easy to hit.

What needs work:

1. **Tap targets.** Many buttons, links and walker list entries are sized for a mouse (`min-width: 40px` and `60px` appear in `styles.css`; the HexMap highlights use `:hover` outlines, which never show on touch). Aim for 44 px minimum.
2. **No hover.** Anything that is only told by hover (the `.hl-*:hover` hex highlights, button titles) needs a tap-then-confirm pattern: first tap shows the preview (move path, attack odds from `previewAttack`), second tap or an on-screen Confirm commits. This is the single most important turn-based touch change, because a stray tap should never spend an action.
3. **Layout.** `.trial` collapses to one column at 980 px, but the board height is `width * 0.72` and the activation panel sits below it, so on a portrait phone the player scrolls between board and controls. A phone layout wants a docked bottom bar (end activation, throttle, selected walker's weapons) over the board, and a portrait board that is taller than 0.72.
4. **Camera help.** A "reset view" and "focus on selected walker" button, since a two-finger gesture is easy to lose the board with. `minPolarAngle`/`maxPolarAngle` already keep the camera sensible.
5. **Safe areas and orientation.** Add `viewport-fit=cover`, `env(safe-area-inset-*)` padding, and decide whether landscape is the main mode. I would design for portrait first, since that is how it is held for a short turn.
6. **Replay and builder.** The Combat Replay and the Lance Ledger builder (`Builder.tsx`, `WalkerEditor.tsx`, the paint/part view) are denser than the battle and are the second pass. The builder is the least mobile-friendly screen; on a phone a stripped "pick a build, tap to change a part" flow is better than the desk-style doll.

## Digital packs and accounts

Current state: **there is no account system, server or purchase flow in the repo.** Cards exist as data (`data/cards.json`, `data/parts.json`) with a `printId` such as `CV-PAL-LEG-T3`; the account-linked instance id described in the vision is not built. Luke's decision of 2026-11-01 is "hobby project, no payments", and card and pack questions are parked.

What a mobile game adds to that decision:

- **Persistent ownership needs a server.** `localStorage` on a phone is wiped when the browser or app is reset, and is not shared between a phone and a laptop. Any collectible loop (packs, trading, "my collection") needs an account, a database of owned instances, and a ledger. This is the same work whether the front end is a PWA or a store app. A small managed backend (sign-in, one table of owned cards, one pack-opening function that rolls rarity on the server so the client cannot cheat) is about **3 to 5 days**, and it is the largest new piece in the whole list. Until then packs can be a local-only demo.
- **Store rules apply only if you publish in the stores.** Apple and Google require their own in-app purchase system for digital goods, take a share of each sale, and require disclosure of pack odds for random items. A PWA sold from your own site avoids the store cut but needs your own payment processor and the same odds disclosure in most places. Because this is a hobby with no payments, the practical advice is: build free packs earned by play first, and decide on money only if the project grows. Check the current store policy text before relying on my summary, since it changes.
- **Selling the physical side** (printed cards, STL files) is a physical or file purchase, not an in-app digital good, but linking a physical card to a digital one by QR is allowed to be a free "claim" action; keep the purchase on a web page rather than in the app.

## What the physical tabletop side keeps

The mobile app does not replace the tabletop; they share the same rules and data.

- **Rules** (`docs/rules.md`, d6 only, hex map, alternating activations) are written to work on a table, and the digital version uses the same engine, so nothing changes.
- **Printable cards** (`cards/`, 63 x 88 mm sheet, `docs/cards.md`) and the **Unit Cards tab** stay as they are. An app can add a "scan this card" QR claim later.
- **3D-printable parts** (the closed, peg-and-magnet GLBs and the STL export at 1.5x scale) are independent of the phone. They do not need to change, though the heavy detail that matters on a print is more than a phone needs, so the app should use its own lighter copies. This is the same "app copy vs print copy" split that the level-of-detail work above produces.
- **Hex maps and scenarios** (`data/maps.json`, `data/scenarios.json`) are shared. A table player and a phone player can use the same scenario.
- One thing a phone makes easy for the table: using the phone as a **dice-and-reference companion** (tap a walker, see its card, stats and the attack odds) without needing the board view at all. That could be a very cheap first mobile deliverable.

## Concrete change list and rough effort

Effort is working time for Sonnet threads (including checks), not elapsed time; add your own time for testing on a real phone, which is the main gate. Costs: none of this needs Meshy.

| # | Change | Effort | Notes |
| --- | --- | --- | --- |
| 1 | **Phone-test the current build.** Host it (GitHub Pages works with `base: './'`), open on your phone, record fps, load time and any crash. Add a frame-counter overlay (`?stats=1`) and an AI-time log. | 2 to 3 h | Do this first. Everything below depends on what it shows. |
| 2 | **Mobile quality tier** in `Board3D.tsx`: auto-detect phone, no composer/bloom, smaller or no shadows, capped pixel ratio, lighter materials, texture size cap. Keep the desktop look as "High". | 0.5 to 1 day | Biggest performance win. |
| 3 | **Walker level of detail**: a low-poly baked proxy per class, swapped by camera distance. Reuses the pattern in `scripts/board-lod.mjs`. | 1 day | Only if step 1 shows 8+ walker battles are slow after step 2. |
| 4 | **Touch interaction**: tap-to-preview then confirm, 44 px targets, no hover-only information, reset/focus camera buttons. | 1 day | |
| 5 | **Phone layout**: bottom action bar, portrait board, safe areas, trimmed Combat Replay. Builder gets a simplified phone flow. | 1 to 1.5 days | The builder is the longest part. |
| 6 | **PWA wrapper**: web manifest, icons, service worker that caches the app shell and the class kit files you actually use, self-hosted fonts, offline play. | 0.5 day | After this the game "installs" from the browser. |
| 7 | **AI in a Web Worker**, if step 1 shows freezes. | 2 to 4 h | |
| 8 | **Account + owned cards + server-side pack opening**, a small managed backend. | 3 to 5 days | Only needed when packs become persistent. Not needed for a playable mobile build. |
| 9 | **Store apps** (Capacitor wrapper, store listing, icons, signing, review). | 1 to 2 days, plus store fees and an Apple developer account | Optional. Includes in-app purchase work if packs cost money. |

Playable mobile build (steps 1, 2, 4, 5, 6, and 3/7 if needed): **about 3 to 5 days**. With accounts and persistent packs (step 8): about **6 to 10 days**. With store release (step 9): about **8 to 12 days**.

## Risks

- **Real-device performance is unmeasured.** Everything under "estimate" above could be off by a lot, in either direction. Step 1 removes most of that uncertainty for very little cost.
- **Old-frame classes** (Scout/Striker/Bulwark/Titan frame sets) are the heaviest; if a battle uses them on a phone, expect that to be where it is slow. They are also the classes still waiting on the Meshy-light rebuild, so the level-of-detail work could wait until they are redone.
- **Browser memory limits on iOS Safari** are lower than on Android Chrome; a long session that keeps replaying battles may need the GPU-leak follow-up already on the audit list (`Board3D` disposal on unmount) fixed first.
- **Store policy** on digital packs is the one area that changes your business model, not just your code. It is only relevant if you choose step 9.

## Recommended path

1. Host the existing build and try it on your phone (step 1). That is a decision-quality measurement, not a port.
2. If it is playable-but-heavy, do steps 2, 4, 5 and 6 as one or two threads. That gives an installable mobile game with the current offline/local saves and no new infrastructure.
3. Leave accounts, packs and stores until you have decided how packs should work, since those decisions drive the backend and the store question rather than the other way round.
