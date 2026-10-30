import { createGame, getChassis, type Deployment, type GameState, type LanceInput, type WalkerInput } from '../src';

export const walker = (name: string, chassis: string, loadout: WalkerInput['loadout'] = {}, trait: string | null = null): WalkerInput => ({
  name,
  chassis,
  driver: { command: 0, trait },
  loadout,
});

/** A lance swears to the faction of its first war-walker unless told otherwise. */
export const lance = (name: string, walkers: WalkerInput[], faction = walkers[0] ? getChassis(walkers[0].chassis).faction : 'foundries'): LanceInput => ({
  name,
  faction,
  walkers,
});

/** A game on the open map with fixed deployments; side 0 activates first. */
export function duel(
  a: WalkerInput[],
  b: WalkerInput[],
  deployments: [Deployment[], Deployment[]],
  seed = 1,
): GameState {
  const state = createGame({
    seed,
    scenario: 'hold-the-field',
    map: 'open-field',
    lances: [lance('A', a), lance('B', b)],
    deployments,
  });
  state.activeSide = 0;
  state.objectives = [];
  return state;
}

/** Three cheap filler walkers so a lance meets the 3-walker minimum. */
export const fillers = (prefix: string) => [walker(`${prefix}1`, 'scavenger'), walker(`${prefix}2`, 'scavenger')];
