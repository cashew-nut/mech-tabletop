# Package 2: torsos and pelvises

`torso.py` builds `<faction>_torso_<frame>` (on `joint_spine`) and
`<faction>_pelvis_<frame>` (on `joint_pelvis`) for every frame a faction's
classes use in `data/chassis.json`: Covenant striker, bulwark and titan;
Foundries scout and bulwark; Reliquary scout, striker and titan. Classes on
the same frame share the parts through the frame fallback.

```sh
~/bvenv/bin/python assets/blender/parts/torso/torso.py preview [faction ...] [--frame titan] [--samples 32] [--out dir]
~/bvenv/bin/python assets/blender/parts/torso/torso.py publish [faction ...] [--frame titan]
node scripts/compress-parts.mjs
```

`preview` renders the live node materials on the frame's stand-ins (front,
back, on the frame) beside the faction's detail tile; `publish` bakes each
part, exports it to `apps/web/public/parts/kit/` and lists it in the
manifest, saving the editable `.blend` to `src/`.

What each faction's parts take from the boards:

- **Covenant**: keeled breastplate of two gold-edged filigree pectorals with
  gothic arches, a filigree gorget band, stacked abdominal lames, the caged
  furnace lantern in a lancet niche with two side lamps, studded flank
  plates, a fluted back plate with vents. Pelvis: filigree belt, a long
  front tasset in lames with a gold point, flared side tassets.
- **Foundries**: a hunched iron hull under rusted slabs, a shoulder yoke,
  the square furnace door (bezel, grate, coals, hinges, latch, bolt ring),
  red enamel flank plates with the stenciled 07 on the left, a gauge,
  steam pipes over the yoke, a boiler hatch with a wheel valve, a heavy
  waist ring with pistons. Pelvis: hip block, riveted skirt with a red
  front panel, hinged side plates.
- **Reliquary**: bone ribs tapering from a banded spine round a dark core
  with a teal heart-light, a gold sternum and sunburst, a glyph-inlaid
  clavicle plate, bone vertebrae down the back and an exposed vertebral
  waist. Pelvis: glyph girdle, long gold-tipped tabard plates front and back.

The Reliquary ribs are laid on a hidden guide shell (`rlq_guide`), which is
removed before baking.

Sizes after `compress-parts.mjs`: Covenant torso about 2.5 MB and pelvis
1.3 MB (most of it geometry: about 42k vertices of swept trim and laid
plates), Foundries 1.4 + 0.9 MB, Reliquary 1.5 + 1.2 MB. The Covenant pair
takes most of a class's 4 MB budget; meshopt compression in the loader
(package 10) would cut the geometry share by most of that.
