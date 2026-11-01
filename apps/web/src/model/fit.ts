// Where equipment sits on a walker: named hardpoints instead of numbered mounts.
//
// Only the classes listed in data/model-kit.json "fit.classes" use this (the ones with full models: Paladin, Brute,
// Seer). Each item names the hardpoints it prefers per location; the planner gives it the first free one. Hardpoints
// are a kit joint plus an offset in fractions of body height, so they follow each body. An item's own "contact" face
// (measured bounds in data/item-bounds.json) is what touches the hardpoint, so plates sit flush and hung gear hangs.
// Anything the planner cannot place falls back to the numbered mounts.
import kitData from '../../../../data/model-kit.json';
import boundsData from '../../../../data/item-bounds.json';

export type Side = 'L' | 'R';
export type Kind = 'arm' | 'core' | 'legs';
export type Contact = 'back' | 'front' | 'bottom' | 'top' | 'center';

export interface HardpointDef {
  /** A kit joint (`elbow`, `chest`); sided joints take their side from `side`. */
  joint?: string;
  /** A numbered mount of the frame, `{loc}` being armLeft or armRight. Keeps the tuned grip of the Meshy bodies. */
  mount?: string;
  /** Fractions of body height: x outward (to the walker's left), y up, z forward. */
  offset?: [number, number, number];
  /** `loc`: the side of the arm it is on; `pair`: one on each side; `L` or `R`: that side; none: centre. */
  side?: 'loc' | 'pair' | Side;
  /** Degrees. Back-facing hardpoints turn the item to face away from the body. */
  rot?: [number, number, number];
  pair?: boolean;
  /** The item face that lands here when the item's own pose names none (the Brute's elbow socket takes the item's back). */
  contact?: Contact[];
  /** Hardpoints this one fills too: the Brute's elbow socket holds one forearm, gun (grip-native) or not (grip). */
  blocks?: string[];
}

export interface ItemFit {
  arm?: string[];
  core?: string[];
  legs?: string[];
  pose?: Record<string, { contact?: Contact[]; rot?: [number, number, number]; scale?: number }>;
}

/** A hand adjustment of one item at one hardpoint of one body, made with the sliders in place.html. */
export interface Nudge {
  /** Fractions of body height, in the hardpoint's axes (x outward, y up, z forward), like hardpoint offsets. */
  offset?: [number, number, number];
  /** Degrees, turning the item about its contact point in the hardpoint's axes. */
  rot?: [number, number, number];
  /** Multiplies the item's size about its contact point. */
  scale?: number;
}

export interface FitData {
  classes: Record<string, { scale: number }>;
  nativeRight: string[];
  hardpoints: Record<string, HardpointDef>;
  overrides: Record<string, Record<string, Partial<HardpointDef>>>;
  items: Record<string, ItemFit>;
  /** Placement table: class, then hardpoint, then an item id (or `*` for every item there). Absent rows change nothing. */
  placements?: Record<string, Record<string, Record<string, Nudge>>>;
}

export const FIT = (kitData as unknown as { fit: FitData }).fit;
const BOUNDS = (boundsData as unknown as { items: Record<string, { min: number[]; max: number[] }> }).items;

/** The fit settings for a class, or null when it still uses the numbered mounts. */
export const fitClass = (chassisId: string) => FIT.classes[chassisId] ?? null;

/** Hardpoint with the class's overrides applied. */
export function hardpoint(chassisId: string, name: string): HardpointDef | undefined {
  const base = FIT.hardpoints[name];
  return base && { ...base, ...(FIT.overrides[chassisId]?.[name] ?? {}) };
}

export interface Placement {
  hp: string;
  /** Which side's joint to hang on, when the hardpoint is sided. */
  side?: Side;
}

/** The kind of location a loadout slot belongs to. */
export const kindOf = (loc: string): Kind => (loc === 'armLeft' || loc === 'armRight' ? 'arm' : (loc as Kind));

/** Place a location's items in order. An entry is null where the item has no preference (fall back to numbered mounts). */
export function planLocation(chassisId: string, loc: string, ids: string[], native: boolean[] = []): Array<Placement[] | null> {
  const kind = kindOf(loc);
  const armSide: Side = loc === 'armRight' ? 'R' : 'L';
  const taken = new Set<string>();
  return ids.map((id, index) => {
    const prefs = FIT.items[id]?.[kind];
    if (!prefs) return null;
    // A class's own item (lance@paladin) was cut for the tuned numbered mount, so it keeps that grip.
    for (const name of native[index] ? prefs.map((n) => (n === 'grip' ? 'grip-native' : n)) : prefs) {
      const def = hardpoint(chassisId, name);
      if (!def || taken.has(name)) continue;
      taken.add(name);
      for (const b of def.blocks ?? []) taken.add(b);
      if (def.side === 'pair') return (['L', 'R'] as Side[]).map((side) => ({ hp: name, side }));
      const side = def.side === 'loc' ? armSide : def.side === 'L' || def.side === 'R' ? def.side : undefined;
      return [{ hp: name, side }];
    }
    return null;
  });
}

/** The point of an item (item space, scale 1) that lands on the hardpoint. */
export function pivotOf(partName: string, contact: Contact[] = []): [number, number, number] {
  const b = BOUNDS[partName];
  if (!b) return [0, 0, 0];
  const mid = (i: number) => (b.min[i] + b.max[i]) / 2;
  const p: [number, number, number] = [0, 0, 0];
  for (const c of contact) {
    if (c === 'center') {
      p[0] = mid(0);
      p[1] = mid(1);
      p[2] = mid(2);
    } else if (c === 'back' || c === 'front') {
      p[0] = mid(0);
      p[1] = mid(1);
      p[2] = c === 'back' ? b.min[2] : b.max[2];
    } else {
      p[0] = mid(0);
      p[2] = mid(2);
      p[1] = c === 'bottom' ? b.min[1] : b.max[1];
    }
  }
  // Combined faces ('back' and 'bottom') keep each axis's own face.
  if (contact.includes('bottom') && contact.includes('back')) {
    p[1] = b.min[1];
    p[2] = b.min[2];
  }
  return p;
}

export const poseOf = (id: string, hp: string) => ({ contact: [] as Contact[], scale: 1, ...(FIT.items[id]?.pose?.default ?? {}), ...(FIT.items[id]?.pose?.[hp] ?? {}) });

export const IDENTITY_NUDGE: Required<Nudge> = { offset: [0, 0, 0], rot: [0, 0, 0], scale: 1 };

/** The placement-table adjustment for an item at a hardpoint of a class, or null when there is none.
 * The row for the item wins field by field over the `*` row of the hardpoint. */
export function nudgeOf(chassisId: string, hp: string, itemId: string): Required<Nudge> | null {
  const rows = FIT.placements?.[chassisId]?.[hp];
  if (!rows || (!rows['*'] && !rows[itemId])) return null;
  const merged = { ...IDENTITY_NUDGE, ...(rows['*'] ?? {}), ...(rows[itemId] ?? {}) };
  const isIdentity = merged.scale === 1 && merged.offset.every((v) => v === 0) && merged.rot.every((v) => v === 0);
  return isIdentity ? null : merged;
}

const isQuiet = (n: Nudge | undefined) => !n || ((n.scale ?? 1) === 1 && (n.offset ?? [0, 0, 0]).every((v) => v === 0) && (n.rot ?? [0, 0, 0]).every((v) => v === 0));

/** One class's placement rows without the ones that change nothing. An item row that undoes its hardpoint's `*` row stays. */
export function compactPlacements(rows: Record<string, Record<string, Nudge>>): Record<string, Record<string, Nudge>> {
  const out: Record<string, Record<string, Nudge>> = {};
  for (const [hp, items] of Object.entries(rows)) {
    const wildcard = !isQuiet(items['*']);
    const kept = Object.entries(items).filter(([item, n]) => !isQuiet(n) || (item !== '*' && wildcard));
    if (kept.length) out[hp] = Object.fromEntries(kept);
  }
  return out;
}
