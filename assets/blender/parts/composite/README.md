# The Paladin and the Brute as composites of real parts

The Iron Covenant Paladin rebuilt as 13 separate, closed parts that plug together with keyed pegs and magnets,
then assembled in Blender into the full walker. It starts from Luke's Meshy Paladin (textured GLB in the project
folder), but every part is now a solid of its own that makes sense when you pick it up: a card can show it alone,
a printer can print it, and the game can swap it.

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
~/bvenv/bin/python -I split.py WORK          # voxel labels, one closed region per part, figure x region   (~3 min)
~/bvenv/bin/python -I joints.py WORK         # keyed peg + hole and magnet pockets at every joint          (~15 s)
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
   bone, blends), centres and radii (2.0 down to 0.55 mm) on the voxel grid, and takes the biggest peg whose root
   sits inside one part and whose hole, with a 0.4 mm wall, sits inside the other. The hole is 0.1 mm looser. The
   flat on the D keys the part. Where the peg is thick and long enough there is a pocket for a 2 x 1 mm disc magnet
   (or 1 x 1 mm) flush in the peg tip and another at the bottom of the hole.
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
| pod | torso or back | equipment: the shoulder pod (`item_carapace-gun@paladin`); no room for a peg yet |

Sided parts are modelled once, for the walker's left, and mirrored for the right, so the right side now matches the
left (the Meshy figure's right arm hung differently). OUT/report.json lists each part's size, volume and triangle
counts and every joint's peg, axis and magnet.

## Known limits

- At today's titan scale (about 62 mm to the spire tip) the thin joints are small: the thigh's peg is 1.1 mm across
  and four joints have no room for a magnet. Printing at 1.5x or 2x would give more joints a magnet, but
  the pegs are cut for 1x: a print-scale option (scale the solids before `joints.py`) is not built yet.
- The pod has no peg (its only contact with the torso and spire is a few struts). Pin or glue it for now.
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
