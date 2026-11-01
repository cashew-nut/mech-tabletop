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
    expect(migrateLance(saved).walkers[0].loadout).toEqual({ armLeft: ['lance'], armRight: [], legs: [], core: ['carapace-gun'] });
  });

  it('drops a cut item reached through an old rename', () => {
    const saved = {
      name: 'Older',
      company: 'halvorsen',
      walkers: [{ name: 'A', chassis: 'striker', driver: { command: 0, trait: null }, loadout: { armLeft: ['shear-blade', 'hellfire-missiles'] } }],
    } as unknown as LanceInput;
    expect(migrateLance(saved).walkers[0].loadout.armLeft).toEqual([]);
  });
});
