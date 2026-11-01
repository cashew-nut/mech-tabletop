// Hand-made maps against the hard rules, then a few generated seeds with timings.
//   npx vite-node tools/mapgen/calibrate.ts -- [seeds=10]
import { generateBoard, checkBoard, Board, MAPS, SCENARIOS, RULES } from '@brass-charter/rules';
const n = Number(process.argv.slice(2).filter((a) => a !== '--')[0] ?? 10);
// Calibration: hand-made maps against the hard rules.
for (const m of MAPS) for (const s of SCENARIOS.filter((x) => x.objectives.length)) {
  const r = checkBoard(Board.fromMap(m), s.objectives, RULES.map.deploymentDepth);
  console.log(m.id, s.id, r.results.filter((x) => !x.ok).map((x) => `${x.rule}: ${x.detail}`).join(' | ') || 'ok');
}
for (let seed = 1; seed <= n; seed++) {
  const t = performance.now();
  const g = generateBoard(seed);
  console.log(g.code, g.map.name, `passed ${g.passed}/${g.tried}`, g.fallback ? 'FALLBACK' : '', `score ${g.scores?.total.toFixed(2)}`, `${(performance.now() - t).toFixed(0)}ms`);
}
