# Paladin fidelity: findings (2026-11-04)

Luke: the Paladin looks lower fidelity than the Brute and Seer in the game.

## What the numbers say (shipped GLBs in apps/web/public/parts/kit, measured with gltf-transform)

| | Paladin | Brute | Seer |
|---|---|---|---|
| Body triangles | 73.3k | 55.9k | 54.7k |
| Triangles per cm2 of surface (world size) | 1012 | 699 | 1316 |
| Base-colour texels per mm2 | 1014 | 951 | 1876 |
| Texture sizes (torso, pelvis, pauldron) | 1024 | 1024 | 1024 |

Every model goes through the same pipeline (assets/blender/parts/composite/build.py): Blender decimate, xatlas unwrap,
Cycles bake from the full-resolution solid, normal map downsized to 512, ORM to 256, then KTX2 (ETC1S colour, UASTC normal).
So the Paladin is not short of triangles or of texture size, and no export setting is different.

## Causes

1. **The look depends on texture, not geometry.** The Paladin is large smooth plates with thin gold filigree and a red
   cloth. The detail that makes it read well is in the colour and normal maps; the Brute has real geometric clutter that
   survives decimation. Any softness in the maps shows on the Paladin and hides on the Brute.
2. **Atlases are mostly empty on every model.** Summed UV area is only 34% (torso), 37% (pelvis), 38% (shin) of each
   Paladin atlas (Brute 25-34%, Seer 29-43%): hundreds of tiny charts with 6 px padding. An offline xatlas test on the
   shipped Paladin pelvis: padding 4 gives 43%, brute-force packing 48%, i.e. about 13% more linear texel density at the
   same file size. Real but modest.
3. **Maps are downsized before they ship.** Normal map is 512 even on 1024 parts, ORM is 256. Fine relief on trims is lost.
4. **No anisotropic filtering.** three.js leaves glTF textures at 1, so filigree smears at glancing angles. Fixed here.
5. **KTX2 ETC1S colour** costs a little (blockier reds, slight tone shift). A PNG-vs-KTX2 render of the same Paladin showed
   a small difference, so this is the smallest lever.

## Changed in this PR

- `apps/web/src/model/assemble.ts`: anisotropic filtering (up to 8x) on kit part textures. No asset changes, no Blender.

## Needs a decision (re-bake in Blender, about 40 min compute plus the bpy install)

- **Texture budget for the Paladin.** Torso, pelvis, pauldron, back, thigh, shin to 2048, normal map to 1024, ORM to 512.
  Roughly 2-3 MB more download (the Paladin kit is 3.9 MB now). This is the single biggest improvement.
- **Tighter UV pack** (padding 4, brute-force pack) in build.py: free, about 13% sharper, applies to all three walkers if
  they are re-baked.
- Re-sculpting is not recommended: geometry is not the gap.
