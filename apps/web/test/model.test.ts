import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import chassisData from '../../../data/chassis.json';
import equipmentData from '../../../data/equipment.json';
import { LOCATIONS, type Location, type WalkerInput } from '@brass-charter/rules';
import { buildWalkerModel } from '../src/model/assemble';
import { isCardOnly } from '../src/model/fit';
import { stlBytes } from '../src/model/exporters';
import { PARTS, baseMm, buildChassis, makePalette } from '../src/model/parts';

const chassis = chassisData.chassis as Array<{ id: string; slots: Record<Location, number> }>;

describe('walker models', () => {
  it('has a part for every item that has a model', () => {
    for (const item of equipmentData.equipment) {
      if (isCardOnly(item.id)) expect(PARTS[item.id], `${item.id} is card-only`).toBeUndefined();
      else expect(PARTS[item.id], item.id).toBeTypeOf('function');
    }
  });

  it('shows no model for card-only items', () => {
    const base = { name: 'Test', chassis: 'paladin', driver: { command: 0, trait: null } };
    const plain = new THREE.Box3().setFromObject(buildWalkerModel({ ...base, loadout: {} } as WalkerInput, '#1f5c63'));
    const kitted = new THREE.Box3().setFromObject(
      buildWalkerModel({ ...base, loadout: { core: ['targeting-array'], legs: ['gyro-stabilisers'] } } as WalkerInput, '#1f5c63'),
    );
    expect(kitted.equals(plain)).toBe(true);
  });

  for (const c of chassis) {
    it(`${c.id} has a mount for every slot and stands on its base`, () => {
      const { root, mounts } = buildChassis(c.id, c.slots, makePalette('#7a2e22'));
      for (const loc of LOCATIONS) {
        expect(mounts[loc].filter(Boolean).length, `${c.id} ${loc}`).toBe(c.slots[loc]);
      }
      const box = new THREE.Box3().setFromObject(root);
      expect(box.min.y).toBeCloseTo(0, 1);
      expect(box.max.y).toBeGreaterThan(baseMm(c.id) * 0.6);
    });

    it(`${c.id} exports an STL with every slot filled`, () => {
      const loadout: WalkerInput['loadout'] = {};
      for (const loc of LOCATIONS) loadout[loc] = Array(c.slots[loc]).fill(loc === 'core' ? 'carapace-gun' : 'autocannon');
      const walker = { name: c.id, chassis: c.id, driver: { command: 0, trait: null }, loadout } as WalkerInput;
      const bytes = stlBytes(buildWalkerModel(walker, '#1f5c63'));
      expect(bytes.byteLength).toBeGreaterThan(10_000);
    });
  }
});
