import { describe, expect, it } from 'vitest';
import { applyAction, getWalker, previewAttack, type GameState } from '../src';
import { duel, walker } from './helpers';

const act = (s: GameState, ...actions: Parameters<typeof applyAction>[1][]) =>
  actions.reduce((st, a) => applyAction(st, a).state, s);

/** One attacker against a Scavenger 1 hex in front of it; the target faces `facing`. */
const melee = (attacker: ReturnType<typeof walker>, fillers: string, facing: 0 | 3, seed = 1) => {
  const s = duel(
    [attacker, walker('F1', fillers), walker('F2', fillers)],
    [walker('Target', 'scavenger'), walker('B2', 'scavenger'), walker('B3', 'scavenger')],
    [
      [{ col: 4, row: 6, facing: 0 }, { col: 0, row: 0 }, { col: 1, row: 0 }],
      [{ col: 5, row: 6, facing }, { col: 15, row: 11 }, { col: 14, row: 11 }],
    ],
    seed,
  );
  return act(s, { type: 'activate', walkerId: 's0w0' });
};

describe('faction weapons', () => {
  it('gives the Lance +1 die on a charge of 2 or more hexes', () => {
    const s = melee(walker('Knight', 'lancer', { armLeft: ['lance'] }), 'lancer', 3);
    const lance = getWalker(s, 's0w0').items[0];
    expect(previewAttack(s, lance.uid, 's1w0')).toMatchObject({ ok: true, dice: 2 });
    getWalker(s, 's0w0').lastMoveDistance = 2;
    expect(previewAttack(s, lance.uid, 's1w0')).toMatchObject({ ok: true, dice: 3 });
  });

  it('lets Kinetic Claws crit on 5s from behind', () => {
    const crits = (facing: 0 | 3) => {
      let n = 0;
      for (let seed = 1; seed <= 300; seed++) {
        const s = melee(walker('Hush', 'wraith', { armLeft: ['kinetic-claws'] }), 'wraith', facing, seed);
        const claws = getWalker(s, 's0w0').items[0];
        const { events } = applyAction(s, { type: 'fire', itemUid: claws.uid, targetId: 's1w0' });
        n += events.filter((e) => e.type === 'critical').length;
      }
      return n;
    };
    // Facing 0 turns the target's back to the Wraith: twice the crit faces.
    expect(crits(0)).toBeGreaterThan(crits(3) * 1.5);
  });

  it('fires the Carapace Gun from the core', () => {
    const s = melee(walker('Warden', 'sentinel', { core: ['carapace-gun'] }), 'lancer', 3);
    const gun = getWalker(s, 's0w0').items[0];
    expect(gun.location).toBe('core');
    expect(previewAttack(s, gun.uid, 's1w0')).toMatchObject({ ok: true, dice: 2 });
  });
});
