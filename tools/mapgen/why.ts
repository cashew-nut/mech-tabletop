// Which hard rules reject candidates, per archetype and template (for tuning piece mixes).
//   npx vite-node tools/mapgen/why.ts -- [candidates=100]
import { ARCHETYPES, TEMPLATES, buildCandidate, checkBoard, RULES } from '@brass-charter/rules';
const n = Number(process.argv.slice(2).filter((a) => a !== '--')[0] ?? 100);
for (const a of ARCHETYPES) for (const t of TEMPLATES) {
  const rng = { state: 12345 };
  const tally: Record<string, number> = {};
  let ok = 0, noObj = 0;
  for (let i = 0; i < n; i++) {
    const c = buildCandidate(a, t, rng, RULES.map.deploymentDepth);
    if (!c) { noObj++; continue; }
    const r = checkBoard(c.board, c.objectives, RULES.map.deploymentDepth, { limits: a.limits });
    if (r.ok) ok++;
    for (const x of r.results) if (!x.ok) tally[x.rule] = (tally[x.rule] ?? 0) + 1;
  }
  console.log(`${a.id.padEnd(8)} ${t.id.padEnd(8)} ok ${ok}/${n} noObj ${noObj}`, JSON.stringify(tally));
}
