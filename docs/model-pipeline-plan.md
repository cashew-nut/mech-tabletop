# Model pipeline plan: more walkers, fewer Meshy credits

Status: proposal, 2026-11-04. Nothing here has been built, and no Meshy credits were spent writing it.

## The short version

Luke's suggested order (faction descriptions, then full concept art, then part art, then modelling) is right for the
2D side, and this plan keeps it. Where it changes is the 3D side: **model each walker from one whole-body Meshy call,
never one call per part**, and cut the parts in Blender with the composite pipeline we already have. Part art is still
made, but as a 2D part sheet for the cards. Part-by-part 3D would cost about six times as much (6 x 30 = 180 credits
against 30), and every part would come out at its own scale and centre line, because Meshy makes up whatever it cannot
see (`docs/meshy.md`). The whole-body route is the one that produced the Paladin, Brute and Seer.

So the concept art becomes the source of truth for both the cards and the model. A typical new walker costs about
**45 to 60 Meshy credits** (about 80 if a 3D re-roll is needed). The balance today is **196 credits** (checked
2026-11-04, no monthly credits), which covers about three walkers.

## What we have already

| Thing | Where | Reuse |
| --- | --- | --- |
| Faction boards | `docs/concept-art/three-factions-board.png`, `iron-covenant-board.png`, `north-star-board.jpg` | Reference images in every prompt (the style is carried by the images more than by words) |
| Three hero meshes (Paladin, Brute, Gilded Seraphim) | project folder root zips | Done; the canonical look for their factions |
| Covenant variant B crops | project folder `art/iron-covenant/variant-b-artillery/` | Starting reference for the Sentinel |
| Saved Meshy sources | project folder `meshy-sources/` (hellfire, kinetic claws, Paladin rack and shield), `models/brute-items/meshy/` | Items, already fitted or ready to fit |
| Composite pipeline | `assets/blender/parts/composite/` (split, joints, build, render, publish) | All of it. A new walker is one new `MODEL=<class>` settings module |
| Item fit | `item_cut.py`, `paladin_items.py`, `seer_items.py` | Weapons and relic parts on designed hardpoints |
| Card data and sheet | `data/parts.json`, `data/cards.json`, `scripts/build-card-sheet.mjs` | Unchanged; only the art source changes |
| Meshy wrapper | `tools/meshy/meshy.py` (balance, text-to-image, image-to-3d) | Extend (see "Spending guard") |

One thing to know: **Meshy keeps API results for only 3 days** (its asset-retention page). The Oct 31 weapon batch has
already gone from the account; what survives is what was saved to the project folder. So every generation is downloaded
and archived the same day.

The six classes without a model are Lancer (striker), Sentinel (bulwark), Scavenger (scout), Artillery (bulwark),
Wraith (scout) and Goliath (titan).

## Stages and approval gates

Meshy spend goes up stage by stage, so the expensive call only happens once the cheap ones are approved.

| # | Stage | Output | Gate | Meshy credits |
| --- | --- | --- | --- | --- |
| 0 | Style bible, once per faction | `docs/style-bible/<faction>.md` and `data/style-bible.json` | **A**: Luke approves each faction's bible | 0 |
| 1 | Class brief | one paragraph from `chassis.json` (role, frame size, stride, slots, weapons) filled into the template | none (goes with B) | 0 |
| 2 | Hero concept | 2 to 4 hero images, made image-to-image from the faction board and the faction's approved heroes | **B**: Luke picks one. It is the class's north star and the card's hero art | 6 to 12 |
| 3 | Turnaround and part sheet | front, side and back views on flat grey, and one sheet with the six body parts and signature weapons laid out apart | **C**: Luke approves. This locks the design and the card art | 6 |
| 4 | Cut map | seams, joint list and peg sizes drawn on the turnaround (Claude, no Meshy) | goes with C | 0 |
| 5 | 3D mesh | multi-image-to-3D from the three views, mesh only, then texture | **D**: Claude checks the silhouette against the turnaround before texturing | 20 + 10 |
| 6 | Composite parts | new `MODEL` module; split, joints, build, render | **E**: Luke approves the parts, assembled and exploded renders (the PR review we do today) | 0 |
| 7 | Publish | game GLBs, `parts.json` and `cards.json` rows, card faces from the stage 2 and 3 art | PR merge | 0 |

Notes on the stages:

- **Stage 2** uses Meshy's image-to-image (up to 5 reference images, 3 credits on nano-banana, 9 on nano-banana-pro).
  References are the faction's board column, its approved hero (the Paladin for the Covenant, and so on) and, once
  they exist, the other approved heroes of that faction. That is what keeps a new walker looking like it belongs.
- **Stage 3** uses image-to-image with `generate_multi_view` on the picked hero for the turnaround (one task, about three
  views) and a second task for the part sheet. The part sheet is cropped into the six body-card arts for free.
- **Stage 5** sends the three views to multi-image-to-3D (Meshy treats the first as the front, which cuts down the
  invented geometry that a single image gives). It runs mesh-only first (20) and adds texture only after gate D
  (retexture, 10), with the approved front view as the texture image. Same 30 credits as a single textured call, but a
  bad shape stops at 20. Both details need checking on the first walker; if retexture loses quality against a
  one-shot textured call, fall back to the one-shot call (30).
- **Tiers 1 to 4** reuse the same model and art with a different card frame and finish, as `docs/cards.md` already
  says: 0 credits. **Legendary relics** get their own stage 2 to 5 run for the one part that changes, modelled as an
  isolated part on a standard socket (the way the ten weapons were), about 33 credits each.
- **Items and signature weapons**: a text-to-image or image-to-image reference (3) and image-to-3D (30), fitted with
  `item_cut.py` onto a hardpoint. Before any new item art, check `meshy-sources/` for one Luke already liked (the Brute
  claw lesson).

### Doing the 2D for free

Stages 2 and 3 are prompt-driven. Claude writes the prompts and reference list; they can run on Meshy (3 credits each)
or Luke can paste them into an image tool he already pays for and drop the result in the thread. That would bring a
walker down to about 30 credits, all of it 3D.

## Spending guard

The rule: a Meshy call is made only for an approved design, and every result is saved.

- `tools/meshy/meshy.py` gains `image-to-image` and `multi-image-to-3d`, prints the cost and the balance before each
  call, and needs `--confirm` to spend.
- A ledger, `meshy-sources/ledger.json` in the project folder, gets one row per call: class, stage, task id, credits,
  and the gate it rests on (the thread message where Luke approved). The 3D commands refuse to run unless the ledger
  shows gate C for that class.
- After each task the script downloads everything (GLB, textures, thumbnail, input images) to
  `meshy-sources/<class>/<task-id>/` and writes a `source.json` with the prompt and references.
- Each class thread gets a credit cap written into its instructions (60 by default). Going over needs Luke's say-so.

## Faction style bible

One short file per faction, plus a machine-readable copy that the prompt script reads. Draft content, taken from the
boards (palette hexes sampled from the boards' colour swatches):

| | Iron Covenant | Ashen Foundries | Reliquary |
| --- | --- | --- | --- |
| Feel | cathedral knights: noble, upright, ornate | industrial warbands: brutal, hunched, functional | relic machines: ancient, gaunt, strange |
| Palette | black enamel `#262527`, gold `#805830`, crimson cloth `#800d14`, bone `#d2c5bb` | rust red `#8d2912`, orange lacquer `#be6a35`, blackened iron `#34322f`, brass `#6e4d2f` | bone white `#a98f77`, aged gold `#94704d`, verdigris teal `#476766`, dark frame `#263237` |
| Motifs | gold filigree trim, sunburst pauldrons, cross heraldry, banners and tabards, spires on the back, glowing furnace chest, slit visor | riveted hull plates with stencilled white numbers, smokestacks, glowing furnace cores, pipes and chains, hazard edges | halo crowns, hooded masks, long clawed fingers, tattered banners, lanterns, ribbed gold limbs, teal glow |
| Silhouette | tall, broad shoulders, straight legs | low, wide, heavy forearms and guns | thin, tall, long limbs |
| Joints for the print | armoured, broad | chunky pistons and collars | gold ball knuckle in a sleeve (the Seer's standard) |
| Never | rust, numbers, exposed pipes, teal | gold filigree, cloth banners, halos | heavy boxy plate, stencils, red lacquer |

### Prompt templates

Each prompt is assembled from the bible and the class brief by a small script, never written by hand per class, so
the wording stays the same across a faction. The `{}` fields come from `data/style-bible.json` and `chassis.json`.

**Hero concept (stage 2, image-to-image, references: board column, faction heroes)**

> Concept art of a {faction.name} war-walker, {class.name} class, {class.role}. Same faction and art style as the
> reference images. {faction.feel}. Colours: {faction.palette}. Details: {faction.motifs}. Silhouette: {class.silhouette}.
> Armed with {class.weapons}. Full body, standing, three-quarter view, dark background, dramatic rim light. Not: {faction.never}.

**Turnaround (stage 3, image-to-image from the picked hero, `generate_multi_view`)**

> The same war-walker as the reference, unchanged design and colours. Front, side and back views, standing in a relaxed
> A-pose with arms held clear of the body and legs apart, flat light grey background, even lighting, no shadows, no
> cloth blowing, no background, nothing held across the body. Joints clearly visible: {faction.joints}. Every limb
> at least {frame.minLimb} of the body height thick.

**Part sheet (stage 3, image-to-image from the picked hero)**

> The same war-walker as the reference, taken apart into its pieces and laid out apart on a flat dark background,
> like a model kit: legs, torso with pelvis, helm, pauldrons, arms, back {class.back}, and {class.weapons}. Each piece
> shows its connection socket. Same colours and detail as the reference.

**Item or relic part (isolated, as in the Oct 31 weapon batch)**

> Isolated game prop on a flat light grey background, side-on three-quarter view, no hands, no body, no stand. {item}
> for a {faction.name} war-walker. {faction.palette}, {faction.motifs}. A flat round mounting boss on the {mount side}.

The minimum limb thickness (`frame.minLimb`) matters for the magnets: a 2 x 1 mm disc in a peg with a 0.4 mm wall
needs about 4 mm of limb at print scale. That is about 5% of a Titan's 75 mm height but 10% of a Scout's 42 mm, so the
Scout prompts ask for chunky limbs and the cut map plans ball knuckles from the start (the Seer needed them added after).

## Magnets, pegs and the 1.5x scale

The pipeline already does this; the plan only makes it a standard.

- Every model is cut at Luke's 1.5x print scale (`PRINT_SCALE = 1.5` in the `MODEL` module): Scout about 42 mm
  up to Titan about 75 mm. Game GLBs are exported back at kit size.
- `joints.py` with `STRICT = True` fits a keyed D-peg at every joint in the six-card layout (`layout.TREE`), with a
  3 x 2 mm disc on the core joints (pelvis, torso, helm, pauldrons) and 2 x 1 mm on limbs and wrists, and checks each hole
  against the real solids.
- The cut map at stage 4 is drawn against the card split (legs, torso and pelvis, helm, pauldrons, arms, crown or back),
  so each body card is one or more whole printed parts.
- Item hardpoints are the existing standard: a boss with an r 1.5 x 3.0 mm D-peg hole and a 2 x 1 mm magnet pocket
  (shoulder, bracer, wrist). Shapes follow the faction (Covenant gunmetal boss with gold bands, Seer gilded sleeve,
  Foundries riveted collar).
- Sided parts are modelled for the left and mirrored, as now.

## How the faction rule is enforced

"Every body part on a walker comes from one faction" is held in three places:

1. **Rules.** Each `parts.json` part already has a faction and a frame size. Add a builder check and a test in
   `packages/rules` that rejects a walker whose six body parts do not share one faction and one frame size. A small,
   separate change.
2. **Art.** Prompts come only from the template plus that faction's bible, always with that faction's reference images,
   and the bible's "Never" column goes in every prompt. At gates B and E, the new walker is shown beside its faction's
   board column and approved heroes.
3. **Print (optional).** Body joints can be keyed per faction, so a Foundries leg physically will not seat in a Covenant
   pelvis: the D-peg's flat is turned to a different angle per faction (Covenant 0, Foundries 120, Reliquary 240
   degrees). Item hardpoints stay universal, because shared gear fits any faction. This is a decision below.

## Budget per new walker

Meshy credits (prices from Meshy's pricing page, 2026-11-04):

| Step | Typical | High |
| --- | --- | --- |
| Hero concept, 2 to 4 rolls at 3 | 6 | 12 (or 36 on nano-banana-pro) |
| Turnaround (1 multi-view task) and part sheet | 6 | 12 |
| Multi-image-to-3D mesh + texture | 30 | 60 (one re-roll) |
| **Walker body** | **42** | **84** |
| Each new signature item (reference + 3D) | 33 | 66 |
| Tiers 1 to 4 | 0 | 0 |

With 196 credits: about three walkers, or two walkers with their items. All six missing classes with two items each
would be roughly 6 x 42 + 12 x 33 = about 650 credits at typical rates, so a top-up or running the 2D outside Meshy
would be needed for the full set. (Meshy-6-lite is cheaper at 15 credits for a textured model, but it was never tested
against the quality bar; one trial on a prop could settle it.)

Claude usage, on Sonnet per the token rules: the 2D stages are a short thread (prompts, a handful of images,
two gates). Modelling is the big one: on past walkers the split, joints, build and renders ran about 15 minutes
of compute, but tuning the cut and joints for a new mesh took most of a long thread. Each walker gets its own thread,
in order, so only one PR needs rebasing at a time. Opus only if a final art pass needs it.

## Moving off Meshy over time

Meshy stays for whole-body sculpts of new classes, where it is far cheaper than hand modelling. Everything after that
should not need it: tiers are finishes, sockets and knuckles are designed in Blender, and the parts we already have
(knuckles, sleeves, collars, bands, filigree plates, rivets, hull plates) can be harvested into a per-faction Blender
detail library for later variants. That is a later step, not part of the first walkers.

## Suggested first run

The Sentinel, as a pilot. It is Covenant, so it reuses the most proven bible and pipeline (the Paladin's); it is a
bulwark, big enough for easy pegs; and the variant B crops are already a reference. Steps: bible for the Covenant
(gate A), Sentinel concept (B), turnaround and part sheet (C), then modelling in its own thread. If the pilot holds,
the other two bibles follow and the remaining classes run one per thread.

## Decisions for Luke

1. **Whole-body 3D, part art for cards only.** Model each walker from one whole-body Meshy call and cut parts in Blender,
   rather than modelling each part from its own art? (Recommended: yes.)
2. **Card art from concept art.** Body and hero cards use the stage 2 and 3 concept art; renders of the 3D model stay
   for the viewer and the game only? (Recommended: yes, as you suggested.)
3. **Who makes the 2D.** Claude runs it on Meshy (about 12 credits a walker), or Claude writes the prompts and you run
   them in your own image tool for free? (Recommended: Meshy for the pilot, to keep it quick; your tool after if you
   want to save credits.)
4. **Faction-keyed pegs** on body joints for the print, or rules and art only? (Recommended: keyed, it is cheap to add now
   and hard to add after parts are printed.)
5. **Pilot class.** Sentinel first? (Recommended.) Others: Goliath (big, Reliquary) or Lancer.
6. **Credit cap.** 60 credits a walker without asking, and a top-up later if all six classes are wanted?
