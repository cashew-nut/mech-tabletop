# Paladin from the Meshy model

The Iron Covenant Paladin is Luke's Meshy image-to-3D model (textured GLB, 2.95M triangles, one mesh) cut into
kit parts. Assembled at rest, the parts reproduce the Meshy figure.

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
