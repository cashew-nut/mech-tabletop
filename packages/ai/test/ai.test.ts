import { describe, expect, it } from 'vitest';
import examples from '../../../data/lances/examples.json';
import { aliveWalkers, applyAction, createGame, legalActions, type GameState, type LanceInput } from '@brass-charter/rules';
import { chooseAction, playOut } from '../src';

const lances = examples.lances as LanceInput[];
const game = (seed: number, a = 0, b = 1, scenario = 'hold-the-field') =>
  createGame({ seed, scenario, map: 'foundry-flats', lances: [lances[a], lances[b]] });

/** Random legal play for side 1, AI for side 0. */
function aiVsRandom(seed: number): GameState {
  let s = game(seed, seed % 3, (seed + 1) % 3);
  let x = seed;
  const rand = () => ((x = (x * 9301 + 49297) % 233280) / 233280);
  for (let i = 0; i < 4000 && s.phase !== 'over'; i++) {
    let action;
    if (s.activeSide === 0) action = chooseAction(s);
    else {
      const actions = legalActions(s);
      const end = actions.find((a) => a.type === 'endActivation' && !a.reactivate);
      action = end && rand() < 0.4 ? end : actions[Math.floor(rand() * actions.length)];
    }
    s = applyAction(s, action).state;
  }
  return s;
}

describe('AI', () => {
  it('only ever picks legal actions and finishes a Trial', () => {
    for (let seed = 1; seed <= 3; seed++) {
      const s = playOut(game(seed, seed % 3, (seed + 2) % 3, seed % 2 ? 'hold-the-field' : 'refinery-seizure'));
      expect(s.phase).toBe('over');
      const wiped = aliveWalkers(s, 0).length === 0 || aliveWalkers(s, 1).length === 0;
      expect(wiped || s.round === 6).toBe(true);
    }
  });

  it('actually fights: shots get fired and damage gets done', () => {
    const s = playOut(game(5));
    expect(s.log.filter((e) => e.type === 'fire').length).toBeGreaterThan(10);
    expect(s.log.filter((e) => e.type === 'hit').length).toBeGreaterThan(5);
  });

  it('beats a random player most of the time', () => {
    let wins = 0;
    const games = 6;
    for (let seed = 1; seed <= games; seed++) if (aiVsRandom(seed).winner === 0) wins++;
    expect(wins).toBeGreaterThanOrEqual(5);
  });
});
