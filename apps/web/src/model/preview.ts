// Standalone turntable for judging the walker models: render.html?chassis=brute&angle=35&set=b&paint=%231f5c63
// kit=force shows a class's kit body even with parts missing (stand-ins fill in), kit=off the procedural one.
// part=covenant_helm_titan shows one Blender part from the manifest on its own.
// Used by scripts/render-walkers.mjs to save preview images without the full app.
// backdrop=covenant|foundries|reliquary picks the world; elev=0.12 drops the camera for a low hero shot.
// lo={"core":["coolant-loop"]} (JSON) sets the loadout; dump=1 puts item and joint positions in data-dump (see scripts/fit-check.mjs).
// fit=off shows the old numbered mounts instead of the hardpoints.
// zoom=2 moves in, fy=0.7 aims at 70% of the height (for close-ups of a hardpoint).
// show=helm,collar keeps only those kit components (the body part of a card); plain=1 drops the floor and skyline
// so only the sky is left behind it; side=R keeps only that side's sided parts; see scripts/render-card-art.mjs.
// solo=1 drops the rest of the body instead of dimming it (the closed composite parts stand on their own); dim=0.07 sets how dark it goes; roll=-55 tilts the model about the view axis.
// lineup=8 stands that many walkers in a row; bench=120 then times that many frames into data-bench.
import * as THREE from 'three';
import type { WalkerInput } from '@brass-charter/rules';
import { buildWalkerModel, ensureKitParts, loadPartLibrary, setFitEnabled, type KitMode } from './assemble';
import { createStage, type Backdrop } from './stage';

const SHOWCASE: Record<string, WalkerInput['loadout']> = {
  lancer: { armRight: ['lance'], armLeft: ['melee-blade'], core: ['carapace-gun'], legs: ['sprint-servos'] },
  sentinel: { armRight: ['kinetic-shield'], armLeft: ['lance'], core: ['carapace-gun', 'reactive-shell', 'field-repair-rig', 'smoke-launcher'], legs: ['anchor-spikes'] },
  paladin: { armRight: ['lance', 'melee-blade'], armLeft: ['missile-rack'], core: ['carapace-gun', 'ablative-plating'], legs: ['jump-jets'] },
  scavenger: { armRight: ['autocannon'], armLeft: ['industrial-claw'], core: ['spotter-drone', 'smoke-launcher'], legs: ['sprint-servos'] },
  brute: { armRight: ['autocannon', 'autocannon'], armLeft: ['industrial-claw', 'kinetic-shield'], core: ['ablative-plating', 'coolant-loop'], legs: ['gyro-stabilisers'] },
  artillery: { armRight: ['rail-cannon', 'autocannon'], armLeft: ['rocket-pod', 'autocannon'], core: ['targeting-array', 'overcharged-boiler'], legs: ['anchor-spikes'] },
  wraith: { armRight: ['kinetic-claws'], armLeft: ['kinetic-claws'], core: ['smoke-launcher'], legs: ['jump-jets'] },
  seer: { armRight: ['hellfire-missiles'], armLeft: ['arc-cannon'], core: ['soul-lantern', 'spotter-drone', 'coolant-loop'], legs: ['gyro-stabilisers'] },
  goliath: { armRight: ['arc-cannon', 'kinetic-claws'], armLeft: ['hellfire-missiles'], core: ['soul-lantern', 'reactive-shell', 'overcharged-boiler'], legs: ['anchor-spikes', 'gyro-stabilisers'] },
};

// A second set covers the parts the first leaves out.
const SHOWCASE_B: Record<string, WalkerInput['loadout']> = {
  brute: { armRight: ['rail-cannon'], armLeft: ['rocket-pod'], core: ['reactive-shell', 'targeting-array'], legs: ['jump-jets'] },
};

const q = new URLSearchParams(location.search);
const chassis = q.get('chassis') ?? 'brute';
const angle = Number(q.get('angle') ?? 35);
const w = Number(q.get('w') ?? 900);
const h = Number(q.get('h') ?? 900);

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(w, h);
document.body.appendChild(renderer.domElement);
const stage = createStage(renderer, (q.get('backdrop') as Backdrop) ?? 'covenant');
stage.setSize(w, h);
const { scene, fit } = stage;

const lib = await loadPartLibrary(renderer);
const kit = (q.get('kit') as KitMode) ?? 'auto';
setFitEnabled(q.get('fit') !== 'off');
const build = (id: string) =>
  buildWalkerModel({ name: id, chassis: id, driver: { command: 0, trait: null }, loadout: q.get('lo') ? JSON.parse(q.get('lo')!) : (q.get('set') === 'b' ? SHOWCASE_B : SHOWCASE)[id] ?? {} } as WalkerInput, q.get('paint') ?? '#7a2e22', lib, kit);
const lineup = Number(q.get('lineup') ?? 1);
const model = new THREE.Group();
const ids = Object.keys(SHOWCASE);
const partName = q.get('part');
if (partName) {
  const file = lib.kitFiles.get(partName) ?? `${partName}.glb`;
  if (lib.load) model.add(await lib.load(file));
}
for (let i = 0; i < (partName ? 0 : lineup); i++) {
  const id = lineup > 1 ? ids[i % ids.length] : chassis;
  await ensureKitParts(lib, id);
  const m = build(id);
  m.position.x = (i - (lineup - 1) / 2) * 34;
  m.position.z = -Math.abs(i - (lineup - 1) / 2) * 10;
  model.add(m);
}
// Card art: the named kit components (kit_<component>[_side] nodes) stay lit and the rest of the body is dimmed, so
// the part shows where it sits. The framing below then fits only the lit part.
const show = q.get('show')?.split(',');
const lit = new THREE.Box3();
if (show) {
  const isKit = (o: THREE.Object3D) => {
    for (let n: THREE.Object3D | null = o; n; n = n.parent) if (n.name.startsWith('kit_')) return true;
    return false;
  };
  const keep = (o: THREE.Object3D) => {
    for (let n: THREE.Object3D | null = o; n; n = n.parent) {
      const m = /^kit_([a-z]+)(?:_([LR]))?$/.exec(n.name);
      if (m) return show.includes(m[1]) && (!side || !m[2] || m[2] === side);
    }
    return false;
  };
  const dim = Number(q.get('dim') ?? 0.07);
  const solo = !!q.get('solo');
  const side = q.get('side');
  model.updateMatrixWorld(true);
  const gone: THREE.Object3D[] = [];
  model.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    if (!isKit(mesh)) {
      // Items and the stand-in plinth would only clutter the card.
      gone.push(mesh);
      return;
    }
    if (keep(mesh)) {
      lit.union(new THREE.Box3().setFromObject(mesh));
      return;
    }
    if (solo) {
      gone.push(mesh);
      return;
    }
    const fade = (m: THREE.Material) => {
      const c = m.clone() as THREE.MeshStandardMaterial;
      c.color?.multiplyScalar(dim);
      if (c.emissive) c.emissiveIntensity *= dim;
      c.envMapIntensity = dim;
      return c;
    };
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(fade) : fade(mesh.material);
  });
  for (const o of gone) o.removeFromParent();
}
const roll = Number(q.get('roll') ?? 0);
if (roll) model.rotation.z = (roll * Math.PI) / 180;
if (q.get('plain')) {
  for (const o of [...scene.children]) if (o.name === 'stage_floor' || o.name.startsWith('stage_backdrop')) o.removeFromParent();
}
scene.add(model);
fit(model);

// Frame the model: fit its bounding box to the view.
const box = lit.isEmpty() ? new THREE.Box3().setFromObject(model) : lit;
const centre = box.getCenter(new THREE.Vector3());
const size = box.getSize(new THREE.Vector3()).length();
const camera = new THREE.PerspectiveCamera(30, w / h, 1, 4000);
const rad = (angle * Math.PI) / 180;
const dist = (size * 1.55) / Number(q.get('zoom') ?? 1);
if (q.get('fy')) centre.y = box.min.y + (box.max.y - box.min.y) * Number(q.get('fy'));
camera.position.set(centre.x + Math.sin(rad) * dist, centre.y + dist * Number(q.get('elev') ?? 0.38), centre.z + Math.cos(rad) * dist);
camera.lookAt(centre);
stage.render(camera);

const bench = Number(q.get('bench') ?? 0);
if (bench) {
  renderer.info.autoReset = false;
  renderer.info.reset();
  stage.render(camera);
  const { calls, triangles } = renderer.info.render;
  // Reading a pixel back makes each frame finish before the clock stops.
  const gl = renderer.getContext();
  const pixel = new Uint8Array(4);
  const t0 = performance.now();
  for (let i = 0; i < bench; i++) {
    camera.position.applyAxisAngle(new THREE.Vector3(0, 1, 0), 0.01);
    camera.lookAt(centre);
    stage.render(camera);
    gl.readPixels(0, 0, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
  }
  const ms = (performance.now() - t0) / bench;
  document.body.dataset.bench = JSON.stringify({ msPerFrame: +ms.toFixed(2), calls, triangles });
}
if (q.get('dump')) {
  const out: { bbox: number[][]; joints: Record<string, number[]>; items: Array<{ id: string; hp: string; min: number[]; max: number[] }> } = { bbox: [], joints: {}, items: [] };
  const bb = new THREE.Box3().setFromObject(model);
  out.bbox = [bb.min.toArray(), bb.max.toArray()];
  model.traverse((o) => {
    const j = o.userData.joint ?? (o.name.startsWith('joint_') ? o.name : undefined);
    if (j) out.joints[j] = o.getWorldPosition(new THREE.Vector3()).toArray();
    if (o.name.startsWith('part_')) {
      const b = new THREE.Box3().setFromObject(o);
      let hp: THREE.Object3D | null = o.parent;
      while (hp && !hp.name.startsWith('hp_') && !hp.name.startsWith('mount_')) hp = hp.parent;
      out.items.push({ id: o.name.slice(5), hp: hp?.name ?? o.parent?.name ?? '', min: b.min.toArray(), max: b.max.toArray() });
    }
  });
  document.body.dataset.dump = JSON.stringify(out);
}
document.body.dataset.ready = '1';
