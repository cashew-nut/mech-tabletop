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
