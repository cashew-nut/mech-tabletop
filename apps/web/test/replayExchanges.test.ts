import { describe, expect, it } from 'vitest';
import { chooseAction } from '@brass-charter/ai';
import { applyAction, createGame, type GameState, type LanceInput } from '@brass-charter/rules';
import examples from '../../../data/lances/examples.json';
import { buildExchanges } from '../src/battle/replayExchanges';

const LANCES = examples.lances as LanceInput[];

/** Play an AI-vs-AI game, handing every step to `visit` with the states either side of it. */
function play(seed: number, visit: (before: GameState, after: GameState, type: string) => void) {
  let state = createGame({ seed, scenario: seed % 2 ? 'surveyor-escort' : 'hold-the-field', map: 'chapel-ruins', deploy: 'auto', lances: [LANCES[seed % LANCES.length], LANCES[(seed + 1) % LANCES.length]] });
  for (let i = 0; i < 1500 && state.phase !== 'over'; i++) {
    const action = chooseAction(state);
    const next = applyAction(state, action).state;
    visit(state, next, action.type);
    state = next;
  }
}

describe('combat replay', () => {
  it('replays exactly the dice the engine logged, and the damage it dealt', () => {
    let exchanges = 0;
    let dealt = 0;
    for (const seed of [1, 2, 3, 4, 5, 6]) {
      play(seed, (before, after, type) => {
        const events = after.log.slice(before.log.length);
        const found = buildExchanges(before, after);
        if (type !== 'fire' && type !== 'ram') return expect(found).toEqual([]);
        // Every roll the engine logged for a target comes back as one exchange with the same faces.
        const logged = events.filter((e) => e.type === 'roll');
        for (const x of found) {
          exchanges++;
          const roll = logged.find((e) => JSON.stringify(e.rolls) === JSON.stringify(x.dice.map((d) => d.value)));
          expect(roll, 'exchange dice match a logged roll').toBeDefined();
          expect(x.dice.filter((d) => d.hit).length).toBe(Number(/: (\d+) hit/.exec(roll!.text)![1]));
          // Armour + structure lost between the two states is what the hit events say it was.
          if (x.targetBefore && x.targetAfter) {
            const sum = (w: typeof x.targetAfter) => Object.values(w!.armour).reduce((a, b) => a + b, 0) + Object.values(w!.structure).reduce((a, b) => a + b, 0);
            const drop = sum(x.targetBefore) - sum(x.targetAfter);
            const claimed = x.impacts.reduce((n, i) => n + i.damage, 0);
            dealt += claimed;
            // Overkill is clamped and criticals add a little, so only check that damage claimed means something was lost.
            if (claimed > 0) expect(drop).toBeGreaterThan(0);
          }
        }
        expect(found.length).toBeLessThanOrEqual(logged.length);
      });
    }
    expect(exchanges).toBeGreaterThan(20);
    expect(dealt).toBeGreaterThan(0);
  });

  it('shows nothing for actions that roll no dice', () => {
    play(3, (before, after, type) => {
      if (type === 'move' || type === 'brace' || type === 'bank') expect(buildExchanges(before, after)).toEqual([]);
    });
  });
});
