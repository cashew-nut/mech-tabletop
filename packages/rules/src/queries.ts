// Read-only questions about a game: where walkers are and what works, movement and reach, line of sight, range
// bands, deployment zones and attack previews. Nothing here changes the state, so map generation and the AI can use it.
import {
  RANGE_BANDS,
  RULES,
  getChassis,
  getEquipment,
  type EquipmentDef,
  type Location,
  type RangeBand,
} from './data';
import {
  arcOf,
  distance,
  hexEq,
  hexKey,
  lineBetween,
  neighbors,
  offsetToHex,
  type Hex,
} from './hex';
import type {
  GameState,
  HexInfo,
  ItemState,
  Side,
  WalkerState,
  Zone,
} from './types';

export class IllegalAction extends Error {}

export const illegal = (msg: string): never => {
  throw new IllegalAction(msg);
};

/** Target id for the Surveyor Escort scenario's surveyor token. */
export const SURVEYOR_ID = 'surveyor';

/** Hexes a side may deploy into: the rows within deployment depth of its edge. */
export function deploymentZone(state: GameState, side: Side): Hex[] {
  const depth = RULES.map.deploymentDepth;
  const out: Hex[] = [];
  for (let row = 0; row < state.map.height; row++) {
    if (side === 0 ? row >= depth : row < state.map.height - depth) continue;
    for (let col = 0; col < state.map.width; col++) out.push(offsetToHex({ col, row }));
  }
  return out;
}

export const undeployedCount = (state: GameState, side: Side) => state.undeployed.filter((w) => w.side === side).length;

/**
 * The Reliquary deploy their last war-walker after the enemy has finished (From the Veil).
 * If both sides are Reliquary, the rule cancels out once both are down to one.
 */
export function mustHold(state: GameState, side: Side): boolean {
  const other = (1 - side) as Side;
  const veiled = (s: Side) => state.lances[s].faction === 'reliquary';
  if (!veiled(side) || undeployedCount(state, side) !== 1 || undeployedCount(state, other) === 0) return false;
  return !(veiled(other) && undeployedCount(state, other) === 1);
}

export const canDeploy = (state: GameState, side: Side) => undeployedCount(state, side) > 0 && !mustHold(state, side);

/** War-walkers the side to move may deploy now. */
export function deployable(state: GameState): WalkerState[] {
  if (state.phase !== 'deployment' || mustHold(state, state.activeSide)) return [];
  return state.undeployed.filter((w) => w.side === state.activeSide);
}

// ---------------------------------------------------------------- queries

export const getWalker = (state: GameState, id: string): WalkerState =>
  state.walkers.find((w) => w.id === id) ?? illegal(`No war-walker "${id}"`);

export const aliveWalkers = (state: GameState, side?: Side) =>
  state.walkers.filter((w) => !w.destroyed && (side === undefined || w.side === side));

export function hexInfo(state: GameState, hex: Hex): HexInfo | null {
  return state.map.hexes[hexKey(hex)] ?? null;
}

export function walkerAt(state: GameState, hex: Hex): WalkerState | null {
  return state.walkers.find((w) => !w.destroyed && hexEq(w.pos, hex)) ?? null;
}

export function passable(state: GameState, hex: Hex): boolean {
  const info = hexInfo(state, hex);
  return !!info && info.terrain !== 'blocking' && !state.wrecks.includes(hexKey(hex));
}

export function enterable(state: GameState, hex: Hex): boolean {
  return passable(state, hex) && !walkerAt(state, hex) && !surveyorAt(state, hex);
}

export function surveyorAt(state: GameState, hex: Hex): boolean {
  return state.surveyor?.status === 'active' && hexEq(state.surveyor.pos, hex);
}

export function zonesOf(loc: Location): Zone[] {
  return loc === 'core' ? ['coreFront', 'coreRear'] : [loc];
}

export function isWorking(w: WalkerState, item: ItemState): boolean {
  return !item.destroyed && !w.destroyedLocations.includes(item.location);
}

export function workingItems(w: WalkerState, id?: string): ItemState[] {
  return w.items.filter((it) => isWorking(w, it) && (id === undefined || it.id === id));
}

export const hasWorking = (w: WalkerState, id: string) => workingItems(w, id).length > 0;

export function faultThreshold(w: WalkerState): number {
  let t = 3;
  if (w.trait === 'iron-nerve') t += 1;
  return t;
}

export function stride(state: GameState, w: WalkerState): number {
  let s = getChassis(w.chassis).stride;
  if (w.items.filter((it) => it.id === 'ablative-plating').length >= 2) s -= 1;
  if (w.actuator.legs) s -= 1;
  if (state.active?.walkerId === w.id && state.active.faults.includes('gear-seize')) s -= 1;
  if (w.destroyedLocations.includes('legs')) s = Math.floor(s / 2);
  return Math.max(1, s);
}

export function stepCost(state: GameState, from: Hex, to: Hex): number {
  const a = hexInfo(state, from)!;
  const b = hexInfo(state, to)!;
  const base = b.terrain === 'rough' || b.terrain === 'heavy' ? 2 : 1;
  return base + Math.max(0, b.elevation - a.elevation);
}

/** Movement allowance for the next Move action of the active walker. */
export function moveAllowance(state: GameState, w: WalkerState): number {
  let s = stride(state, w);
  if (state.active && !state.active.usedMoveAction && hasWorking(w, 'sprint-servos')) s += 1;
  return s;
}

/** Cheapest path to every hex reachable within `budget` movement. */
export function reachable(state: GameState, w: WalkerState, budget: number): Map<string, { cost: number; path: Hex[] }> {
  const best = new Map<string, { cost: number; path: Hex[] }>();
  best.set(hexKey(w.pos), { cost: 0, path: [] });
  const frontier: Array<{ hex: Hex; cost: number; path: Hex[] }> = [{ hex: w.pos, cost: 0, path: [] }];
  while (frontier.length) {
    frontier.sort((a, b) => a.cost - b.cost);
    const cur = frontier.shift()!;
    for (const next of neighbors(cur.hex)) {
      if (!enterable(state, next)) continue;
      const cost = cur.cost + stepCost(state, cur.hex, next);
      if (cost > budget) continue;
      const k = hexKey(next);
      const prev = best.get(k);
      if (prev && prev.cost <= cost) continue;
      const path = [...cur.path, next];
      best.set(k, { cost, path });
      frontier.push({ hex: next, cost, path });
    }
  }
  best.delete(hexKey(w.pos));
  return best;
}

// ---------------------------------------------------------------- line of sight

function lineBlocked(state: GameState, line: Hex[], ceiling: number): { blocked: boolean; light: boolean } {
  let light = false;
  for (const hex of line.slice(1, -1)) {
    const info = hexInfo(state, hex);
    if (!info) return { blocked: true, light };
    const k = hexKey(hex);
    if (info.terrain === 'blocking' || info.terrain === 'heavy' || state.wrecks.includes(k) || state.smoke.includes(k)) {
      return { blocked: true, light };
    }
    if (info.elevation > ceiling) return { blocked: true, light };
    if (info.terrain === 'light') light = true;
  }
  return { blocked: false, light };
}

/** Line of sight between two hexes, and whether it passes through light cover. */
export function lineOfSight(state: GameState, a: Hex, b: Hex): { clear: boolean; throughLight: boolean } {
  const ceiling = Math.max(hexInfo(state, a)?.elevation ?? 0, hexInfo(state, b)?.elevation ?? 0);
  const one = lineBlocked(state, lineBetween(a, b, 1), ceiling);
  const two = lineBlocked(state, lineBetween(a, b, -1), ceiling);
  if (one.blocked && two.blocked) return { clear: false, throughLight: false };
  const open = one.blocked ? [two] : two.blocked ? [one] : [one, two];
  return { clear: true, throughLight: open.every((l) => l.light) };
}

export function rangeBand(dist: number): RangeBand | null {
  if (dist <= RANGE_BANDS.short[1]) return 'short';
  if (dist <= RANGE_BANDS.medium[1]) return 'medium';
  if (dist <= RANGE_BANDS.long[1]) return 'long';
  return null;
}

/** Range bands from nearest to farthest. */
export const BAND_ORDER: RangeBand[] = ['melee', 'short', 'medium', 'long'];
/** The target number of an attack before range and modifiers. */
export const BASE_TN = 4;
/** What each range band adds to the target number. */
export const BAND_TN: Record<RangeBand, number> = { melee: 0, short: 0, medium: 1, long: 2 };

/** The hit rule: a 6 always hits, a 1 always misses, anything else hits on the TN or more. */
export const isHit = (roll: number, tn: number) => roll === 6 || (roll !== 1 && roll >= tn);

// ---------------------------------------------------------------- attack preview

export interface AttackPreview {
  ok: boolean;
  reason?: string;
  tn: number;
  dice: number;
  band: RangeBand | null;
  indirect: boolean;
  pressure: number;
}

function pressureCost(state: GameState, w: WalkerState, def: EquipmentDef): number {
  const a = state.active;
  if (def.category === 'weapon' && w.trait === 'gunner' && a && !a.firstWeaponFired) return Math.max(0, def.pressure - 1);
  return def.pressure;
}

/** Whether the active walker can fire `itemUid` at `targetId`, and with what TN and dice. */
export function previewAttack(state: GameState, itemUid: string, targetId: string): AttackPreview {
  const fail = (reason: string): AttackPreview => ({ ok: false, reason, tn: 0, dice: 0, band: null, indirect: false, pressure: 0 });
  const a = state.active;
  if (!a?.started) return fail('No war-walker is active');
  const w = getWalker(state, a.walkerId);
  const item = w.items.find((it) => it.uid === itemUid);
  if (!item) return fail('No such item');
  const def = getEquipment(item.id);
  const wp = def.weapon;
  if (!wp) return fail(`${def.name} is not a weapon`);
  if (!isWorking(w, item)) return fail(`${def.name} is destroyed`);
  if (item.firedThisActivation) return fail(`${def.name} already fired this activation`);
  if (a.jammedUid === item.uid) return fail(`${def.name} is jammed`);
  if (item.ammo !== null && item.ammo <= 0) return fail(`${def.name} is out of ammo`);
  if (w.prone) return fail('Prone war-walkers cannot fire');
  const sv = targetId === SURVEYOR_ID ? state.surveyor : null;
  const t = sv ? null : state.walkers.find((x) => x.id === targetId);
  if (sv) {
    if (sv.status !== 'active') return fail('No such target');
    if (sv.side === w.side) return fail('Cannot target your own surveyor');
  } else {
    if (!t || t.destroyed) return fail('No such target');
    if (t.side === w.side) return fail('Cannot target a friendly war-walker');
  }
  const tPos = sv ? sv.pos : t!.pos;
  const tSide = sv ? sv.side : t!.side;
  const pressure = pressureCost(state, w, def);
  if (pressure > a.pressure) return fail('Not enough Pressure');
  if (arcOf(w.pos, w.facing, tPos) !== 'front') return fail('Target is not in the front arc');

  const dist = distance(w.pos, tPos);
  const melee = wp.range === 'melee';
  let band: RangeBand | null;
  let indirect = false;
  let tn = BASE_TN;
  if (melee) {
    if (dist !== 1) return fail('Melee weapons need an adjacent target');
    band = 'melee';
  } else {
    band = rangeBand(dist);
    if (!band || BAND_ORDER.indexOf(band) > BAND_ORDER.indexOf(wp.range)) return fail('Target is out of range');
    if (wp.minRange && dist < wp.minRange) return fail(`Target is inside minimum range ${wp.minRange}`);
    const los = lineOfSight(state, w.pos, tPos);
    if (!los.clear) {
      const seen =
        t?.spottedBy === w.side ||
        aliveWalkers(state, w.side).some((f) => f.id !== w.id && lineOfSight(state, f.pos, tPos).clear);
      if (!def.tags?.includes('indirect') || !seen) return fail('No line of sight');
      indirect = true;
      tn += 1;
    }
    tn += BAND_TN[band];
    const here = hexInfo(state, tPos)!;
    const inSmoke = state.smoke.includes(hexKey(tPos));
    const hexCover = here.terrain === 'heavy' ? 2 : here.terrain === 'light' || inSmoke ? 1 : 0;
    const lineCover = !indirect && los.throughLight ? 1 : 0;
    tn += Math.max(hexCover, lineCover);
    if (a.moved && !hasWorking(w, 'gyro-stabilisers')) tn += def.tags?.includes('static') ? 2 : 1;
  }
  if (t) {
    if (t.lastMoveDistance >= 4) tn += 1;
    if (t.braced) tn += 1;
    if (t.prone) tn -= 1;
    if (t.spottedBy === w.side) tn -= 1;
  }
  // A surveyor with an escort next to it is screened.
  if (sv && aliveWalkers(state, sv.side).some((f) => distance(f.pos, sv.pos) === 1)) tn += 1;
  if ((hexInfo(state, w.pos)?.elevation ?? 0) > (hexInfo(state, tPos)?.elevation ?? 0)) tn -= 1;
  if (hasWorking(w, 'targeting-array')) tn -= 1;
  if (a.faults.includes('steam-scald')) tn += 1;
  if (aliveWalkers(state, tSide).some((f) => hasWorking(f, 'soul-lantern') && distance(f.pos, tPos) <= 2)) tn += 1;
  tn = Math.max(2, tn);

  let dice = wp.dice;
  if (def.tags?.includes('charge') && w.lastMoveDistance >= 2) dice += 1;
  if (w.actuator[item.location]) dice -= 1;
  dice = Math.max(1, dice);
  return { ok: true, tn, dice, band, indirect, pressure };
}
