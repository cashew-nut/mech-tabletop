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
| arm | pauldron | Meshy put the shoulder ball inside the pauldron, so the upper arm hangs from it |
| forearm | arm | |
| hand | forearm | |
| thigh | pelvis | |
| shin | thigh | |
| foot | shin | |
| blade | hand | equipment: the siege blade (`item_lance@paladin`) |
| pod | torso or back | equipment: the shoulder pod (`item_carapace-gun@paladin`); a 2 mm peg, no magnet |

Sided parts are modelled once, for the walker's left, and mirrored for the right, so the right side now matches the
left (the Meshy figure's right arm hung differently). OUT/report.json lists each part's size, volume and triangle
counts and every joint's peg, axis and magnet.

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
`kit/covenant_<part>_paladin.glb` (left side only, the web mirrors the right), `blade` as `item_lance@paladin.glb` and
`pod` as `item_carapace-gun@paladin.glb`. Items are stored at scout scale with their origin on the grip or pod mount
(the web grows them by 1.7), so the script moves and scales their vertices; every other part keeps its joint origin.
It deletes the old `-right`, `cloth` and `collar` Paladin parts and edits the manifest. `data/model-kit.json`
`omit.paladin` stops the Titan collar and cloth filling in for the retired ones (the torso carries its own collar and
the pelvis its tabard). Then:

```sh
node scripts/compress-parts.mjs   # KTX2_NORMAL=etc1s KTX2_BASE_Q=150, on the 13 files (needs `npm i --no-save basisu`)
node scripts/item-bounds.mjs      # item boxes for the equipment fit
```

The 13 files come to 3.9 MB (the old cut was 4.5 MB with the right-hand copies, cloth and collar).

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
  sits in the parent's sleeve. The sleeve has a domed end and two raised bands so it reads as a joint housing, not a
  can. Knuckles carry UV (-2, -2) and bake as polished gold (`KNUCKLE_FINISH`).
- **Pegs never cut through a neighbour.** joints.py clears each peg's whole length, with clearance, out of every part it
  passes through, not only the parent (`passes_through` in joints.json). The Seer's fit check found pegs running through
  a third part (the right pauldron sits between the arm and the torso).
- **Magnets first.** With `PREFER_MAGNET`, joints.py takes the biggest peg that also takes a magnet, rather than the
  biggest peg. Magnet sizes now include 3 x 2 mm.
- **Both arms are their own.** The Seer's asymmetry is its character (sword hand on the left, spear on the right), so
  the arms and pauldrons are built natively for each side (`arm`, `forearm`, `hand`, `pauldron`, and `*_r`). Legs are
  built for the left and mirrored, like the Paladin.
- **One solid per part.** The left wing is a loose shell in the Meshy file. `seer.design()` fuses any loose piece of a
  part to its body with a short gold strut, and drops crumbs.
- **Held equipment.** In the Meshy figure the spear is couched under the right arm and touches it only at the elbow,
  with no room for a peg. It is now held: moved so a plain stretch of shaft runs through the right fist, turned (search
  over small rotations) until it clears the body and legs, the grip stretch trued up as a 1.6 mm round shaft, and a
  1.72 mm bore cut through the fist. It is a push fit and can be turned in the fist to set its angle.
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
| pauldron | torso | left shoulder plate and wing (the wing was a loose shell; now fused); on a small knuckle |
| pauldron_r | torso | right shoulder plate and wing |
| arm, forearm, hand | torso, arm, forearm | left: the hand carries the downward sword |
| arm_r, forearm_r, hand_r | torso, arm_r, forearm_r | right: the fist has the spear bore |
| thigh, shin, foot | pelvis, thigh, shin | mirrored for the right |
| spear | hand_r (held) | equipment: `item_arc-cannon@seer` |

### The Seer in the game

```sh
node scripts/publish-composite.mjs ../models/seer-composite/glb seer     # from the build output
KTX2_NORMAL=etc1s KTX2_BASE_Q=150 node scripts/compress-parts.mjs <the files this prints>
node scripts/item-bounds.mjs
```

No Blender needed. The 16 body parts become `kit/reliquary_<part>_seer.glb`; the right arm and pauldron (`arm_r`,
`forearm_r`, `hand_r`, `pauldron_r`) publish as the `-right` variants, so the web uses them as they are instead of
mirroring the left. The legs are left only (the web mirrors them), and the old open-shell `thigh-right`, `shin-right`
and `foot-right` are deleted and dropped from the manifest. The spear is `item_arc-cannon@seer`. All of it comes to
5.1 MB. `data/model-kit.json` `omit.seer` keeps the Striker's collar from filling in (the torso has its own).

The script also writes the Seer's skeleton onto `reliquary_frame_striker.glb` from `frameTunes["reliquary/striker"]`:
the new joints, `jointsRight` for the right shoulder, elbow and wrist (the Seer's right arm is posed differently, so it
is not the mirror of the left), and `mount_armRight_0` placed on the spear's grip (`mount_armLeft_0` is its mirror).
`assets/blender/kit/skeleton.py` reads `jointsRight` too, so a rebuilt frame matches. The helm is built on the neck
knuckle but hangs on `joint_head`; the script moves its vertices by the difference. The spear's origin is its grip, which
is where the mount is, so it only needs dividing by 1.2 (the web's Striker part scale).
