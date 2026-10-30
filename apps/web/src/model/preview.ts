// Standalone turntable for judging the walker models: render.html?chassis=bulwark&angle=35
// Used by scripts/render-walkers.mjs to save preview images without the full app.
import * as THREE from 'three';
import type { WalkerInput } from '@brass-charter/rules';
import { buildWalkerModel, loadPartLibrary } from './assemble';
import { createStage } from './stage';

const SHOWCASE: Record<string, WalkerInput['loadout']> = {
  scout: { armRight: ['scattergun'], armLeft: ['shear-blade'], core: ['smoke-launcher'], legs: ['sprint-servos'] },
  striker: { armRight: ['autocannon', 'autocannon'], armLeft: ['missile-rack'], core: ['targeting-array', 'coolant-loop'], legs: ['jump-jets'] },
  bulwark: { armRight: ['rail-lance'], armLeft: ['kinetic-shield', 'impact-hammer'], core: ['overcharged-boiler', 'ablative-plating', 'smoke-launcher'], legs: ['anchor-spikes'] },
  titan: { armRight: ['arc-mortar', 'thermal-projector'], armLeft: ['beam-cutter', 'beam-cutter', 'kinetic-shield'], core: ['static-choir', 'spotter-drone', 'overcharged-boiler'], legs: ['gyro-stabilisers', 'anchor-spikes'] },
};

const q = new URLSearchParams(location.search);
const chassis = q.get('chassis') ?? 'bulwark';
const angle = Number(q.get('angle') ?? 35);
const w = Number(q.get('w') ?? 900);
const h = Number(q.get('h') ?? 900);

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(w, h);
document.body.appendChild(renderer.domElement);
const { scene, fit } = createStage(renderer);

const lib = await loadPartLibrary();
const walker: WalkerInput = { name: chassis, chassis, driver: { command: 0, trait: null }, loadout: SHOWCASE[chassis] ?? {} } as WalkerInput;
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
