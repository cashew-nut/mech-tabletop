// Seed sweep: generate many boards and report what the plan's test table asks for.
//   npx vite-node tools/mapgen/sweep.ts -- [seeds=1000] [firstSeed=1] [distinctSample=500]
import { ARCHETYPES, RULES, TEMPLATES, boardDistance, checkBoard, generateBoard, type GeneratedBoard } from '@brass-charter/rules';

const args = process.argv.slice(2).filter((a) => a !== '--');
const seeds = Number(args[0] ?? 1000);
const first = Number(args[1] ?? 1);
const sampleN = Number(args[2] ?? 500);

const arch = new Map<string, number>();
const tpl = new Map<string, number>();
const fallbacks: string[] = [];
const recheckFails: string[] = [];
const times: number[] = [];
const passRates: number[] = [];
const sample: GeneratedBoard[] = [];
for (let i = 0; i < seeds; i++) {
  const t = performance.now();
  const g = generateBoard(first + i);
  times.push(performance.now() - t);
  arch.set(g.archetype, (arch.get(g.archetype) ?? 0) + 1);
  tpl.set(g.template, (tpl.get(g.template) ?? 0) + 1);
  passRates.push(g.passed / g.tried);
  if (g.fallback) fallbacks.push(g.code);
  else {
    const a = ARCHETYPES.find((x) => x.id === g.archetype)!;
    const r = checkBoard(g.board, g.objectives, RULES.map.deploymentDepth, { limits: a.limits });
    if (!r.ok) recheckFails.push(`${g.code}: ${r.results.filter((x) => !x.ok).map((x) => x.rule).join(',')}`);
  }
  if (sample.length < sampleN) sample.push(g);
  if ((i + 1) % 250 === 0) console.error(`  ${i + 1}/${seeds}`);
}
const sorted = [...times].sort((a, b) => a - b);
const pct = (x: number) => `${(x * 100).toFixed(1)}%`;
console.log(`Seeds ${first}..${first + seeds - 1}`);
console.log(`Fallbacks: ${fallbacks.length}${fallbacks.length ? ` (${fallbacks.slice(0, 10).join(', ')})` : ''}`);
console.log(`Hard-rule recheck failures: ${recheckFails.length}${recheckFails.length ? ` (${recheckFails.slice(0, 10).join('; ')})` : ''}`);
console.log(`Time per board: median ${sorted[Math.floor(sorted.length / 2)].toFixed(0)} ms, p95 ${sorted[Math.floor(sorted.length * 0.95)].toFixed(0)} ms, max ${sorted.at(-1)!.toFixed(0)} ms`);
console.log(`Candidate pass rate: median ${pct([...passRates].sort((a, b) => a - b)[Math.floor(passRates.length / 2)])}, min ${pct(Math.min(...passRates))}`);
console.log(`Archetypes: ${ARCHETYPES.map((a) => `${a.id} ${pct((arch.get(a.id) ?? 0) / seeds)}`).join(', ')}`);
console.log(`Templates: ${TEMPLATES.map((t) => `${t.id} ${pct((tpl.get(t.id) ?? 0) / seeds)}`).join(', ')}`);

const d: number[] = [];
let closest = { d: 2, a: '', b: '' };
for (let i = 0; i < sample.length; i++) {
  for (let j = i + 1; j < sample.length; j++) {
    const x = boardDistance(sample[i], sample[j]);
    d.push(x);
    if (x < closest.d) closest = { d: x, a: sample[i].code, b: sample[j].code };
  }
}
d.sort((a, b) => a - b);
console.log(`Distinctness over ${sample.length} boards (${d.length} pairs): median ${d[Math.floor(d.length / 2)].toFixed(2)}, 1st percentile ${d[Math.floor(d.length * 0.01)].toFixed(2)}, min ${d[0].toFixed(2)} (${closest.a} vs ${closest.b}), pairs under 0.2: ${d.filter((x) => x < 0.2).length}`);
