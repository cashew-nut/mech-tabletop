// Publish a composite walker (assets/blender/parts/composite) into the game, without Blender.
//   node scripts/publish-composite.mjs DIR/glb [paladin|brute|seer]   (DIR is the build.py output, e.g. models/paladin-composite)
//   node scripts/compress-parts.mjs <the files this prints>   (KTX2 and quantisation; see assets/blender/parts/meshy/README.md)
//
// build.py writes one GLB per part with its origin on its joint, in millimetres. The game wants the same parts under
// kit names, so this renames and wraps them:
//   pelvis, torso, helm, back, pauldron, arm, forearm, hand, thigh, shin, foot -> kit/covenant_<part>_paladin.glb
//   blade -> item_lance@paladin.glb          pod -> item_carapace-gun@paladin.glb
// Items are stored at scout scale with their origin on the hand/core mount (the web grows them by the titan factor 1.7),
// so their vertices are moved by the mount offset in data/model-kit.json and divided by 1.7.
// The Brute (foundries/bulwark, grown 1.4 by the web) has no arm, forearm or hand: its parts are pelvis, torso, helm, back,
// pauldron, thigh, shin and foot, and each gun is a whole forearm with its origin on the elbow. The guns are moved onto the
// numbered arm mount the old brute items used, so they hang from the same hardpoint; both are modelled for the left.
// The Seer (reliquary/striker, grown 1.2 by the web) is asymmetric: its arms and pauldrons are built for each side, so the
// right ones (arm_r, pauldron_r, forearm_r, hand_r) publish as the `-right` variants and hang on joints of their own
// (frameTunes "jointsRight" moves joint_shoulder_R, elbow_R and wrist_R off the mirror of the left). Its helm is built on the
// neck knuckle but hangs on the head joint, so its vertices are moved by the difference. The spear is the right hand's item
// with its origin on the grip, where the frame's mount_armRight_0 is. The script also moves the frame's joints to the tunes.
// The old open-shell cut is retired: its right-hand copies (the web mirrors the left), cloth and collar files go, and the
// manifest drops them. The collar is part of the torso now (data/model-kit.json "omit" keeps the Titan collar off).
import { existsSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';

const PARTS = resolve('apps/web/public/parts');
const MODELS = {
  paladin: {
    faction: 'covenant', cls: 'paladin', tunes: 'covenant/titan', itemScale: 1.7,
    kit: ['pelvis', 'torso', 'helm', 'back', 'pauldron', 'arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'],
    // part -> [item id, numbered mount, joint the part's origin is on (default: the mount's own joint; 'mount': the mount itself)]
    items: { blade: ['lance@paladin', 'mount_armLeft_0'], pod: ['carapace-gun@paladin', 'mount_core_0'] },
  },
  brute: {
    faction: 'foundries', cls: 'brute', tunes: 'foundries/bulwark', itemScale: 1.4,
    kit: ['pelvis', 'torso', 'helm', 'back', 'pauldron', 'thigh', 'shin', 'foot'],
    items: { rockets: ['rocket-pod@brute', 'mount_armLeft_0', 'elbow'], gatling: ['autocannon@brute', 'mount_armLeft_0', 'elbow'] },
  },
  seer: {
    faction: 'reliquary', cls: 'seer', tunes: 'reliquary/striker', itemScale: 1.2, frame: 'reliquary_frame_striker',
    kit: ['pelvis', 'torso', 'helm', 'crown', 'back', 'pauldron', 'arm', 'forearm', 'hand', 'pauldron_r', 'arm_r', 'forearm_r', 'hand_r', 'thigh', 'shin', 'foot'],
    // build part -> [kit component, the joint its origin sits on, the joint it hangs on when that differs]
    component: { pauldron_r: 'pauldron-right', arm_r: 'arm-right', forearm_r: 'forearm-right', hand_r: 'hand-right' },
    origin: { helm: ['neck', 'head'] },
    items: { spear: ['arc-cannon@seer', 'mount_armRight_0', 'mount'] },
  },
};

const src = process.argv[2];
const model = MODELS[process.argv[3] ?? 'paladin'];
if (!src || !existsSync(src) || !model) {
  console.error('usage: node scripts/publish-composite.mjs DIR/glb [paladin|brute|seer]');
  process.exit(1);
}
const { faction, cls, itemScale: ITEM_SCALE, kit: KIT, items: ITEMS, component: COMPONENT = {}, origin: ORIGIN = {} } = model;
const kitName = (k) => `${faction}_${COMPONENT[k] ?? k}_${cls}`;
const tunes = JSON.parse(readFileSync('data/model-kit.json', 'utf8')).frameTunes[model.tunes];
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
const toGltf = ([x, y, z]) => [x, z, -y]; // Blender (z up) to glTF (y up)
for (const k of KIT) {
  const name = kitName(k);
  // A part built on one joint but hung on another (the Seer's helm) is moved by the difference.
  const [from, to] = ORIGIN[k] ?? [];
  const delta = from ? toGltf(tunes.joints[from].map((c, i) => c - tunes.joints[to][i])) : null;
  written.push(await convert(join(src, `${k}.glb`), name, join(PARTS, 'kit', `${name}.glb`), delta && ((p) => p.map((c, i) => c + delta[i]))));
}
for (const [k, [id, mount, originJoint]] of Object.entries(ITEMS)) {
  const [mountJoint, [dx, dy, dz]] = tunes.mounts[mount]; // Blender axes, mm, relative to the mount's joint
  // Where the mount is relative to the joint the part's origin sits on (nowhere if the origin is the mount).
  const from = tunes.joints[originJoint ?? mountJoint];
  const to = tunes.joints[mountJoint];
  const [ox, oy, oz] = originJoint === 'mount' ? [0, 0, 0] : [to[0] - from[0] + dx, to[1] - from[1] + dy, to[2] - from[2] + dz];
  const off = [ox, oz, -oy]; // glTF is y-up: (x, z, -y)
  const name = `item_${id}`;
  written.push(await convert(join(src, `${k}.glb`), name, join(PARTS, `${name}.glb`), (p) => p.map((c, i) => (c - off[i]) / ITEM_SCALE)));
}

// The Seer measures its own skeleton: move the frame's joints (and the numbered arm mounts) to the tunes, the right arm's
// shoulder, elbow and wrist to "jointsRight". Nodes hang from their parent joint, so each is placed by the difference.
if (model.frame) {
  const framePath = join(PARTS, 'kit', `${model.frame}.glb`);
  const doc = await io.read(framePath);
  const nodes = new Map(doc.getRoot().listNodes().map((n) => [n.getName(), n]));
  const PARENT = { hip: 'pelvis', spine: 'pelvis', knee: 'hip', ankle: 'knee', chest: 'spine', neck: 'chest', head: 'neck', shoulder: 'chest', elbow: 'shoulder', wrist: 'elbow' };
  const SIDED = new Set(['shoulder', 'elbow', 'wrist', 'hip', 'knee', 'ankle']);
  const place = (side, name) => {
    if (side === 'R' && tunes.jointsRight?.[name]) return tunes.jointsRight[name];
    const p = tunes.joints[name];
    return side === 'R' ? [-p[0], p[1], p[2]] : p;
  };
  nodes.get('joint_pelvis').setTranslation(toGltf(tunes.joints.pelvis));
  for (const side of ['L', 'R'])
    for (const [name, parent] of Object.entries(PARENT)) {
      const node = nodes.get(SIDED.has(name) ? `joint_${name}_${side}` : `joint_${name}`);
      if (!node || (side === 'R' && !SIDED.has(name))) continue;
      const p = place(side, name);
      const q = parent === 'pelvis' || !SIDED.has(parent) ? tunes.joints[parent] : place(side, parent);
      node.setTranslation(toGltf(p.map((c, i) => c - q[i])));
    }
  for (const [mount, [, off]] of Object.entries(tunes.mounts)) if (nodes.has(mount)) nodes.get(mount).setTranslation(toGltf(off));
  await io.write(framePath, doc);
}

// Retire the old cut: right-hand copies and every part the composite does not have (cloth, collar, the Brute's arm and hands).
const manifestPath = join(PARTS, 'manifest.json');
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
const keep = new Set(KIT.map(kitName));
const old = new RegExp(`^${faction}_.+_${cls}$`);
for (const key of Object.keys(manifest.kit)) {
  if (!old.test(key)) continue;
  if (!keep.has(key)) {
    rmSync(join(PARTS, manifest.kit[key]), { force: true });
    delete manifest.kit[key];
  }
}
for (const k of KIT) manifest.kit[kitName(k)] = `kit/${kitName(k)}.glb`;
for (const [, [id]] of Object.entries(ITEMS)) manifest.items[id] = `item_${id}.glb`;
for (const kind of ['items', 'kit']) manifest[kind] = Object.fromEntries(Object.entries(manifest[kind]).sort(([a], [b]) => (a < b ? -1 : 1)));
writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

console.log(written.map((f) => f.replace(`${resolve('.')}/`, '')).join('\n'));
console.log(`\nnext: KTX2_NORMAL=etc1s KTX2_BASE_Q=150 node scripts/compress-parts.mjs ${written.map((f) => f.replace(`${resolve('.')}/`, '')).join(' ')}`);
