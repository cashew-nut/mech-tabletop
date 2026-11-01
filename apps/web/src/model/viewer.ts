// Interactive walker viewer: apps/web/viewer.html (run `npm run dev -w apps/web`, open /viewer.html?chassis=paladin).
// Shows a class's kit body (the closed composite parts) with its equipment, a turntable, a part list with toggles, and an
// Explode button: every part slides off along the line from its parent, and a line from each joint shows where it plugs in.
// ?chassis=paladin|brute|seer  ?set=weapons|heavy|... (a loadout from scripts/fit-sets.json)  ?explode=1 starts pulled apart.
// document.body.dataset.ready is set once the model is up; window.viewer has setExplode(t) and toggleExplode() for tests.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { getChassis, type WalkerInput } from '@brass-charter/rules';
import fitSets from '../../../../scripts/fit-sets.json';
import { FACTION_COLOURS, buildWalkerModel, ensureKitParts, loadPartLibrary } from './assemble';
import { explodeOffsets, kitParents, type Unit } from './explode';
import { createStage, type Backdrop } from './stage';

const WALKERS = ['paladin', 'brute', 'seer'];
const SETS = fitSets as unknown as Record<string, Record<string, WalkerInput['loadout']>>;
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;

const q = new URLSearchParams(location.search);
let chassis = WALKERS.includes(q.get('chassis') ?? '') ? q.get('chassis')! : 'paladin';
const setName = q.get('set');

const view = $('view');
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
view.prepend(renderer.domElement);
const stage = createStage(renderer, 'covenant');
const camera = new THREE.PerspectiveCamera(30, 1, 1, 4000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false; // the camera follows the figure as it opens
controls.autoRotateSpeed = 1.6;
controls.maxPolarAngle = Math.PI * 0.52;

function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  renderer.setSize(w, h, false);
  stage.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(view);
resize();

const lib = await loadPartLibrary(renderer);

interface Part extends Unit {
  node: THREE.Object3D;
  /** Where the node's origin (its joint) sits at rest, world space. */
  home: THREE.Vector3;
  /** Lowest point at rest, world y. */
  floor: number;
  item: boolean;
  label: string;
}

let model: THREE.Group | null = null;
let parts: Part[] = [];
let offsets = new Map<string, THREE.Vector3>();
let guides: THREE.LineSegments | null = null;
let sockets: THREE.Points | null = null;
let current = 0; // 0 = together, 1 = pulled apart
let target = 0;

const prettyKit = (id: string) => {
  const m = /^kit_([a-z]+)(?:_([LR]))?$/.exec(id)!;
  return m[1] + (m[2] ? (m[2] === 'L' ? ' (left)' : ' (right)') : '');
};

/** The nodes that make up the walker: kit parts first, then the equipment hung on it. */
function collect(root: THREE.Object3D): Part[] {
  root.updateMatrixWorld(true);
  const out: Part[] = [];
  const centreOf = (n: THREE.Object3D) => new THREE.Box3().setFromObject(n).getCenter(new THREE.Vector3());
  root.traverse((o) => {
    const isKit = /^kit_[a-z]+(_[LR])?$/.test(o.name);
    const isItem = o.name.startsWith('part_');
    if (!isKit && !isItem) return;
    out.push({
      id: isItem ? `${o.name}#${out.length}` : o.name, parent: null, node: o, item: isItem,
      centre: centreOf(o), home: o.getWorldPosition(new THREE.Vector3()), floor: new THREE.Box3().setFromObject(o).min.y,
      label: isItem ? o.name.slice(5).replace(/-/g, ' ') + sideOf(o) : prettyKit(o.name),
    });
  });
  const kit = out.filter((p) => !p.item);
  const parents = kitParents(kit.map((p) => p.id), chassis);
  for (const p of kit) p.parent = parents.get(p.id) ?? null;
  // Equipment hangs off whichever body part is nearest to it.
  for (const it of out.filter((p) => p.item)) {
    let best = Infinity;
    for (const k of kit) {
      const d = k.centre.distanceToSquared(it.centre);
      if (d < best) { best = d; it.parent = k.id; }
    }
  }
  // Kit parts first, then equipment, so the panel reads body then gear.
  return [...kit, ...out.filter((p) => p.item)];
}

function sideOf(o: THREE.Object3D) {
  for (let n: THREE.Object3D | null = o; n; n = n.parent) {
    const m = /^hp_.*_([LR])$/.exec(n.name);
    if (m) return m[1] === 'L' ? ' (left)' : ' (right)';
  }
  return '';
}

function apply() {
  if (!model) return;
  for (const p of parts) {
    const off = offsets.get(p.id);
    const par = p.node.parent;
    if (!off || !par) continue;
    p.node.position.copy(par.worldToLocal(p.home.clone().addScaledVector(off, current)));
  }
  model.updateMatrixWorld(true);
  if (guides) {
    const pos: number[] = [];
    const dots: number[] = [];
    const byId = new Map(parts.map((p) => [p.id, p]));
    for (const p of parts) {
      const par = p.parent ? byId.get(p.parent) : undefined;
      if (!par || !p.node.visible) continue;
      const socket = p.home.clone().addScaledVector(offsets.get(par.id) ?? new THREE.Vector3(), current);
      const now = p.home.clone().addScaledVector(offsets.get(p.id) ?? new THREE.Vector3(), current);
      pos.push(socket.x, socket.y, socket.z, now.x, now.y, now.z);
      dots.push(socket.x, socket.y, socket.z);
    }
    guides.geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    sockets!.geometry.setAttribute('position', new THREE.Float32BufferAttribute(dots, 3));
    guides.visible = sockets!.visible = $<HTMLInputElement>('guides').checked && current > 0.01;
  }
}

function frame(views: Record<string, THREE.Vector3>) {
  // Fit both the closed and the fully exploded figure, so the camera does not need to move as it opens.
  const keep = current;
  const fit = (t: number) => {
    current = t;
    apply();
    const box = new THREE.Box3().setFromObject(model!);
    const radius = box.getSize(new THREE.Vector3()).length() / 2;
    return { centre: box.getCenter(new THREE.Vector3()), dist: (radius / Math.sin((camera.fov * Math.PI) / 360)) * 1.05 };
  };
  const closed = fit(0), open = fit(1);
  current = keep;
  apply();
  zoom = { closed: closed.dist, open: open.dist, centreClosed: closed.centre, centreOpen: open.centre, applied: 1 };
  controls.minDistance = closed.dist * 0.3;
  controls.maxDistance = open.dist * 2.5;
  for (const [k, d] of Object.entries(views)) views[k] = d.clone().normalize().multiplyScalar(closed.dist);
  return { views };
}

let viewPositions: Record<string, THREE.Vector3> = {};
/** How far the camera sits at rest and fully open, and the point it looks at in each state. */
let zoom = { closed: 1, open: 1, centreClosed: new THREE.Vector3(), centreOpen: new THREE.Vector3(), applied: 1 };
const VIEWS: Record<string, [string, THREE.Vector3]> = {
  front: ['Front', new THREE.Vector3(0, 0.1, 1)],
  side: ['Side', new THREE.Vector3(1, 0.1, 0)],
  back: ['Back', new THREE.Vector3(0, 0.1, -1)],
  three: ['Three-quarter', new THREE.Vector3(0.65, 0.3, 0.8)],
};
/** Move the camera back and the look-at point up as the figure opens, keeping the angle the viewer chose. */
function follow() {
  const t = Math.min(1, Math.max(0, current));
  const want = (zoom.closed + (zoom.open - zoom.closed) * t) / zoom.closed;
  const offset = camera.position.clone().sub(controls.target).multiplyScalar(want / zoom.applied);
  zoom.applied = want;
  controls.target.copy(zoom.centreClosed).lerp(zoom.centreOpen, t);
  camera.position.copy(controls.target).add(offset);
  controls.update();
}
const setView = (k: string) => {
  controls.target.copy(zoom.centreClosed);
  camera.position.copy(zoom.centreClosed).add(viewPositions[k]);
  zoom.applied = 1;
  follow();
};

async function load(id: string) {
  chassis = id;
  const c = getChassis(id);
  $('msg').style.display = 'grid';
  await ensureKitParts(lib, id);
  if (model) {
    stage.scene.remove(model);
    model = null;
  }
  if (guides) {
    stage.scene.remove(guides, sockets!);
    guides = sockets = null;
  }
  const sets = SETS[id] ?? {};
  const loadout = (setName && sets[setName]) || Object.values(sets)[0] || {};
  const m = buildWalkerModel(
    { name: id, chassis: id, driver: { command: 0, trait: null }, loadout } as WalkerInput,
    FACTION_COLOURS[c.faction ?? 'covenant'] ?? '#7a1c1c', lib, 'force',
  );
  stage.setBackdrop((c.faction ?? 'covenant') as Backdrop);
  stage.scene.add(m);
  stage.fit(m);
  model = m;
  parts = collect(m);
  const kitCount = parts.filter((p) => !p.item).length;
  const size = new THREE.Box3().setFromObject(m).getSize(new THREE.Vector3());
  offsets = explodeOffsets(parts, size.y * 0.14);
  // Lift the whole figure by whatever the legs would sink below the floor, so nothing goes through the plinth.
  const lift = Math.max(0, ...parts.map((p) => 0.5 - (p.floor + (offsets.get(p.id)?.y ?? 0))));
  for (const o of offsets.values()) o.y += lift;

  guides = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xe0b85a, depthTest: false, transparent: true, opacity: 0.9 }));
  sockets = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ color: 0xffe9a8, size: 6, sizeAttenuation: false, depthTest: false }));
  guides.renderOrder = sockets.renderOrder = 10;
  guides.frustumCulled = sockets.frustumCulled = false;
  stage.scene.add(guides, sockets);

  // The panel: one toggle per part.
  const list = $('parts');
  list.replaceChildren();
  for (const p of parts) {
    const row = document.createElement('label');
    row.className = 'row';
    const cb = Object.assign(document.createElement('input'), { type: 'checkbox', checked: true });
    cb.onchange = () => {
      p.node.visible = cb.checked;
      apply();
    };
    const name = document.createElement('span');
    name.textContent = p.label;
    row.append(cb, name);
    if (p.item) row.style.color = '#d98a5a';
    list.append(row);
  }
  $('title').textContent = `${c.name}`;
  $('sub').textContent = `${kitCount} body parts, ${parts.length - kitCount} equipment pieces`;
  const eq = $<HTMLInputElement>('equipment');
  eq.onchange = () => {
    parts.filter((p) => p.item).forEach((p, i) => {
      p.node.visible = eq.checked;
      (list.children[parts.indexOf(p)].querySelector('input') as HTMLInputElement).checked = eq.checked;
      void i;
    });
    apply();
  };
  eq.checked = true;

  const f = frame(Object.fromEntries(Object.entries(VIEWS).map(([k, [, d]]) => [k, d.clone()])));
  viewPositions = f.views;
  apply();
  setView('three');
  $('msg').style.display = 'none';
  history.replaceState(null, '', `?chassis=${id}${setName ? `&set=${setName}` : ''}${target ? '&explode=1' : ''}`);
  document.querySelectorAll<HTMLButtonElement>('#walkers button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.id === id)));
}

// Controls ------------------------------------------------------------------------------------------------------------

const btn = $<HTMLButtonElement>('explode-btn');
const slider = $<HTMLInputElement>('explode');
const sync = () => {
  const open = target > 0.5;
  btn.setAttribute('aria-pressed', String(open));
  btn.textContent = open ? 'Collapse' : 'Explode';
};
function setExplode(t: number, instant = false) {
  target = t;
  if (instant) current = t;
  slider.value = String(t);
  sync();
}
const toggleExplode = () => setExplode(target > 0.5 ? 0 : 1);
btn.onclick = toggleExplode;
// Dragging the slider takes over directly; the button then continues from there.
slider.oninput = () => setExplode(+slider.value, true);
$<HTMLInputElement>('guides').onchange = apply;
$<HTMLInputElement>('turntable').onchange = (e) => (controls.autoRotate = (e.target as HTMLInputElement).checked);
controls.autoRotate = true;

for (const w of WALKERS) {
  const b = document.createElement('button');
  b.textContent = getChassis(w).name;
  b.dataset.id = w;
  b.onclick = () => load(w);
  $('walkers').append(b);
}
for (const [k, [label]] of Object.entries(VIEWS)) {
  const b = document.createElement('button');
  b.textContent = label;
  b.onclick = () => setView(k);
  $('views').append(b);
}
addEventListener('keydown', (e) => {
  if (e.key.toLowerCase() === 'e' && !(e.target instanceof HTMLInputElement && e.target.type === 'text')) toggleExplode();
});

(window as unknown as { viewer: unknown }).viewer = { setExplode, toggleExplode, load, get current() { return current; }, get parts() { return parts.map((p) => ({ id: p.id, parent: p.parent, label: p.label })); } };

await load(chassis);
if (q.get('explode')) setExplode(1, true);
apply();

let last = performance.now();
renderer.setAnimationLoop((now) => {
  const dt = Math.min((now - last) / 1000, 0.1);
  last = now;
  if (Math.abs(current - target) > 1e-3) {
    // Ease toward the target; the whole move takes about half a second.
    current += (target - current) * Math.min(1, dt * 8);
    if (Math.abs(current - target) < 1e-3) current = target;
    apply();
  }
  follow();
  stage.render(camera);
});
document.body.dataset.ready = '1';
