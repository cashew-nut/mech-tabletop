# Paladin from the Meshy model

The Iron Covenant Paladin is Luke's Meshy image-to-3D model (textured GLB, 2.95M triangles, one mesh) cut into
kit parts. Assembled at rest, the parts reproduce the Meshy figure.

These parts are open shells that only look right in place. `../composite/` cuts the same figure into closed,
standalone parts with joints; use that for anything a part has to do on its own (cards, printing).

```sh
python3 -I cut.py extract Meshy_..._texture.glb WORK     # mesh.npz and textures (numpy only)
python3 -I cut.py label WORK --preview                   # lab.npy, names.json, colour-coded views (needs scipy, pillow)
python3 -I build.py tunes                                # frameTunes into data/model-kit.json (joints, mounts)
~/bvenv/bin/pip install xatlas                           # UV atlas generator used by build.py
~/bvenv/bin/python -I build.py WORK [part ...]           # decimate, unwrap, bake, publish (about 15 s a part)
KTX2_NORMAL=etc1s KTX2_BASE_Q=150 node scripts/compress-parts.mjs apps/web/public/parts/kit/covenant_*_paladin.glb apps/web/public/parts/item_*@paladin.glb
~/bvenv/bin/python -I assemble.py OUT --ortho            # rest-pose renders (run before compressing: Blender can't read KTX2)
```

Gotchas learned:
- Voxel remesh punches holes in the cut parts; direct quadric decimation of the welded part is clean.
- Blender's smart UV project shatters a decimated noisy mesh; xatlas packs it well. Meshy splits vertices along its own UV
  seams, so weld by position before decimating.
- Livery: the parts are one texture each, so the web finds the paintable red texels by hue in the shader (`liveryMaterial` in
  assemble.ts, materials named `hull_<part>_livery`). Gold, black iron and steel stay as baked. Per-part texture sizes are in
  `PARTS` (base, normal, ORM); the normal map dominated the file size, so it is 384 to 512 px and ETC1S.
- Thigh, shin and foot are built once and mirrored for the right side (the legs are mirror images).
- Equipment uses `item_lance@paladin` (siege blade, left) and `item_carapace-gun@paladin` (shoulder pod, left); the
  web mirrors them for the right arm and the second core mount.

## Foundries Brute (second model)

Same pipeline with `MODEL=brute` (settings in `brute_cut.py`: bones, joints, scale, items): `cut.py extract` the GLB, then
`python3 -I brute_cut.py label WORK --preview`, `MODEL=brute build.py tunes`, `build_frames.py foundries --frames bulwark`,
`MODEL=brute build.py WORK`, `MODEL=brute assemble.py OUT --ortho [--viewer FILE.glb]`, then compress as above.
- Meshy gave 6.2M triangles; cutting by centroid in numpy and building straight from the labelled subsets was fine (about 6 min for all parts).
- The stance is not symmetric, so every sided part is built for both sides (no mirroring). Parts keep their true place because each part's origin is its joint.
- The two forearm guns are equipment: `item_rocket-pod@brute` (left) and `item_autocannon@brute` (modelled on the right arm; `NATIVE_RIGHT` in assemble.ts flips it for the left).
- Joints are written to `frameTunes["foundries/bulwark"]`, so the Artillery (also on the bulwark frame) hangs its parts on the same joints.

## Gilded Seraphim (third model, Reliquary Seer on the Striker frame)

Same pipeline with `MODEL=seraphim` (settings in `seraphim_cut.py`): `cut.py extract` the GLB (3.03M triangles), `~/bvenv/bin/python -I seraphim_cut.py label WORK --preview`,
`MODEL=seraphim build.py tunes`, `build_frames.py reliquary --frames striker`, `MODEL=seraphim build.py WORK` (about 3 min), `MODEL=seraphim assemble.py OUT [--viewer FILE.glb]`, then compress as above.
- Halo and its crown spire are `reliquary_crown_seer` (the head joint). The tall spires behind the shoulders are `back`. Sided parts are built for both sides (the stance is not symmetric).
- The red banner is torso down to the waist, then pelvis (red texels plus the dark cloth between the legs), so livery repaints it.
- The spear is equipment: `item_arc-cannon@seer`, cut from the right hand (`NATIVE_RIGHT` in assemble.ts flips it for the left arm). The Seer's arc cannon slot shows it.
- Joints are written to `frameTunes["reliquary/striker"]`; only the Seer uses the Striker frame.
