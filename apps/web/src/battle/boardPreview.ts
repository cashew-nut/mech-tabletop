// Preview of the Blender board kit: every piece on a row of tiles, lit like the board. Used for review renders.
//   render-board.html?piece=tower_spire&angle=30&dist=6   (no piece: the whole kit in a row)
import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { KIT_PIECES, loadBoardKit, type KitPiece } from './boardKit';

const params = new URLSearchParams(location.search);
const only = params.get('piece') as KitPiece | null;
const angle = (Number(params.get('angle') ?? (only ? 30 : 0)) * Math.PI) / 180;
const pixel = Number(params.get('pixel') ?? 1);

const renderer = new THREE.WebGLRenderer({ antialias: false });
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.setClearColor(0x232a36);
const w = innerWidth;
const h = innerHeight;
renderer.setSize(Math.ceil(w / pixel), Math.ceil(h / pixel), false);
renderer.domElement.style.cssText = `width:${w}px;height:${h}px;image-rendering:pixelated`;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture; // as in Board3D
scene.environmentIntensity = 0.45;
scene.add(new THREE.HemisphereLight(0xdfe6f5, 0x4a4036, 0.5));
const sun = new THREE.DirectionalLight(0xffd9a0, 1.4);
sun.position.set(-10, 18, -7);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 60 });
sun.shadow.bias = -0.0008;
sun.shadow.normalBias = 0.02;
scene.add(sun);
const rim = new THREE.DirectionalLight(0x6f8cff, 0.5);
rim.position.set(12, 8, 10);
scene.add(rim);

const kit = await loadBoardKit();
if (!kit) throw new Error('Board kit failed to load');
const pieces = only ? [only] : KIT_PIECES.filter((p) => !p.startsWith('tile_'));
const tiles = KIT_PIECES.filter((p) => p.startsWith('tile_'));
const spacing = 2.2;
pieces.forEach((p, i) => {
  const x = (i - (pieces.length - 1) / 2) * spacing;
  const t = kit.make(tiles[i % tiles.length]);
  t.position.set(x, 0, 0);
  scene.add(t);
  const piece = kit.make(p);
  piece.position.set(x, 0.05, 0);
  scene.add(piece);
});
if (!only) {
  tiles.forEach((p, i) => {
    const t = kit.make(p);
    t.position.set((i - (tiles.length - 1) / 2) * 1.75, 0, 2.6);
    scene.add(t);
  });
}
const span = only ? 1 : pieces.length * spacing;
const dist = Number(params.get('dist') ?? (only ? 6 : span * 0.75));
const camera = new THREE.PerspectiveCamera(32, w / h, 0.1, 200);
const target = new THREE.Vector3(0, only ? 1.2 : 0.8, only ? 0 : 1.0);
camera.position.set(target.x + Math.sin(angle) * dist, target.y + dist * 0.45, target.z - Math.cos(angle) * dist);
camera.lookAt(target);
renderer.render(scene, camera);
document.body.dataset.ready = '1';
