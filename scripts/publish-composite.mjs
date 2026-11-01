// Publish the composite Paladin (assets/blender/parts/composite) into the game, without Blender.
//   node scripts/publish-composite.mjs DIR/glb          (DIR is the build.py output, e.g. models/paladin-composite)
//   node scripts/compress-parts.mjs <the files this prints>   (KTX2 and quantisation; see assets/blender/parts/meshy/README.md)
//
// build.py writes one GLB per part with its origin on its joint, in millimetres. The game wants the same parts under
// kit names, so this renames and wraps them:
//   pelvis, torso, helm, back, pauldron, arm, forearm, hand, thigh, shin, foot -> kit/covenant_<part>_paladin.glb
//   blade -> item_lance@paladin.glb          pod -> item_carapace-gun@paladin.glb
// Items are stored at scout scale with their origin on the hand/core mount (the web grows them by the titan factor 1.7),
// so their vertices are moved by the mount offset in data/model-kit.json and divided by 1.7.
// The old open-shell cut is retired: its right-hand copies (the web mirrors the left), cloth and collar files go, and the
// manifest drops them. The collar is part of the torso now (data/model-kit.json "omit" keeps the Titan collar off).
import { existsSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';

const PARTS = resolve('apps/web/public/parts');
const ITEM_SCALE = 1.7;
const KIT = ['pelvis', 'torso', 'helm', 'back', 'pauldron', 'arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'];
const ITEMS = { blade: ['lance@paladin', 'mount_armLeft_0'], pod: ['carapace-gun@paladin', 'mount_core_0'] };

const src = process.argv[2];
if (!src || !existsSync(src)) {
  console.error('usage: node scripts/publish-composite.mjs DIR/glb');
  process.exit(1);
}
const tunes = JSON.parse(readFileSync('data/model-kit.json', 'utf8')).frameTunes['covenant/titan'];
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);

/** Wrap a part's nodes in a root named for the part; optionally move/scale its vertices. */
async function convert(file, name, out, fix) {
  const doc = await io.read(file);
  const scene = doc.getRoot().getDefaultScene();
  const root = doc.createNode(name);
  for (const n of scene.listChildren()) {
    scene.removeChild(n);
    root.addChild(n);
  }
  scene.addChild(root);
  for (const mat of doc.getRoot().listMaterials()) mat.setName(`hull_${name}_livery`);
  if (fix) {
    for (const mesh of doc.getRoot().listMeshes())
      for (const prim of mesh.listPrimitives()) {
        const pos = prim.getAttribute('POSITION');
        const v = [0, 0, 0];
        for (let i = 0; i < pos.getCount(); i++) pos.setElement(i, fix(pos.getElement(i, v)));
      }
  }
  await io.write(out, doc);
  return out;
}

const written = [];
for (const k of KIT) {
  const name = `covenant_${k}_paladin`;
  written.push(await convert(join(src, `${k}.glb`), name, join(PARTS, 'kit', `${name}.glb`)));
}
for (const [k, [id, mount]] of Object.entries(ITEMS)) {
  const [, [dx, dy, dz]] = tunes.mounts[mount]; // Blender axes, mm, relative to the joint the part's origin sits on
  const off = [dx, dz, -dy]; // glTF is y-up: (x, z, -y)
  const name = `item_${id}`;
  written.push(await convert(join(src, `${k}.glb`), name, join(PARTS, `${name}.glb`), (p) => p.map((c, i) => (c - off[i]) / ITEM_SCALE)));
}

// Retire the old cut: right-hand copies, cloth and collar.
const manifestPath = join(PARTS, 'manifest.json');
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
const keep = new Set(KIT.map((k) => `covenant_${k}_paladin`));
for (const key of Object.keys(manifest.kit)) {
  if (!/^covenant_.+_paladin$/.test(key)) continue;
  if (!keep.has(key)) {
    rmSync(join(PARTS, manifest.kit[key]), { force: true });
    delete manifest.kit[key];
  }
}
for (const k of KIT) manifest.kit[`covenant_${k}_paladin`] = `kit/covenant_${k}_paladin.glb`;
for (const [, [id]] of Object.entries(ITEMS)) manifest.items[id] = `item_${id}.glb`;
for (const kind of ['items', 'kit']) manifest[kind] = Object.fromEntries(Object.entries(manifest[kind]).sort(([a], [b]) => (a < b ? -1 : 1)));
writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

console.log(written.map((f) => f.replace(`${resolve('.')}/`, '')).join('\n'));
console.log(`\nnext: KTX2_NORMAL=etc1s KTX2_BASE_Q=150 node scripts/compress-parts.mjs ${written.map((f) => f.replace(`${resolve('.')}/`, '')).join(' ')}`);
