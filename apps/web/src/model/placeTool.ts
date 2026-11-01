// Sliders for placing equipment: apps/web/place.html (run `npm run place`).
// Pick a class and a loadout, pick one of the placed items, and nudge it with the sliders. The walker is rebuilt on every
// move from the live placement table (fit.placements in data/model-kit.json), so what you see is what the game will draw.
// "Copy" gives the table as JSON; `node scripts/merge-placements.mjs <file>` writes it back into model-kit.json.
// Unsaved work is kept in this browser (localStorage) so a reload does not lose it.
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { getChassis, type WalkerInput } from '@brass-charter/rules';
import equipmentData from '../../../../data/equipment.json';
import fitSets from '../../../../scripts/fit-sets.json';
import { FACTION_COLOURS, buildWalkerModel, ensureKitParts, loadPartLibrary } from './assemble';
import { FIT, IDENTITY_NUDGE, compactPlacements, hardpoint, nudgeOf, type Nudge } from './fit';
import { createStage, type Backdrop } from './stage';

type Loadout = WalkerInput['loadout'];
const LOCS = ['armLeft', 'armRight', 'core', 'legs'] as const;
const EQUIPMENT_IDS = new Set(equipmentData.equipment.map((e) => e.id));
const CLASSES = Object.keys(FIT.classes);
const SETS = fitSets as unknown as Record<string, Record<string, Loadout>>;
const DRAFT_KEY = 'brass-charter-placements-draft';

type Table = Record<string, Record<string, Record<string, Nudge>>>;
const table = (FIT.placements ??= {}) as Table;
const committed = JSON.stringify(table);

// A draft from an earlier session replaces the committed table, with a banner so it is not mistaken for the real thing.
let draftLoaded = false;
try {
  const draft = localStorage.getItem(DRAFT_KEY);
  if (draft && draft !== committed) {
    const parsed = JSON.parse(draft) as Table;
    for (const k of Object.keys(table)) if (!k.startsWith('$')) delete table[k];
    Object.assign(table, parsed);
    draftLoaded = true;
  }
} catch {
  /* no storage, or a broken draft: start from the committed table */
}

const q = new URLSearchParams(location.search);
let chassis = CLASSES.includes(q.get('chassis') ?? '') ? q.get('chassis')! : CLASSES[0];
let loadout: Loadout = SETS[chassis] ? { ...Object.values(SETS[chassis])[0] } : {};
if (q.get('set') && SETS[chassis]?.[q.get('set')!]) loadout = { ...SETS[chassis][q.get('set')!] };
if (q.get('lo')) loadout = JSON.parse(q.get('lo')!);
let selected: { item: string; hp: string } | null = null;
let scope: 'item' | 'hp' = 'item';

// --- scene -----------------------------------------------------------------

const view = document.getElementById('view')!;
const panel = document.getElementById('panel')!;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
view.appendChild(renderer.domElement);
const stage = createStage(renderer, 'covenant');
const camera = new THREE.PerspectiveCamera(30, 1, 1, 4000);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
const lib = await loadPartLibrary(renderer);

/** Set whenever the picture needs drawing again. */
let dirty = true;
let model: THREE.Object3D | null = null;
const marks = new THREE.Group();
stage.scene.add(marks);
let boxes: THREE.BoxHelper[] = [];

const resize = () => {
  const w = view.clientWidth;
  const h = view.clientHeight;
  renderer.setSize(w, h);
  stage.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  dirty = true;
};
new ResizeObserver(resize).observe(view);
resize();

/** Put the camera in front of the model, turned `angle` degrees, or leave it where it is. */
function frame(angle?: number, focus?: THREE.Object3D) {
  if (!model) return;
  const box = new THREE.Box3().setFromObject(focus ?? model);
  const centre = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  const dist = size * (focus ? 2.4 : 1.55);
  if (angle !== undefined || focus) {
    const rad = ((angle ?? Math.atan2(camera.position.x - controls.target.x, camera.position.z - controls.target.z) * (180 / Math.PI)) * Math.PI) / 180;
    camera.position.set(centre.x + Math.sin(rad) * dist, centre.y + dist * 0.3, centre.z + Math.cos(rad) * dist);
  }
  controls.target.copy(centre);
  dirty = true;
}

// --- building ----------------------------------------------------------------

const walker = (): WalkerInput =>
  ({ name: 'preview', chassis, driver: { command: 0, trait: null }, loadout: Object.fromEntries(LOCS.map((l) => [l, (loadout[l] ?? []).filter((id) => EQUIPMENT_IDS.has(id))])) }) as WalkerInput;

interface Placed {
  item: string;
  hp: string;
  parts: THREE.Object3D[];
}
let placed: Placed[] = [];
let first = true;

function rebuild() {
  if (model) stage.scene.remove(model);
  const c = getChassis(chassis);
  model = buildWalkerModel(walker(), FACTION_COLOURS[c.faction ?? ''] ?? '#7a2e22', lib);
  stage.scene.add(model);
  stage.fit(model);
  model.updateMatrixWorld(true);

  placed = [];
  model.traverse((o) => {
    const f = o.userData.fit as { item: string; hp: string } | undefined;
    if (!f) return;
    const hit = placed.find((p) => p.item === f.item && p.hp === f.hp);
    if (hit) hit.parts.push(o);
    else placed.push({ item: f.item, hp: f.hp, parts: [o] });
  });
  if (!selected || !placed.some((p) => p.item === selected!.item && p.hp === selected!.hp)) selected = placed[0] ? { item: placed[0].item, hp: placed[0].hp } : null;

  // Outline the chosen item and show the hardpoint's axes (red outward, green up, blue forward).
  marks.clear();
  boxes = [];
  const sel = placed.find((p) => p.item === selected?.item && p.hp === selected?.hp);
  const height = (model.getObjectByProperty('name', 'joint_head') ?? model).getWorldPosition(new THREE.Vector3()).y;
  for (const part of sel?.parts ?? []) {
    const box = new THREE.BoxHelper(part, 0xffd34a);
    marks.add(box);
    boxes.push(box);
    const anchor = part.parent?.parent?.parent;
    if (anchor) {
      const axes = new THREE.AxesHelper(height * 0.07);
      (axes.material as THREE.Material).depthTest = false;
      axes.renderOrder = 10;
      // On the right the hardpoint is the mirror image of the left, so out still points away from the body.
      if (part.userData.fit?.side === 'R' && !hardpoint(chassis, part.userData.fit.hp)?.mount) axes.scale.x = -1;
      anchor.add(axes);
    }
  }
  dirty = true;
  if (first) {
    frame(35);
    first = false;
  }
}

let pending = false;
const schedule = () => {
  if (pending) return;
  pending = true;
  requestAnimationFrame(() => {
    pending = false;
    rebuild();
    syncPanel(false);
  });
};

// --- table -------------------------------------------------------------------

const rowKey = () => (scope === 'item' ? selected!.item : '*');
const current = (): Required<Nudge> => {
  if (!selected) return IDENTITY_NUDGE;
  if (scope === 'item') return nudgeOf(chassis, selected.hp, selected.item) ?? IDENTITY_NUDGE;
  const wildcard = table[chassis]?.[selected.hp]?.['*'];
  return { ...IDENTITY_NUDGE, ...(wildcard ?? {}) };
};

function exportJson() {
  const out: Table = {};
  for (const cls of CLASSES) out[cls] = compactPlacements(table[cls] ?? {});
  // Short arrays on one line.
  return JSON.stringify(out, null, 2).replace(/\[\s+(-?[\d.e-]+(?:,\s+-?[\d.e-]+)*)\s+\]/g, (_, inner: string) => `[${inner.replace(/\s+/g, ' ')}]`) + '\n';
}

function persist() {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(table));
  } catch {
    /* storage off */
  }
}

function write(vals: Required<Nudge>) {
  if (!selected) return;
  const rows = ((table[chassis] ??= {})[selected.hp] ??= {});
  rows[rowKey()] = { offset: [...vals.offset], rot: [...vals.rot], scale: vals.scale };
  persist();
  schedule();
}

function removeRow() {
  if (!selected) return;
  delete table[chassis]?.[selected.hp]?.[rowKey()];
  persist();
  schedule();
}

// --- panel -------------------------------------------------------------------

const FIELDS: Array<{ key: 'offset' | 'rot' | 'scale'; i: number; label: string; min: number; max: number; step: number }> = [
  { key: 'offset', i: 0, label: 'Out', min: -0.2, max: 0.2, step: 0.001 },
  { key: 'offset', i: 1, label: 'Up', min: -0.2, max: 0.2, step: 0.001 },
  { key: 'offset', i: 2, label: 'Forward', min: -0.2, max: 0.2, step: 0.001 },
  { key: 'rot', i: 0, label: 'Pitch', min: -180, max: 180, step: 1 },
  { key: 'rot', i: 1, label: 'Turn', min: -180, max: 180, step: 1 },
  { key: 'rot', i: 2, label: 'Roll', min: -180, max: 180, step: 1 },
  { key: 'scale', i: 0, label: 'Scale', min: 0.2, max: 3, step: 0.01 },
];

const html = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

function buildPanel() {
  const sets = Object.keys(SETS[chassis] ?? {});
  panel.innerHTML = `
    ${draftLoaded ? `<div class="banner">Showing unsaved work from this browser, not the committed table. <button id="discard">Discard it</button></div>` : ''}
    <h1>Place equipment</h1>
    <div class="row"><span class="k">Class</span><select id="chassis">${CLASSES.map((c) => `<option ${c === chassis ? 'selected' : ''}>${c}</option>`).join('')}</select>
      <span class="k">Preset</span><select id="preset"><option value="">custom</option>${sets.map((s) => `<option>${s}</option>`).join('')}</select></div>
    <h2>Loadout</h2>
    <div class="loadout">${LOCS.map((l) => `<div class="row"><span class="k">${l}</span><input type="text" data-loc="${l}" list="equipment" value="${html((loadout[l] ?? []).join(', '))}"></div>`).join('')}</div>
    <datalist id="equipment">${[...EQUIPMENT_IDS].map((id) => `<option value="${id}">`).join('')}</datalist>
    <h2>Placed items</h2>
    <div id="items"></div>
    <h2>Nudge</h2>
    <div class="row"><label><input type="radio" name="scope" value="item" ${scope === 'item' ? 'checked' : ''}> this item here</label>
      <label><input type="radio" name="scope" value="hp" ${scope === 'hp' ? 'checked' : ''}> every item at this hardpoint</label></div>
    <div id="sliders">${FIELDS.map((f, n) => `<div class="row"><span class="k">${f.label}</span><input type="range" data-n="${n}" min="${f.min}" max="${f.max}" step="${f.step}"><input type="number" data-n="${n}" min="${f.min}" max="${f.max}" step="${f.step}"></div>`).join('')}</div>
    <p class="hint">Out, up and forward are fractions of body height, along the hardpoint's axes (the coloured arrows: red out, green up, blue forward). Turn and scale pivot on the point where the item touches the hardpoint. The right side mirrors the left.</p>
    <div class="buttons"><button id="reset-row">Reset this row</button><button id="reset-class">Reset ${chassis}</button><button id="focus">Zoom to item</button></div>
    <div class="buttons">${[['Front', 0], ['Side', 90], ['Back', 180], ['Three-quarter', 35]].map(([n, a]) => `<button data-angle="${a}">${n}</button>`).join('')}</div>
    <h2>Table</h2>
    <div class="buttons"><button id="copy">Copy JSON</button><button id="download">Download</button></div>
    <textarea id="json" readonly></textarea>
    <p class="hint">Save the JSON as placements.json and run <code>node scripts/merge-placements.mjs placements.json</code>, then <code>npm run validate</code>.</p>`;

  const $ = <T extends HTMLElement>(sel: string) => panel.querySelector<T>(sel)!;
  $<HTMLSelectElement>('#chassis').onchange = (e) => {
    chassis = (e.target as HTMLSelectElement).value;
    loadout = SETS[chassis] ? { ...Object.values(SETS[chassis])[0] } : {};
    selected = null;
    first = true;
    void load();
  };
  $<HTMLSelectElement>('#preset').onchange = (e) => {
    const name = (e.target as HTMLSelectElement).value;
    if (!name) return;
    loadout = { ...SETS[chassis][name] };
    selected = null;
    buildPanel();
    schedule();
  };
  panel.querySelectorAll<HTMLInputElement>('input[data-loc]').forEach((input) => {
    input.onchange = () => {
      loadout = { ...loadout, [input.dataset.loc!]: input.value.split(/[\s,]+/).filter(Boolean) };
      schedule();
    };
  });
  panel.querySelectorAll<HTMLInputElement>('input[name=scope]').forEach((r) => {
    r.onchange = () => {
      scope = r.value as 'item' | 'hp';
      syncPanel(false);
    };
  });
  panel.querySelectorAll<HTMLInputElement>('#sliders input').forEach((input) => {
    input.oninput = () => {
      if (input.value === '' || !Number.isFinite(Number(input.value))) return;
      const f = FIELDS[Number(input.dataset.n)];
      const vals = { offset: [...current().offset], rot: [...current().rot], scale: current().scale } as Required<Nudge>;
      if (f.key === 'scale') vals.scale = Number(input.value);
      else (vals[f.key] as number[])[f.i] = Number(input.value);
      write(vals);
      // Keep the twin control (slider or number box) in step straight away.
      panel.querySelectorAll<HTMLInputElement>(`#sliders input[data-n="${input.dataset.n}"]`).forEach((twin) => (twin.value = input.value));
    };
  });
  $('#reset-row').onclick = removeRow;
  $('#reset-class').onclick = () => {
    if (!confirm(`Clear every adjustment for ${chassis}?`)) return;
    delete table[chassis];
    persist();
    schedule();
  };
  $('#focus').onclick = () => {
    const p = placed.find((x) => x.item === selected?.item && x.hp === selected?.hp);
    if (p) frame(undefined, p.parts[0]);
  };
  panel.querySelectorAll<HTMLButtonElement>('button[data-angle]').forEach((b) => (b.onclick = () => frame(Number(b.dataset.angle))));
  $('#copy').onclick = async () => {
    const text = exportJson();
    try {
      await navigator.clipboard.writeText(text);
      $('#copy').textContent = 'Copied';
    } catch {
      $<HTMLTextAreaElement>('#json').select();
      $('#copy').textContent = 'Select and copy below';
    }
    setTimeout(() => ($('#copy').textContent = 'Copy JSON'), 2000);
  };
  $('#download').onclick = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([exportJson()], { type: 'application/json' }));
    a.download = 'placements.json';
    a.click();
  };
  const discard = panel.querySelector<HTMLButtonElement>('#discard');
  if (discard)
    discard.onclick = () => {
      localStorage.removeItem(DRAFT_KEY);
      location.reload();
    };
  syncPanel(true);
}

/** Refresh the item list, slider positions and JSON after anything changed. */
function syncPanel(rebuildList: boolean) {
  const items = panel.querySelector<HTMLElement>('#items')!;
  if (rebuildList || items.dataset.sig !== placed.map((p) => `${p.item}|${p.hp}`).join(',')) {
    items.dataset.sig = placed.map((p) => `${p.item}|${p.hp}`).join(',');
    items.innerHTML = placed.length
      ? placed
          .map((p) => {
            const row = table[chassis]?.[p.hp];
            const edited = row && (row[p.item] || row['*']);
            return `<label><input type="radio" name="item" value="${p.item}|${p.hp}" ${p.item === selected?.item && p.hp === selected?.hp ? 'checked' : ''}>${p.item} <span class="hint">at ${p.hp}${p.parts.length > 1 ? ' (both sides)' : ''}${edited ? ' · edited' : ''}</span></label>`;
          })
          .join('')
      : '<p class="hint">Nothing placed. Add equipment ids to the loadout (this tool only places items on the three built classes).</p>';
    items.querySelectorAll<HTMLInputElement>('input').forEach((r) => {
      r.onchange = () => {
        const [item, hp] = r.value.split('|');
        selected = { item, hp };
        schedule();
      };
    });
  }
  const cur = current();
  panel.querySelectorAll<HTMLInputElement>('#sliders input').forEach((input) => {
    const f = FIELDS[Number(input.dataset.n)];
    const v = f.key === 'scale' ? cur.scale : cur[f.key][f.i];
    // Do not fight the control being dragged.
    if (document.activeElement !== input) input.value = String(f.step < 0.01 ? +v.toFixed(3) : +v.toFixed(2));
  });
  panel.querySelector<HTMLTextAreaElement>('#json')!.value = exportJson();
}

async function load() {
  await ensureKitParts(lib, chassis);
  const c = getChassis(chassis);
  stage.setBackdrop((c.faction as Backdrop) ?? 'covenant');
  buildPanel();
  rebuild();
  syncPanel(true);
  document.body.dataset.ready = '1';
}

// Draw only when something moved: it keeps an old laptop cool and lets the sliders stay responsive.
controls.addEventListener('change', () => (dirty = true));
const loop = () => {
  requestAnimationFrame(loop);
  const moved = controls.update();
  if (!dirty && !moved) return;
  dirty = false;
  for (const b of boxes) b.update();
  stage.render(camera);
};
loop();
await load();

// For scripted checks: where the chosen item sits in the world now.
(window as unknown as Record<string, unknown>).__place = {
  selectedBox: () => {
    const p = placed.find((x) => x.item === selected?.item && x.hp === selected?.hp);
    const b = new THREE.Box3();
    for (const part of p?.parts ?? []) b.expandByObject(part);
    return { item: selected?.item, hp: selected?.hp, min: b.min.toArray(), max: b.max.toArray() };
  },
  centres: () => (placed.find((x) => x.item === selected?.item && x.hp === selected?.hp)?.parts ?? []).map((part) => new THREE.Box3().setFromObject(part).getCenter(new THREE.Vector3()).toArray()),
};
