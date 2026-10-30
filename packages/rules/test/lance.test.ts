import { describe, expect, it } from 'vitest';
import examples from '../../../data/lances/examples.json';
import { validateLance, walkerCost, type LanceInput } from '../src';
import { lance, walker } from './helpers';

describe('lance building', () => {
  it('accepts every example lance at exactly 100 points', () => {
    for (const l of examples.lances as LanceInput[]) {
      const report = validateLance(l);
      expect(report.errors).toEqual([]);
      expect(report.total).toBe(100);
    }
  });

  it('applies Company discounts', () => {
    const w = walker('Plated', 'striker', { core: ['ablative-plating'] });
    expect(walkerCost(w, null)).toBe(20);
    expect(walkerCost(w, { id: 'halvorsen', name: '', specialty: '', doctrine: '', pointModifiers: { 'ablative-plating': -1 } })).toBe(19);
  });

  it('rejects illegal builds', () => {
    const report = validateLance(
      lance('Bad', [
        walker('Overfull', 'scout', { armLeft: ['missile-rack'] }),
        walker('Wrong mount', 'scout', { legs: ['autocannon'] }),
        walker('Double array', 'titan', { core: ['targeting-array', 'targeting-array'] }),
      ]),
    );
    expect(report.errors.join('\n')).toMatch(/armLeft uses 2 slots/);
    expect(report.errors.join('\n')).toMatch(/cannot be mounted in legs/);
    expect(report.errors.join('\n')).toMatch(/fitted 2 times/);
  });

  it('enforces lance size and budget', () => {
    const titans = Array.from({ length: 4 }, (_, i) => walker(`T${i}`, 'titan'));
    const report = validateLance(lance('Heavy', titans));
    expect(report.errors).toContain('costs 128 points, budget is 100');
    expect(validateLance(lance('Tiny', [walker('S', 'scout')])).errors[0]).toMatch(/needs 3-5/);
  });
});
