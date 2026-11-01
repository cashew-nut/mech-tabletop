import { describe, expect, it } from 'vitest';
import chassisJson from '../../../data/chassis.json';
import partsJson from '../../../data/parts.json';
import cardsJson from '../../../data/cards.json';
import equipmentJson from '../../../data/equipment.json';

type Stats = Record<string, number | Record<string, number>>;
interface Part { id: string; class: string; slot: string; faction: string; frame: string; frameSize: number; stats: Stats }
interface Card { printId: string; kind: string; partId?: string; itemId?: string; tier: number; faction: string; frameSize: number | null; stats: Stats; statsPlaceholder: boolean; slot?: string }

const parts = partsJson.parts as unknown as Part[];
const cards = cardsJson.cards as unknown as Card[];
const chassis = chassisJson.chassis;

/** Flatten nested stats to dotted keys, such as armour.coreFront. */
const flat = (s: Record<string, unknown>, prefix = ''): Record<string, number> =>
  Object.entries(s).reduce<Record<string, number>>((out, [k, v]) => {
    if (typeof v === 'number') out[prefix + k] = v;
    else if (v && typeof v === 'object' && !Array.isArray(v)) Object.assign(out, flat(v as Record<string, unknown>, `${prefix}${k}.`));
    return out;
  }, {});

const SLOTS = partsJson.slots.map((s) => s.id);
const SUMMED = ['points', 'stride', 'boiler', 'slots.armLeft', 'slots.armRight', 'slots.core', 'slots.legs', 'armour.coreFront', 'armour.coreRear', 'armour.arm', 'armour.legs', 'structure.core', 'structure.other'];

describe('body part cards', () => {
  it('splits every class into the six body parts', () => {
    expect(SLOTS).toEqual(['legs', 'torso', 'helm', 'pauldrons', 'arms', 'crown-back']);
    expect(parts).toHaveLength(chassis.length * 6);
    for (const c of chassis) expect(parts.filter((p) => p.class === c.id).map((p) => p.slot)).toEqual(SLOTS);
    expect(new Set(parts.map((p) => p.id)).size).toBe(parts.length);
  });

  for (const c of chassis) {
    describe(c.id, () => {
      const mine = parts.filter((p) => p.class === c.id);

      it('sums exactly to chassis.json', () => {
        const total: Record<string, number> = {};
        for (const p of mine) for (const [k, v] of Object.entries(flat(p.stats))) total[k] = (total[k] ?? 0) + v;
        expect(Object.keys(total).sort()).toEqual([...SUMMED].sort());
        expect(total).toEqual(flat({ points: c.points, stride: c.stride, boiler: c.boiler, slots: c.slots, armour: c.armour, structure: c.structure }));
      });

      it('shares the class faction, frame and frame size on all six parts', () => {
        for (const p of mine) expect([p.faction, p.frame, p.frameSize]).toEqual([c.faction, c.frame, c.size]);
      });

      it('has no negative or fractional stats', () => {
        for (const p of mine) for (const v of Object.values(flat(p.stats))) expect(Number.isInteger(v) && v >= 0).toBe(true);
      });
    });
  }
});

describe('card records', () => {
  const partById = new Map(parts.map((p) => [p.id, p]));
  const body = cards.filter((c) => c.kind === 'body');

  it('prints a unique id on every card', () => {
    expect(new Set(cards.map((c) => c.printId)).size).toBe(cards.length);
    for (const c of cards) expect(c.printId).toMatch(/^[A-Z]{2}-[A-Z]{2,3}-[A-Z]{3,5}(-T[1-5])$/);
  });

  it('covers all five tiers for three example parts, in order', () => {
    const tiersOf = (id: string) => body.filter((c) => c.partId === id).map((c) => c.tier);
    const full = parts.map((p) => p.id).filter((id) => tiersOf(id).length === 5);
    expect(full).toHaveLength(3);
    for (const id of full) expect(tiersOf(id)).toEqual([1, 2, 3, 4, 5]);
    expect(cardsJson.tiers.map((t) => t.tier)).toEqual([1, 2, 3, 4, 5]);
  });

  it('keeps tier 1 equal to the part and flags higher tiers as placeholders', () => {
    for (const c of body) {
      const part = partById.get(c.partId!)!;
      expect(part).toBeDefined();
      expect([c.faction, c.frameSize, c.slot]).toEqual([part.faction, part.frameSize, part.slot]);
      if (c.tier === 1) expect(c.stats).toEqual(part.stats);
      expect(c.statsPlaceholder).toBe(c.tier > 1);
    }
  });

  it('never lowers a stat at a higher tier', () => {
    for (const c of body.filter((x) => x.tier > 1)) {
      const base = flat(partById.get(c.partId!)!.stats);
      for (const [k, v] of Object.entries(flat(c.stats))) expect(v).toBeGreaterThanOrEqual(base[k] ?? 0);
    }
  });

  it('copies equipment stats from equipment.json', () => {
    const items = cards.filter((c) => c.kind === 'equipment');
    expect(items.length).toBeGreaterThanOrEqual(4);
    for (const c of items) {
      const e = equipmentJson.equipment.find((x) => x.id === c.itemId)!;
      expect(e).toBeDefined();
      expect(c.frameSize).toBeNull();
      expect([c.stats.slots, c.stats.points, c.stats.pressure]).toEqual([e.slots, e.points, e.pressure]);
    }
  });
});
