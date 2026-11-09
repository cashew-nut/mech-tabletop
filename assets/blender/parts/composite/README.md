# Composite models: the Paladin, the Brute and the Seer as real parts

One pipeline, three models so far: `MODEL=paladin` (default, settings in `paladin.py`), `MODEL=brute` (`brute.py`)
and `MODEL=seer` (`seer.py`). The scripts are shared; each model module holds its labelling rules, joint tree, print
scale, budgets, render labels, peg and magnet sizes, and any designed changes. `layout.py` picks the module.
Solids, pegs, STLs and the .blend are in print mm; build.py writes the game GLBs at kit mm.

## The Paladin

The Iron Covenant Paladin rebuilt as 13 separate, closed parts that plug together with keyed pegs and magnets,
then assembled in Blender into the full walker. It starts from Luke's Meshy Paladin (textured GLB in the project
folder), but every part is now a solid of its own that makes sense when you pick it up: a card can show it alone,
a printer can print it, and the game can swap it. It is cut at Luke's 1.5x collector scale (`PRINT_SCALE = 1.5`):
about 76 mm to the helm top and 94 mm to the spire tip, and the game GLBs are scaled back to kit mm.

## Why this replaces the earlier cut

`../meshy/` gave each part the Meshy triangles labelled for it. That reproduces the figure when every part is in
place, but each part on its own is an open, ragged shell with holes where its neighbours were, so the Paladin cards
(PR #43) had to show each part lit up on a dimmed body. The Meshy figure turns out to be one closed (watertight)
surface, so it can be treated as a solid and cut like one.

## Pipeline

```sh
python3 -I ../meshy/cut.py extract Meshy_..._texture.glb WORK   # mesh.npz and Meshy's textures
~/bvenv/bin/python -I ../meshy/cut.py label WORK                 # triangle labels (only the cloth labels are used here)
~/bvenv/bin/pip install scikit-image manifold3d xatlas scipy pillow
~/bvenv/bin/python -I split.py WORK          # voxel labels, one closed region per part, figure x region   (~5 min)
~/bvenv/bin/python -I joints.py WORK         # keyed peg + hole and magnet pockets at every joint          (~50 s)
~/bvenv/bin/python -I build.py WORK OUT      # bake, game GLB, print STL, assembled .blend                 (~2 min)
~/bvenv/bin/python -I render.py OUT          # parts sheet, assembled, exploded and posed renders          (~5 min)
node ../../../../scripts/publish-composite.mjs OUT/glb       # into apps/web/public/parts (no Blender), then compress, see below
~/bvenv/bin/python -I peek.py WORK OUT.png --explode 1 [--dir kit]   # quick flat-shaded check, a colour per piece
```

All of it runs headless in the cloud container (4 CPU cores, no GPU). Nothing needs to run on a laptop.

1. **split.py** labels a 0.25 mm voxel grid around the figure with the same rules as `../meshy/cut.py` (bone
   capsules, plus boxes for the helm, collar, spire, pods and blades, plus the red cloth triangles), hands small
   stray lumps to the neighbour they touch so each part stays one connected solid, turns each part's voxels into a
   smooth closed region, and intersects the figure with it (manifold3d). Meshy's UVs ride along as vertex
   properties; cut faces are marked with UV (-1, -1).
2. **joints.py** fits a D-section peg at each joint (`layout.TREE`). It searches axes (the cut face's normal, the
   bone, blends), centres and radii (3.0 down to 0.55 mm for the Paladin) on the voxel grid, and takes the biggest
   peg that takes a magnet whose root sits inside one part and whose hole, with a 0.4 mm wall, sits inside the other.
   The hole is 0.1 mm looser. The flat on the D keys the part. Where the peg is thick and long enough there is a
   pocket for a 3 x 2, 2 x 1 or 1 x 1 mm disc magnet flush in the peg tip and another at the bottom of the hole.
   With `STRICT = True` (the Paladin) each joint is also checked against the real solids, not only the voxel grid:
   each hole and its wall are reserved so a later hole keeps clear of them, a left part's hole in a centre part stays
   clear of its mirror image, and a 0.2 mm skin round each hole (from 1.5 mm below its mouth) must lie in the part,
   so no hole breaks out of its side. `CLEAR_MIRRORED` trims the pelvis and torso where the mirrored right thigh and
   pauldron would sink in (the figure is not symmetric).
3. **build.py** writes, per part: a print STL (the full-detail solid simplified to 0.015 mm, still closed), a game
   GLB (decimated to the old budget, xatlas UVs, Cycles bake of colour, roughness, metallic and normals from the
   solid; cut faces, pegs and holes bake as gunmetal), origin at its kit joint. `paladin_composite.blend` holds all
   parts, the right side mirrored from the left, parented joint to joint, so rotating the thigh swings the shin and foot.

## Parts

| Part | Plugs into | Notes |
| --- | --- | --- |
| pelvis | (root) | waist, hip armour and the front and back tabard |
| torso | pelvis | chest, collar and the banner on the back |
| helm | torso | |
| back | torso | the reliquary spire and its struts |
| pauldron | torso | the plate, the shoulder joint under it, and the cape |
| pauldron_r | torso | the right shoulder: the figure's own black pauldron and its long cape (gold cross, white sunburst) |
| arm | pauldron | Meshy put the shoulder ball inside the pauldron, so the upper arm hangs from it |
| forearm | arm | |
| hand | forearm | |
| thigh | pelvis | |
| shin | thigh | |
| foot | shin | |
| blade | hand | equipment: the siege blade (`item_lance@paladin`) |
| pod | torso or back | equipment: the shoulder pod (`item_carapace-gun@paladin`); a 2 mm peg, no magnet |

Sided parts are modelled once, for the walker's left, and mirrored for the right, so the right side now matches the
left (the Meshy figure's right arm hung differently). The exception is the right pauldron (`NATIVE_RIGHT` in
`paladin.py`, 2026-11-08): mirroring the left lost the figure's best feature, the long crimson cape on the right that
the concept art has, so `pauldron_r` is cut from the figure's own right side. It carries the left pauldron's pegs,
mirrored (into the torso's mirrored hole, and down into the mirrored arm), each on a round boss that reaches back into
the part until it is solid, and it is trimmed wherever the mirrored arm, forearm and hand sit (the Meshy right arm hung
in front of the cape; the mirrored one runs through its inner edge, which is hidden behind the arm). The cape's top
front was labelled arm by cut.py, which left a hole under the gold cross: `paladin.cloth_tris` takes the red there
as cape when it joins the cape's own cloth. OUT/report.json lists each part's size, volume and triangle counts and every
joint's peg, axis and magnet.

## Known limits

- Joints at 1.5x (OUT/report.json has every axis and centre). Peg across, then magnet:

  | Joint | 1x (before) | 1.5x |
  | --- | --- | --- |
  | thigh into pelvis | 1.1 mm, none | 6.0 mm, 2 x 1 |
  | torso / pelvis | 4.0 mm, 2 x 1 | 6.0 mm, 3 x 2 (peg now on the pelvis) |
  | helm into torso | 4.0 mm, 2 x 1 | 6.0 mm, 3 x 2 |
  | pauldron into torso | 4.0 mm, 2 x 1 | 6.0 mm, 3 x 2 |
  | spire (back) into torso | 3.0 mm, 2 x 1 | 3.0 mm, 2 x 1 |
  | arm / pauldron | 2.3 mm, none | 2.3 mm, 1 x 1 (peg now on the pauldron) |
  | forearm / arm | 2.3 mm, 1 x 1 | 3.5 mm, 2 x 1 |
  | hand into forearm | 2.6 mm, none | 4.4 mm, 2 x 1 |
  | shin into thigh | 3.0 mm, 2 x 1 | 2.3 mm, 1 x 1 |
  | foot / shin | 4.0 mm, none | 6.0 mm, 2 x 1 |
  | blade into hand | 1.7 mm, none | 2.6 mm, 2 x 1 |
  | pod into torso | no peg | 2.0 mm, none |

  The 1x knee and spire pegs were bigger only because the 1x check was voxel-only: at 1.5x the strict check finds a
  crease in the thigh just above the knee and a sloped face under the spire, and the bigger pegs would break out.
- Two Paladin-only changes to the cut (in `paladin.py`): the hips are fitted before the torso, so they get first pick
  of the pelvis (otherwise the torso's hole takes the room and the hips get a 2 mm peg); and Meshy sculpted a thin
  lip over a 0.5 mm slot at the top of the forearm, so the arm now takes the lip, the slot and the top 2 mm of the
  forearm and the elbow seam is a flat face through solid metal.
- Not test-printed. Magnet pockets are 0.1 mm over the stock size; check the fit on a test print first.
- The surface is still Meshy's sculpt; only the cuts, joints and symmetry are new. Torso, pelvis, helm and spire are
  not yet symmetrised. Cut faces are plain gunmetal, not designed sockets with detail.
- The Paladin's game parts are these now (see below). The old open-shell cut in `../meshy/` is kept for reference
  and for the other two Meshy models, but it no longer builds the Paladin.

## In the game

`scripts/publish-composite.mjs` copies OUT/glb into `apps/web/public/parts`: the 11 body parts as
`kit/covenant_<part>_paladin.glb` (left side only, the web mirrors the right) and the right pauldron as
`kit/covenant_pauldron-right_paladin.glb` (the web uses a `-right` part instead of the mirror), `blade` as `item_lance@paladin.glb` and
`pod` as `item_carapace-gun@paladin.glb`. Items are stored at scout scale with their origin on the grip or pod mount
(the web grows them by 1.7), so the script moves and scales their vertices; every other part keeps its joint origin.
It deletes the old `-right`, `cloth` and `collar` Paladin parts and edits the manifest. `data/model-kit.json`
`omit.paladin` stops the Titan collar and cloth filling in for the retired ones (the torso carries its own collar and
the pelvis its tabard). Then:

```sh
node scripts/compress-parts.mjs   # KTX2_NORMAL=etc1s KTX2_BASE_Q=150, on the 13 files (needs `npm i --no-save basisu`)
node scripts/item-bounds.mjs      # item boxes for the equipment fit
```

The 13 files came to 3.9 MB (the old cut was 4.5 MB with the right-hand copies, cloth and collar); with the shoulder and
bracer sockets (4.2 MB) and the right pauldron with its long cape (2026-11-08) the 14 come to 5.0 MB.

## The Paladin's items (Carapace Gun, Missile Rack, Kinetic Shield)

Three items for the Paladin, built the way the walker was: the shape is Meshy's, the fit is designed. Nothing is hand-modelled
from boxes. Two are new Meshy generations (a text-to-image reference in the Paladin's black, gold and red, then image-to-3D;
about 66 credits for both), the third is the pod the Paladin was already cut with.

```sh
python3 -I ../meshy/cut.py extract RACK.glb RACK_WORK                  # and the same for the shield
~/bvenv/bin/python -I paladin_items.py PARTS OUT --rack RACK_WORK --shield SHIELD_WORK --pod PALADIN_WORK   # ~35 s
~/bvenv/bin/python -I paladin_items_build.py PARTS OUT [--samples 32] [--only items|loadouts|sockets]    # bake ~2.5 min, renders ~6 min
```

PARTS is `models/paladin-composite-1.5x`; PALADIN_WORK is the Paladin's WORK folder after `split.py` (its `parts/pod.npz` is the
pod's textured solid). `paladin_items.py` writes `fit.json` and exits 1 if a check fails; `paladin_items_build.py` bakes through
`build.py` (so textures, budgets and cut-face materials are the walker's own) and writes the game GLBs, print STLs and
`paladin_items.blend`.

- **Shoulder hardpoint.** A gunmetal pedestal on each side of the torso's upper back, up to the pod's old seat plane, with the
  D hole and a magnet pocket in it: r 1.5 x 3.0 mm peg, 2 x 1 mm disc, 0.4 mm wall at least. Since 2026-11-08 it is shaped as
  a fitting rather than a plain 3.1 mm cylinder (which read as a tin can on the back): it flares into a 4 mm flange where it
  meets the torso, chamfers at the seat to the collar's own radius, and carries two proud gold bands like the collars'
  (`SHOULDER_BOSS`). The Carapace Gun and the Missile Rack use the same socket, either side. The boss is trimmed where the
  back spire, helm, pauldrons (the native right one on the right) and arms are, so nothing of the walker moves.
- **Bracer hardpoint.** The same hole in a boss on the forearm's outer face with a chamfered seat and a gold rim
  (`BRACER_BOSS`), tilted 12 degrees to follow the forearm (the face slopes in towards the elbow), seat 0.5 mm proud of the
  highest metal under the collar. The Kinetic Shield plugs into it. The native right pauldron's cape hangs past the right
  forearm, so it gives way to the mirrored socket (`stl/pauldron_r_clear.stl` is the right pauldron to print with the
  socketed forearm; what it loses is inside the forearm).
- **Sockets in the game.** `hosts/<socket>.npz` holds the visible part of each socket with crease-split normals and a gold
  flag per triangle; `scripts/publish-composite.mjs` merges them into the torso and forearm as a gunmetal and a gold
  primitive (build.py's cut-face and knuckle colours). The gunmetal is blackened steel, rougher than the cut faces (0.9):
  the seat is a flat disc facing up, and before 2026-11-08 (smoother, no normals) the stage's rim light glanced off it
  and bloomed into a white halo over the shoulders.
- **Items.** Each carries a gunmetal collar with two gold bands, then its own peg. The Carapace Gun keeps the Meshy pod but loses
  its old stem: the pod is a thin-walled lattice where no 3 mm disc fits, so the stem is cut flat and the new collar and peg
  carry it. The Missile Rack stands on its own Meshy post; the shield is stood off 2.6 mm from the forearm.
- **Checks** (fit.json): one closed piece; peg fills none of the host's metal; the hole and its wall lie inside the host; no
  clash with any part of the walker, at rest, mirrored on the right side too. The shield also bent at the elbow (-30, -45
  degrees): it grazes the pauldron by under 1 mm3, listed in fit.json as `bent_clashes_mm3`.
- Item frame: +Z out of the host, origin on the seat. Items are modelled for the left; the web mirrors them for the right.
  Game GLBs are at kit size (print mm / 1.5) with their origin on the `chest` joint (shoulder items) or the `elbow` joint
  (shield), like the other composite parts. **Not published to the game yet**: the hosts gained sockets (the torso and the
  forearm change), so publishing means re-baking the torso and forearm GLBs and re-tuning the fit entries.

## The Seer's Hellfire Missiles

The Hellfire Missiles were cut in the item rework (step 3) and come back as a composite part for the Seer, built like the
Paladin's items: Meshy's shape, a designed fit. No new Meshy credits: the launcher is the Oct 31 Meshy generation
(image-to-3D task `01a1938a-a9f8-7753-968d-3d86a411c7a7`, the one baked into the old `item_hellfire-missiles.glb`), whose
full-resolution source was still on Meshy and is now in the project folder at `meshy-sources/hellfire/`.

```sh
python3 -I ../meshy/cut.py extract meshy-sources/hellfire/01a1938a-....glb HF_WORK
MODEL=seer ~/bvenv/bin/python -I seer_items.py SEER OUT --hellfire HF_WORK        # search + checks, ~3 min, exits 1 on a failed check
MODEL=seer ~/bvenv/bin/python -I seer_items_build.py SEER OUT [--samples 32]     # bake, blend, renders, ~4 min
```

SEER is `models/seer-composite-v2` (its right arm is the mirror of the left). Outputs are in the project folder at
`models/seer-items/` and `renders/seer-items/`.

- **Launcher.** Two stacked missiles with curved blade tips on a shared housing, 17 mm long at print scale, blades forward,
  standing on a gunmetal collar with gold bands under the back of the housing. One closed piece; r 1.3 x 2.2 mm D peg with a
  2 x 1 mm magnet.
- **Shoulder hardpoint.** A socket in the Seer's own joint style (since the 2026-11-08 polish: a bronze body narrowing to a
  rounded foot, a gilded lip and a gold band) sunk into the shoulder drum on top of the `arm` part, with the hole and
  magnet pocket. The drum is a 2.2 mm half ball, too small to hold a magnet hole on its
  own, so the sleeve carries the 0.4 mm wall. Because the right arm is the mirrored left one, both shoulders have the socket
  and the one launcher fits either side. A torso mount was tried first and fails (the shoulder plate is too thin, and the back
  spires are in the way on the right).
- **Right pauldron.** On v2, whose native right pauldron's plate lay over the right shoulder drum, it got a 2.7 mm3
  clearance cut where the sleeve and collar come through (`stl/pauldron_r_cleared.stl`; in the blend, a boolean
  modifier). Since 2026-11-02 the right pauldron is the left one mirrored and needs none.
- **Checks** (fit.json): closed and one piece; peg fills none of the arm; hole wall inside the arm; no clash with any part on
  either side at rest, and none on the left with the arm swung 15 degrees either way.
- Item frame: +Z up out of the socket, -Y forward; the game GLB is at kit size with its origin on the socket seat.
  **In the game** (`node scripts/publish-composite.mjs SEER/glb seer ITEMS/glb`, then `compress-parts.mjs` on the arm and
  the launcher): until the 2026-11-08 polish the arm GLB carried the sleeve as a separate flat-gold primitive
  (`hosts/arm_sleeve.npz`); now seer_items.py, run on the work folder, fuses the socket into the kit arm
  (`ITEMS/kit/arm.npz`) and the arm is baked with it (see the Seer's Polish notes). `item_hellfire-missiles@seer.glb`
  has its origin on the socket seat, and `fit.hardpoints.shoulder-sockets` puts one on each shoulder. In the rules it is
  body equipment (core, 2 slots), so it takes no arm slot. Since the right pauldron became the left one mirrored, it
  needs no clearance cut.
- The serrated teeth and the thin ring behind the blades are about 0.1 mm thick at 17 mm: too thin to print cleanly. The
  missile bodies are 1.1 mm and the blades 0.3 to 1.3 mm.

## The Ashen Foundries Brute (MODEL=brute)

The same pipeline cuts Luke's Meshy Brute (`Meshy_AI_ashen_foundry_mech_..._image-to-3d-texture.glb`, 6.24M
triangles, also one closed surface). Its settings and the reasons for each change live in `brute.py`; every script
takes `MODEL=brute`, and the Paladin is the default, unchanged.

```sh
python3 -I ../meshy/cut.py extract Meshy_AI_ashen_foundry_..._texture.glb WORK    # no cut.py label needed
MODEL=brute ~/bvenv/bin/python -I split.py WORK        # ~2 min
MODEL=brute ~/bvenv/bin/python -I joints.py WORK       # ~1 min
MODEL=brute ~/bvenv/bin/python -I build.py WORK OUT    # writes OUT/brute_composite.blend
MODEL=brute ~/bvenv/bin/python -I render.py OUT        # adds swap.png: the guns swapped over
```

What the Paladin taught, and what the Brute does differently:

- **Cut at print scale.** The Paladin's pegs were cut for 1x, so its thigh peg was 1.1 mm. The Brute is cut at Luke's
  1.5x print scale (2.1x the bulwark kit, since the web grows bulwark parts by 1.4): about 75 mm to the helm top.
  Pegs go up to 8 mm across and pockets take stock 5 x 2, 3 x 2 or 2 x 1 mm magnets. Game GLBs are scaled back to
  kit size with origins on the `foundries/bulwark` joints, so they can replace the open-shell parts in place.
- **Symmetric limbs, symmetric labels.** Every sided part is cut from the walker's left and mirrored, so one pauldron
  card and one leg card fit either side, and the right half of the torso and pelvis is carved where the mirrored
  parts will sit (the labels use |x|). Anything that would still overlap is trimmed off the centre parts, so the
  assembled walker has no clashing volume. The torso, pelvis, helm and stacks keep Meshy's asymmetric detail.
- **Parts follow the machine, not the human skeleton.** The Brute has no hands: below the elbow each forearm is a gun.
  So each gun is a whole forearm, and the 3 mm upper-arm stub hidden under the pauldron joins the pauldron (the
  shoulder unit). That replaces three thin joints (shoulder to arm, elbow, wrist) with one, at the elbow.
- **Designed sockets where the sculpt gives none.** The Paladin's pod had no peg. The Brute's gatling, which Meshy
  holds raised on the right arm, is mirrored, turned onto the cannon arm's barrel axis, moved onto its breech, trimmed
  where it would clash with the pauldron, and given the cannon's exact peg plus a collar to carry it. Both guns use one
  socket, so either fits either elbow (`render.py` shows the swap).
- **Pegs both ways.** `joints.py` tries the peg on the child and on the parent and keeps the one that holds better
  (bigger magnet, then girth times length), which turned the hip from a 3 mm peg into a 4.6 mm one with a 3 x 2 magnet.

| Part | Plugs into | Notes |
| --- | --- | --- |
| pelvis | (root) | waist, hip armour, the hip pegs for both thighs |
| torso | pelvis | the furnace box, the "07" plate, the big chimney behind the left shoulder |
| helm | torso | with its crown tower |
| back | torso | rear pack, the exhaust drum and the antennae |
| pauldron | torso | shoulder plate, its stack and antennae, and the upper-arm stub; the elbow socket is underneath |
| thigh | pelvis | |
| shin | thigh | |
| foot | shin | |
| rockets | pauldron | weapon forearm: the cannon with its rocket box (`item_rocket-pod@brute`), left by default |
| gatling | pauldron | weapon forearm (`item_autocannon@brute`), right by default, on the cannon's socket |

`brute_composite.blend` holds every part with both guns on both arms; the default loadout (cannon left, gatling
right) is shown and the other two are hidden spares (custom property `spare`).

### The Brute in the game

```sh
node scripts/publish-composite.mjs ../models/brute-composite/glb brute     # from the build output
KTX2_NORMAL=etc1s KTX2_BASE_Q=150 node scripts/compress-parts.mjs <the files this prints>
node scripts/item-bounds.mjs
```

The 8 body parts become `kit/foundries_<part>_brute.glb` (left only; the web mirrors the right) and the two guns the
items `item_rocket-pod@brute` (rockets) and `item_autocannon@brute` (gatling). The old open-shell Brute parts (arm,
forearm and hand, and every `-right` copy) are deleted and dropped from the manifest, and `data/model-kit.json`
`omit.brute` keeps the Bulwark's arm, forearm, hand and collar from filling in. The 8 parts and 2 guns come to 4.4 MB
(the old cut was 5.25 MB).

Each gun is built with its origin on the elbow; the script moves it onto the numbered arm mount (`mount_armLeft_0`) the
old brute items used, and divides by 1.4, so the fit hardpoints work unchanged. Both guns are modelled for the left
now (the gatling was mirrored onto the cannon's socket), so `autocannon@brute` left `fit.nativeRight`.
An arm slot with nothing equipped shows the pauldron's gunmetal elbow socket and no forearm.

### Brute polish (2026-11-08)

The cut kept every shape and texel of Meshy's Brute but lost what makes the concept read: the glowing furnace, the hot
eyes, and red lacquer that looks different from brass and black iron. `brute_polish.py` (wired in at the end of
`brute.py`) puts that back; the commands are the usual Brute ones above (split, joints, build), and nothing moves a joint,
peg or magnet (joints.py gives the same pegs and magnets as before).

- **Finishes.** Meshy's metal/roughness map is about 0.45 / 0.45 everywhere, so in the game the whole walker shone alike
  and the back mirrored the foundry stage's red rim light. `surface_textures` writes WORK/tex_mr_polish.png from the colour:
  paint (red, white stencils, ochre panels) metal 0 rough 0.58, brass 0.9 / 0.34, blackened iron 0.6 / 0.6, with Meshy's
  own roughness kept as wear. build.py loads it in place of tex_1 for any model with `surface_textures`.
- **Glow.** `glow_weight` marks the furnace window under the "07" plate and the eye slits (`GLOW_BOXES`, Meshy units);
  build.py stores it as a `glow` vertex attribute, bakes an extra emissive map for the parts that have any (torso, helm),
  and exports it with `GLOW_STRENGTH` 3 (KHR_materials_emissive_strength). The web needs no change: three's glTF loader
  reads it and the stage's bloom does the rest.
- **Antennae.** Meshy's 0.3 to 0.6 mm wire antennae (eight on the walker) were unprintable and read as stray hairs, but
  the concept has them. `design` re-makes each as a rod tapering 0.9 to 0.6 mm with a knob, on the wire's own line and
  height. One wire beside the chimney was split between the back and the torso (the two would have clashed by 8 mm3): an
  antenna now has one owner and is cleared out of every other part.
- **Sharper maps.** `NORMAL_SIZE = 1024`, `ORM_SIZE = 512` (build.py's defaults stay 512 and 256 for the other models).
- **Published:** the 8 body parts only, compressed with the Brute's recipe (`KTX2_NORMAL=etc1s KTX2_BASE_Q=150`): 3.6 to
  4.9 MB. The guns are rebaked in the .blend but not republished (Luke: the cannon arm and the gatling are "essentially
  perfect"); `publish-composite.mjs DIR brute` stops at the guns if DIR has only the body parts, after writing them.

### The Brute's claw and rail cannon on the elbow socket

The Industrial Claw and the Rail Cannon keep the sculpts every walker uses (`item_industrial-claw`, `item_rail-cannon`),
but the Brute gets its own copies cut onto the cannon arm's elbow socket, so they seat on the socket like the guns
instead of floating on the `grip` hardpoint. No new Meshy generation: the original high-detail sculpts are in the Meshy
account history and download for free (`GET /openapi/v1/image-to-3d?sort_by=-created_at`; the claw is task
`01a1938a-a9e6-74d1-993b-e3a0016057bf`, the rail cannon `01a1937f-24c3-70d2-be1a-a567272c27ad`).

```sh
python3 -I ../meshy/cut.py extract CLAW.glb WORK_CLAW
MODEL=brute ~/bvenv/bin/python -I item_cut.py WORK_CLAW claw PARTS --length 30 --muzzle - --boss-at 0.14
MODEL=brute ~/bvenv/bin/python -I item_cut.py WORK_RAIL rail PARTS --length 33 --muzzle - --boss-at 0.15 --girth 1.35
echo '{}' > WORK/joints.json; MODEL=brute ~/bvenv/bin/python -I build.py WORK OUT claw     # (and rail): STL, game GLB, OUT/claw_part.blend
MODEL=brute ~/bvenv/bin/python -I brute_items_build.py PARTS REVIEW claw=OUT_CLAW rail=OUT_RAIL   # renders on the walker
node scripts/publish-composite.mjs DIR_WITH_claw.glb_AND_rail.glb brute --items   # then compress-parts and item-bounds
```

PARTS is the Brute composite build (`stl/`, `report.json`, `brute_composite.blend`). `item_cut.py` points the prop where the
cannon arm's barrel points (the jaws or muzzle forward; `--muzzle -` because these sculpts have more vertices at the
business end), scales it to `--length` print mm, puts the top of the housing at `--boss-at` of the length from the rear
on the socket, subtracts the rest of the walker, and adds the gatling's collar and the cannon arm's exact peg
(`brute_socket.py`: 3 mm D-section, 3.5 mm long, 2 x 1 mm magnet). `--girth` thickens a prop across its length: the rail
cannon is 1.35x thicker than the sculpt, which was spindly next to the Brute's guns and thin for a print. Check
`WORK/item.json`: `trimmed_mm3` and `swing_clash_mm3` should be empty (the arm swung 15 degrees either way touches nothing).

| Item | Size (print mm) | Notes |
| --- | --- | --- |
| `item_industrial-claw@brute` | 12 x 29 x 21 | the original claw, unchanged except the collar and peg; one closed piece |
| `item_rail-cannon@brute` | 10 x 33 x 20 | the original rail cannon, 1.35x girth; one closed piece |

Both are whole forearms with their origin on the elbow, so the claw, the rail cannon, the cannon arm and the gatling all
fit either elbow; modelled for the left, the web mirrors them for the right.

## The Reliquary Seer (MODEL=seer)

Luke's Meshy Gilded Seraphim, rebuilt as 17 closed parts. Same steps, with `MODEL=seer` and no `label` step (the
Seer's rules work on the voxels directly; the banner is found by its red texels):

```sh
python3 -I ../meshy/cut.py extract Meshy_AI_The_Gilded_Seraphim_..._texture.glb WORK
MODEL=seer ~/bvenv/bin/python split.py WORK        # ~5 min
MODEL=seer ~/bvenv/bin/python joints.py WORK       # ~1 min
MODEL=seer ~/bvenv/bin/python build.py WORK OUT    # bake, game GLB, print STL, seer_composite.blend
MODEL=seer ~/bvenv/bin/python render.py OUT
```

`-I` is fine too (it ignores `PYTHON*` variables, not `MODEL`); run from a folder of your own.

What the Paladin taught, and what changed for the Seer:

- **Print scale.** Like the Brute, the Seer is cut at Luke's 1.5x collector scale (`PRINT_SCALE`; print mm = kit mm x
  scale), about 56 mm to the helm top and 68 mm to the crown spire, and build.py scales the game GLBs back to kit mm.
  The Paladin is now cut at 1.5x too.
- **Designed joints.** The Seer's limbs are rods about 1.2 mm thick even at 1.5x, so no peg fits where Meshy joins them.
  Every limb joint (neck, shoulders, elbows, wrists, hips, knees, ankles) now has a gilded ball knuckle with a sleeve
  that runs deep into the parent part, and the cut between the parts is the plane through the ball's centre, square to
  the bone. Each part gets half a ball with a flat round face; the peg grows from the child, the hole (with its magnet)
  sits in the parent's housing. Since the 2026-11-08 polish (below) the ball is aged gold in a dark housing with gold
  trim; the gold carries UV (-2, -2) (`KNUCKLE_FINISH`), the housing's bronze UV (-3, -3) (`FRAME_FINISH`).
- **Pegs never cut through a neighbour.** joints.py clears each peg's whole length, with clearance, out of every part it
  passes through, not only the parent (`passes_through` in joints.json). The Seer's fit check found pegs running through
  a third part (the right pauldron sits between the arm and the torso).
- **Magnets first.** With `PREFER_MAGNET`, joints.py takes the biggest peg that also takes a magnet, rather than the
  biggest peg. Magnet sizes now include 3 x 2 mm.
- **One arm, mirrored (2026-11-02).** The first cut built both arms natively, but the Meshy right arm is bent to couch
  its spear and read badly on its own, and the left hand had a sword grown into it, so a second spear doubled up. Now
  the left hand's sword is cut off below the fist (`SWORD`, `SWORD_CUT`: the hand's voxels past the bottom of the fist
  along the blade go to a throwaway `_sword` part), the fist gets the spear bore, and the right arm is the left one
  mirrored (`arm`, `forearm`, `hand` are in `SIDED`, the Meshy right arm's voxels only carve the torso). The pauldrons
  and wings stay native to each side; `CLEAR_MIRRORED = ("arm", "forearm", "hand")` trims the right pauldron where the
  mirrored arm sits. Legs are built for the left and mirrored, like the Paladin.
- **One solid per part.** The left wing is a loose shell in the Meshy file. `seer.design()` fuses any loose piece of a
  part to its body with a short gold strut, and drops crumbs.
- **Held equipment.** In the Meshy figure the spear is couched under the right arm and touches it only at the elbow,
  with no room for a peg. It is now held in the fist, either side: turned onto the line of the old sword, then searched
  over small turns (up to 30 degrees, and about its own axis) until it clears the arm, body and legs and its tip stays
  above the base. The spear is about 40 mm long and the fist hangs low, so it ends up pointing down and forward, like the
  single spear Luke liked on the left. The grip stretch is trued up as a 1.6 mm round shaft and a 1.72 mm bore is cut
  through the fist. It is a push fit and can be turned in the fist to set its angle.
- **Centre line.** The first Seraphim cut used x = 0.28 as the centre; slices of the mesh (shoulder orbs, feet) put it at
  0.235. The Seer measures its own joints (`JOINTS_ABS`) instead of reading `frameTunes["reliquary/striker"]`, so the
  game's frame tunes will need updating when these parts are published.

### Seer parts

| Part | Plugs into | Notes |
| --- | --- | --- |
| pelvis | (root) | waist, the loincloths front and back, the banner below the waist |
| torso | pelvis | chest, collar, the banner above the waist, the pendants on the back |
| helm | torso | on a neck knuckle |
| crown | helm | the halo and its crown spire (thin contact: an r 0.75 mm peg, no magnet) |
| back | torso | the reliquary spires |
| pauldron | torso | shoulder plate and wing (the left wing was a loose shell; now fused); on a small knuckle; mirrored for the right since 2026-11-02 (the native right wing's spar read as a third arm) |
| arm, forearm, hand | torso, arm, forearm | mirrored for the right; the fist still has the old spear bore (the sword is gone) |
| thigh, shin, foot | pelvis, thigh, shin | mirrored for the right |
| spear | (raw material) | cut by `seer_wrist.py` into the wrist-socket arc spear, below |

### Polish (2026-11-08)

Luke asked for a careful look at each Meshy walker's rough edges (the Meshy first pass often looked better than the game
model). On the Seer, three things let it down, and all three were ours rather than Meshy's:

- **Knuckles read as tin cans.** Every joint was a polished gold ball inside a gold can as wide as the ball, so the limbs
  were strings of bright cylinders that bloomed in the game. The size is fixed by the peg (hole plus a 0.4 mm wall), so
  the look changed, not the envelope (`seer.knuckle_solid`, `HOUSING`): the ball is aged gold (darker, less glossy,
  close to Meshy's own gilding texels), with a slim seam band where the parts meet; the housing up the parent's bone is
  darkened bronze, narrowing a little, with a gold collar at the ball, a gold band at its top and a short cone into the
  limb instead of a lid (near-black was tried first and read as black cans on the figure); the child's half of the ball has a slim gold collar where its limb leaves it (along the
  upper arm at the shoulder, `CHILD_AXIS`). seer_elbow.py and seer_wrist.py use the same solids (the elbow's seam sits on
  the bent cut, the spear's ferrule is a housing).
- **Dark patches round the balls.** The parts are cut from smoothed voxel regions, and the smoothing rounded off the
  region's edge a few tenths of a mm inside the ball's rim, so cut-face metal showed through in patches. `design()` now
  gives each part the exact half of every knuckle it meets (`true_knuckles`, split on the plane through the ball's
  centre). The labelled region below the cut is back to 0.7 of the ball's radius (it had been cut to nothing with the old
  child-side can): shallower, the forearm's cuff wrapped under the hand's ball and the hand no longer pulled straight off.
  The hip housings are shorter (`HOUSING_TOP`): at full length their tip reached the torso's side of the waist cut and
  the torso caught on it when lifted off.
- **The designed surfaces looked like new plastic, and streaked.** Flat colours next to Meshy's worn gilding. With
  `DESIGNED_WEAR` build.py bakes the cut faces, gold and bronze with darker crevices (ambient occlusion over the part's own
  shape) and a faint mottle in colour and roughness (`wear()`). And every designed solid is a few long side triangles
  between hard rims: smooth shading averaged the rims' normals down those triangles, and the bake turned that into
  bright streaks down every knuckle. With `SHARP_DESIGNED` the bake source gets sharp edges wherever a designed face
  meets another at more than 35 degrees (`sharpen()`; Meshy's own surface stays smooth).
- **The chest glared.** Meshy's roughness map is near mirror-smooth in places (the chest plate: median 0.29, a quarter
  under 0.1), and the game's bloom turned its highlights into white glare. `ROUGH_FLOOR = 0.42` keeps the baked
  roughness at or above that: the highlights spread into a sheen, closer to how Meshy's own viewer lit it.
- **Blocky normals in the game.** With ETC1S normal maps (`KTX2_NORMAL=etc1s KTX2_BASE_Q=150`, what the other walkers
  use) the chest showed square blocks in its shading. The Seer's parts are compressed with the script's defaults
  instead (UASTC normal maps, colour at quality 200): about 6.3 MB for the twelve body parts instead of 3.9 MB, and the
  shading matches the uncompressed parts.
- **The Hellfire sockets were flower pots.** The game drew the shoulder sleeves as a separate untextured bright-gold mesh
  that bloomed, with green environment stripes. The sleeve is now in the joints' style (bronze tapered body, gilded lip,
  gold band, rounded foot), and it is part of the arm itself: `seer_items.py` run on the work folder writes the arm with
  its socket fused on (`ITEMS/kit/arm.npz`), so the arm's bake carries it and `publish-composite.mjs` no longer merges a
  gold primitive into the arm.

The rebuild, from the Meshy files (about 45 minutes):

```sh
python3 -I ../meshy/cut.py extract Meshy_AI_The_Gilded_Seraphim_..._texture.glb WORK
python3 -I ../meshy/cut.py extract meshy-sources/hellfire/01a1938a-a9f8-....glb HF
python3 -I ../meshy/cut.py extract meshy-sources/kinetic-claws/01a1938a-aa42-....glb CLAWS
MODEL=seer ~/bvenv/bin/python split.py WORK && MODEL=seer ~/bvenv/bin/python joints.py WORK
MODEL=seer ~/bvenv/bin/python -I seer_elbow.py WORK BENT --deg 25
MODEL=seer ~/bvenv/bin/python -I seer_items.py BENT ITEMS --hellfire HF       # writes ITEMS/kit/arm.npz, the arm with its socket
MODEL=seer ~/bvenv/bin/python -I seer_wrist.py BENT WRIST --claws CLAWS
cp ITEMS/kit/arm.npz BENT/kit/arm.npz && rm BENT/kit/spear.npz              # the spear is raw material for seer_wrist.py
MODEL=seer ~/bvenv/bin/python -I build.py BENT OUT                          # every part, seer_composite.blend
MODEL=seer ~/bvenv/bin/python -I build.py WORK HAND hand                    # the game hand, unbent (turned below)
node scripts/turn-part.mjs HAND/glb/hand.glb OUT/glb/hand.glb BENT/bend.json
MODEL=seer ~/bvenv/bin/python -I seer_wrist_build.py OUT WRIST --bend BENT/bend.json
MODEL=seer ~/bvenv/bin/python -I seer_items_build.py OUT ITEMS
MODEL=seer ~/bvenv/bin/python -I render.py OUT
```

### The Seer in the game

```sh
node scripts/publish-composite.mjs ../models/seer-composite/glb seer ITEMS_GLB   # build output; ITEMS_GLB holds the spear,
                                                                              # claws and launcher GLBs (seer_wrist_build.py, seer_items_build.py)
node scripts/compress-parts.mjs <the files this prints>      # the defaults: UASTC normal maps (see Polish, above)
node scripts/item-bounds.mjs
```

No Blender needed. The 12 body parts become `kit/reliquary_<part>_seer.glb`, left only (the web mirrors the arm,
pauldron and legs); the old `-right` arm, forearm, hand and pauldron are deleted and dropped from the manifest. The arc
spear and the claws come from `seer_wrist.py` (below), published with its glb folder as the items folder. `data/model-kit.json` `omit.seer` keeps the Striker's collar from
filling in (the torso has its own).

The script also writes the Seer's skeleton onto `reliquary_frame_striker.glb` from `frameTunes["reliquary/striker"]`:
the new joints, and `mount_armLeft_0` placed on the left fist's grip (`mount_armRight_0` is its mirror; the Seer's own
weapons no longer use it). Since the
right arm became the mirror of the left, the Seer has no `jointsRight` any more.
(`assets/blender/kit/skeleton.py` still reads `jointsRight` where a model has one.) The helm is built on the neck
knuckle but hangs on `joint_head`; the script moves its vertices by the difference. The spear's origin is its grip, which
is where the mount is, so it only needs dividing by 1.2 (the web's Striker part scale).

### The Seer's wrist weapons: arc spear and kinetic claws

Luke (2026-11-02): a spear pushed through the fist and claws hung by the hand do not suit magnetic parts, since nothing
should be carried. Like the Paladin's siege blade they now continue the arm: each one replaces the hand on its wrist socket.

```sh
python3 -I ../meshy/cut.py extract 01a1938a-aa42-71d6-beb1-9ff035b5041d.glb CLAWS   # meshy-sources/kinetic-claws/ (Meshy history, no credits)
MODEL=seer python3 -I seer_elbow.py WORK BENT --deg 25                # bend the elbow: re-cut arm/forearm, turn the hand (checks)
MODEL=seer python3 -I seer_wrist.py BENT WRIST --claws CLAWS          # BENT holds WORK + the bent kit, joints.json, bend.json (~1 min)
MODEL=seer ~/bvenv/bin/python -I seer_wrist_build.py SEER WRIST --bend BENT/bend.json   # bake, seer_wrist.blend, renders
node scripts/turn-part.mjs hand.glb hand_bent.glb BENT/bend.json      # the game hand turned with the forearm, no rebake
node scripts/publish-composite.mjs SEER/glb seer WRIST/glb --items    # item_arc-cannon@seer, item_kinetic-claws@seer
```

- **The socket is the hand's.** Each weapon carries an exact copy of the hand's half ball, sleeve and peg (r 1.15 mm D,
  1 x 1 mm magnet), cut out of the hand itself, so it pushes into the forearm's existing hole and the forearm is unchanged.
  Swap hand, spear and claws freely. `fit.json` checks: closed, one piece, no clash with either side of the walker or the
  base, the peg matches the hand's exactly, and a straight 6 mm pull along the socket axis clears the forearm.
- **Spear.** The Seraphim's own spear without its bulky rear housing (what stuck up behind the arm): a gilded sleeve in the
  knuckles' style runs from the half ball onto the shaft and the blade grows out of the wrist. Its angle off the forearm's
  line is searched, smallest first; with the bent elbow it sits straight on (0 degrees), scaled 0.8 to about 15 mm.
- **Claws.** The original Meshy claws (Luke liked the Oct 31 weapon batch; no new generation), the gauntlet's rear cut off,
  the big glowing rings round the wrist ball so they go on like a glove; the ring shells are fused on with short gold struts.
  Scaled 0.9 to about 14 mm, straight down the forearm's line.
- **Bent elbow (second pass, Luke's sketch review).** The arms read too long and stiff with the weapons tilted, so
  `seer_elbow.py` turns the forearm and hand 25 degrees forward about the elbow ball's centre: the cut plane between arm
  and forearm is re-cut on the bisector, the knuckle halves swapped across it, the peg stays on the arm bone (r 1.3 x
  2.6 mm, 1 x 1 mm magnet) and the wall round it is checked against the unbent baseline. Only arm and forearm are rebaked;
  the hand is the same print part, placed turned. In the game `frameTunes.reliquary/striker.wrist` moves to the bent wrist.
- **In the game.** The items' origin is the wrist joint. `fit.hardpoints.wrist-socket` (joint wrist, no offset, `hides:
  ["hand"]`) takes them, and `fit.overrides.seer.grip.nativeAs` sends the Seer's own copies there instead of the numbered
  grip; the web hides the hand on that side (`assemble.ts`). A shared (non-Seer) copy still goes to the grip.
- **Mirrored pauldron.** `swap_parts.py` puts the re-cut torso, pauldron and back (the only parts the mirrored pauldron
  changes) into the assembled v2 walker without rebaking the rest.

## The Covenant Sentinel (MODEL=sentinel)

New walker from the Meshy pilot (`docs/model-pipeline-plan.md`): concept art, then one whole-body model, then this cut. Settings in
`sentinel.py`; the figure is z -1..1 (Meshy normalised it), centre line x = 0. The model has no hands on the right: the forearm is the
Carapace Gun, cut from the right and re-seated on the left forearm's socket like the Brute's gatling (`RESEAT`).

```sh
python3 -I ../meshy/cut.py extract model.glb WORK       # the retextured GLB, 3.8M triangles
~/bvenv/bin/python -I repair_mesh.py WORK               # closes Meshy's pin-holes (manifold3d refuses the raw mesh)
MODEL=sentinel ~/bvenv/bin/python -I split.py WORK      # ~1.5 min
MODEL=sentinel ~/bvenv/bin/python -I joints.py WORK     # ~2 min
MODEL=sentinel ~/bvenv/bin/python -I build.py WORK OUT  # ~4 min
MODEL=sentinel ~/bvenv/bin/python -I render.py OUT      # ~4 min
```

`~/bvenv` here is a Python 3.11 venv with `pip install bpy scikit-image manifold3d xatlas scipy pillow trimesh`, and
`apt-get install libegl1 libgl1` for Workbench. Results and notes: `docs/sentinel-composite/`.

Polish pass (2026-11-09; before and after in `docs/sentinel-composite/`):

- **Level gun.** `RESEAT_POSE = {"gun": "mirror"}` makes joints.py keep the gun in the pose Meshy sculpted (level,
  pointing forward, as in the concept) instead of turning it 66 degrees onto the forearm's line, which hung it barrel-down
  to the ground. This works because Meshy's two upper arms are mirror images, so the mirrored gun already sits on the left
  elbow. The gun then gets the forearm's peg and collar as before, and `pull_clear` trims whatever of it the upper arm would
  block when the gun is pulled straight off along the peg axis.
- **Covenant finish.** `covenant_grade.py` grades Meshy's dusty khaki and grey-brown retexture to the Paladin's black enamel,
  bright worn gold and crimson (soft per-texel classes by hue, saturation and brightness; each class moved to the Paladin's
  baked colour, roughness and metal; dust on the dark plate calmed). It writes WORK/tex_0_covenant.jpg and tex_1_covenant.jpg
  (Meshy's own files are left alone) and sentinel.py's `surface_textures` hands them to build.py.
- **Amber eyes and grille.** Meshy painted the concept's lights as cream texels: two slanted eyes under the helm's brow and
  the furnace window behind the chest grille. `covenant_grade.lamp_mask` finds those texels through the mesh's UVs inside
  sentinel.py's glow regions (`GRILLE`, `EYES`), `glow_map` turns them into amber light (tex_glow.png) and darkens their own
  colour to amber glass, so they read as light rather than as pale paint; `glow_weight` gives build.py the same regions.
  build.py now drops an emissive map that bakes black (a part that touches a glow region but has nothing lit there).

## The Foundries Artillery (MODEL=artillery)

Second new walker from the Meshy pipeline. Settings in `artillery.py`; the figure is z -0.80 to 0.80 with its centre line at x = 0.09.
Same steps as the Sentinel (`cut.py extract`, `repair_mesh.py`, then `split.py`, `joints.py`, `build.py`, `render.py` with `MODEL=artillery`;
about 4 + 1 + 2 + 3 minutes). Meshy's invented third leg is dropped (`REAR_LEG`), the head is a dome stand-in (`HELM`), and the howitzer
stays with the torso. Notes: `docs/artillery-composite/`.

Polish pass (2026-11-09): `artillery_polish.py` holds the `design` hook (designed clawed feet, a level rear plate with lames and a
hatch, a cupola, stray rods cut away). `split.py` re-stamps each part named in the model's `CHANGED` into the voxel grid after
`design`, so `joints.py` measures against the new shapes. `paint.py` paints panel by panel (`M.paint`), designed solids carry their
finish as a UV code, and `build.py` bakes the per-corner paint attributes, a stencil atlas (`M.stencil_atlas`) and optional glow;
`GAME_SPLIT` gives the game mesh split normals. Notes and renders: `docs/artillery-composite/`.

## The Reliquary Goliath (MODEL=goliath)

Third walker from the Meshy pipeline. Settings in `goliath.py`; the figure is z -1..1, centre line x = 0, and the mesh is mirrored in x
once after `cut.py extract` (so the Arc Cannon falls on the figure's right):

```sh
python3 -I ../meshy/cut.py extract meshy-sources/goliath/model/01a1b612-.../model.glb WORK
python3 -c "import numpy as np; a=dict(np.load('WORK/mesh.npz')); a['V'][:,0]*=-1; a['F']=a['F'][:,::-1].copy(); np.savez('WORK/mesh.npz',**a)"
~/bvenv/bin/python -I repair_mesh.py WORK
MODEL=goliath ~/bvenv/bin/python -I split.py WORK && MODEL=goliath ~/bvenv/bin/python -I joints.py WORK   # ~3 min
MODEL=goliath ~/bvenv/bin/python -I build.py WORK OUT && MODEL=goliath ~/bvenv/bin/python -I render.py OUT  # ~3 + 5 min
```

Polish pass (2026-11-09; notes and before/after in `docs/goliath-composite/`):

- **Reliquary grade.** Meshy's retexture came out one dusty khaki stone (metallic 0.09), so the model read pale bone head to foot.
  `reliquary_grade.py` sorts each texel by brightness into bone, aged gold or black frame metal, with the split set by the region it
  lies on (`goliath.gilt`, drawn into UV space through the mesh by `uv_raster`): on the hood, chest plates and wings the plates stay
  bone and only the ribbing turns gold; on the limbs, cannon, spires and halo nearly everything but the frame turns gold. Red goes
  to deep crimson, teal stays teal. It writes WORK/tex_0_reliquary.jpg, tex_1_reliquary.jpg and tex_glow.png (Meshy's files stay).
- **Soul-light.** The teal texels in the chest cage and the pack's core (`goliath.CAGE`, `CORE`) light up, and two slanted eye slits
  (`EYES`, not painted by Meshy) are lit on the dark face under the hood. `glow_weight` gives build.py the same regions.
- **Knuckles.** The gold-sleeve "top hats" are replaced by the Seer's polished knuckle (`seer.knuckle_solid`), with the exact halves
  put back after the cut (`true_knuckles`). The finish is matched to this figure's gold (the Seer's pale ball and olive housing read
  grey here); the upper arm is a bronze rod with three gold ribs, and the palm is bronze under gold claws.
