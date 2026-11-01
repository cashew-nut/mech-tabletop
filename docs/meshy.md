# Meshy workflow (image to 3D)

Tested 2026-10-31 with a crop of the north-star board (`docs/concept-art/north-star-board.jpg`, region 540,100 to 760,300, upscaled 4x).
Result files are in the project folder `renders/meshy/` (not in git: `renders/` is ignored and the GLB is 80 MB): `helm-crop.png` (input), `helm-crop.glb`, `helm-crop-thumb.png`, `helm-crop-vs-meshy.png`.

## Auth
Cloud sessions: Luke added a network secret, so the proxy injects the key for `api.meshy.ai/openapi/v1/`. No key is needed in code or env.
Elsewhere: set `MESHY_API_KEY` (starts `msy_`). Never print or commit it.

## Use
```
python3 tools/meshy/meshy.py balance
python3 tools/meshy/meshy.py image-to-3d crop.png --out renders/meshy   # creates, polls, downloads GLB + thumbnail
python3 tools/meshy/meshy.py status TASK_ID
```
Stdlib only. Image is sent as a base64 data URI (PNG or JPG, crop tight, upscale small crops).

## What we learned
- API task creation works on the current paid plan. One image-to-3D with PBR texture cost **30 credits** (balance 1243 to 1213).
- Took about 4 minutes. Progress sits at 99% for around 2 minutes while texturing; keep polling.
- Output is a textured GLB (80 MB untouched, so decimate before use) plus a thumbnail. Texture and gold filigree read close to the art.
- Meshy **invents unseen geometry**. Our crop showed only head and shoulders, yet it produced a full torso, belt and hands, with a different silhouette. Treat it as a style or detail reference, not a drop-in part.
- It is one fused mesh, not our kit parts (`mount_*` names, `hull*` repaint rule, KTX2). It would need splitting and retopo before it could enter `public/parts/manifest.json`.

## Recommended use
Concept inspiration, props, scenery (ruins, crates, spires), and silhouette studies. Keep Blender-scripted parts for walkers.

## Skill
Meshy publishes an open `meshy-3d-agent` skill pack (linked from https://docs.meshy.ai/en/api/ai.). Nothing in testing needs it: the API surface we use is three calls, wrapped by `tools/meshy/meshy.py`. This doc plus the script are enough for any session to call Meshy.

## Weapons (2026-10-31)
Clean reference first: `python3 tools/meshy/meshy.py text-to-image "PROMPT" --out ref.png` (3 credits, model nano-banana). Prompt for an isolated
side-on prop, no stand or hands, flat grey background. Then `image-to-3d` (30 credits). Board crops (about 130x57 px) were too blurry.
Bake: `python3 -I cut.py extract GLB WORK`, then `~/bvenv/bin/python -I weapon.py WORK ITEM --length L --rear Y --zc Z [--muzzle +x] [--upright] [--keep-x lo,hi] [--tris N]`.
Check the muzzle points left (-Y) in a side render; use `--muzzle +x` when it does not. Boxy props need more triangles (rocket pod 14k).
Ten signature weapons done this way (not Covenant lance or carapace gun, which stay procedural except the Paladin variants).

Meshy meshes of 1.5M triangles (gyro stabilisers, targeting array) stall Blender's decimation (stuck at 85k tris) and bake badly. `--weld N` (high mesh) and `--lo-weld N` (clustered low mesh) get a result but it is shattered; regenerate those images with simpler, chunkier shapes instead.

## Board scenery (2026-11-01)
Three hero pieces for the 3D board came from Meshy: a bell tower, a furnace chimney tower and a lancet ruin wall. 99 credits in all: 3 for each text-to-image reference (isolated tabletop prop on a hex plinth, flat grey background) and 30 for each image-to-3D.
Bake: `python3 -I assets/blender/parts/meshy/cut.py extract GLB WORK`, then `~/bvenv/bin/python -I assets/blender/board/hero.py WORK NAME --height H --max-width W --crop-base F --tris N --lo-weld 40 [--smoke]`. It writes `apps/web/public/board/hero_<name>.glb` (10 to 16k triangles, 1024 px colour and normal maps as JPEG, 1.1 to 1.5 MB each).
- `--lo-weld` is needed: Meshy's 1.3M to 3.3M triangle meshes stall Blender's decimator, so the low mesh is clustered on a grid that coarsens until the count is near the target, and the normal map carries the detail.
- `--crop-base` removes the plinth Meshy invents (the wall needed 0.16 to lose its floor slab).
- `--smoke` adds an empty named `smoke` at the top, which the board uses for chimney smoke.
- The tile detail texture (`stone_detail.jpg`) is one more 3-credit text-to-image ("seamless tileable granite"), made tileable and high-passed with numpy; the board material projects it from three axes in world space.
Hero pieces are optional: `boardKit.ts` loads them separately and the procedural towers and walls stand in when a file is missing.
