import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import { explodeOffsets, kitParents, type Unit } from '../src/model/explode';

const ids = ['kit_pelvis', 'kit_torso', 'kit_helm', 'kit_pauldron_L', 'kit_arm_L', 'kit_forearm_L', 'kit_hand_L', 'kit_thigh_R', 'kit_shin_R', 'kit_foot_R'];

describe('exploded view', () => {
  it('plugs each part into its parent, on the same side', () => {
    const p = kitParents(ids, 'paladin');
    expect(p.get('kit_pelvis')).toBeNull();
    expect(p.get('kit_torso')).toBe('kit_pelvis');
    expect(p.get('kit_helm')).toBe('kit_torso');
    expect(p.get('kit_arm_L')).toBe('kit_pauldron_L');
    expect(p.get('kit_hand_L')).toBe('kit_forearm_L');
    expect(p.get('kit_foot_R')).toBe('kit_shin_R');
  });

  it('climbs past parts a class does not have (the Brute has no arm) and honours the Seer tree', () => {
    const brute = kitParents(['kit_torso', 'kit_pauldron_L', 'kit_forearm_L', 'kit_pelvis'], 'brute');
    expect(brute.get('kit_forearm_L')).toBe('kit_pauldron_L'); // no arm: the nearest ancestor present
    const seer = kitParents(['kit_torso', 'kit_pauldron_L', 'kit_arm_L', 'kit_pelvis'], 'seer');
    expect(seer.get('kit_arm_L')).toBe('kit_torso');
  });

  it('moves each part one step past its parent, so chains fan out', () => {
    const at = (x: number, y: number): THREE.Vector3 => new THREE.Vector3(x, y, 0);
    const units: Unit[] = [
      { id: 'a', parent: null, centre: at(0, 0) },
      { id: 'b', parent: 'a', centre: at(0, 10) },
      { id: 'c', parent: 'b', centre: at(0, 20) },
    ];
    const off = explodeOffsets(units, 3);
    expect(off.get('a')!.length()).toBe(0);
    expect(off.get('b')!.y).toBeCloseTo(3);
    expect(off.get('c')!.y).toBeCloseTo(6);
  });
});
