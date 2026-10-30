import { describe, expect, it } from 'vitest';
import { EQUIPMENT, hitChance, mountableItems, walkerStats } from '../src';
import { walker } from './helpers';

describe('walker stats', () => {
  it('derives stride, armour and slots from the build', () => {
    const s = walkerStats(walker('P', 'brute', { core: ['ablative-plating', 'ablative-plating'], armLeft: ['rail-cannon'] }));
    expect(s.armour.coreFront).toBe(13);
    expect(s.armour.coreRear).toBe(8);
    expect(s.stride).toBe(1);
    expect(s.slotsFree).toEqual({ armLeft: 0, armRight: 2, core: 0, legs: 1 });
  });

  it('sums Pressure to fire everything, with the Gunner discount', () => {
    const w = walker('G', 'brute', { armLeft: ['rail-cannon'], core: ['carapace-gun'] });
    expect(walkerStats(w).alphaPressure).toBe(4);
    expect(walkerStats({ ...w, driver: { command: 0, trait: 'gunner' } }).alphaPressure).toBe(3);
  });

  it('estimates expected damage by range band', () => {
    const s = walkerStats(walker('A', 'scavenger', { armLeft: ['autocannon'] }));
    expect(s.weapons[0].expected).toEqual({ short: 1.5, medium: 1 });
    expect(hitChance(6)).toBeCloseTo(1 / 6);
  });

  it('filters items by location', () => {
    const legs = mountableItems('legs', EQUIPMENT).map((e) => e.id);
    expect(legs).toContain('jump-jets');
    expect(legs).toContain('ablative-plating');
    expect(legs).not.toContain('autocannon');
  });
});
