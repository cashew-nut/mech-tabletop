// Turn a part GLB about its own origin, positions, normals and tangents, without a rebake (textures stay valid).
//   node scripts/turn-part.mjs IN.glb OUT.glb BEND.json
// BEND.json is seer_elbow.py's output: "R" is the 3 x 3 turn in Blender axes (z up). The Seer's hand turns with its bent
// forearm about the wrist, its origin, so only its orientation changes; the frame's wrist joint moves (frameTunes).
import { readFileSync } from 'node:fs';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { transformMesh } from '@gltf-transform/functions';

const [src, dst, bendPath] = process.argv.slice(2);
const R = JSON.parse(readFileSync(bendPath, 'utf8')).R;
// Blender (x, y, z) -> glTF (x, z, -y): conjugate the turn into glTF axes, B = P R P^T with P mapping Blender to glTF.
const P = [[1, 0, 0], [0, 0, 1], [0, -1, 0]];
const mul = (A, B) => A.map((r) => B[0].map((_, j) => r.reduce((s, v, k) => s + v * B[k][j], 0)));
const T = (A) => A[0].map((_, j) => A.map((r) => r[j]));
const B = mul(mul(P, R), T(P));
// glTF matrices are column-major 4 x 4
const m = [B[0][0], B[1][0], B[2][0], 0, B[0][1], B[1][1], B[2][1], 0, B[0][2], B[1][2], B[2][2], 0, 0, 0, 0, 1];
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
const doc = await io.read(src);
for (const mesh of doc.getRoot().listMeshes()) transformMesh(mesh, m);
await io.write(dst, doc);
console.log(dst);
