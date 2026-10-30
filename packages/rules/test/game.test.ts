import { describe, expect, it } from 'vitest';
import examples from '../../../data/lances/examples.json';
import { aliveWalkers, applyAction, createGame, legalActions, type Action, type GameState, type LanceInput } from '../src';

const lances = examples.lances as LanceInput[];

/** A crude random player: prefers shooting, then moving, and ends activations eventually. */
function choose(actions: Action[], rand: () => number): Action {
  const fire = actions.filter((a) => a.type === 'fire' || a.type === 'ram');
  if (fire.length && rand() < 0.8) return fire[Math.floor(rand() * fire.length)];
  const end = actions.find((a) => a.type === 'endActivation' && !a.reactivate);
  if (end && rand() < 0.35) return end;
  return actions[Math.floor(rand() * actions.length)];
}

function play(seed: number, a: LanceInput, b: LanceInput, scenario: string): GameState {
  let s = createGame({ seed, scenario, map: 'foundry-flats', lances: [a, b] });
  let x = seed * 9301 + 49297;
  const rand = () => ((x = (x * 9301 + 49297) % 233280) / 233280);
  let steps = 0;
  while (s.phase !== 'over') {
    const actions = legalActions(s);
    expect(actions.length).toBeGreaterThan(0);
    s = applyAction(s, choose(actions, rand)).state;
    if (++steps > 5000) throw new Error('game did not finish');
  }
  return s;
}

describe('full Trials', () => {
  const pairs: Array<[number, number, string]> = [
    [0, 1, 'hold-the-field'],
    [1, 2, 'refinery-seizure'],
    [2, 0, 'hold-the-field'],
  ];
  for (const [i, j, scenario] of pairs) {
    it(`${lances[i].name} vs ${lances[j].name} on ${scenario} plays to a result`, () => {
      for (let seed = 1; seed <= 2; seed++) {
        const s = play(seed, lances[i], lances[j], scenario);
        expect(s.phase).toBe('over');
        expect(s.winner).not.toBeNull();
        const wiped = aliveWalkers(s, 0).length === 0 || aliveWalkers(s, 1).length === 0;
        expect(wiped || s.round === 6).toBe(true);
        for (const w of s.walkers) {
          expect(w.overpressure).toBeGreaterThanOrEqual(0);
          expect(w.overpressure).toBeLessThan(6);
          for (const v of Object.values(w.armour)) expect(v).toBeGreaterThanOrEqual(0);
        }
      }
    });
  }

  it('is deterministic for a given seed', () => {
    const a = play(7, lances[0], lances[1], 'hold-the-field');
    const b = play(7, lances[0], lances[1], 'hold-the-field');
    expect(a.log).toEqual(b.log);
  });
});
