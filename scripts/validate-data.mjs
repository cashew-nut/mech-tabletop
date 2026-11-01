// Validates the game data in data/ and checks that every example lance is legal.
// Run with: npm run validate
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const dataDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'data');
const load = (path) => JSON.parse(readFileSync(join(dataDir, path), 'utf8'));

const errors = [];
const fail = (where, msg) => errors.push(`${where}: ${msg}`);

const LOCATIONS = ['armLeft', 'armRight', 'core', 'legs'];
const MOUNT_OF = { armLeft: 'arm', armRight: 'arm', core: 'core', legs: 'legs' };
const CATEGORIES = ['weapon', 'defence', 'mobility', 'system'];
const RANGES = ['melee', 'short', 'medium', 'long'];

const { chassis } = load('chassis.json');
const { equipment } = load('equipment.json');
const drivers = load('drivers.json');
const { factions } = load('factions.json');
const scenarioFile = load('scenarios.json');

function indexById(list, where) {
  const map = new Map();
  for (const item of list) {
    if (!item.id) fail(where, `entry without id: ${JSON.stringify(item).slice(0, 60)}`);
    else if (map.has(item.id)) fail(where, `duplicate id "${item.id}"`);
    else map.set(item.id, item);
  }
  return map;
}

const isPosInt = (n) => Number.isInteger(n) && n > 0;
const isNonNegInt = (n) => Number.isInteger(n) && n >= 0;

// Chassis
const chassisById = indexById(chassis, 'chassis.json');
for (const c of chassis) {
  const w = `chassis "${c.id}"`;
  for (const key of ['size', 'points', 'stride', 'boiler']) {
    if (!isPosInt(c[key])) fail(w, `${key} must be a positive integer`);
  }
  for (const loc of LOCATIONS) {
    if (!isNonNegInt(c.slots?.[loc])) fail(w, `slots.${loc} must be a non-negative integer`);
  }
  for (const key of ['coreFront', 'coreRear', 'arm', 'legs']) {
    if (!isPosInt(c.armour?.[key])) fail(w, `armour.${key} must be a positive integer`);
  }
  for (const key of ['core', 'other']) {
    if (!isPosInt(c.structure?.[key])) fail(w, `structure.${key} must be a positive integer`);
  }
}

// Equipment
const equipmentById = indexById(equipment, 'equipment.json');
for (const e of equipment) {
  const w = `equipment "${e.id}"`;
  if (!e.name) fail(w, 'missing name');
  if (!CATEGORIES.includes(e.category)) fail(w, `unknown category "${e.category}"`);
  if (!Array.isArray(e.mount) || e.mount.length === 0) fail(w, 'mount must be a non-empty list');
  else for (const m of e.mount) {
    if (!['arm', 'core', 'legs', 'any'].includes(m)) fail(w, `unknown mount "${m}"`);
  }
  if (!isPosInt(e.slots)) fail(w, 'slots must be a positive integer');
  if (!isNonNegInt(e.pressure)) fail(w, 'pressure must be a non-negative integer');
  if (!isPosInt(e.points)) fail(w, 'points must be a positive integer');
  if (e.category === 'weapon') {
    const wp = e.weapon;
    if (!wp) fail(w, 'weapons need a weapon block');
    else {
      if (!isPosInt(wp.dice)) fail(w, 'weapon.dice must be a positive integer');
      if (!isNonNegInt(wp.damage)) fail(w, 'weapon.damage must be a non-negative integer');
      if (!RANGES.includes(wp.range)) fail(w, `unknown weapon.range "${wp.range}"`);
    }
  }
}

// Drivers
const commandCost = new Map(drivers.command.map((c) => [c.value, c.points]));
const traitsById = indexById(drivers.traits, 'drivers.json');

// Factions
const factionsById = indexById(factions, 'factions.json');
for (const f of factions) {
  for (const itemId of Object.keys(f.pointModifiers ?? {})) {
    if (!equipmentById.has(itemId)) fail(`faction "${f.id}"`, `pointModifiers names unknown item "${itemId}"`);
  }
  if (f.traitModifier !== undefined && !Number.isInteger(f.traitModifier)) fail(`faction "${f.id}"`, 'traitModifier must be an integer');
}
// The model kit (data/model-kit.json) must cover every faction, frame and slot.
const modelKit = load('model-kit.json');
const JOINTS = ['root', 'pelvis', 'spine', 'chest', 'neck', 'head', 'shoulder', 'elbow', 'wrist', 'hip', 'knee', 'ankle'];
for (const comp of modelKit.components) {
  if (!JOINTS.includes(comp.joint)) fail(`model-kit component "${comp.id}"`, `unknown joint "${comp.joint}"`);
  if (/[_@]/.test(comp.id)) fail(`model-kit component "${comp.id}"`, 'ids cannot contain _ or @ (they are part of kit part names)');
}
for (const c of chassis) {
  if (!factionsById.has(c.faction)) fail(`chassis "${c.id}"`, `unknown faction "${c.faction}"`);
  if (!c.frame) fail(`chassis "${c.id}"`, 'missing frame (the 3D model skeleton it uses)');
  else if (!modelKit.frames[c.frame]) fail(`chassis "${c.id}"`, `frame "${c.frame}" is not in model-kit.json`);
  if (!modelKit.factions[c.faction]) fail(`chassis "${c.id}"`, `faction "${c.faction}" has no proportions in model-kit.json`);
  for (const loc of LOCATIONS) {
    if ((c.slots[loc] ?? 0) > (modelKit.spareMounts[loc] ?? 0)) fail(`chassis "${c.id}"`, `${c.slots[loc]} ${loc} slots but the frames only have ${modelKit.spareMounts[loc]} mounts`);
  }
}
for (const e of equipment) {
  if (e.faction !== undefined && !factionsById.has(e.faction)) fail(`equipment "${e.id}"`, `unknown faction "${e.faction}"`);
}

// Scenarios
indexById(scenarioFile.scenarios, 'scenarios.json');
const { width, height } = scenarioFile.map;
for (const s of scenarioFile.scenarios) {
  for (const o of s.objectives) {
    if (o.col < 0 || o.col >= width || o.row < 0 || o.row >= height) {
      fail(`scenario "${s.id}"`, `objective (${o.col}, ${o.row}) is off the ${width}x${height} map`);
    }
  }
}

// Maps
const TERRAIN = ['open', 'rough', 'light', 'heavy', 'blocking'];
const { maps } = load('maps.json');
indexById(maps, 'maps.json');
for (const m of maps) {
  for (const h of m.hexes) {
    const w = `map "${m.id}"`;
    if (h.col < 0 || h.col >= m.width || h.row < 0 || h.row >= m.height) fail(w, `hex (${h.col}, ${h.row}) is off the map`);
    if (h.terrain && !TERRAIN.includes(h.terrain)) fail(w, `unknown terrain "${h.terrain}"`);
    if (h.elevation !== undefined && ![0, 1, 2].includes(h.elevation)) fail(w, `elevation must be 0, 1 or 2`);
  }
  // Every scenario must be playable on every map.
  const blocked = new Set(m.hexes.filter((h) => h.terrain === 'blocking').map((h) => `${h.col},${h.row}`));
  for (const s of scenarioFile.scenarios) {
    for (const o of [...s.objectives, ...(s.surveyor ? [s.surveyor] : [])]) {
      if (blocked.has(`${o.col},${o.row}`)) fail(`map "${m.id}"`, `scenario "${s.id}" puts a token on blocking terrain at (${o.col}, ${o.row})`);
    }
  }
}

// Lances
function walkerCost(walker, faction, where) {
  const c = chassisById.get(walker.chassis);
  if (!c) {
    fail(where, `unknown chassis "${walker.chassis}"`);
    return 0;
  }
  if (faction && c.faction !== faction.id) fail(where, `${c.name} is a ${c.faction} class, not ${faction.id}`);
  let total = c.points;

  const cmd = walker.driver?.command ?? 0;
  if (!commandCost.has(cmd)) fail(where, `invalid driver command ${cmd}`);
  else total += commandCost.get(cmd);
  const trait = walker.driver?.trait;
  if (trait) {
    if (!traitsById.has(trait)) fail(where, `unknown trait "${trait}"`);
    else total += Math.max(1, traitsById.get(trait).points + (faction?.traitModifier ?? 0));
  }

  const counts = new Map();
  for (const [loc, items] of Object.entries(walker.loadout ?? {})) {
    if (!LOCATIONS.includes(loc)) {
      fail(where, `unknown location "${loc}"`);
      continue;
    }
    let used = 0;
    for (const id of items) {
      const e = equipmentById.get(id);
      if (!e) {
        fail(where, `unknown item "${id}"`);
        continue;
      }
      if (!e.mount.includes('any') && !e.mount.includes(MOUNT_OF[loc])) {
        fail(where, `${e.name} cannot be mounted in ${loc}`);
      }
      if (faction && e.faction && e.faction !== faction.id) fail(where, `${e.name} is ${e.faction} gear, not ${faction.id}`);
      used += e.slots;
      counts.set(id, (counts.get(id) ?? 0) + 1);
      total += Math.max(1, e.points + (faction?.pointModifiers?.[id] ?? 0));
    }
    if (used > c.slots[loc]) fail(where, `${loc} uses ${used} slots but ${c.name} has ${c.slots[loc]}`);
  }
  for (const [id, n] of counts) {
    const max = equipmentById.get(id).maxPerWalker;
    if (max && n > max) fail(where, `${equipmentById.get(id).name} fitted ${n} times, max ${max}`);
  }
  return total;
}

const { budget, minWalkers, maxWalkers } = scenarioFile.lance;
const lanceDir = join(dataDir, 'lances');
const summary = [];
for (const file of readdirSync(lanceDir).filter((f) => f.endsWith('.json'))) {
  for (const lance of load(join('lances', file)).lances) {
    const where = `lance "${lance.name}"`;
    const faction = factionsById.get(lance.faction);
    if (!faction) fail(where, `unknown faction "${lance.faction}"`);
    const n = lance.walkers.length;
    if (n < minWalkers || n > maxWalkers) fail(where, `has ${n} war-walkers, needs ${minWalkers}-${maxWalkers}`);
    const costs = lance.walkers.map((w) => walkerCost(w, faction, `${where} / ${w.name}`));
    const total = costs.reduce((a, b) => a + b, 0);
    if (total > budget) fail(where, `costs ${total} points, budget is ${budget}`);
    summary.push(`  ${lance.name}: ${total}/${budget} pts [${costs.join(', ')}]`);
  }
}

console.log(`chassis: ${chassis.length}, equipment: ${equipment.length}, traits: ${drivers.traits.length}, factions: ${factions.length}, scenarios: ${scenarioFile.scenarios.length}, maps: ${maps.length}`);
console.log('lances:');
console.log(summary.join('\n'));

// Equipment fit in model-kit.json: every item's hardpoints exist and every mount kind has a preference.
{
  const kit = load('model-kit.json');
  const bounds = load('item-bounds.json').items;
  const fit = kit.fit;
  if (!fit) fail('model-kit.json', 'missing "fit"');
  else {
    for (const cls of Object.keys(fit.classes)) {
      if (!chassisById.has(cls)) fail('model-kit.json fit.classes', `unknown class "${cls}"`);
      if (!fit.overrides?.[cls]) fail('model-kit.json fit.overrides', `no section for "${cls}"`);
    }
    for (const [cls, hps] of Object.entries(fit.overrides ?? {})) {
      for (const hp of Object.keys(hps)) if (!fit.hardpoints[hp]) fail(`model-kit.json fit.overrides.${cls}`, `unknown hardpoint "${hp}"`);
    }
    const kindOf = { arm: 'arm', core: 'core', legs: 'legs' };
    for (const e of equipment) {
      const item = fit.items[e.id];
      if (!item) { fail('model-kit.json fit.items', `no fit for "${e.id}"`); continue; }
      for (const m of e.mount.includes('any') ? ['arm', 'core', 'legs'] : e.mount) {
        if (!item[kindOf[m]]?.length) fail(`model-kit.json fit.items.${e.id}`, `no hardpoints for ${m}`);
      }
      for (const k of ['arm', 'core', 'legs']) for (const hp of item[k] ?? []) if (!fit.hardpoints[hp]) fail(`model-kit.json fit.items.${e.id}`, `unknown hardpoint "${hp}"`);
    }
    for (const id of fit.nativeRight) if (!bounds[id]) fail('model-kit.json fit.nativeRight', `no part "${id}" in item-bounds.json (run node scripts/item-bounds.mjs)`);
  }
}

if (errors.length) {
  console.error(`\n${errors.length} problem(s):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log('\nAll data valid.');
