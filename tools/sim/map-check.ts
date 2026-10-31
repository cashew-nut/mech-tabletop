// Side balance on one map: mirrored AI-vs-AI Trials (each pairing played from both sides) across every scenario.
//   npx vite-node tools/sim/map-check.ts -- <mapId> [games=120] [seed=1]
import examples from '../../data/lances/examples.json';
import { playOut } from '@brass-charter/ai';
import { SCENARIOS, createGame, type LanceInput } from '@brass-charter/rules';
import { randomLance } from './randomLance';

const args = process.argv.slice(2).filter((a) => a !== '--');
const map = args[0] ?? 'chapel-ruins';
const games = Number(args[1] ?? 120);
const seed0 = Number(args[2] ?? 1);
const EXAMPLES = examples.lances as LanceInput[];

let side0 = 0;
let draws = 0;
let played = 0;
let steps = 0;
const byScenario = new Map<string, { s0: number; n: number }>();
for (let g = 0; g < games; g++) {
  const seed = seed0 + g;
  const rng = { state: seed * 31 + 7 };
  const a = g % 2 ? randomLance(rng, 'A') : EXAMPLES[g % EXAMPLES.length];
  const b = randomLance(rng, 'B');
  const scenario = SCENARIOS[g % SCENARIOS.length].id;
  for (const [x, y] of [[a, b], [b, a]] as const) {
    const end = playOut(createGame({ seed, scenario, map, lances: [x, y], deploy: 'alternate' }));
    const s = end.winner === 'draw' ? 0.5 : end.winner === 0 ? 1 : 0;
    side0 += s;
    draws += end.winner === 'draw' ? 1 : 0;
    played++;
    steps += end.round;
    const t = byScenario.get(scenario) ?? { s0: 0, n: 0 };
    t.s0 += s;
    t.n++;
    byScenario.set(scenario, t);
  }
}
const pct = (x: number, n: number) => `${((x / n) * 100).toFixed(0)}%`;
console.log(`${map}: ${played} games, side 0 scores ${pct(side0, played)}, draws ${pct(draws, played)}, avg rounds ${(steps / played).toFixed(1)}`);
for (const [s, t] of byScenario) console.log(`  ${s.padEnd(18)} side 0 ${pct(t.s0, t.n)} (${t.n})`);
