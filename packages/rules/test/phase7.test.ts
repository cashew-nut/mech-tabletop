import { describe, expect, it } from 'vitest';
import {
  SURVEYOR_ID,
  applyAction,
  createGame,
  deployable,
  deploymentZone,
  getWalker,
  hexToOffset,
  legalActions,
  neighbors,
  offsetToHex,
  type Action,
  type GameState,
} from '../src';
import { lance, walker } from './helpers';

const act = (s: GameState, ...actions: Action[]) => actions.reduce((st, a) => applyAction(st, a).state, s);
const trio = (p: string) => [walker(`${p}1`, 'scout'), walker(`${p}2`, 'scout'), walker(`${p}3`, 'scout')];

const alternate = (companies: [string, string] = ['halvorsen', 'meridian'], seed = 3) =>
  createGame({
    seed,
    scenario: 'hold-the-field',
    map: 'open-field',
    lances: [lance('A', trio('A'), companies[0]), lance('B', trio('B'), companies[1])],
    deploy: 'alternate',
  });

/** Deploy whatever the side to move can, into the first free hex of its zone. */
function deployAll(s: GameState): { state: GameState; order: number[] } {
  const order: number[] = [];
  while (s.phase === 'deployment') {
    const deploy = legalActions(s)[0] as Extract<Action, { type: 'deploy' }>;
    order.push(s.activeSide);
    s = act(s, deploy);
  }
  return { state: s, order };
}

describe('alternating deployment', () => {
  it('starts in a deployment phase with nobody on the map', () => {
    const s = alternate();
    expect(s.phase).toBe('deployment');
    expect(s.walkers).toHaveLength(0);
    expect(s.undeployed).toHaveLength(6);
  });

  it('alternates sides, then starts round 1', () => {
    const { state, order } = deployAll(alternate());
    expect(order).toHaveLength(6);
    for (let i = 1; i < order.length; i++) expect(order[i]).not.toBe(order[i - 1]);
    expect(state.phase).toBe('activation');
    expect(state.round).toBe(1);
    expect(state.walkers).toHaveLength(6);
  });

  it('only allows hexes in the deployment zone', () => {
    const s = alternate();
    const w = deployable(s)[0];
    const far = s.activeSide === 0 ? { col: 4, row: 8 } : { col: 4, row: 1 };
    expect(() => act(s, { type: 'deploy', walkerId: w.id, hex: offsetToHex(far) })).toThrow(/deployment zone/);
    const rows = deploymentZone(s, s.activeSide).map((h) => hexToOffset(h).row);
    expect(new Set(rows).size).toBe(3);
  });

  it('refuses other actions until deployment is done', () => {
    const s = alternate();
    expect(() => act(s, { type: 'pass' })).toThrow(/deploy first/);
  });

  it('makes Calloway & Vane place their last war-walker after the enemy', () => {
    for (const seed of [1, 2, 3, 4]) {
      const { order } = deployAll(alternate(['calloway-vane', 'halvorsen'], seed));
      expect(order[order.length - 1]).toBe(0);
      expect(order.slice(0, -1).filter((x) => x === 1)).toHaveLength(3);
    }
  });

  it('cancels out when both sides are Calloway & Vane', () => {
    const { state, order } = deployAll(alternate(['calloway-vane', 'calloway-vane']));
    expect(order).toHaveLength(6);
    expect(state.phase).toBe('activation');
  });
});

describe('Surveyor Escort', () => {
  const escortGame = () => {
    const s = createGame({
      seed: 5,
      scenario: 'surveyor-escort',
      map: 'open-field',
      lances: [lance('A', trio('A')), lance('B', trio('B'))],
      deployments: [
        [{ col: 7, row: 1 }, { col: 0, row: 0 }, { col: 1, row: 0 }],
        [{ col: 7, row: 4, facing: 2 }, { col: 15, row: 11 }, { col: 14, row: 11 }],
      ],
    });
    s.activeSide = 0;
    return s;
  };

  it('places the surveyor in side 0 zone and blocks the hex', () => {
    const s = escortGame();
    expect(s.surveyor).toMatchObject({ side: 0, hp: 5, status: 'active' });
    expect(hexToOffset(s.surveyor!.pos)).toEqual({ col: 7, row: 2 });
  });

  it('moves 2 hexes for 1 Pressure when an adjacent friend escorts it', () => {
    let s = act(escortGame(), { type: 'activate', walkerId: 's0w0' });
    const escorts = legalActions(s).filter((a) => a.type === 'escort');
    expect(escorts.length).toBeGreaterThan(0);
    const before = s.active!.pressure;
    const sv = s.surveyor!.pos;
    const step1 = neighbors(sv).find((n) => hexToOffset(n).row === 3 && hexToOffset(n).col === 6)!;
    const step2 = neighbors(step1).find((n) => hexToOffset(n).row === 4 && hexToOffset(n).col === 6)!;
    s = act(s, { type: 'escort', path: [step1, step2] });
    expect(s.active!.pressure).toBe(before - 1);
    expect(hexToOffset(s.surveyor!.pos)).toEqual({ col: 6, row: 4 });
  });

  it('cannot be escorted by an enemy or from a distance', () => {
    const s = act(escortGame(), { type: 'activate', walkerId: 's0w1' });
    const path = [neighbors(s.surveyor!.pos)[0]];
    expect(() => act(s, { type: 'escort', path })).toThrow(/next to the surveyor/);
  });

  it('scores for side 0 when it reaches the far edge', () => {
    const s0 = escortGame();
    s0.surveyor!.pos = offsetToHex({ col: 3, row: 9 });
    getWalker(s0, 's0w0').pos = offsetToHex({ col: 3, row: 8 });
    let s = act(s0, { type: 'activate', walkerId: 's0w0' });
    const step1 = offsetToHex({ col: 3, row: 10 });
    const step2 = neighbors(step1).find((n) => hexToOffset(n).row === 11)!;
    s = act(s, { type: 'escort', path: [step1, step2] });
    expect(s.surveyor!.status).toBe('exited');
    expect(s.vp[0]).toBe(6);
  });

  it('can be shot by side 1 and gives 4 VP when destroyed', () => {
    const s0 = escortGame();
    s0.activeSide = 1;
    s0.surveyor!.hp = 1; // one hit left
    const b = getWalker(s0, 's1w0');
    b.items.push({ uid: 'x', id: 'autocannon', location: 'armLeft', destroyed: false, ammo: 6, uses: null, firedThisActivation: false });
    let s = act(s0, { type: 'activate', walkerId: 's1w0' });
    const shot = legalActions(s).find((a) => a.type === 'fire' && a.targetId === SURVEYOR_ID);
    expect(shot).toBeDefined();
    for (let i = 0; i < 6 && s.surveyor!.status === 'active'; i++) {
      s.walkers.find((w) => w.id === 's1w0')!.items.forEach((it) => (it.firedThisActivation = false));
      s.active!.pressure = 9;
      s = act(s, shot!);
    }
    expect(s.surveyor!.status).toBe('destroyed');
    expect(s.vp[1]).toBe(4);
  });
});
