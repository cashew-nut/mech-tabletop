// Balance simulator: AI-vs-AI Trials between the example lances and random
// legal lances, reporting win rates by lance, chassis, item, trait and size.
//
//   npm run sim -- [randomGames=400] [seed=1]
import examples from '../../data/lances/examples.json';
import { playOut } from '@brass-charter/ai';
import { COMPANIES, EQUIPMENT, MAPS, SCENARIOS, TRAITS, createGame, type GameState, type LanceInput } from '@brass-charter/rules';
import { randomLance } from './randomLance';

const randomGames = Number(process.argv[2] ?? 400);
const seed0 = Number(process.argv[3] ?? 1);
const scenarios = SCENARIOS.filter((s) => s.objectives.length).map((s) => s.id);
const maps = MAPS.map((m) => m.id);
const EXAMPLES = examples.lances as LanceInput[];

type Tally = { games: number; score: number };
const tally = () => new Map<string, Tally>();
const add = (m: Map<string, Tally>, key: string, score: number) => {
  const t = m.get(key) ?? { games: 0, score: 0 };
  t.games++;
  t.score += score;
  m.set(key, t);
};

function play(a: LanceInput, b: LanceInput, seed: number): GameState {
  return playOut(createGame({ seed, scenario: scenarios[seed % scenarios.length], map: maps[seed % maps.length], lances: [a, b] }));
}

const scoreFor = (s: GameState, side: 0 | 1) => (s.winner === 'draw' ? 0.5 : s.winner === side ? 1 : 0);
const pct = (t: Tally) => `${((t.score / t.games) * 100).toFixed(0).padStart(3)}%`;

// 1. Example lances, every ordered pairing.
console.log('Example lances (each pairing both ways, 8 seeds per order)');
const ex = tally();
const vs: string[] = [];
for (let i = 0; i < EXAMPLES.length; i++) {
  for (let j = 0; j < EXAMPLES.length; j++) {
    if (i === j) continue;
    let score = 0;
    for (let k = 0; k < 8; k++) {
      const s = play(EXAMPLES[i], EXAMPLES[j], seed0 + k);
      score += scoreFor(s, 0);
      add(ex, EXAMPLES[i].name, scoreFor(s, 0));
      add(ex, EXAMPLES[j].name, scoreFor(s, 1));
    }
    vs.push(`  ${EXAMPLES[i].name} vs ${EXAMPLES[j].name}: ${score}/8`);
  }
}
for (const [name, t] of ex) console.log(`  ${pct(t)}  ${name}`);
console.log(vs.join('\n'));

// 2. Random lances.
const rng = { state: seed0 * 7919 };
const byItem = tally();
const byChassis = tally();
const byTrait = tally();
const bySize = tally();
const byCompany = tally();
let firstPlayerScore = 0;
const lengths: number[] = [];
const started = Date.now();
for (let g = 0; g < randomGames; g++) {
  const lances = [randomLance(rng, 'A'), randomLance(rng, 'B')] as [LanceInput, LanceInput];
  const s = play(lances[0], lances[1], seed0 + 1000 + g);
  firstPlayerScore += scoreFor(s, 0);
  lengths.push(s.round);
  lances.forEach((l, side) => {
    const score = scoreFor(s, side as 0 | 1);
    add(bySize, `${l.walkers.length} walkers`, score);
    add(byCompany, l.company, score);
    for (const id of new Set(l.walkers.flatMap((w) => Object.values(w.loadout).flat() as string[]))) add(byItem, id, score);
    for (const id of new Set(l.walkers.map((w) => w.chassis))) add(byChassis, id, score);
    for (const id of new Set(l.walkers.map((w) => w.driver.trait).filter(Boolean) as string[])) add(byTrait, id, score);
  });
}

const report = (title: string, m: Map<string, Tally>, names: Map<string, string> = new Map()) => {
  console.log(`\n${title} (win rate of lances that include it)`);
  for (const [k, t] of [...m].sort((a, b) => b[1].score / b[1].games - a[1].score / a[1].games)) {
    console.log(`  ${pct(t)}  ${(names.get(k) ?? k).padEnd(22)} ${String(t.games).padStart(4)} games`);
  }
};
console.log(`\n${randomGames} random-lance Trials in ${((Date.now() - started) / 1000).toFixed(0)}s; side that deployed first scored ${((firstPlayerScore / randomGames) * 100).toFixed(0)}%`);
report('Lance size', bySize);
report('Chassis', byChassis);
report('Items', byItem, new Map(EQUIPMENT.map((e) => [e.id, e.name])));
report('Driver traits', byTrait, new Map(TRAITS.map((t) => [t.id, t.name])));
report('Companies', byCompany, new Map(COMPANIES.map((c) => [c.id, c.name])));
