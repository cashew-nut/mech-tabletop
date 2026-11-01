// Merges placements copied from the sliders tool (apps/web/place.html) into data/model-kit.json.
//   node scripts/merge-placements.mjs placements.json     (or pipe it in: pbpaste | node scripts/merge-placements.mjs -)
// The file looks like { "paladin": { "grip": { "lance": { "offset": [0, 0.01, 0], "rot": [0, 0, 0], "scale": 1 } } } }.
// A class in the file replaces that class's whole table, so the tool's copy always carries everything it knows about.
// Rows with no adjustment are dropped. Run `npm run validate` afterwards.
import { readFileSync, writeFileSync } from 'node:fs';

const file = process.argv[2];
if (!file) {
  console.error('usage: node scripts/merge-placements.mjs <placements.json | ->');
  process.exit(2);
}
const incoming = JSON.parse(readFileSync(file === '-' ? 0 : file, 'utf8'));
const path = new URL('../data/model-kit.json', import.meta.url);
const raw = readFileSync(path, 'utf8');
const kit = JSON.parse(raw);
kit.fit.placements ??= {};

const isZero = (v) => !v || v.every((n) => n === 0);
const quiet = (n) => !n || ((n.scale ?? 1) === 1 && isZero(n.offset) && isZero(n.rot));
for (const [cls, rows] of Object.entries(incoming)) {
  if (cls.startsWith('$')) continue;
  if (!kit.fit.classes[cls]) throw new Error(`"${cls}" is not a class with a fit (${Object.keys(kit.fit.classes).join(', ')})`);
  const table = {};
  for (const [hp, items] of Object.entries(rows)) {
    if (!kit.fit.hardpoints[hp]) throw new Error(`${cls}: unknown hardpoint "${hp}"`);
    // An item's row that undoes the hardpoint-wide "*" row has to stay, or the "*" row would apply to it again.
    const overridesWildcard = !quiet(items['*']);
    const kept = Object.fromEntries(Object.entries(items).filter(([item, n]) => !quiet(n) || (item !== '*' && overridesWildcard)));
    if (Object.keys(kept).length) table[hp] = kept;
  }
  kit.fit.placements[cls] = table;
  console.log(`${cls}: ${Object.values(table).reduce((n, items) => n + Object.keys(items).length, 0)} row(s)`);
}

// Replace only the "placements" block of the file, so the rest keeps its formatting (1.0 stays 1.0) and the diff stays small.
const key = raw.indexOf('"placements":');
if (key < 0) throw new Error('data/model-kit.json has no "placements" block to replace');
const open = raw.indexOf('{', key);
let depth = 0;
let end = open;
for (let i = open, inString = false; i < raw.length; i++) {
  const ch = raw[i];
  if (inString) {
    if (ch === '\\') i++;
    else if (ch === '"') inString = false;
  } else if (ch === '"') inString = true;
  else if (ch === '{') depth++;
  else if (ch === '}' && --depth === 0) {
    end = i + 1;
    break;
  }
}
const block = JSON.stringify(kit.fit.placements, null, 2).replace(/\n/g, '\n    ');
writeFileSync(path, raw.slice(0, open) + block + raw.slice(end));
