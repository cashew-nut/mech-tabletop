import { describe, expect, it } from 'vitest';
import { migrateLance } from '../src/storage';
import type { LanceInput } from '@brass-charter/rules';

describe('saved lances', () => {
  it('drop the items cut from the game and keep the rest', () => {
    const saved = {
      name: 'Old',
      faction: 'covenant',
      walkers: [{ name: 'Vigil', chassis: 'lancer', driver: { command: 0, trait: null }, loadout: { armLeft: ['lance'], armRight: ['melee-blade'], legs: ['jump-jets'], core: ['carapace-gun'] } }],
    } as LanceInput;
    expect(migrateLance(saved).walkers[0].loadout).toEqual({ armLeft: ['lance', 'carapace-gun'], armRight: [], legs: [], core: [] });
  });

  it('moves a core Carapace Gun to the first arm with room and leaves it in the core when there is none', () => {
    const walker = (chassis: string, loadout: Record<string, string[]>) => ({ name: 'W', chassis, driver: { command: 0, trait: null }, loadout });
    const saved = {
      name: 'Gunners',
      faction: 'covenant',
      walkers: [
        walker('sentinel', { core: ['carapace-gun', 'reactive-shell'] }),
        walker('sentinel', { armLeft: ['lance'], armRight: ['lance'], core: ['carapace-gun'] }),
      ],
    } as unknown as LanceInput;
    const [free, full] = migrateLance(saved).walkers;
    expect(free.loadout).toEqual({ core: ['reactive-shell'], armLeft: ['carapace-gun'] });
    expect(full.loadout).toEqual({ armLeft: ['lance'], armRight: ['lance'], core: ['carapace-gun'] });
  });

  it('drops a cut item reached through an old rename', () => {
    const saved = {
      name: 'Older',
      company: 'halvorsen',
      walkers: [{ name: 'A', chassis: 'striker', driver: { command: 0, trait: null }, loadout: { armLeft: ['shear-blade', 'anchor-spikes'] } }],
    } as unknown as LanceInput;
    expect(migrateLance(saved).walkers[0].loadout.armLeft).toEqual([]);
  });
});
