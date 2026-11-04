# Sentinel concept art (pilot walker, 2026-11-04)

Made with Meshy image-to-image (nano-banana, 3 credits each, 24 credits in all) from `docs/style-bible/covenant.md`
through `tools/meshy/prompts.py`. Hero references: the Sentinel crop and Covenant hero from the three-faction board, the
approved Paladin front view and the Covenant variant B artillery platform. Luke picked hero roll 2 (2026-11-04); the turnaround
and part sheet were made from it. Originals (including the unused rolls 1 and 3 and the roll 1 turnaround) and a `source.json`
per task are in the project folder `meshy-sources/sentinel/`; the ledger is `meshy-sources/ledger.json`.

| File | What |
| --- | --- |
| `concept-sheet.jpg` | everything on one page |
| `hero.jpg` | the north star (roll 2) and card hero art |
| `turnaround-front/side/back.png` | front, side and back views from one multi-view task (cloak and scenery removed) |
| `partsheet.png` | the walker taken apart (card art source) |

Known gaps: the back view draws the legs with exposed pistons where the front has plate, and shows a plain pauldron
where the front has red inserts; the Carapace Gun is missing from the part sheet (it is in the turnaround); the part
sheet has no upper arms. The side view shows the gun arm raised, which is also how the hero holds it.

## 3D model (2026-11-04)

Luke approved the turnaround; one whole-body model from the three views (front first):
mesh only (multi-image-to-3d, 20 credits, 3.8M triangles), silhouette checked against the turnaround
(`tools/meshy/silhouette.py`: spires, pauldrons, gun, tabard and stance all match; the banner flag is not in the mesh),
then retexture from the same three views (meshy-7, original UVs, PBR, 10 credits). `model-vs-concept.jpg` compares the result
with the hero. Files are in the project folder `meshy-sources/sentinel/model/` (mesh task `01a1a5cf...`, textured `01a1a5d1...`).
Total for the Sentinel: 54 credits (24 for the 2D art, 30 for the model), balance 142. Next: composite parts (Blender cut).
