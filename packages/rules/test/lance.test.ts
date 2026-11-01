import { describe, expect, it } from 'vitest';
import examples from '../../../data/lances/examples.json';
import { getFaction, validateLance, walkerCost, type LanceInput } from '../src';
import { lance, walker } from './helpers';

describe('lance building', () => {
  it('accepts every example lance at 95 to 100 points', () => {
    for (const l of examples.lances as LanceInput[]) {
      const report = validateLance(l);
      expect(report.errors).toEqual([]);
      expect(report.total).toBeGreaterThanOrEqual(95);
      expect(report.total).toBeLessThanOrEqual(100);
    }
  });

  it('applies faction discounts', () => {
    const w = walker('Plated', 'brute', { core: ['ablative-plating'] });
    expect(walkerCost(w, null)).toBe(17);
    expect(walkerCost(w, getFaction('foundries'))).toBe(16);
    const knight = walker('Sworn', 'lancer', {}, 'brawler');
    expect(walkerCost(knight, null)).toBe(19);
    expect(walkerCost(knight, getFaction('covenant'))).toBe(18);
  });

  it('keeps classes and signature gear inside their faction', () => {
    const report = validateLance(
      lance('Mixed', [
        walker('Knight', 'lancer', { armLeft: ['lance'], core: ['smoke-launcher'] }),
        walker('Thief', 'lancer', { armLeft: ['kinetic-claws'] }),
        walker('Turncoat', 'scavenger'),
      ]),
    );
    expect(report.errors).toEqual(['Thief: Kinetic Claws is Reliquary gear', 'Turncoat: Scavenger is not a Iron Covenant class']);
  });

  it('rejects illegal builds', () => {
    const report = validateLance(
      lance('Bad', [
        walker('Overfull', 'scavenger', { armLeft: ['missile-rack'] }),
        walker('Wrong mount', 'scavenger', { legs: ['autocannon'] }),
        walker('Double array', 'brute', { core: ['targeting-array', 'targeting-array'] }),
      ]),
    );
    expect(report.errors.join('\n')).toMatch(/armLeft uses 2 slots/);
    expect(report.errors.join('\n')).toMatch(/cannot be mounted in legs/);
    expect(report.errors.join('\n')).toMatch(/fitted 2 times/);
  });

  it('enforces lance size and budget', () => {
    const paladins = Array.from({ length: 5 }, (_, i) => walker(`P${i}`, 'paladin', { armLeft: ['lance'], armRight: ['lance'] }));
    const report = validateLance(lance('Heavy', paladins));
    expect(report.errors).toContain('costs 210 points, budget is 100');
    expect(validateLance(lance('Tiny', [walker('S', 'scavenger')])).errors[0]).toMatch(/needs 3-5/);
  });
});
