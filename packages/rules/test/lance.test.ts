import { describe, expect, it } from 'vitest';
import examples from '../../../data/lances/examples.json';
import { armItemLimit, getChassis, getEquipment, getFaction, hasEquipment, validateLance, validateWalker, walkerCost, type LanceInput } from '../src';
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

  it('has cut the five items that had no model to fit (Hellfire Missiles came back as Seer body equipment)', () => {
    for (const id of ['melee-blade', 'anchor-spikes', 'jump-jets', 'overcharged-boiler', 'field-repair-rig']) {
      expect(hasEquipment(id), id).toBe(false);
    }
  });

  it('lets a Brute or Seer arm carry one item only, since it has one socket (the Paladin still takes two)', () => {
    const errors = (w: ReturnType<typeof walker>) => validateWalker(w);
    expect(errors(walker('B', 'brute', { armLeft: ['autocannon', 'autocannon'] })).join('\n')).toMatch(/armLeft holds 2 items/);
    expect(errors(walker('S', 'seer', { armRight: ['arc-cannon', 'kinetic-claws'] })).join('\n')).toMatch(/armRight holds 2 items/);
    expect(errors(walker('B', 'brute', { armLeft: ['rail-cannon'], armRight: ['industrial-claw'] }))).toEqual([]);
    expect(errors(walker('P', 'paladin', { armLeft: ['lance', 'kinetic-shield'] }))).toEqual([]);
    expect(armItemLimit(getChassis('brute'), 'armLeft')).toBe(1);
    expect(armItemLimit(getChassis('brute'), 'core')).toBeUndefined();
    expect(armItemLimit(getChassis('paladin'), 'armLeft')).toBeUndefined();
  });

  it('shows the Siege Blade and Arc Spear names, with the old ids', () => {
    expect(getEquipment('lance').name).toBe('Siege Blade');
    expect(getEquipment('arc-cannon').name).toBe('Arc Spear');
  });

  it('mounts the Missile Rack on an arm that has 2 free slots', () => {
    expect(getEquipment('missile-rack').mount).toEqual(['arm']);
    expect(validateLance(lance('Rack', [walker('A', 'sentinel', { armLeft: ['missile-rack'] }), walker('B', 'paladin', { armRight: ['missile-rack'] }), walker('C', 'sentinel')])).errors.join('\n')).not.toMatch(/Missile Rack/);
    // the Sentinel arm has 2 slots: a rack fills it, so a Carapace Gun on the same arm is one slot too many
    expect(validateWalker(walker('A', 'sentinel', { armLeft: ['missile-rack', 'carapace-gun'] }), 'covenant').join('\n')).toMatch(/armLeft uses 3 slots/);
    expect(validateWalker(walker('A', 'scavenger', { armLeft: ['missile-rack'] }), null).join('\n')).toMatch(/armLeft uses 2 slots but Scavenger has 1/);
    expect(validateWalker(walker('B', 'sentinel', { core: ['missile-rack'] }), 'covenant').join('\n')).toMatch(/cannot be mounted in core/);
  });

  it('mounts the Hellfire Missiles on the core, so they take no arm slot', () => {
    expect(getEquipment('hellfire-missiles').mount).toEqual(['core']);
    expect(validateLance(lance('Fire', [walker('A', 'seer', { core: ['hellfire-missiles'] }), walker('B', 'seer'), walker('C', 'seer')])).errors.join('\n')).not.toMatch(/Hellfire/);
    expect(validateLance(lance('Fire', [walker('A', 'seer', { armRight: ['hellfire-missiles'] }), walker('B', 'seer'), walker('C', 'seer')])).errors.join('\n')).toMatch(/cannot be mounted in armRight/);
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
