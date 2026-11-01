# The Paladin as a composite of real parts

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
- The game still loads the old open-shell parts. Publishing these as `covenant_<component>_paladin` (and retiring
  the separate `cloth` and `collar` parts) is the next step, then re-rendering the card art from them.
