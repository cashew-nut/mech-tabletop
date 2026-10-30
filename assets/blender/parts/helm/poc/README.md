Proof-of-concept Iron Covenant helm (2026-10-30), headless Blender 5.2.
Setup: python3 -m venv bvenv && bvenv/bin/pip install bpy pillow numpy   (bpy wheel ~400 MB, needs Python 3.13)
Run:   bvenv/bin/python -I filigree.py OUT/filigree.png
       bvenv/bin/python helm.py OUT [samples=96] [angle_deg=32]   # Cycles CPU, ~1 min at 48 samples
       bvenv/bin/python -I post.py OUT/helm-raw-32.png OUT/helm-32.png   # bloom, vignette, grain
Units here are arbitrary (helm ~2 units tall), not the repo's mm convention.

Kept here as package 1's starting point. Its methods now live in the kit:
the surface-laid plates, lames, trim, studs and fluting are `kit.shapes.Shell`,
the iron and gold are `kit.materials` (covenant armour, trim, filigree), the
filigree mask is `kit.textures.filigree()`, and the lights and post pass are
`kit.render.studio()` and `kit.render.post()`. A rebuilt helm should use those,
be named covenant_helm_<class or frame>, sit on joint_head and go out through
`kit.publish()`.
