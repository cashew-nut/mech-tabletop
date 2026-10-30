import { describe, expect, it } from 'vitest';
import { applyAction, getWalker, hexKey, IllegalAction, legalActions, previewAttack, type GameState } from '../src';
import { duel, walker } from './helpers';

// Side 0 lead at col 2, side 1 lead at col 5, same row: 3 hexes apart, facing each other.
const setup = (attacker = walker('Gun', 'striker', { armLeft: ['autocannon'], core: ['targeting-array'] }), seed = 1) =>
  duel(
    [attacker, walker('A2', 'scout'), walker('A3', 'scout')],
    [walker('Target', 'striker'), walker('B2', 'scout'), walker('B3', 'scout')],
    [
      [
        { col: 2, row: 6, facing: 0 },
        { col: 0, row: 0 },
        { col: 1, row: 0 },
      ],
      [
        { col: 5, row: 6, facing: 3 },
        { col: 15, row: 11 },
        { col: 14, row: 11 },
      ],
    ],
    seed,
  );

const act = (s: GameState, ...actions: Parameters<typeof applyAction>[1][]) =>
  actions.reduce((st, a) => applyAction(st, a).state, s);

describe('activation and Pressure', () => {
  it('gives a war-walker its boiler rating in Pressure', () => {
    const s = act(setup(), { type: 'activate', walkerId: 's0w0' });
    expect(s.active?.pressure).toBe(5);
  });

  it('Opening the Throttle adds Pressure and Overpressure', () => {
    const s = act(setup(), { type: 'activate', walkerId: 's0w0', throttle: 2 });
    expect(s.active?.pressure).toBe(7);
    expect(getWalker(s, 's0w0').overpressure).toBe(2);
  });

  it('blows the safety valve at 6 Overpressure and ends the activation', () => {
    const s0 = setup();
    getWalker(s0, 's0w0').overpressure = 5;
    getWalker(s0, 's0w0').trait = 'iron-nerve'; // avoid a Fault roll muddying the test
    const s = act(s0, { type: 'activate', walkerId: 's0w0', throttle: 1 });
    expect(s.active).toBeNull();
    expect(getWalker(s, 's0w0').overpressure).toBe(0);
    expect(getWalker(s, 's0w0').activated).toBe(true);
    expect(s.activeSide).toBe(1);
  });

  it('moves within Stride for 1 Pressure and refuses longer paths', () => {
    let s = act(setup(), { type: 'activate', walkerId: 's0w0' });
    const w = getWalker(s, 's0w0');
    const path = [
      { q: w.pos.q, r: w.pos.r - 1 },
      { q: w.pos.q, r: w.pos.r - 2 },
    ];
    s = act(s, { type: 'move', path });
    expect(getWalker(s, 's0w0').pos).toEqual(path[1]);
    expect(s.active?.pressure).toBe(4);
    const tooFar = [1, 2, 3].map((i) => ({ q: path[1].q, r: path[1].r - i }));
    expect(() => act(s, { type: 'move', path: tooFar })).toThrow(IllegalAction);
  });

  it('alternates sides between activations', () => {
    const s = act(setup(), { type: 'activate', walkerId: 's0w0' }, { type: 'endActivation' });
    expect(s.activeSide).toBe(1);
    expect(() => act(s, { type: 'activate', walkerId: 's0w1' })).toThrow(/side 1's turn/);
  });
});

describe('attack preview', () => {
  it('computes the target number from modifiers', () => {
    const s = act(setup(), { type: 'activate', walkerId: 's0w0' });
    const gun = getWalker(s, 's0w0').items.find((i) => i.id === 'autocannon')!;
    // base 4, short range +0, Targeting Array -1
    expect(previewAttack(s, gun.uid, 's1w0')).toMatchObject({ ok: true, tn: 3, dice: 3, band: 'short' });

    const covered = structuredClone(s);
    covered.map.hexes[hexKey(getWalker(s, 's1w0').pos)].terrain = 'light';
    expect(previewAttack(covered, gun.uid, 's1w0').tn).toBe(4);

    const braced = structuredClone(s);
    getWalker(braced, 's1w0').braced = true;
    expect(previewAttack(braced, gun.uid, 's1w0').tn).toBe(4);
  });

  it('refuses targets outside the front arc or range', () => {
    let s = act(setup(), { type: 'activate', walkerId: 's0w0' }, { type: 'turn', facing: 3 });
    const gun = getWalker(s, 's0w0').items.find((i) => i.id === 'autocannon')!;
    expect(previewAttack(s, gun.uid, 's1w0')).toMatchObject({ ok: false, reason: 'Target is not in the front arc' });
    s = structuredClone(s);
    getWalker(s, 's0w0').facing = 0;
    getWalker(s, 's1w0').pos = { q: getWalker(s, 's0w0').pos.q + 9, r: getWalker(s, 's0w0').pos.r };
    expect(previewAttack(s, gun.uid, 's1w0')).toMatchObject({ ok: false, reason: 'Target is out of range' });
  });

  it('blocks line of sight through blocking terrain', () => {
    const s = act(setup(), { type: 'activate', walkerId: 's0w0' });
    const w = getWalker(s, 's0w0');
    s.map.hexes[hexKey({ q: w.pos.q + 1, r: w.pos.r })].terrain = 'blocking';
    s.map.hexes[hexKey({ q: w.pos.q + 2, r: w.pos.r })].terrain = 'blocking';
    const gun = w.items.find((i) => i.id === 'autocannon')!;
    expect(previewAttack(s, gun.uid, 's1w0')).toMatchObject({ ok: false, reason: 'No line of sight' });
  });

  it('stops the Rail Lance firing after moving', () => {
    let s = setup(walker('Rail', 'striker', { armLeft: ['rail-lance'] }));
    s = act(s, { type: 'activate', walkerId: 's0w0' });
    const w = getWalker(s, 's0w0');
    s = act(s, { type: 'move', path: [{ q: w.pos.q, r: w.pos.r + 1 }], facing: 0 });
    const lance = w.items[0];
    expect(previewAttack(s, lance.uid, 's1w0')).toMatchObject({ ok: false, reason: 'Rail Lance cannot fire after moving' });
  });
});

describe('damage', () => {
  it('hits about as often as the target number says', () => {
    let hits = 0;
    const trials = 300;
    for (let seed = 1; seed <= trials; seed++) {
      const s = act(setup(walker('Gun', 'striker', { armLeft: ['autocannon'] }), seed), { type: 'activate', walkerId: 's0w0' });
      const gun = getWalker(s, 's0w0').items[0];
      const { events } = applyAction(s, { type: 'fire', itemUid: gun.uid, targetId: 's1w0' });
      const roll = events.find((e) => e.type === 'roll')!;
      hits += (roll.rolls as number[]).filter((r) => r >= 4).length;
    }
    // TN 4 on 3 dice: expect 1.5 hits per attack
    expect(hits / trials).toBeGreaterThan(1.3);
    expect(hits / trials).toBeLessThan(1.7);
  });

  it('removes armour before structure and conserves damage', () => {
    for (let seed = 1; seed <= 50; seed++) {
      const s = act(setup(walker('Gun', 'striker', { armLeft: ['autocannon'] }), seed), { type: 'activate', walkerId: 's0w0' });
      const before = getWalker(s, 's1w0');
      const gun = getWalker(s, 's0w0').items[0];
      const { state, events } = applyAction(s, { type: 'fire', itemUid: gun.uid, targetId: 's1w0' });
      const after = getWalker(state, 's1w0');
      const toArmour: Record<string, number> = {};
      for (const e of events.filter((e) => e.type === 'hit')) {
        const zone = e.zone as string;
        toArmour[zone] = (toArmour[zone] ?? 0) + (e.damage as number) - (e.structure as number);
      }
      for (const zone of Object.keys(before.armour) as Array<keyof typeof before.armour>) {
        expect(before.armour[zone] - after.armour[zone]).toBe(toArmour[zone] ?? 0);
      }
    }
  });

  it('destroys a war-walker whose core runs out, leaving a wreck and scoring VP', () => {
    let destroyed = 0;
    for (let seed = 1; seed <= 40; seed++) {
      const s = act(setup(walker('Brute', 'striker', { armLeft: ['scattergun'] }), seed), { type: 'activate', walkerId: 's0w0' });
      const t = getWalker(s, 's1w0');
      t.pos = { q: getWalker(s, 's0w0').pos.q + 1, r: t.pos.r };
      t.armour = { coreFront: 0, coreRear: 0, armLeft: 0, armRight: 0, legs: 0 };
      t.structure = { core: 1, armLeft: 1, armRight: 1, legs: 1 };
      t.destroyedLocations = ['armLeft', 'armRight', 'legs'];
      const gun = getWalker(s, 's0w0').items[0];
      const { state } = applyAction(s, { type: 'fire', itemUid: gun.uid, targetId: 's1w0' });
      if (getWalker(state, 's1w0').destroyed) {
        destroyed++;
        expect(state.wrecks).toContain(hexKey(t.pos));
        expect(state.vp[0]).toBe(Math.ceil(t.cost / 4));
      }
    }
    expect(destroyed).toBeGreaterThan(30);
  });

  it('Kinetic Shield spends Reserve to cancel damage', () => {
    const s0 = setup(walker('Brute', 'striker', { armLeft: ['scattergun'] }));
    const t = getWalker(s0, 's1w0');
    t.items.push({ uid: 'shield', id: 'kinetic-shield', location: 'armRight', destroyed: false, ammo: null, uses: null, firedThisActivation: false });
    t.reserve = 2;
    t.pos = { q: getWalker(s0, 's0w0').pos.q + 1, r: t.pos.r };
    const s = act(s0, { type: 'activate', walkerId: 's0w0' });
    const { state, events } = applyAction(s, { type: 'fire', itemUid: getWalker(s, 's0w0').items[0].uid, targetId: 's1w0' });
    const hits = events.filter((e) => e.type === 'hit').length;
    if (hits > 0) expect(getWalker(state, 's1w0').reserve).toBe(Math.max(0, 2 - hits));
  });
});

describe('turn order', () => {
  it('lets the smaller lance pass once per round', () => {
    const s0 = setup();
    getWalker(s0, 's0w2').destroyed = true;
    const s = act(s0, { type: 'pass' });
    expect(s.activeSide).toBe(1);
    const back = act(s, { type: 'activate', walkerId: 's1w0' }, { type: 'endActivation' });
    expect(() => act(back, { type: 'pass' })).toThrow(/Already passed/);
    expect(() => act(setup(), { type: 'pass' })).toThrow(/fewer/);
  });

  it('lets a Tactician activate twice in a row once per Trial', () => {
    const s0 = setup(walker('Tac', 'striker', {}, 'tactician'));
    let s = act(s0, { type: 'activate', walkerId: 's0w0' }, { type: 'endActivation', reactivate: true });
    expect(s.activeSide).toBe(0);
    expect(() => act(s, { type: 'activate', walkerId: 's0w1' })).toThrow(/Tactician/);
    s = act(s, { type: 'activate', walkerId: 's0w0' });
    expect(() => act(s, { type: 'endActivation', reactivate: true })).toThrow(/unused Tactician/);
  });

  it('scores objectives and runs out after 6 rounds', () => {
    let s = setup();
    s.objectives = [{ hex: getWalker(s, 's0w0').pos, vp: 1 }];
    let guard = 0;
    while (s.phase !== 'over' && guard++ < 200) {
      const side = s.activeSide;
      const next = s.walkers.find((w) => w.side === side && !w.destroyed && !w.activated)!;
      s = act(s, { type: 'activate', walkerId: next.id }, { type: 'endActivation' });
    }
    expect(s.phase).toBe('over');
    expect(s.round).toBe(6);
    expect(s.vp).toEqual([6, 0]);
    expect(s.winner).toBe(0);
  });
});

describe('legal actions', () => {
  it('lists only actions that apply', () => {
    const s = act(setup(), { type: 'activate', walkerId: 's0w0' });
    const actions = legalActions(s);
    expect(actions.some((a) => a.type === 'fire')).toBe(true);
    expect(actions.some((a) => a.type === 'move')).toBe(true);
    for (const a of actions) expect(() => applyAction(s, a)).not.toThrow();
  });
});
