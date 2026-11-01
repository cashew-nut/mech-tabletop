// Level-of-detail copies of the heavy board pieces: public/board/<piece>_lod1.glb and _lod2.glb, geometry only.
//   node scripts/board-lod.mjs [piece ...]          (default: every piece over MIN_TRIS triangles)
// The files carry no textures: the loader (boardKit.ts) gives kit LODs the base piece's material, and hero LODs a plain
// vertex-colour one.
// The Blender kit pieces are flat-shaded triangle soups (every face has its own vertices), which a simplifier cannot
// connect, so their vertices are first welded by position; normals and baked colours are averaged over the welded
// vertices. That smooths the shading a little, which is what you want from a far-off LOD anyway (keeping faceted normals on
// the brick-heavy kit pieces turned their simplified copies into black slivers). The textured Meshy hero
// pieces are cut into tiny UV islands, so their LODs trade the texture for vertex colour sampled from it (the loader gives
// them a plain vertex-colour material tinted like the original).
// Needs only the dev dependencies (@gltf-transform, meshoptimizer, jpeg-js); no Blender.
import { readdirSync, statSync } from 'node:fs';
import { resolve } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { prune } from '@gltf-transform/functions';
import jpeg from 'jpeg-js';
import { MeshoptSimplifier } from 'meshoptimizer';

const DIR = resolve('apps/web/public/board');
const MIN_TRIS = 1500;
/** Fraction of triangles kept, and the largest error the simplifier may add (a fraction of the piece's size). */
const LEVELS = [
  { name: 'lod1', ratio: 0.5, error: 0.012 },
  { name: 'lod2', ratio: 0.22, error: 0.03 },
];

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);
await MeshoptSimplifier.ready;

const triangles = (doc) => {
  let n = 0;
  for (const mesh of doc.getRoot().listMeshes()) for (const p of mesh.listPrimitives()) n += (p.getIndices()?.getCount() ?? p.getAttribute('POSITION').getCount()) / 3;
  return n;
};

const srgbToLinear = (c) => ((c /= 255) <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);

/** Sample a textured primitive's base colour at every vertex and store it as COLOR_0 (linear), dropping the UVs. The Meshy hero
 * pieces are atlas-unwrapped into tiny islands, which no simplifier can merge across; vertex colour has no seams. */
function bakeTextureToColour(doc, prim) {
  const uv = prim.getAttribute('TEXCOORD_0');
  const tex = prim.getMaterial()?.getBaseColorTexture();
  if (!uv || !tex) return;
  const img = jpeg.decode(Buffer.from(tex.getImage()), { useTArray: true });
  const n = uv.getCount();
  const colour = new Float32Array(n * 3);
  const t = [0, 0];
  for (let i = 0; i < n; i++) {
    uv.getElement(i, t);
    const x = Math.min(img.width - 1, Math.max(0, Math.floor((t[0] - Math.floor(t[0])) * img.width)));
    const y = Math.min(img.height - 1, Math.max(0, Math.floor((t[1] - Math.floor(t[1])) * img.height)));
    for (let k = 0; k < 3; k++) colour[i * 3 + k] = srgbToLinear(img.data[(y * img.width + x) * 4 + k]);
  }
  prim.setAttribute('COLOR_0', doc.createAccessor().setType('VEC3').setArray(colour));
  prim.setAttribute('TEXCOORD_0', null);
}

/** Replace one primitive's geometry with a welded, simplified copy. */
function simplifyPrimitive(doc, prim, ratio, error) {
  bakeTextureToColour(doc, prim);
  const attrs = Object.fromEntries(prim.listSemantics().map((s) => [s, prim.getAttribute(s)]));
  const pos = attrs.POSITION;
  const n = pos.getCount();
  const index = prim.getIndices()?.getArray() ?? Uint32Array.from({ length: n }, (_, i) => i);
  // Weld by position (and UV): one welded vertex per key.
  const keys = new Map();
  const remap = new Uint32Array(n);
  const p = [0, 0, 0];
  let m = 0;
  for (let i = 0; i < n; i++) {
    pos.getElement(i, p);
    const key = `${Math.round(p[0] * 2000)},${Math.round(p[1] * 2000)},${Math.round(p[2] * 2000)}`;
    let id = keys.get(key);
    if (id === undefined) keys.set(key, (id = m++));
    remap[i] = id;
  }
  const welded = Uint32Array.from(index, (i) => remap[i]);
  const positions = new Float32Array(m * 3);
  for (let i = 0; i < n; i++) positions.set(pos.getElement(i, p), remap[i] * 3);
  const [kept, err] = MeshoptSimplifier.simplify(welded, positions, 3, Math.max(3, Math.floor((welded.length * ratio) / 3) * 3), error);
  // Compact to the vertices the kept triangles use, and average each attribute over the original vertices that map to them.
  const used = new Map();
  const outIndex = new Uint32Array(kept.length);
  kept.forEach((v, i) => {
    let id = used.get(v);
    if (id === undefined) used.set(v, (id = used.size));
    outIndex[i] = id;
  });
  const count = used.size;
  const out = {};
  for (const [semantic, acc] of Object.entries(attrs)) {
    const size = acc.getElementSize();
    const sum = new Float32Array(count * size);
    const num = new Float32Array(count);
    const e = new Array(size);
    for (let i = 0; i < n; i++) {
      const id = used.get(remap[i]);
      if (id === undefined) continue;
      acc.getElement(i, e);
      for (let k = 0; k < size; k++) sum[id * size + k] += e[k];
      num[id]++;
    }
    for (let id = 0; id < count; id++) for (let k = 0; k < size; k++) sum[id * size + k] /= num[id];
    if (semantic === 'NORMAL') {
      for (let id = 0; id < count; id++) {
        const l = Math.hypot(sum[id * 3], sum[id * 3 + 1], sum[id * 3 + 2]) || 1;
        for (let k = 0; k < 3; k++) sum[id * 3 + k] /= l;
      }
    }
    out[semantic] = doc.createAccessor().setType(acc.getType()).setArray(sum);
  }
  for (const s of prim.listSemantics()) prim.setAttribute(s, out[s]);
  prim.setIndices(doc.createAccessor().setType('SCALAR').setArray(outIndex));
  return err;
}

const wanted = process.argv.slice(2);
const pieces = readdirSync(DIR).filter((f) => f.endsWith('.glb') && !/_lod\d\.glb$/.test(f)).map((f) => f.replace(/\.glb$/, ''));
for (const piece of pieces) {
  if (wanted.length && !wanted.includes(piece)) continue;
  const count = triangles(await io.read(`${DIR}/${piece}.glb`));
  if (!wanted.length && count < MIN_TRIS) continue;
  for (const level of LEVELS) {
    const doc = await io.read(`${DIR}/${piece}.glb`);
    // Simplifier error is relative to the piece's extent.
    for (const mesh of doc.getRoot().listMeshes()) for (const prim of mesh.listPrimitives()) simplifyPrimitive(doc, prim, level.ratio, level.error);
    // Geometry only: drop textures, and helper nodes such as the smoke anchor.
    for (const tex of doc.getRoot().listTextures()) tex.dispose();
    for (const node of doc.getRoot().listNodes()) if (!node.getMesh() && node.listChildren().length === 0) node.dispose();
    await doc.transform(prune({ keepAttributes: true, keepLeaves: true }));
    const out = `${DIR}/${piece}_${level.name}.glb`;
    await io.write(out, doc);
    console.log(`${piece}_${level.name}: ${Math.round(count)} -> ${Math.round(triangles(doc))} tris, ${Math.round(statSync(out).size / 1024)} KB`);
  }
}
