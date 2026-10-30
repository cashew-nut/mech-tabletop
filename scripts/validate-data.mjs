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
const { companies } = load('companies.json');
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

// Companies
const companiesById = indexById(companies, 'companies.json');
for (const co of companies) {
  for (const itemId of Object.keys(co.pointModifiers ?? {})) {
    if (!equipmentById.has(itemId)) fail(`company "${co.id}"`, `pointModifiers names unknown item "${itemId}"`);
  }
}

// Scenarios
indexById(scenarioFile.scenarios, 'scenarios.json');
const { width, height } = scenarioFile.map;
for (const s of scenarioFile.scenarios) {
  for (const o of s.objectives) {
    if (o.q < 0 || o.q >= width || o.r < 0 || o.r >= height) {
      fail(`scenario "${s.id}"`, `objective (${o.q}, ${o.r}) is off the ${width}x${height} map`);
    }
  }
}

// Lances
function walkerCost(walker, company, where) {
  const c = chassisById.get(walker.chassis);
  if (!c) {
    fail(where, `unknown chassis "${walker.chassis}"`);
    return 0;
  }
  let total = c.points;

  const cmd = walker.driver?.command ?? 0;
  if (!commandCost.has(cmd)) fail(where, `invalid driver command ${cmd}`);
  else total += commandCost.get(cmd);
  const trait = walker.driver?.trait;
  if (trait) {
    if (!traitsById.has(trait)) fail(where, `unknown trait "${trait}"`);
    else total += traitsById.get(trait).points;
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
      used += e.slots;
      counts.set(id, (counts.get(id) ?? 0) + 1);
      total += Math.max(1, e.points + (company?.pointModifiers?.[id] ?? 0));
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
    const company = companiesById.get(lance.company);
    if (!company) fail(where, `unknown company "${lance.company}"`);
    const n = lance.walkers.length;
    if (n < minWalkers || n > maxWalkers) fail(where, `has ${n} war-walkers, needs ${minWalkers}-${maxWalkers}`);
    const costs = lance.walkers.map((w) => walkerCost(w, company, `${where} / ${w.name}`));
    const total = costs.reduce((a, b) => a + b, 0);
    if (total > budget) fail(where, `costs ${total} points, budget is ${budget}`);
    summary.push(`  ${lance.name}: ${total}/${budget} pts [${costs.join(', ')}]`);
  }
}

console.log(`chassis: ${chassis.length}, equipment: ${equipment.length}, traits: ${drivers.traits.length}, companies: ${companies.length}, scenarios: ${scenarioFile.scenarios.length}`);
console.log('lances:');
console.log(summary.join('\n'));

if (errors.length) {
  console.error(`\n${errors.length} problem(s):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log('\nAll data valid.');
