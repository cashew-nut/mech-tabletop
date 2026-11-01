import { describe, expect, it } from 'vitest';
import equipmentData from '../../../data/equipment.json';
import chassisData from '../../../data/chassis.json';
import { FIT, fitClass, hardpoint, planLocation, pivotOf, poseOf } from '../src/model/fit';

const names = (plan: ReturnType<typeof planLocation>) => plan.map((p) => p?.map((x) => (x.side ? `${x.hp}:${x.side}` : x.hp)).join('+') ?? null);

describe('equipment fit', () => {
  it('only the built classes use hardpoints', () => {
    for (const id of ['paladin', 'brute', 'seer']) expect(fitClass(id), id).not.toBeNull();
    for (const id of ['lancer', 'sentinel', 'scavenger', 'artillery', 'wraith', 'goliath']) expect(fitClass(id), id).toBeNull();
  });

  it('puts a second weapon after a two-slot weapon on the forearm, not the shoulder', () => {
    expect(names(planLocation('brute', 'armLeft', ['rocket-pod', 'kinetic-shield']))).toEqual(['grip:L', 'bracer:L']);
    expect(names(planLocation('brute', 'armRight', ['rail-cannon', 'autocannon']))).toEqual(['grip:R', 'forearm-top:R']);
  });

  it('fills the arm ladder in order and uses the right side', () => {
    expect(names(planLocation('paladin', 'armRight', ['lance', 'melee-blade', 'missile-rack']))).toEqual(['grip:R', 'forearm-top:R', 'shoulder-top:R']);
    expect(names(planLocation('paladin', 'armRight', ['lance', 'melee-blade', 'missile-rack', 'lance']))[3]).toBeNull();
  });

  it('spreads core items over different hardpoints, away from the neck', () => {
    const plan = names(planLocation('seer', 'core', ['carapace-gun', 'reactive-shell', 'ablative-plating', 'coolant-loop']));
    expect(plan).toEqual(['shoulder-top-L:L', 'chest-front', 'back-high', 'back-low']);
    expect(new Set(plan).size).toBe(plan.length);
  });

  it('puts leg gear on both legs from one slot', () => {
    expect(names(planLocation('paladin', 'legs', ['jump-jets']))).toEqual(['calf-back:L+calf-back:R']);
  });

  it('gives an unknown item no placement, so it falls back to the numbered mounts', () => {
    expect(planLocation('brute', 'core', ['not-an-item'])).toEqual([null]);
  });

  it('describes every item for every location it can mount in', () => {
    const kinds: Record<string, 'arm' | 'core' | 'legs'> = { arm: 'arm', core: 'core', legs: 'legs' };
    for (const e of equipmentData.equipment) {
      const mounts = e.mount.includes('any') ? ['arm', 'core', 'legs'] : e.mount;
      for (const m of mounts) {
        const prefs = FIT.items[e.id]?.[kinds[m]];
        expect(prefs?.length, `${e.id} ${m}`).toBeGreaterThan(0);
      }
    }
  });

  it('only names hardpoints that exist, and every class has its overrides section', () => {
    for (const [id, item] of Object.entries(FIT.items)) {
      for (const k of ['arm', 'core', 'legs'] as const) for (const hp of item[k] ?? []) expect(FIT.hardpoints[hp], `${id} ${hp}`).toBeDefined();
    }
    for (const id of Object.keys(FIT.classes)) {
      expect(FIT.overrides[id], id).toBeDefined();
      expect(chassisData.chassis.some((c) => c.id === id), id).toBe(true);
    }
    expect(hardpoint("paladin", "grip-native")?.mount).toBeDefined();
  });

  it('measures a contact face from the item bounds', () => {
    // A plate's back face is its smallest z, a hung item's top face is its largest y.
    const back = pivotOf('reactive-shell', ['back']);
    expect(back[2]).toBeCloseTo(-0.41, 1);
    expect(pivotOf('soul-lantern', ['top'])[1]).toBeGreaterThan(5);
    expect(poseOf('soul-lantern', 'waist-L').contact).toEqual(['top']);
  });
});
