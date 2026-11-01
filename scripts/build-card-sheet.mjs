// Build the printable card sheet from data/cards.json and the art in cards/art.
//   node scripts/build-card-sheet.mjs [facesDir]
// Writes cards/sheet.html (A4, 3 x 3 cards of 63 x 88 mm per page, with crop marks) and cards/paladin-cards.pdf.
// With facesDir, also saves each card face as a 300 dpi PNG named by its print id.
// Render the art first with scripts/render-card-art.mjs. Needs Playwright installed globally.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const { chromium } = createRequire(import.meta.url)('playwright');
const { tiers, cards } = JSON.parse(readFileSync(join(root, 'data/cards.json'), 'utf8'));
const { factions } = JSON.parse(readFileSync(join(root, 'data/factions.json'), 'utf8'));
const facesDir = process.argv[2];

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const factionName = (id) => factions.find((f) => f.id === id)?.name ?? id;
const SLOT_LABEL = { legs: 'Legs', torso: 'Torso + pelvis', helm: 'Helm', pauldrons: 'Pauldrons', arms: 'Arms', 'crown-back': 'Crown / back' };

/** The stat boxes on a card: [label, value]. */
function statBoxes(c) {
  const s = c.stats;
  if (c.kind === 'equipment') {
    const w = s.weapon;
    return [
      ['Slots', s.slots],
      ['Pressure', s.pressure],
      ['Points', s.points],
      ...(w ? [['Dice', `${w.dice}×${w.damage}`], ['Range', w.range], ...(w.pierce ? [['Pierce', w.pierce]] : []), ...(w.ammo ? [['Ammo', w.ammo]] : [])] : [['Mount', s.mount.join('/')]]),
    ];
  }
  return [
    ['Points', s.points],
    ...(s.stride ? [['Stride', s.stride]] : []),
    ...(s.boiler ? [['Boiler', s.boiler]] : []),
    ...(s.armour?.coreFront ? [['Armour front', s.armour.coreFront]] : []),
    ...(s.armour?.coreRear ? [['Armour rear', s.armour.coreRear]] : []),
    ...(s.armour?.arm ? [['Armour arm', s.armour.arm]] : []),
    ...(s.armour?.legs ? [['Armour legs', s.armour.legs]] : []),
    ...(s.structure?.core ? [['Structure', s.structure.core]] : []),
    ...(s.structure?.other ? [['Structure limb', s.structure.other]] : []),
    ...(s.slots?.core ? [['Core slots', s.slots.core]] : []),
    ...(s.slots?.armLeft ? [['Arm slots', `${s.slots.armLeft} + ${s.slots.armRight}`]] : []),
    ...(s.slots?.legs ? [['Leg slots', s.slots.legs]] : []),
  ];
}

function face(c) {
  const tier = tiers.find((t) => t.tier === c.tier);
  const kindLabel = c.kind === 'body' ? `Body · ${SLOT_LABEL[c.slot]}` : `Equipment · ${c.stats.category}`;
  const boxes = statBoxes(c)
    .map(([l, v]) => `<div class="stat"><b>${esc(v)}${c.statsPlaceholder && l !== 'Points' ? '' : ''}</b><span>${esc(l)}</span></div>`)
    .join('');
  const pips = c.frameSize ? `<span class="pips" title="Frame size ${c.frameSize}">${'<i></i>'.repeat(c.frameSize)}</span>` : '';
  const rules = c.kind === 'equipment' && c.stats.rules ? `<p class="rules">${esc(c.stats.rules)}</p>` : '';
  const ph = c.statsPlaceholder ? '<em class="ph">placeholder stats</em>' : '';
  const run = c.printRun ? `<em class="run">No. ___ / ${c.printRun}</em>` : '';
  return `<article class="card t${c.tier} ${c.faction} ${c.kind}" data-print-id="${esc(c.printId)}">
  <div class="inner">
    <header><h2>${esc(c.name)}</h2><div class="kind">${esc(kindLabel)}</div></header>
    <div class="art"><img src="art/${esc(c.art)}.jpg" alt=""><span class="faction">${esc(factionName(c.faction))}</span></div>
    <div class="stats">${boxes}</div>
    ${rules}
    <footer>
      <span class="id">${esc(c.printId)}</span>
      ${pips}
      <span class="tier">${esc(tier.name)}</span>
    </footer>
    ${ph}${run}
  </div>
</article>`;
}

// Tier 1 cards first (the ten faces), then the tier ladders.
const ordered = [...cards.filter((c) => c.tier === 1), ...cards.filter((c) => c.tier > 1)];
const pages = [];
for (let i = 0; i < ordered.length; i += 9) pages.push(ordered.slice(i, i + 9));

const css = `
@page { size: A4; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
body { background: #fff; font-family: Inter, 'DejaVu Sans', sans-serif; -webkit-print-color-adjust: exact; print-color-adjust: exact }
.page { position: relative; width: 210mm; height: 297mm; page-break-after: always; overflow: hidden; background: #fff }
.grid { position: absolute; left: 10.5mm; top: 16.5mm; width: 189mm; display: grid; grid-template-columns: repeat(3, 63mm); grid-auto-rows: 88mm }
.cap { position: absolute; left: 10.5mm; right: 10.5mm; bottom: 6mm; font: 7pt 'JetBrains Mono', monospace; color: #666 }
.mark { position: absolute; background: #000 }
.mark.h { height: 0.2mm; width: 4mm } .mark.v { width: 0.2mm; height: 4mm }

.card { width: 63mm; height: 88mm; padding: 0; position: relative; background: #111; --edge: #8b8b8b; --edge2: #5d5d5d; --accent: #b88a2e; color: #eee6d4 }
.card.covenant { --accent: #c9a04a; --wash: #4a1313 } .card.foundries { --accent: #d2813a; --wash: #4a2a10 } .card.reliquary { --accent: #5fb3a8; --wash: #12403d }
.card.t1 { --edge: #8d8f93; --edge2: #55575b }
.card.t2 { --edge: #c1824a; --edge2: #7a4a22 }
.card.t3 { --edge: #aebfce; --edge2: #5f7388 }
.card.t4 { --edge: #e2b84a; --edge2: #8e6a14 }
.card.t5 { --edge: conic-gradient(from 20deg, #ffd1f0, #c8f1ff, #d6ffd1, #fff3b0, #ffd1f0); --edge2: #888 }
.card::before { content: ''; position: absolute; inset: 0; border-radius: 3mm; background: linear-gradient(145deg, var(--edge), var(--edge2) 60%, var(--edge)) }
.card.t5::before { background: var(--edge) }
.inner { position: absolute; inset: 1.8mm; border-radius: 1.8mm; background: radial-gradient(120% 70% at 50% 0%, var(--wash, #333), #141210 70%); display: flex; flex-direction: column; padding: 2mm 2.2mm 1.6mm; overflow: hidden }
header h2 { font: 700 3.9mm/1.05 'Bitstream Charter', 'DejaVu Serif', serif; letter-spacing: 0.01em }
.kind { font-size: 2mm; text-transform: uppercase; letter-spacing: 0.14em; color: var(--accent); margin-top: 0.5mm }
.art { position: relative; margin-top: 1.4mm; height: 45mm; border-radius: 1mm; overflow: hidden; border: 0.3mm solid var(--accent); background: #22252a }
.art img { width: 100%; height: 100%; object-fit: cover; display: block }
.faction { position: absolute; left: 0; bottom: 0; padding: 0.5mm 1.6mm; font-size: 1.9mm; text-transform: uppercase; letter-spacing: 0.12em; background: rgba(10, 8, 6, .78); color: var(--accent); border-top-right-radius: 1mm }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.8mm; margin-top: 1.5mm }
.stat { background: rgba(0, 0, 0, .45); border: 0.2mm solid rgba(255, 255, 255, .14); border-radius: 0.8mm; text-align: center; padding: 0.5mm 0.3mm 0.4mm }
.stat b { display: block; font: 700 3.4mm/1.1 'Bitstream Charter', 'DejaVu Serif', serif; color: #fff }
.stat span { display: block; font-size: 1.55mm; text-transform: uppercase; letter-spacing: 0.08em; color: #b9ad94 }
.rules { margin-top: 1.2mm; font: italic 2.1mm/1.25 'Bitstream Charter', 'DejaVu Serif', serif; color: #d8cfba }
footer { margin-top: auto; display: flex; align-items: center; justify-content: space-between; gap: 1mm; font-size: 1.8mm; text-transform: uppercase; letter-spacing: 0.08em }
footer .id { font: 1.8mm 'JetBrains Mono', monospace; color: #a79c85; letter-spacing: 0 }
footer .tier { color: var(--edge2); background: var(--edge); border-radius: 0.8mm; padding: 0.3mm 1.4mm; font-weight: 700; color: #151515 }
.card.t5 footer .tier { background: linear-gradient(90deg, #ffb6e6, #b6f0ff, #c8ffb6, #fff0a0) }
.pips { display: inline-flex; gap: 0.5mm } .pips i { width: 1.5mm; height: 1.5mm; background: var(--accent); border-radius: 0.2mm; display: block }
.ph { position: absolute; right: 2.2mm; top: 7.2mm; font: normal 1.5mm 'JetBrains Mono', monospace; color: #e8dcc0; background: rgba(0, 0, 0, .6); padding: 0.2mm 0.8mm; border-radius: 0.5mm; text-transform: uppercase }
.run { position: absolute; left: 2.2mm; right: 2.2mm; bottom: 5.4mm; text-align: center; font: normal 2mm 'JetBrains Mono', monospace; color: #ffe9a8 }
`;

const marks = (() => {
  const out = [];
  for (const x of [10.5, 73.5, 136.5, 199.5]) for (const y of [16.5 - 5, 16.5 + 264 + 1]) out.push(`<i class="mark v" style="left:${x - 0.1}mm;top:${y}mm"></i>`);
  for (const y of [16.5, 104.5, 192.5, 280.5]) for (const x of [10.5 - 5, 199.5 + 1]) out.push(`<i class="mark h" style="left:${x}mm;top:${y - 0.1}mm"></i>`);
  return out.join('');
})();

const html = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Brass Charter: Paladin card sheet</title><style>${css}</style></head><body>
${pages
  .map(
    (p, i) => `<section class="page">${marks}<div class="grid">${p.map(face).join('\n')}</div>
<div class="cap">Brass Charter · Paladin cards · page ${i + 1}/${pages.length} · 63×88 mm, print at 100% · cut on the marks · tier 2–5 stats are placeholders</div></section>`,
  )
  .join('\n')}
</body></html>
`;
writeFileSync(join(root, 'cards/sheet.html'), html);

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 3.125 });
  await page.goto(`file://${join(root, 'cards/sheet.html')}`);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0));
  await page.pdf({ path: join(root, 'cards/paladin-cards.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true });
  console.log('cards/paladin-cards.pdf');
  if (facesDir) {
    mkdirSync(resolve(facesDir), { recursive: true });
    for (const el of await page.locator('article.card').all()) {
      const id = await el.getAttribute('data-print-id');
      await el.screenshot({ path: join(resolve(facesDir), `${id}.png`) });
    }
    console.log(`${cards.length} faces in ${facesDir}`);
  }
} finally {
  await browser.close();
}
