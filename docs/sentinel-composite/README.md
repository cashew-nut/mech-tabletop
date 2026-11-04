# Sentinel composite parts (gate E, 2026-11-04)

The Sentinel Meshy model (`meshy-sources/sentinel/model/`) cut into 12 closed parts by the shared composite pipeline
(`MODEL=sentinel`, settings in `assets/blender/parts/composite/sentinel.py`). Printed at Luke's 1.5x scale: 63 mm to the
helm top, about 79 mm to the spire tips. Parts, STLs, game GLBs and the .blend are in the project folder
`models/sentinel-composite/`; renders in `renders/sentinel-composite/` (JPEG copies here).

| File | What |
| --- | --- |
| `assembled.jpg` | front, three-quarter, side and back, textured |
| `exploded.jpg` | every part pulled apart, front and back |
| `parts.jpg` | each part alone |
| `pose.jpg` | posed by rotating joints (gun raised, legs striding) |

## The parts

Pelvis (with the tabard), torso (with the gorget), helm, back (two spires and the pack), and the left-hand set, mirrored for
the right: pauldron, upper arm, forearm, gauntlet, thigh, greave, sabaton. The twelfth part is the **Carapace Gun**: the figure's
right forearm is the gun, so it is cut from the right, mirrored, turned 66 degrees and re-seated on the forearm's socket
(the Brute's gatling trick), so it fits either elbow in place of forearm and gauntlet. Every part is one closed solid (report.json).

| Joint | Peg across | Magnet |
| --- | --- | --- |
| thigh into pelvis | 4.4 mm | 3 x 2 |
| torso / pelvis | 6.0 mm | 2 x 1 |
| helm into torso | 5.5 mm | 3 x 2 |
| back (spires) / torso | 6.0 mm | 2 x 1 |
| pauldron into torso | 5.0 mm | 3 x 2 |
| arm / pauldron | 4.0 mm | 2 x 1 |
| forearm / arm | 2.0 mm | 1 x 1 |
| gun / arm (same socket) | 2.0 mm | 1 x 1 |
| gauntlet into forearm | 3.0 mm | none |
| greave into thigh | 3.5 mm | 2 x 1 |
| sabaton / greave | 2.6 mm | 2 x 1 |

All pass the strict checks (hole walls inside the part, no break-outs, mirrored side clear).

## Things to know

- **Mesh repair.** Meshy's mesh had 160 open edges and 14 three-way edges, so manifold3d refused it. `repair_mesh.py` drops the
  faulty faces and fan-fills the holes (76 faces net). Run it after `cut.py extract`, before `split.py`.
- **Weak joints.** The elbow (forearm, gun) has only a 2 mm peg with a 1 x 1 magnet because the upper arm is a small part (7 x 7 x 10 mm).
  The gauntlet has no magnet. A knuckle (as on the Seer) would fix both.
- **Helm.** The Meshy helm is a thin hood, so the helm part is only 273 mm3.
- **Not in the concept art any more.** The banner pole and flag did not come out of Meshy (too thin). Add them by hand if wanted.
- **Not published to the game yet.** That needs a `covenant/bulwark` frame tune in `data/model-kit.json`, a Sentinel entry in
  `scripts/publish-composite.mjs`, `parts.json` rows and the card faces.
- **Not test-printed.** Magnet pockets are 0.1 mm over stock size, as on the other walkers.
