// Publish a composite walker (assets/blender/parts/composite) into the game, without Blender.
//   node scripts/publish-composite.mjs DIR/glb [paladin|brute|seer|sentinel|artillery|goliath]   (DIR is the build.py output, e.g. models/paladin-composite)
//   node scripts/publish-composite.mjs DIR/glb brute --items   (only the items present in DIR/glb: the Brute's claw and rail cannon)
//   node scripts/compress-parts.mjs <the files this prints>   (KTX2 and quantisation; see assets/blender/parts/meshy/README.md)
//
// build.py writes one GLB per part with its origin on its joint, in millimetres. The game wants the same parts under
// kit names, so this renames and wraps them:
//   pelvis, torso, helm, back, pauldron, arm, forearm, hand, thigh, shin, foot -> kit/covenant_<part>_paladin.glb
//   pauldron_r (the figure's own right pauldron and long cape) -> kit/covenant_pauldron-right_paladin.glb
//   blade -> item_lance@paladin.glb          pod -> item_carapace-gun@paladin.glb
//   with ITEMS (paladin_items_build.py's output): carapace-gun, missile-rack, kinetic-shield -> item_<id>@paladin.glb, and the
//   shoulder and bracer sockets merged into the torso and forearm (a gunmetal and a gold primitive, with normals)
// Items are stored at scout scale with their origin on the hand/core mount (the web grows them by the titan factor 1.7),
// so their vertices are moved by the mount offset in data/model-kit.json and divided by 1.7.
// The Brute (foundries/bulwark, grown 1.4 by the web) has no arm, forearm or hand: its parts are pelvis, torso, helm, back,
// pauldron, thigh, shin and foot, and each gun is a whole forearm with its origin on the elbow. The guns are moved onto the
// numbered arm mount the old brute items used, so they hang from the same hardpoint; both are modelled for the left.
// The Seer (reliquary/striker, grown 1.2 by the web) is built for the left and mirrored by the web: arm, pauldron and
// wing, and legs (its native right pauldron, published as the `-right` variant before 2026-11-02, is retired). A model whose right arm is its
// own can still give frameTunes "jointsRight" (joint_shoulder_R, elbow_R and wrist_R off the mirror of the left). Its helm
// is built on the neck knuckle but hangs on the head joint, so its vertices are moved by the difference. The arc spear and
// the kinetic claws take the hand's place on the wrist socket, with their origin on the wrist joint (seer_wrist.py).
// The Sentinel (covenant/bulwark, its own frame covenant_frame_sentinel copied from the bulwark frame) has the Paladin's eleven
// body parts under covenant_<part>_sentinel and no items yet; its twelfth part, the Carapace Gun forearm, is not published
// (it needs fit entries first, see docs/sentinel-composite/README.md).
// The script also moves the frame's joints to the tunes.
// The old open-shell cut is retired: its right-hand copies (the web mirrors the left), cloth and collar files go, and the
// manifest drops them. The collar is part of the torso now (data/model-kit.json "omit" keeps the Titan collar off).
import { existsSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { mergeDocuments, unpartition } from '@gltf-transform/functions';

const PARTS = resolve('apps/web/public/parts');
const MODELS = {
  paladin: {
    faction: 'covenant', cls: 'paladin', tunes: 'covenant/titan', itemScale: 1.7,
    kit: ['pelvis', 'torso', 'helm', 'back', 'pauldron', 'pauldron_r', 'arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'],
    // The right pauldron is the figure's own (black, with the long cape): the web uses it on the right instead of the mirror.
    component: { pauldron_r: 'pauldron-right' },
    // part -> [item id, numbered mount, joint the part's origin is on (default: the mount's own joint; 'mount': the mount itself)]
    // The Carapace Gun, Missile Rack and Kinetic Shield come from paladin_items_build.py's folder (the 4th argument), cut on the
    // chest and elbow joints; their sockets (hosts/*.npz) are merged into the torso and the forearm.
    items: {
      blade: ['lance@paladin', 'mount_armLeft_0'],
      'carapace-gun': ['carapace-gun@paladin', 'mount_core_0', 'chest', 'items'],
      'missile-rack': ['missile-rack@paladin', 'mount_core_0', 'chest', 'items'],
      'kinetic-shield': ['kinetic-shield@paladin', 'mount_armLeft_0', 'elbow', 'items'],
    },
    hosts: { torso: ['spine', ['shoulder_L', 'shoulder_R']], forearm: ['elbow', ['bracer_L']] },
  },
  brute: {
    // Its own frame: a copy of the bulwark frame (Artillery keeps that one) with the joints the parts were cut on.
    faction: 'foundries', cls: 'brute', tunes: 'foundries/brute', itemScale: 1.4, frame: 'foundries_frame_brute', frameFrom: 'foundries_frame_bulwark',
    kit: ['pelvis', 'torso', 'helm', 'back', 'pauldron', 'thigh', 'shin', 'foot'],
    items: {
      rockets: ['rocket-pod@brute', 'mount_armLeft_0', 'elbow'], gatling: ['autocannon@brute', 'mount_armLeft_0', 'elbow'],
      // The original Meshy claw and rail cannon sculpts, cut onto the cannon arm's elbow peg (item_cut.py): whole forearms.
      claw: ['industrial-claw@brute', 'mount_armLeft_0', 'elbow'], rail: ['rail-cannon@brute', 'mount_armLeft_0', 'elbow'],
    },
  },
  seer: {
    faction: 'reliquary', cls: 'seer', tunes: 'reliquary/striker', itemScale: 1.2, frame: 'reliquary_frame_striker',
    kit: ['pelvis', 'torso', 'helm', 'crown', 'back', 'pauldron', 'arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'],
    // Compressed with compress-parts.mjs's defaults (UASTC normals): ETC1S normals show as blotches on its gold and bronze.
    ktx2: '',
    // build part -> [kit component, the joint its origin sits on, the joint it hangs on when that differs]
    origin: { helm: ['neck', 'head'] },
    // The arc spear and the kinetic claws (seer_wrist.py) plug into the wrist socket in place of the hand: their origin is
    // the wrist joint, and the web hides the hand on that side (fit.hardpoints wrist-socket). The Hellfire launcher stands on a
    // socket in the arm's shoulder drum (seer_items.py): its origin is the socket seat, given here as an offset from the
    // shoulder joint (kit mm, Blender axes). Since the 2026-11-08 polish the socket is part of the arm's own mesh and
    // textures (no `hosts` entry: the flat-gold sleeve primitive is gone). The right arm is the left mirrored, so the one
    // socket serves both shoulders.
    items: {
      'arc-cannon': ['arc-cannon@seer', ['wrist', [0, 0, 0]], 'mount', 'items'],
      'kinetic-claws': ['kinetic-claws@seer', ['wrist', [0, 0, 0]], 'mount', 'items'],
      'hellfire-missiles': ['hellfire-missiles@seer', ['shoulder', [1.396, -0.958, 1.896]], 'mount', 'items'],
    },
  },
  sentinel: {
    faction: 'covenant', cls: 'sentinel', tunes: 'covenant/sentinel', itemScale: 1.4, frame: 'covenant_frame_sentinel', frameFrom: 'covenant_frame_bulwark',
    kit: ['pelvis', 'torso', 'helm', 'back', 'pauldron', 'arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'],
    // The Carapace Gun is cut as a whole forearm on the elbow (RESEAT in sentinel.py), modelled for the left; the web hangs it
    // on the right elbow (fit.items.carapace-gun.classes.sentinel) and hides the forearm and hand there.
    items: { gun: ['carapace-gun@sentinel', ['elbow', [0, 0, 0]], 'elbow'] },
  },
  artillery: {
    // Its own frame, a copy of the bulwark frame with the joints the parts were cut on (like the Brute's). The howitzer is part of the torso.
    faction: 'foundries', cls: 'artillery', tunes: 'foundries/artillery', itemScale: 1.4, frame: 'foundries_frame_artillery', frameFrom: 'foundries_frame_bulwark',
    // Its shell arm (forearm + clamp with the shell) is an item, the Shell Arm weapon, not a body part: the elbow holds one forearm,
    // the shell or another weapon. "forearm+hand" merges the two parts into one item with its origin on the elbow.
    kit: ['pelvis', 'torso', 'helm', 'back', 'pauldron', 'arm', 'thigh', 'shin', 'foot'],
    items: { 'forearm+hand': ['shell-arm@artillery', ['elbow', [0, 0, 0]], 'elbow', undefined, { forearm: 'elbow', hand: 'wrist' }] },
  },
  goliath: {
    // Its own frame, a copy of the titan frame with the joints the parts were cut on. The Arc Cannon is its right forearm, cut as a
    // whole forearm on the elbow (RESEAT in goliath.py), modelled for the left; the web hangs it on the right elbow
    // (fit.items.arc-cannon.classes.goliath) and hides the forearm and hand there. The hand is a bare gilded claw.
    faction: 'reliquary', cls: 'goliath', tunes: 'reliquary/goliath', itemScale: 1.7, frame: 'reliquary_frame_goliath', frameFrom: 'reliquary_frame_titan',
    kit: ['pelvis', 'torso', 'helm', 'back', 'pauldron', 'arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'],
    items: { gun: ['arc-cannon@goliath', ['elbow', [0, 0, 0]], 'elbow'] },
  },
};

const src = process.argv[2];
const itemsOnly = process.argv.includes('--items');
const model = MODELS[process.argv[3] ?? 'paladin'];
const itemsDir = process.argv[4];
if (!src || !existsSync(src) || !model) {
  console.error('usage: node scripts/publish-composite.mjs DIR/glb [paladin|brute|seer|sentinel|artillery|goliath] [ITEMS_DIR]');
  process.exit(1);
}
const { faction, cls, itemScale: ITEM_SCALE, kit: KIT, items: ITEMS, component: COMPONENT = {}, origin: ORIGIN = {} } = model;
const kitName = (k) => `${faction}_${COMPONENT[k] ?? k}_${cls}`;
const tunes = JSON.parse(readFileSync('data/model-kit.json', 'utf8')).frameTunes[model.tunes];
const PRINT = 1.5; // print mm per kit mm (paladin.py PRINT_SCALE)
/** Read a numpy .npz of float32 P (n,3) and int32 T (m,3), optionally float32 N (n,3) and int32 M (m): stored (uncompressed)
 * .npy members. */
function readNpz(file) {
  const z = readFileSync(file);
  // The central directory has the real sizes (a streamed zip leaves them 0 in the local headers).
  let e = z.length - 22;
  while (z.readUInt32LE(e) !== 0x06054b50) e--;
  let c = z.readUInt32LE(e + 16);
  const out = {};
  for (let n = z.readUInt16LE(e + 10); n > 0; n--) {
    const method = z.readUInt16LE(c + 10);
    const size = z.readUInt32LE(c + 24);
    const nl = z.readUInt16LE(c + 28);
    const xl = z.readUInt16LE(c + 30);
    const cl = z.readUInt16LE(c + 32);
    const lo = z.readUInt32LE(c + 42);
    const name = z.toString('latin1', c + 46, c + 46 + nl).replace(/\.npy$/, '');
    c += 46 + nl + xl + cl;
    if (method !== 0) throw new Error(`${file}: compressed npz member`);
    const start = lo + 30 + z.readUInt16LE(lo + 26) + z.readUInt16LE(lo + 28);
    const hl = z.readUInt16LE(start + 8);
    const copy = new Uint8Array(z.subarray(start + 10 + hl, start + size)).buffer;
    out[name] = name === 'P' || name === 'N' ? new Float32Array(copy) : new Int32Array(copy);
  }
  return out;
}
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);

/** Wrap a part's nodes in a root named for the part; optionally move/scale its vertices. */
async function convert(file, name, out, fix, host) {
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
  if (host) addHost(doc, host);
  await io.write(out, doc);
  return out;
}

/** Merge the sockets (npz files in print mm, Blender axes, world) into a part's mesh: a gunmetal primitive and, where the
 * sockets mark triangles gold (M = 1, paladin_items.py), a gold one, each with the sockets' own normals (N) when they have
 * them. Gunmetal and gold are build.py's cut-face and knuckle colours, so a socket matches the item collar on it, but the
 * gunmetal is blackened steel (roughness 0.9, not 0.42): a socket's seat is a flat disc facing up, and a smoother one
 * caught the stage's rim light and bloomed into a white halo over the shoulders.
 * `joint` is the joint the part's origin sits on (kit mm), so the sockets land where the part's own vertices are.
 * A host given a colour (the Seer's sleeve) is all that colour. */
function addHost(doc, [joint, names, colour]) {
  const mesh = doc.getRoot().listMeshes()[0];
  const buf = doc.getRoot().listBuffers()[0];
  const j = tunes.joints[joint];
  const groups = [0, 1].map(() => ({ pos: [], nor: [], idx: [] }));
  let normals = true;
  for (const n of names) {
    const { P, T, N, M } = readNpz(join(itemsDir, '..', 'hosts', `${n}.npz`));
    normals &&= !!N;
    const seen = [new Map(), new Map()];
    for (let t = 0; t < T.length / 3; t++) {
      const g = M ? M[t] : 0;
      const grp = groups[g];
      for (let c = 0; c < 3; c++) {
        const v = T[3 * t + c];
        if (!seen[g].has(v)) {
          seen[g].set(v, grp.pos.length / 3);
          const [x, y, z] = [P[3 * v] / PRINT - j[0], P[3 * v + 1] / PRINT - j[1], P[3 * v + 2] / PRINT - j[2]];
          grp.pos.push(x, z, -y); // Blender (z up) to glTF (y up)
          if (N) grp.nor.push(N[3 * v], N[3 * v + 2], -N[3 * v + 1]);
        }
        grp.idx.push(seen[g].get(v));
      }
    }
  }
  const mats = [
    () =>
      colour
        ? doc.createMaterial('hardpoint_gold').setBaseColorFactor([...colour, 1]).setMetallicFactor(0.9).setRoughnessFactor(0.35)
        : doc.createMaterial('hardpoint_gunmetal').setBaseColorFactor([0.035, 0.035, 0.04, 1]).setMetallicFactor(1).setRoughnessFactor(0.9),
    () => doc.createMaterial('hardpoint_gold').setBaseColorFactor([0.56, 0.4, 0.18, 1]).setMetallicFactor(1).setRoughnessFactor(0.3),
  ];
  groups.forEach((grp, g) => {
    if (!grp.idx.length) return;
    const prim = doc
      .createPrimitive()
      .setAttribute('POSITION', doc.createAccessor().setType('VEC3').setArray(new Float32Array(grp.pos)).setBuffer(buf))
      .setIndices(doc.createAccessor().setType('SCALAR').setArray(new Uint32Array(grp.idx)).setBuffer(buf))
      .setMaterial(mats[g]());
    if (normals) prim.setAttribute('NORMAL', doc.createAccessor().setType('VEC3').setArray(new Float32Array(grp.nor)).setBuffer(buf));
    mesh.addPrimitive(prim);
  });
}

const written = [];
const toGltf = ([x, y, z]) => [x, z, -y]; // Blender (z up) to glTF (y up)
for (const k of itemsOnly ? [] : KIT) {
  const name = kitName(k);
  // A part built on one joint but hung on another (the Seer's helm) is moved by the difference.
  const [from, to] = ORIGIN[k] ?? [];
  const delta = from ? toGltf(tunes.joints[from].map((c, i) => c - tunes.joints[to][i])) : null;
  const host = itemsDir && model.hosts?.[k];
  written.push(await convert(join(src, `${k}.glb`), name, join(PARTS, 'kit', `${name}.glb`), delta && ((p) => p.map((c, i) => c + delta[i])), host));
}
/** Merge several parts (each cut on its own joint) into one item GLB: `joints` names the joint each part's origin sits on. */
async function convertMerged(k, joints, name, out, vertexFix) {
  const doc = await io.read(join(src, `${k.split('+')[0]}.glb`));
  const root = doc.createNode(name);
  const first = doc.getRoot().getDefaultScene();
  for (const n of first.listChildren()) {
    first.removeChild(n);
    root.addChild(n);
  }
  first.addChild(root);
  const fixed = new Set();
  const fixMeshes = (d, fix) => {
    for (const mesh of d.getRoot().listMeshes())
      for (const prim of mesh.listPrimitives()) {
        const pos = prim.getAttribute('POSITION');
        const v = [0, 0, 0];
        for (let i = 0; i < pos.getCount(); i++) pos.setElement(i, fix(pos.getElement(i, v)));
      }
  };
  fixMeshes(doc, vertexFix(joints[k.split('+')[0]]));
  for (const part of k.split('+').slice(1)) {
    const other = await io.read(join(src, `${part}.glb`));
    fixMeshes(other, vertexFix(joints[part]));
    const before = new Set(doc.getRoot().listScenes());
    mergeDocuments(doc, other);
    for (const scene of doc.getRoot().listScenes()) {
      if (before.has(scene)) continue;
      for (const n of scene.listChildren()) {
        scene.removeChild(n);
        root.addChild(n);
      }
      scene.dispose();
    }
  }
  for (const mat of doc.getRoot().listMaterials()) mat.setName(`hull_${name}_livery`);
  await doc.transform(unpartition());
  await io.write(out, doc);
  return out;
}

for (const [k, [id, mount, originJoint, from_, partJoints]] of Object.entries(ITEMS)) {
  if (from_ === 'items' && !itemsDir) continue; // needs paladin_items_build.py's folder
  if (itemsOnly && !existsSync(join(from_ === 'items' ? itemsDir : src, `${k.split('+')[0]}.glb`))) continue;
  if (partJoints) {
    // Each part's vertices are moved from its own joint to the mount, like a single part's below.
    const [mountJoint, [dx, dy, dz]] = Array.isArray(mount) ? mount : tunes.mounts[mount];
    const to = tunes.joints[mountJoint];
    const vertexFix = (joint) => {
      const from = tunes.joints[joint];
      const off = toGltf([to[0] - from[0] + dx, to[1] - from[1] + dy, to[2] - from[2] + dz]);
      return (p) => p.map((c, i) => (c - off[i]) / ITEM_SCALE);
    };
    written.push(await convertMerged(k, partJoints, `item_${id}`, join(PARTS, `item_${id}.glb`), vertexFix));
    continue;
  }
  const [mountJoint, [dx, dy, dz]] = Array.isArray(mount) ? mount : tunes.mounts[mount]; // Blender axes, mm, relative to the mount's joint
  // Where the mount is relative to the joint the part's origin sits on (nowhere if the origin is the mount).
  const from = tunes.joints[originJoint ?? mountJoint];
  const to = tunes.joints[mountJoint];
  const [ox, oy, oz] = originJoint === 'mount' ? [0, 0, 0] : [to[0] - from[0] + dx, to[1] - from[1] + dy, to[2] - from[2] + dz];
  const off = [ox, oz, -oy]; // glTF is y-up: (x, z, -y)
  const name = `item_${id}`;
  written.push(await convert(join(from_ === 'items' ? itemsDir : src, `${k}.glb`), name, join(PARTS, `${name}.glb`), (p) => p.map((c, i) => (c - off[i]) / ITEM_SCALE)));
}

// The Seer and the Brute measure their own skeletons: move the frame's joints (and the numbered arm mounts) to the tunes,
// the right arm's shoulder, elbow and wrist to "jointsRight". Nodes hang from their parent joint, so each is placed by the
// difference. The Brute's frame is a class frame (foundries_frame_brute, which the web prefers over the bulwark frame),
// copied from the frame it shares with Artillery.
if (model.frame && !itemsOnly) {
  const framePath = join(PARTS, 'kit', `${model.frame}.glb`);
  const doc = await io.read(model.frameFrom ? join(PARTS, 'kit', `${model.frameFrom}.glb`) : framePath);
  if (model.frameFrom) {
    doc.getRoot().getDefaultScene().listChildren()[0].setName(model.frame);
  }
  // covenant_frame_bulwark was exported with Blender's ".002" suffix on every node name: the joints would not be found.
  for (const n of doc.getRoot().listNodes()) if (/\.\d{3}$/.test(n.getName())) n.setName(n.getName().replace(/\.\d{3}$/, ''));
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
  if (model.frameFrom) written.push(framePath);
}

// Retire the old cut: right-hand copies and every part the composite does not have (cloth, collar, the Brute's arm and hands).
const manifestPath = join(PARTS, 'manifest.json');
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
const keep = new Set([...KIT.map(kitName), ...(model.frameFrom ? [model.frame] : [])]);
const old = new RegExp(`^${faction}_.+_${cls}$`);
for (const key of itemsOnly ? [] : Object.keys(manifest.kit)) {
  if (!old.test(key)) continue;
  if (!keep.has(key)) {
    rmSync(join(PARTS, manifest.kit[key]), { force: true });
    delete manifest.kit[key];
  }
}
if (!itemsOnly) for (const k of KIT) manifest.kit[kitName(k)] = `kit/${kitName(k)}.glb`;
if (model.frameFrom && !itemsOnly) manifest.kit[model.frame] = `kit/${model.frame}.glb`;
for (const [k, [id, , , from_]] of Object.entries(ITEMS))
  if (from_ === 'items' ? itemsDir && existsSync(join(itemsDir, `${k}.glb`)) : !itemsOnly || existsSync(join(src, `${k.split('+')[0]}.glb`))) manifest.items[id] = `item_${id}.glb`;
for (const kind of ['items', 'kit']) manifest[kind] = Object.fromEntries(Object.entries(manifest[kind]).sort(([a], [b]) => (a < b ? -1 : 1)));
writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);

console.log(written.map((f) => f.replace(`${resolve('.')}/`, '')).join('\n'));
console.log(`\nnext: ${model.ktx2 ?? 'KTX2_NORMAL=etc1s KTX2_BASE_Q=150 '}node scripts/compress-parts.mjs ${written.map((f) => f.replace(`${resolve('.')}/`, '')).join(' ')}`);
