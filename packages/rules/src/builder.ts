// Derived numbers for a war-walker build, for the lance builder and unit cards.
import { LOCATIONS, getChassis, getEquipment, type EquipmentDef, type Location, type RangeBand } from './data';
import type { WalkerInput } from './lance';
import type { Zone } from './types';

export interface WeaponSummary {
  id: string;
  name: string;
  location: Location;
  dice: number;
  damage: number;
  range: RangeBand;
  pressure: number;
  /** Expected damage per attack at base TN for each band it can reach (before armour). */
  expected: Partial<Record<RangeBand, number>>;
}

export interface WalkerStats {
  stride: number;
  sprintStride: number;
  boiler: number;
  armour: Record<Zone, number>;
  structure: Record<Location, number>;
  slotsUsed: Record<Location, number>;
  slotsFree: Record<Location, number>;
  weapons: WeaponSummary[];
  /** Pressure to fire every weapon once. */
  alphaPressure: number;
  /** Pressure to move once and fire every weapon once. */
  fullTurnPressure: number;
  faultThreshold: number;
}

const BAND_TN: Record<RangeBand, number> = { melee: 4, short: 4, medium: 5, long: 6 };
const BANDS: RangeBand[] = ['melee', 'short', 'medium', 'long'];

/** Chance one die hits at a TN (a 6 always hits, a 1 always misses). */
export const hitChance = (tn: number) => (7 - Math.min(6, Math.max(2, tn))) / 6;

export function walkerStats(input: WalkerInput): WalkerStats {
  const c = getChassis(input.chassis);
  const fitted: Array<{ def: EquipmentDef; location: Location }> = [];
  for (const loc of LOCATIONS) for (const id of input.loadout[loc] ?? []) fitted.push({ def: getEquipment(id), location: loc });
  const has = (id: string) => fitted.some((f) => f.def.id === id);
  const gunner = input.driver.trait === 'gunner';

  const armour: Record<Zone, number> = {
    coreFront: c.armour.coreFront,
    coreRear: c.armour.coreRear,
    armLeft: c.armour.arm,
    armRight: c.armour.arm,
    legs: c.armour.legs,
  };
  for (const f of fitted.filter((f) => f.def.id === 'ablative-plating')) {
    if (f.location === 'core') {
      armour.coreFront += 2;
      armour.coreRear += 2;
    } else armour[f.location] += 2;
  }
  const plating = fitted.filter((f) => f.def.id === 'ablative-plating').length;
  const stride = Math.max(1, c.stride - (plating >= 2 ? 1 : 0));

  const slotsUsed = { armLeft: 0, armRight: 0, core: 0, legs: 0 } as Record<Location, number>;
  for (const f of fitted) slotsUsed[f.location] += f.def.slots;
  const slotsFree = Object.fromEntries(LOCATIONS.map((l) => [l, c.slots[l] - slotsUsed[l]])) as Record<Location, number>;

  const tnBonus = has('targeting-array') ? -1 : 0;
  const weapons: WeaponSummary[] = fitted
    .filter((f) => f.def.weapon)
    .map(({ def, location }) => {
      const wp = def.weapon!;
      const reach = wp.range === 'melee' ? ['melee'] : BANDS.slice(1, BANDS.indexOf(wp.range) + 1);
      const expected: Partial<Record<RangeBand, number>> = {};
      for (const band of reach as RangeBand[]) {
        if (wp.minRange && band === 'short') continue;
        expected[band] = Math.round(wp.dice * hitChance(BAND_TN[band] + tnBonus) * wp.damage * 10) / 10;
      }
      return { id: def.id, name: def.name, location, dice: wp.dice, damage: wp.damage, range: wp.range, pressure: def.pressure, expected };
    });
  const pressures = weapons.map((w) => w.pressure).sort((a, b) => b - a);
  if (gunner && pressures.length) pressures[0] = Math.max(0, pressures[0] - 1);
  const alphaPressure = pressures.reduce((a, b) => a + b, 0);

  let threshold = 3;
  if (input.driver.trait === 'iron-nerve') threshold += 1;

  return {
    stride,
    sprintStride: stride + (has('sprint-servos') ? 1 : 0),
    boiler: c.boiler,
    armour,
    structure: { core: c.structure.core, armLeft: c.structure.other, armRight: c.structure.other, legs: c.structure.other },
    slotsUsed,
    slotsFree,
    weapons,
    alphaPressure,
    fullTurnPressure: alphaPressure + 1,
    faultThreshold: threshold,
  };
}

/** Items that could go in a location of this chassis, whether or not they fit right now. */
export function mountableItems(location: Location, all: EquipmentDef[]): EquipmentDef[] {
  const mount = location === 'core' ? 'core' : location === 'legs' ? 'legs' : 'arm';
  return all.filter((e) => e.mount.includes('any') || e.mount.includes(mount));
}
