// Standalone turntable for judging the walker models: render.html?chassis=brute&angle=35&set=b&paint=%231f5c63
// kit=force shows a class's kit body even with parts missing (stand-ins fill in), kit=off the procedural one.
// part=covenant_helm_titan shows one Blender part from the manifest on its own.
// Used by scripts/render-walkers.mjs to save preview images without the full app.
// backdrop=covenant|foundries|reliquary picks the world; elev=0.12 drops the camera for a low hero shot.
// loadout=armLeft:lance,armRight:lance sets the equipment; fov=24 and dist=1.2 tighten the camera.
// lineup=8 stands that many walkers in a row; bench=120 then times that many frames into data-bench.
import * as THREE from 'three';
import type { WalkerInput } from '@brass-charter/rules';
import { buildWalkerModel, ensureKitParts, loadPartLibrary, type KitMode } from './assemble';
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
// loadout=armLeft:lance,armRight:lance,core:ablative-plating overrides the showcase loadout.
const custom = q.get('loadout');
const customLoadout = custom
  ? Object.fromEntries([...new Set(custom.split(',').map((x) => x.split(':')[0]))].map((loc) => [loc, custom.split(',').filter((x) => x.startsWith(loc + ':')).map((x) => x.split(':')[1])]))
  : null;
const build = (id: string) =>
  buildWalkerModel({ name: id, chassis: id, driver: { command: 0, trait: null }, loadout: customLoadout ?? (q.get('set') === 'b' ? SHOWCASE_B : SHOWCASE)[id] ?? {} } as WalkerInput, q.get('paint') ?? '#7a2e22', lib, kit);
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
scene.add(model);
fit(model);

// Frame the model: fit its bounding box to the view.
const box = new THREE.Box3().setFromObject(model);
const centre = box.getCenter(new THREE.Vector3());
const size = box.getSize(new THREE.Vector3()).length();
const camera = new THREE.PerspectiveCamera(Number(q.get('fov') ?? 30), w / h, 1, 4000);
const rad = (angle * Math.PI) / 180;
const dist = size * 1.55 * Number(q.get('dist') ?? 1);
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
document.body.dataset.ready = '1';
