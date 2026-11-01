// One-off seeding tool: splits every class in data/chassis.json into six body part cards and writes
//   data/parts.json   the part cards for all nine classes
//   data/cards.json   the printable card records for the Paladin milestone
// Run with: node scripts/seed-parts.mjs
//
// This is how the first split was made, not part of the build. Once the numbers are tuned by hand, do not run
// it again (it overwrites them). packages/rules/test/parts.test.ts keeps the parts and chassis.json in step.
import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const dataDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'data');
const load = (f) => JSON.parse(readFileSync(join(dataDir, f), 'utf8'));
const { chassis } = load('chassis.json');
const { equipment } = load('equipment.json');

/** The six body slots, in card order, with the kit components (data/model-kit.json) each one covers. */
const SLOTS = [
  { id: 'legs', code: 'LEG', name: 'Legs', kit: ['thigh', 'shin', 'foot'] },
  { id: 'torso', code: 'TOR', name: 'Torso', kit: ['torso', 'pelvis'] },
  { id: 'helm', code: 'HLM', name: 'Helm', kit: ['helm', 'collar'] },
  { id: 'pauldrons', code: 'PLD', name: 'Pauldrons', kit: ['pauldron'] },
  { id: 'arms', code: 'ARM', name: 'Arms', kit: ['arm', 'forearm', 'hand'] },
  { id: 'crown-back', code: 'CRB', name: 'Crown & Back', kit: ['crown', 'back', 'cloth'] },
];
const ORDER = SLOTS.map((s) => s.id);

/** Split `total` into whole numbers in proportion to `shares` (slot id -> weight); the shares sum exactly to total. */
function split(total, shares) {
  const ids = Object.keys(shares);
  const sum = ids.reduce((n, id) => n + shares[id], 0);
  const out = Object.fromEntries(ids.map((id) => [id, Math.floor((total * shares[id]) / sum)]));
  let left = total - Object.values(out).reduce((a, b) => a + b, 0);
  const byRemainder = [...ids].sort((a, b) => ((total * shares[b]) % sum) / sum - ((total * shares[a]) % sum) / sum || ORDER.indexOf(a) - ORDER.indexOf(b));
  for (const id of byRemainder) {
    if (left-- <= 0) break;
    out[id]++;
  }
  return out;
}

const POINT_WEIGHTS = { legs: 25, torso: 30, helm: 10, pauldrons: 10, arms: 15, 'crown-back': 10 };
const FACTION_CODE = { covenant: 'CV', foundries: 'AF', reliquary: 'RQ' };

function partsFor(c) {
  const stats = Object.fromEntries(ORDER.map((id) => [id, {}]));
  const put = (id, group, key, value) => {
    if (!value) return;
    if (group) (stats[id][group] ??= {})[key] = value;
    else stats[id][key] = value;
  };
  // Points: every part costs at least 1 when the class is big enough to allow it.
  const floor = c.points >= ORDER.length ? 1 : 0;
  const extra = split(c.points - floor * ORDER.length, POINT_WEIGHTS);
  for (const id of ORDER) put(id, null, 'points', floor + extra[id]);
  // Whole stats live on the part that provides them.
  put('legs', null, 'stride', c.stride);
  put('crown-back', null, 'boiler', c.boiler);
  put('legs', 'slots', 'legs', c.slots.legs);
  put('torso', 'slots', 'core', c.slots.core);
  put('arms', 'slots', 'armLeft', c.slots.armLeft);
  put('arms', 'slots', 'armRight', c.slots.armRight);
  put('torso', 'structure', 'core', c.structure.core);
  put('arms', 'structure', 'other', c.structure.other);
  put('legs', 'armour', 'legs', c.armour.legs);
  // Armour is shared between the parts that cover the location.
  for (const [key, shares] of Object.entries({
    coreFront: { torso: 60, helm: 20, pauldrons: 20 },
    coreRear: { torso: 50, 'crown-back': 50 },
    arm: { arms: 60, pauldrons: 40 },
  })) {
    for (const [id, n] of Object.entries(split(c.armour[key], shares))) put(id, 'armour', key, n);
  }
  return ORDER.map((id) => {
    const slot = SLOTS.find((s) => s.id === id);
    return {
      id: `${c.id}-${id}`,
      class: c.id,
      slot: id,
      name: `${c.name} ${slot.name}`,
      faction: c.faction,
      frame: c.frame,
      frameSize: c.size,
      kit: slot.kit,
      stats: stats[id],
    };
  });
}

const parts = chassis.flatMap(partsFor);

// ---- cards -----------------------------------------------------------------------------------------------------

const TIERS = [
  { tier: 1, id: 'stamped', name: 'Stamped', finish: 'Cast iron, matte, stamped serial.' },
  { tier: 2, id: 'riveted', name: 'Riveted', finish: 'Bronze rivets and a hand-brushed edge.' },
  { tier: 3, id: 'guild-forged', name: 'Guild-forged', finish: 'Polished steel with a guild mark.' },
  { tier: 4, id: 'masterwork', name: 'Masterwork', finish: 'Gilded trim, signed by the forgemaster.' },
  { tier: 5, id: 'legendary-relic', name: 'Legendary Relic', finish: 'Holofoil card, unique geometry, numbered print run.' },
];

/** Placeholder tier rule (no balance work yet): each tier above 1 adds 1 to the part's primary stat and 1 point. */
const PRIMARY = { legs: ['armour', 'legs'], torso: ['armour', 'coreFront'], arms: ['armour', 'arm'] };
const EXAMPLES = ['paladin-legs', 'paladin-torso', 'paladin-arms'];
const TIER_ONE_ONLY = ['paladin-helm', 'paladin-pauldrons', 'paladin-crown-back'];
const PLACEHOLDER_RUN = 50;

const printCode = (part) => `${FACTION_CODE[part.faction]}-${part.class.slice(0, 3).toUpperCase()}-${SLOTS.find((s) => s.id === part.slot).code}`;

function bodyCard(part, tier) {
  const stats = structuredClone(part.stats);
  stats.points = (stats.points ?? 0) + (tier - 1);
  if (tier > 1) {
    const [group, key] = PRIMARY[part.slot];
    stats[group][key] += tier - 1;
  }
  return {
    printId: `${printCode(part)}-T${tier}`,
    kind: 'body',
    partId: part.id,
    name: part.name,
    slot: part.slot,
    faction: part.faction,
    frame: part.frame,
    frameSize: part.frameSize,
    tier,
    stats,
    statsPlaceholder: tier > 1,
    ...(tier === 5 ? { printRun: PLACEHOLDER_RUN, printRunPlaceholder: true } : {}),
    art: part.id,
  };
}

const ITEM_CARDS = ['lance', 'carapace-gun', 'gyro-stabilisers', 'targeting-array'];
function itemCard(id) {
  const e = equipment.find((x) => x.id === id);
  const { id: _id, name, faction, category, mount, slots, pressure, points, weapon, tags, rules, uses, maxPerWalker } = e;
  const art = `paladin-${id}`;
  return {
    printId: `CV-EQ-${id.replace(/-/g, '').slice(0, 5).toUpperCase()}-T1`,
    kind: 'equipment',
    itemId: id,
    name,
    // Shared gear is printed with the Covenant art variant, so the card carries that faction.
    faction: 'covenant',
    frame: null,
    frameSize: null,
    tier: 1,
    stats: { category, mount, slots, pressure, points, ...(weapon ? { weapon } : {}), ...(uses ? { uses } : {}), ...(maxPerWalker ? { maxPerWalker } : {}), tags: tags ?? [], rules },
    statsPlaceholder: false,
    art,
    ...(faction ? {} : { shared: true }),
  };
}

const byId = Object.fromEntries(parts.map((p) => [p.id, p]));
const cards = [
  ...[...EXAMPLES, ...TIER_ONE_ONLY].flatMap((id) => (EXAMPLES.includes(id) ? [1, 2, 3, 4, 5] : [1]).map((t) => bodyCard(byId[id], t))),
  ...ITEM_CARDS.map(itemCard),
];

// ---- write (one part or card per line, so diffs stay readable) ---------------------------------------------------

const lines = (list) => list.map((x) => `    ${JSON.stringify(x)}`).join(',\n');

writeFileSync(
  join(dataDir, 'parts.json'),
  `{
  "$comment": "Body part cards. Each class in chassis.json splits into six parts; the parts' stats add up to the class's stats exactly (packages/rules/test/parts.test.ts checks it). Whole-class stats sit on one part: stride on legs, boiler on crown-back, slots on the part that holds them, structure.core on the torso, structure.other (per limb location) on the arms. Armour and points are shared out between the parts that cover them. frameSize is the class's size and is the same on all six parts, not summed. kit lists the model-kit.json components the part covers. Seeded by scripts/seed-parts.mjs.",
  "slots": ${JSON.stringify(SLOTS.map(({ id, code, name, kit }) => ({ id, code, name, kit })))},
  "parts": [
${lines(parts)}
  ]
}
`,
);

writeFileSync(
  join(dataDir, 'cards.json'),
  `{
  "$comment": "Printable card records for the Paladin milestone (see docs/cards.md). A card is a part or item at a tier. printId is the part id plus tier and is what a card prints; account-linked instance ids come later. Tier 1 body stats equal the part's stats in parts.json. Tier 2 to 5 stats are placeholders (statsPlaceholder: true), not balanced. Seeded by scripts/seed-parts.mjs.",
  "tiers": ${JSON.stringify(TIERS)},
  "tierRule": "Placeholder: each tier above 1 adds 1 to the part's primary stat (legs: armour.legs, torso: armour.coreFront, arms: armour.arm) and 1 to points.",
  "cards": [
${lines(cards)}
  ]
}
`,
);
console.log(`${parts.length} parts, ${cards.length} cards`);
