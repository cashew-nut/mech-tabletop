# Package 4: arms and hands

`arms.py` builds every upper arm (`arm`, on the shoulder joint), forearm
(`forearm`, on the elbow) and hand (`hand`, on the wrist) for the frames the
classes in `data/chassis.json` use, then publishes them through `kit.publish()`.

```sh
~/bvenv/bin/python parts/arms/arms.py                      # all 27 parts (~15 min)
~/bvenv/bin/python parts/arms/arms.py reliquary_hand_titan  # one part
~/bvenv/bin/python parts/arms/arms.py --review OUT [faction ...]   # review renders beside the art, no publish
node ../../scripts/compress-parts.mjs                       # then convert textures to KTX2
```

What each faction gets, from the boards' close-ups (`detail_covenant_gauntlet`,
`covenant_gauntlet`, `detail_foundries_piston_arm`, `detail_reliquary_arm`,
`detail_reliquary_claw` in `assets/art/crops.json`):

| | Upper arm | Forearm | Hand |
| --- | --- | --- | --- |
| Covenant | three gold-edged iron lames, filigree on the middle one | fanned elbow cop, flared vambrace with a filigree plate | curved gauntlet plates, four plated three-segment fingers |
| Foundries | riveted iron wrap, red hull panel with the stencilled 07, front ram | banded barrel with brass collars, twin hydraulic rams, riveted cuff | three heavy fingers, a hydraulic line to every knuckle |
| Reliquary | ceramic shell with gold ribs and a teal seam over a relic spine | tapering vambrace with gold tracery over exposed bones | skeletal gold talons on a small ceramic back plate |

Parts are named for the frame (`covenant_hand_titan`), so every class on that
frame shares them. Hands are posed `open`, `grip` or `fist` (`POSES`); the
faction default is in `DEFAULT_POSE`, and `CLASS_HANDS` gives the Lancer a
grip, the Brute a fist and the Goliath a grip as class parts.

No `.blend` is kept: the script is the source and rebuilds the same parts.
Fingers and rods are never thinner than 0.6 mm (`MIN_R`), so Scout hands print,
but Reliquary talon tips are finer than the kit's 1 mm wall guide.
