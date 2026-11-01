// AI games on a sample of generated boards: side balance plus rough fun proxies,
// compared with the hand-made maps. Mirrored: each pairing is played from both sides.
//   npx vite-node tools/mapgen/sim-sample.ts -- [boards=40] [pairings=20] [firstSeed=1] [baseline=1]
import examples from '../../data/lances/examples.json';
import { playOut } from '@brass-charter/ai';
import { MAPS, SCENARIOS, createGame, generateBoard, hexKey, type GameState, type LanceInput, type MapDef, type ScenarioDef } from '@brass-charter/rules';
import { randomLance } from '../sim/randomLance';

const args = process.argv.slice(2).filter((a) => a !== '--');
const boards = Number(args[0] ?? 40);
const pairings = Number(args[1] ?? 20);
const first = Number(args[2] ?? 1);
const baseline = (args[3] ?? '1') === '1';
const EXAMPLES = examples.lances as LanceInput[];

interface Tally { s0: number; n: number; draws: number; early: number; swaps: number; contested: number; margin: number }
const blank = (): Tally => ({ s0: 0, n: 0, draws: 0, early: 0, swaps: 0, contested: 0, margin: 0 });

/** Objective holders round by round, from the end-phase events. */
function objectiveSwaps(end: GameState): number {
  const holder = new Map<string, number>();
  let swaps = 0;
  for (const e of end.log as Array<{ type: string; side?: number; hex?: { q: number; r: number } }>) {
    if (e.type !== 'objective' || !e.hex) continue;
    const k = hexKey(e.hex);
    if (holder.has(k) && holder.get(k) !== e.side) swaps++;
    holder.set(k, e.side!);
  }
  return swaps;
}

function play(map: string | MapDef, scenario: string | ScenarioDef, seed0: number, t: Tally) {
  for (let g = 0; g < pairings; g++) {
    const seed = seed0 * 1000 + g;
    const rng = { state: seed * 31 + 7 };
    const a = g % 2 ? randomLance(rng, 'A') : EXAMPLES[g % EXAMPLES.length];
    const b = randomLance(rng, 'B');
    for (const [x, y] of [[a, b], [b, a]] as const) {
      const end = playOut(createGame({ seed, scenario, map, lances: [x, y], deploy: 'alternate' }));
      t.s0 += end.winner === 'draw' ? 0.5 : end.winner === 0 ? 1 : 0;
      t.draws += end.winner === 'draw' ? 1 : 0;
      t.early += end.round <= 3 ? 1 : 0;
      const sw = objectiveSwaps(end);
      t.swaps += sw;
      t.contested += sw > 0 ? 1 : 0;
      t.margin += Math.abs(end.vp[0] - end.vp[1]);
      t.n++;
    }
  }
}

const pct = (x: number, n: number) => `${((x / n) * 100).toFixed(0)}%`;
const line = (label: string, t: Tally) =>
  `${label.padEnd(34)} side0 ${pct(t.s0, t.n).padStart(4)}  draws ${pct(t.draws, t.n).padStart(4)}  over by r3 ${pct(t.early, t.n).padStart(4)}  objective changed hands ${pct(t.contested, t.n).padStart(4)}  avg VP margin ${(t.margin / t.n).toFixed(1)}  (${t.n})`;

const all = blank();
const outliers: string[] = [];
for (let i = 0; i < boards; i++) {
  const gb = generateBoard(first + i);
  const t = blank();
  play(gb.map, gb.scenario, first + i, t);
  for (const k of Object.keys(all) as Array<keyof Tally>) all[k] += t[k];
  const share = t.s0 / t.n;
  if (share < 0.35 || share > 0.65) outliers.push(`${gb.code} ${pct(t.s0, t.n)}`);
  console.log(line(`${gb.code}`, t));
}
console.log('');
console.log(line(`GENERATED (${boards} boards)`, all));
console.log(`Boards outside 35-65%: ${outliers.length}${outliers.length ? ` (${outliers.join(', ')})` : ''}`);
if (baseline) {
  const base = blank();
  let k = 0;
  for (const m of MAPS) for (const s of SCENARIOS.filter((x) => x.objectives.length)) play(m.id, s.id, 900 + k++, base);
  console.log(line(`HAND-MADE (${MAPS.length} maps x 3 scenarios)`, base));
}
