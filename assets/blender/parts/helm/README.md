Package 1: helms (kit component `helm`, joint `head`).

    ~/bvenv/bin/python assets/blender/parts/helm/helms.py                       # build, bake and publish all 12
    ~/bvenv/bin/python assets/blender/parts/helm/helms.py covenant --frames titan --render OUT --no-publish

`helms.py` builds one helm per faction and frame (`<faction>_helm_<frame>`),
so every class gets its faction's helm. A class-specific helm can be added
later as `<faction>_helm_<class>` and the web picks it first.

- Iron Covenant: beaked armet with vertical amber slits, filigree brow, cheek lames, low crest.
- Ashen Foundries: slab head under a red enamel hood, furnace visor behind a cage grille, stack.
- Reliquary: pointed bone-ceramic cowl with pale-gold ribs round a dark mask with teal eyes.

Each helm is modelled in helm units (R = 1, skull centre at the origin,
facing -Y). `finalize()` applies every piece, scales it by `FIT[faction]`
(R and the height of the skull centre above the head joint, as fractions of
the frame's height) and moves it into the head joint's space. Art crops for
review: `covenant_helm`, `helm_foundries`, `detail_reliquary_helm`.
Review renders are in the project's `renders/helm/` folder.

`poc/` is the original proof of concept, kept for reference.
