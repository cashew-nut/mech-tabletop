# Artillery concept art (first Ashen Foundries walker, 2026-11-04)

Made with Meshy image-to-image (nano-banana, 3 credits each, 15 in all) from `docs/style-bible/foundries.md` through
`tools/meshy/prompts.py`. References for the hero: the Artillery and Brute tiles and the Foundries hero from the
three-faction board, and the approved Brute 3D render. Luke picked hero roll 3 (2026-11-04); the turnaround and part sheet
were made from it alone. Originals (including the unused hero rolls 1 and 2, kept only in the project folder) and a
`source.json` per task are in `meshy-sources/artillery/`; ledger rows are in `meshy-sources/ledger.json`.

| File | What |
| --- | --- |
| `concept-sheet.jpg` | hero, front, side, back and part sheet on one page |
| `hero.jpg` | the north star (roll 3) and card hero art |
| `turnaround-front/side/back.png` | one multi-view task, transparent background |
| `partsheet.jpg` | the walker taken apart (card art source) |

Known gaps (for the Sentinel-style check before 3D):

- The turnaround colours drifted from the hero's rust red to ochre and brown, with no red lacquer. The hero stays the colour
  reference, and the retexture step can use it.
- The "side" view is a three-quarter view with the howitzer pointing to the left.
- The part sheet shows the torso, back and howitzer as one assembled block with the left arm; legs and one pauldron appear
  once, not as a left and right pair; no hands.

## 3D model (2026-11-04)

Luke approved the turnaround ("build it and put it in the game"); one whole-body model from the three views (front first):
mesh only (multi-image-to-3d, 20 credits, 2.9M triangles), silhouette checked against the turnaround
(`tools/meshy/silhouette.py`: howitzer, stacks, arms and stance match), then retexture from the same three views (meshy-7, 10 credits).
Files: project folder `meshy-sources/artillery/model/` (mesh task `01a1a802...`, textured `01a1a804...`). Total for the Artillery: 45 credits
(15 for the 2D art, 30 for the model), balance 97. The composite cut is in `docs/artillery-composite/`.
