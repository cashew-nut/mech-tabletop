// Standalone turntable for judging the walker models: render.html?chassis=brute&angle=35&set=b&paint=%231f5c63
// Used by scripts/render-walkers.mjs to save preview images without the full app.
import * as THREE from 'three';
import type { WalkerInput } from '@brass-charter/rules';
import { buildWalkerModel, loadPartLibrary } from './assemble';
import { createStage } from './stage';

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
const { scene, fit } = createStage(renderer);

const lib = await loadPartLibrary();
const walker: WalkerInput = { name: chassis, chassis, driver: { command: 0, trait: null }, loadout: (q.get('set') === 'b' ? SHOWCASE_B : SHOWCASE)[chassis] ?? {} } as WalkerInput;
const model = buildWalkerModel(walker, q.get('paint') ?? '#7a2e22', lib);
scene.add(model);
fit(model);

// Frame the model: fit its bounding box to the view.
const box = new THREE.Box3().setFromObject(model);
const centre = box.getCenter(new THREE.Vector3());
const size = box.getSize(new THREE.Vector3()).length();
const camera = new THREE.PerspectiveCamera(30, w / h, 1, 2000);
const rad = (angle * Math.PI) / 180;
const dist = size * 1.55;
camera.position.set(centre.x + Math.sin(rad) * dist, centre.y + dist * 0.38, centre.z + Math.cos(rad) * dist);
camera.lookAt(centre);
renderer.render(scene, camera);
document.body.dataset.ready = '1';
