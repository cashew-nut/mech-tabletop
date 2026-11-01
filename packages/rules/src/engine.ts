// The Brass Charter rules engine. Pure functions over a serialisable state:
// applyAction(state, action) returns a new state and the events it produced.
import {
  LOCATIONS,
  RANGE_BANDS,
  RULES,
  getChassis,
  getFaction,
  getEquipment,
  getMap,
  getScenario,
  type EquipmentDef,
  type MapDef,
  type ScenarioDef,
  type Location,
  type RangeBand,
} from './data';
import {
  arcOf,
  directionTo,
  distance,
  hexToOffset,
  facingTowards,
  hexEq,
  hexKey,
  lineBetween,
  neighbor,
  neighbors,
  offsetToHex,
  type Facing,
  type Hex,
} from './hex';
import { validateLance, walkerCost, type LanceInput } from './lance';
import { d6, pick } from './rng';
import type {
  Action,
  Activation,
  FaultId,
  GameEvent,
  GameState,
  HexInfo,
  ItemState,
  Side,
  WalkerState,
  Zone,
} from './types';

export class IllegalAction extends Error {}

const illegal = (msg: string): never => {
  throw new IllegalAction(msg);
};

const OVERPRESSURE_LIMIT = 6;
const MAX_RESERVE = 2;
const MAX_THROTTLE = 2;
/** Target id for the Surveyor Escort scenario's surveyor token. */
export const SURVEYOR_ID = 'surveyor';

// ---------------------------------------------------------------- setup

export interface Deployment {
  col: number;
  row: number;
  facing?: Facing;
}

export interface GameSetup {
  seed: number;
  /** A scenario id from data/scenarios.json, or a scenario built elsewhere (for example by the board generator). */
  scenario: string | ScenarioDef;
  /** A map id from data/maps.json, or a map built elsewhere (for example by the board generator). */
  map: string | MapDef;
  lances: [LanceInput, LanceInput];
  /** Optional fixed positions per side; otherwise walkers line up on their edge. */
  deployments?: [Deployment[], Deployment[]];
  /**
   * 'alternate' starts with a deployment phase in which the sides take turns
   * placing war-walkers (section 5). 'auto' (the default) lines them up.
   */
  deploy?: 'auto' | 'alternate';
}

export function createGame(setup: GameSetup): GameState {
  const mapDef = typeof setup.map === 'string' ? getMap(setup.map) : setup.map;
  const scenario = typeof setup.scenario === 'string' ? getScenario(setup.scenario) : setup.scenario;
  const hexes: Record<string, HexInfo> = {};
  for (let row = 0; row < mapDef.height; row++) {
    for (let col = 0; col < mapDef.width; col++) {
      hexes[hexKey(offsetToHex({ col, row }))] = { terrain: 'open', elevation: 0 };
    }
  }
  for (const h of mapDef.hexes) {
    hexes[hexKey(offsetToHex(h))] = { terrain: h.terrain ?? 'open', elevation: h.elevation ?? 0 };
  }

  const state: GameState = {
    rng: { state: setup.seed | 0 },
    round: 1,
    rounds: RULES.rounds,
    phase: 'activation',
    scenario: scenario.id,
    map: { id: mapDef.id, width: mapDef.width, height: mapDef.height, hexes },
    objectives: scenario.objectives.map((o) => ({ hex: offsetToHex(o), vp: o.vp })),
    smoke: [],
    wrecks: [],
    lances: setup.lances.map((l) => ({ name: l.name, faction: l.faction })),
    walkers: [],
    undeployed: [],
    surveyor: scenario.surveyor
      ? { side: scenario.surveyor.side, pos: offsetToHex(scenario.surveyor), hp: scenario.surveyor.hp, status: 'active' }
      : null,
    vp: [0, 0],
    activeSide: 0,
    active: null,
    passesUsed: [0, 0],
    pendingTactician: null,
    winner: null,
    log: [],
  };

  const centre = mapCentre(state);
  const alternate = setup.deploy === 'alternate' && !setup.deployments;
  setup.lances.forEach((lance, sideIndex) => {
    const side = sideIndex as Side;
    const report = validateLance(lance);
    if (report.errors.length) throw new Error(`Lance "${lance.name}" is not legal: ${report.errors.join('; ')}`);
    const faction = getFaction(lance.faction);
    const deploy = alternate ? null : (setup.deployments?.[side] ?? defaultDeployment(state, side, lance.walkers.length));
    lance.walkers.forEach((input, i) => {
      const c = getChassis(input.chassis);
      const id = `s${side}w${i}`;
      const items: ItemState[] = [];
      for (const loc of LOCATIONS) {
        for (const itemId of input.loadout[loc] ?? []) {
          const def = getEquipment(itemId);
          items.push({
            uid: `${id}i${items.length}`,
            id: itemId,
            location: loc,
            destroyed: false,
            ammo: def.weapon?.ammo ?? null,
            uses: def.uses ?? null,
            firedThisActivation: false,
          });
        }
      }
      const armour: Record<Zone, number> = {
        coreFront: c.armour.coreFront,
        coreRear: c.armour.coreRear,
        armLeft: c.armour.arm,
        armRight: c.armour.arm,
        legs: c.armour.legs,
      };
      for (const item of items.filter((it) => it.id === 'ablative-plating')) {
        for (const zone of zonesOf(item.location)) armour[zone] += 2;
      }
      const pos = deploy ? offsetToHex(deploy[i]) : { q: 0, r: 0 };
      if (deploy && !enterable(state, pos)) throw new Error(`Cannot deploy ${input.name} at ${deploy[i].col},${deploy[i].row}`);
      const walker: WalkerState = {
        id,
        side,
        name: input.name,
        chassis: c.id,
        size: c.size,
        cost: walkerCost(input, faction),
        command: input.driver.command,
        trait: input.driver.trait,
        pos,
        facing: deploy ? (deploy[i].facing ?? facingTowards(pos, centre)) : 0,
        items,
        armour,
        maxArmour: { ...armour },
        structure: { core: c.structure.core, armLeft: c.structure.other, armRight: c.structure.other, legs: c.structure.other },
        destroyedLocations: [],
        actuator: { armLeft: false, armRight: false, core: false, legs: false },
        overpressure: 0,
        reserve: 0,
        prone: false,
        anchored: false,
        braced: false,
        activated: false,
        destroyed: false,
        skipNext: false,
        lastMoveDistance: 0,
        pendingDrain: 0,
        spottedBy: null,
        aceUsed: false,
        reactiveUsed: false,
        tacticianUsed: false,
      };
      (deploy ? state.walkers : state.undeployed).push(walker);
    });
  });

  const events: GameEvent[] = [];
  if (alternate) {
    // Each side rolls a d6; the loser deploys first.
    let r0 = 0;
    let r1 = 0;
    while (r0 === r1) {
      r0 = d6(state.rng);
      r1 = d6(state.rng);
    }
    state.phase = 'deployment';
    state.activeSide = r0 < r1 ? 0 : 1;
    events.push({ type: 'deployment', text: `Deployment. Side ${state.activeSide} deploys first (${r0} vs ${r1}).` });
  } else {
    startRound(state, events);
  }
  state.log.push(...events);
  return state;
}

const mapCentre = (state: GameState) =>
  offsetToHex({ col: Math.floor(state.map.width / 2), row: Math.floor(state.map.height / 2) });

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

const undeployedCount = (state: GameState, side: Side) => state.undeployed.filter((w) => w.side === side).length;

/**
 * The Reliquary deploy their last war-walker after the enemy has finished (From the Veil).
 * If both sides are Reliquary, the rule cancels out once both are down to one.
 */
function mustHold(state: GameState, side: Side): boolean {
  const other = (1 - side) as Side;
  const veiled = (s: Side) => state.lances[s].faction === 'reliquary';
  if (!veiled(side) || undeployedCount(state, side) !== 1 || undeployedCount(state, other) === 0) return false;
  return !(veiled(other) && undeployedCount(state, other) === 1);
}

const canDeploy = (state: GameState, side: Side) => undeployedCount(state, side) > 0 && !mustHold(state, side);

/** War-walkers the side to move may deploy now. */
export function deployable(state: GameState): WalkerState[] {
  if (state.phase !== 'deployment' || mustHold(state, state.activeSide)) return [];
  return state.undeployed.filter((w) => w.side === state.activeSide);
}

function doDeploy(ctx: Ctx, action: Extract<Action, { type: 'deploy' }>) {
  const { state, emit } = ctx;
  const side = state.activeSide;
  const index = state.undeployed.findIndex((w) => w.id === action.walkerId);
  if (index < 0) illegal(`${action.walkerId} is not waiting to deploy`);
  const w = state.undeployed[index];
  if (w.side !== side) illegal(`It is side ${side}'s turn to deploy`);
  if (mustHold(state, side)) illegal('Calloway & Vane hold their last war-walker until the enemy has deployed');
  if (!deploymentZone(state, side).some((h) => hexEq(h, action.hex))) illegal('That hex is outside the deployment zone');
  if (!enterable(state, action.hex)) illegal('That hex is blocked or occupied');
  w.pos = action.hex;
  w.facing = action.facing ?? facingTowards(action.hex, mapCentre(state));
  state.undeployed.splice(index, 1);
  state.walkers.push(w);
  const { col, row } = hexToOffset(action.hex);
  emit('deploy', `${w.name} deploys at ${col},${row}.`, { walkerId: w.id, hex: action.hex });
  const other = (1 - side) as Side;
  if (canDeploy(state, other)) state.activeSide = other;
  else if (canDeploy(state, side)) state.activeSide = side;
  else {
    state.phase = 'activation';
    const events: GameEvent[] = [];
    startRound(state, events);
    for (const e of events) emit(e.type, e.text, e);
  }
}

function defaultDeployment(state: GameState, side: Side, count: number): Deployment[] {
  const row = side === 0 ? 1 : state.map.height - 2;
  const out: Deployment[] = [];
  const taken = new Set<string>();
  for (let i = 0; i < count; i++) {
    const target = Math.round(((i + 1) * state.map.width) / (count + 1)) - 1;
    for (let shift = 0; shift < state.map.width; shift++) {
      const col = target + (shift % 2 ? -1 : 1) * Math.ceil(shift / 2);
      const hex = offsetToHex({ col, row });
      const info = state.map.hexes[hexKey(hex)];
      if (col >= 0 && col < state.map.width && info && enterable(state, hex) && !taken.has(hexKey(hex))) {
        taken.add(hexKey(hex));
        out.push({ col, row });
        break;
      }
    }
  }
  return out;
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

function enterable(state: GameState, hex: Hex): boolean {
  return passable(state, hex) && !walkerAt(state, hex) && !surveyorAt(state, hex);
}

function surveyorAt(state: GameState, hex: Hex): boolean {
  return state.surveyor?.status === 'active' && hexEq(state.surveyor.pos, hex);
}

function zonesOf(loc: Location): Zone[] {
  return loc === 'core' ? ['coreFront', 'coreRear'] : [loc];
}

export function isWorking(w: WalkerState, item: ItemState): boolean {
  return !item.destroyed && !w.destroyedLocations.includes(item.location);
}

export function workingItems(w: WalkerState, id?: string): ItemState[] {
  return w.items.filter((it) => isWorking(w, it) && (id === undefined || it.id === id));
}

const hasWorking = (w: WalkerState, id: string) => workingItems(w, id).length > 0;

function faultThreshold(w: WalkerState): number {
  let t = hasWorking(w, 'overcharged-boiler') ? 2 : 3;
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

const BAND_ORDER: RangeBand[] = ['melee', 'short', 'medium', 'long'];
const BAND_TN: Record<RangeBand, number> = { melee: 0, short: 0, medium: 1, long: 2 };

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
  let tn = 4;
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
    if (t.braced || t.anchored) tn += 1;
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
  if (band === 'long' && w.anchored && hasWorking(w, 'anchor-spikes')) dice += 1;
  if (w.actuator[item.location]) dice -= 1;
  dice = Math.max(1, dice);
  return { ok: true, tn, dice, band, indirect, pressure };
}

// ---------------------------------------------------------------- actions

export interface ActionResult {
  state: GameState;
  events: GameEvent[];
}

export function applyAction(prev: GameState, action: Action): ActionResult {
  if (prev.phase === 'over') illegal('The Trial is over');
  const state = structuredClone(prev);
  const events: GameEvent[] = [];
  const emit = (type: string, text: string, extra: Record<string, unknown> = {}) => events.push({ type, text, ...extra });
  const ctx: Ctx = { state, emit };

  if (state.phase === 'deployment') {
    if (action.type !== 'deploy') illegal('War-walkers must deploy first');
    doDeploy(ctx, action as Extract<Action, { type: 'deploy' }>);
  } else if (action.type === 'deploy') illegal('Deployment is over');
  else if (action.type === 'activate') doActivate(ctx, action.walkerId, action.throttle ?? 0);
  else if (action.type === 'pass') doPass(ctx);
  else {
    const a = state.active;
    if (!a?.started) illegal('No war-walker is active');
    const w = getWalker(state, a!.walkerId);
    doWalkerAction(ctx, w, a!, action as Exclude<Action, { type: 'activate' | 'pass' | 'deploy' }>);
    if (state.active?.forceEnd && state.phase !== 'over') endActivation(ctx, w, false);
  }
  state.log.push(...events);
  return { state, events };
}

interface Ctx {
  state: GameState;
  emit: (type: string, text: string, extra?: Record<string, unknown>) => void;
}

function spend(a: Activation, n: number) {
  if (n > a.pressure) illegal(`Needs ${n} Pressure, has ${a.pressure}`);
  a.pressure -= n;
}

function canActivate(state: GameState, side: Side): boolean {
  if (state.pendingTactician) return getWalker(state, state.pendingTactician).side === side;
  return aliveWalkers(state, side).some((w) => !w.activated);
}

function doActivate(ctx: Ctx, walkerId: string, throttle: number) {
  const { state, emit } = ctx;
  if (state.active) illegal('Another war-walker is already active');
  const w = getWalker(state, walkerId);
  if (w.destroyed) illegal(`${w.name} is destroyed`);
  if (w.side !== state.activeSide) illegal(`It is side ${state.activeSide}'s turn`);
  if (state.pendingTactician && state.pendingTactician !== w.id) illegal('The Tactician must activate again first');
  if (w.activated) illegal(`${w.name} has already activated this round`);
  if (!Number.isInteger(throttle) || throttle < 0 || throttle > MAX_THROTTLE) illegal(`Throttle must be 0-${MAX_THROTTLE}`);
  state.pendingTactician = null;

  const a: Activation = {
    walkerId: w.id,
    pressure: 0,
    started: true,
    moved: false,
    usedMoveAction: false,
    firstWeaponFired: false,
    braced: false,
    faults: [],
    jammedUid: null,
    forceEnd: false,
  };
  state.active = a;
  w.braced = false;
  w.lastMoveDistance = 0;
  for (const it of w.items) it.firedThisActivation = false;

  if (w.skipNext) {
    w.skipNext = false;
    emit('skip', `${w.name} is venting its blown safety valve and skips this activation.`, { walkerId: w.id });
    endActivation(ctx, w, false);
    return;
  }

  if (w.overpressure >= faultThreshold(w)) {
    let roll = d6(state.rng);
    if (roll <= 2 && w.trait === 'ace' && !w.aceUsed) {
      w.aceUsed = true;
      roll = d6(state.rng);
      emit('reroll', `${w.name}'s Ace driver rerolls the Fault check.`, { walkerId: w.id });
    }
    if (roll <= 2) {
      const faults: FaultId[] = ['valve-stick', 'gear-seize', 'breech-jam', 'steam-scald', 'gauge-failure', 'boiler-surge'];
      const fault = faults[d6(state.rng) - 1];
      a.faults.push(fault);
      emit('fault', `${w.name} suffers a fault: ${fault.replaceAll('-', ' ')}.`, { walkerId: w.id, fault });
      if (fault === 'breech-jam') {
        const weapons = workingItems(w).filter((it) => getEquipment(it.id).weapon);
        if (weapons.length) a.jammedUid = pick(state.rng, weapons).uid;
      }
      if (fault === 'boiler-surge') addOverpressure(ctx, w, 1);
    }
  }
  if (a.forceEnd) {
    endActivation(ctx, w, false);
    return;
  }

  let pressure = getChassis(w.chassis).boiler;
  if (hasWorking(w, 'overcharged-boiler')) pressure += 1;
  if (w.actuator.core) pressure -= 1;
  if (a.faults.includes('valve-stick')) pressure -= 1;
  pressure -= w.pendingDrain;
  w.pendingDrain = 0;
  a.pressure = Math.max(0, pressure);
  emit('activate', `${w.name} activates with ${a.pressure} Pressure.`, { walkerId: w.id, pressure: a.pressure });

  if (throttle > 0) {
    if (a.faults.includes('gauge-failure')) {
      emit('throttle', `${w.name} cannot open the throttle (gauge failure).`, { walkerId: w.id, throttle: 0 });
      return;
    }
    a.pressure += throttle;
    emit('throttle', `${w.name} opens the throttle for +${throttle} Pressure.`, { walkerId: w.id, throttle });
    addOverpressure(ctx, w, throttle);
    if (a.forceEnd) endActivation(ctx, w, false);
  }
}

function doPass(ctx: Ctx) {
  const { state, emit } = ctx;
  if (state.active) illegal('Cannot pass during an activation');
  if (state.pendingTactician) illegal('The Tactician must activate again first');
  const side = state.activeSide;
  const other = (1 - side) as Side;
  if (state.passesUsed[side] >= 1) illegal('Already passed this round');
  if (aliveWalkers(state, side).length >= aliveWalkers(state, other).length) illegal('Only the side with fewer war-walkers may pass');
  if (!canActivate(state, other)) illegal('The other side has nothing left to activate');
  state.passesUsed[side] += 1;
  emit('pass', `Side ${side} passes.`, { side });
  state.activeSide = other;
}

function doWalkerAction(ctx: Ctx, w: WalkerState, a: Activation, action: Exclude<Action, { type: 'activate' | 'pass' | 'deploy' }>) {
  const { state, emit } = ctx;
  switch (action.type) {
    case 'move': {
      if (w.prone) illegal('Prone war-walkers must stand up first');
      if (!action.path.length) illegal('Empty path');
      const allowance = moveAllowance(state, w);
      let cost = 0;
      let at = w.pos;
      for (const step of action.path) {
        if (distance(at, step) !== 1) illegal('Path steps must be adjacent');
        if (!enterable(state, step)) illegal('Path enters a blocked or occupied hex');
        cost += stepCost(state, at, step);
        at = step;
      }
      if (cost > allowance) illegal(`Path costs ${cost} movement, allowance is ${allowance}`);
      spend(a, 1);
      const last = action.path.length > 1 ? action.path[action.path.length - 2] : w.pos;
      w.facing = action.facing ?? (directionTo(last, at) as Facing);
      w.pos = at;
      w.anchored = false;
      a.moved = true;
      a.usedMoveAction = true;
      w.lastMoveDistance += action.path.length;
      emit('move', `${w.name} moves ${action.path.length} hex${action.path.length > 1 ? 'es' : ''}.`, { walkerId: w.id, path: action.path });
      return;
    }
    case 'turn': {
      if (w.prone) illegal('Prone war-walkers must stand up first');
      spend(a, 1);
      w.facing = action.facing;
      emit('turn', `${w.name} turns.`, { walkerId: w.id, facing: action.facing });
      return;
    }
    case 'brace': {
      if (w.prone) illegal('Prone war-walkers cannot brace');
      if (a.braced) illegal('Already braced this activation');
      spend(a, 1);
      a.braced = true;
      w.braced = true;
      emit('brace', `${w.name} braces.`, { walkerId: w.id });
      return;
    }
    case 'bank': {
      if (w.reserve >= MAX_RESERVE) illegal(`Reserve is full (${MAX_RESERVE})`);
      spend(a, 1);
      w.reserve += 1;
      emit('bank', `${w.name} banks 1 Pressure in Reserve.`, { walkerId: w.id });
      return;
    }
    case 'standUp': {
      if (!w.prone) illegal('Not prone');
      spend(a, 1);
      w.prone = false;
      emit('stand', `${w.name} stands up.`, { walkerId: w.id });
      return;
    }
    case 'fire': {
      const p = previewAttack(state, action.itemUid, action.targetId);
      if (!p.ok) illegal(p.reason!);
      const item = w.items.find((it) => it.uid === action.itemUid)!;
      const def = getEquipment(item.id);
      if (action.targetId === SURVEYOR_ID) {
        fireAtSurveyor(ctx, w, item, p);
        return;
      }
      const t = getWalker(state, action.targetId);
      spend(a, p.pressure);
      a.firstWeaponFired = true;
      item.firedThisActivation = true;
      if (item.ammo !== null) item.ammo -= 1;
      emit('fire', `${w.name} fires ${def.name} at ${t.name} (${p.dice} dice, TN ${p.tn}).`, {
        walkerId: w.id,
        targetId: t.id,
        itemId: def.id,
      });
      const backstab = def.tags?.includes('backstab') && arcOf(t.pos, t.facing, w.pos) === 'rear';
      const rolls = rollAttack(ctx, w, p.dice, p.tn, backstab ? 5 : (def.weapon!.critOn ?? 6));
      const melee = def.weapon!.range === 'melee';
      resolveHits(ctx, w, t, rolls, {
        damage: def.weapon!.damage + (melee && w.trait === 'brawler' ? 1 : 0),
        pierce: def.weapon!.pierce ?? 0,
        overpressure: def.tags?.includes('overpressure') ? 1 : 0,
        drain: def.tags?.includes('drain') ? 1 : 0,
      });
      if (def.tags?.includes('push') && rolls.some((r) => r.hit) && !t.destroyed) push(ctx, w, t);
      if (def.tags?.includes('blast')) {
        for (const other of aliveWalkers(state)) {
          if (other.id === t.id || distance(other.pos, t.pos) !== 1) continue;
          const splash = rollAttack(ctx, w, 1, p.tn, 6);
          if (splash.some((r) => r.hit)) emit('blast', `Blast catches ${other.name}.`, { targetId: other.id });
          resolveHits(ctx, w, other, splash, { damage: def.weapon!.damage, pierce: 0, overpressure: 0, drain: 0 });
        }
      }
      return;
    }
    case 'ram': {
      if (w.prone) illegal('Prone war-walkers cannot Ram');
      const t = getWalker(state, action.targetId);
      if (t.destroyed || t.side === w.side) illegal('Invalid Ram target');
      if (distance(w.pos, t.pos) !== 1 || arcOf(w.pos, w.facing, t.pos) !== 'front') illegal('Ram needs an adjacent target in the front arc');
      spend(a, 2);
      emit('ram', `${w.name} rams ${t.name}.`, { walkerId: w.id, targetId: t.id });
      const rolls = rollAttack(ctx, w, 2, 4, 6);
      resolveHits(ctx, w, t, rolls, { damage: w.size + (w.trait === 'brawler' ? 1 : 0), pierce: 0, overpressure: 0, drain: 0 });
      addOverpressure(ctx, w, 1);
      if (!t.destroyed) addOverpressure(ctx, t, 1);
      return;
    }
    case 'useItem':
      useItem(ctx, w, a, action);
      return;
    case 'escort':
      escort(ctx, w, a, action.path);
      return;
    case 'endActivation':
      endActivation(ctx, w, !!action.reactivate);
      return;
  }
}

// ---------------------------------------------------------------- surveyor escort

function surveyorDef(state: GameState) {
  return getScenario(state.scenario).surveyor!;
}

function fireAtSurveyor(ctx: Ctx, w: WalkerState, item: ItemState, p: AttackPreview) {
  const { state, emit } = ctx;
  const sv = state.surveyor!;
  const def = getEquipment(item.id);
  spend(state.active!, p.pressure);
  state.active!.firstWeaponFired = true;
  item.firedThisActivation = true;
  if (item.ammo !== null) item.ammo -= 1;
  emit('fire', `${w.name} fires ${def.name} at the surveyor (${p.dice} dice, TN ${p.tn}).`, {
    walkerId: w.id,
    targetId: SURVEYOR_ID,
    itemId: def.id,
  });
  const hits = rollAttack(ctx, w, p.dice, p.tn, 7).filter((r) => r.hit).length;
  if (!hits) return;
  sv.hp = Math.max(0, sv.hp - hits);
  if (sv.hp > 0) {
    emit('hit', `The surveyor takes ${hits} hit${hits > 1 ? 's' : ''} (${sv.hp} left).`, { targetId: SURVEYOR_ID });
    return;
  }
  sv.status = 'destroyed';
  const scorer = (1 - sv.side) as Side;
  const vp = surveyorDef(state).destroyVp;
  state.vp[scorer] += vp;
  emit('destroyed', `The surveyor is destroyed! Side ${scorer} scores ${vp} VP.`, { targetId: SURVEYOR_ID, side: scorer, vp });
}

/** The row the surveyor must reach to leave the far edge. */
export function surveyorExitRow(state: GameState): number {
  return state.surveyor?.side === 0 ? state.map.height - 1 : 0;
}

function escort(ctx: Ctx, w: WalkerState, a: Activation, path: Hex[]) {
  const { state, emit } = ctx;
  const sv = state.surveyor;
  if (!sv || sv.status !== 'active') illegal('There is no surveyor to escort');
  if (sv!.side !== w.side) illegal("Cannot escort the enemy's surveyor");
  if (w.prone) illegal('Prone war-walkers cannot escort');
  if (distance(w.pos, sv!.pos) !== 1) illegal('Must be next to the surveyor');
  if (path.length < 1 || path.length > 2) illegal('The surveyor moves 1 or 2 hexes');
  let at = sv!.pos;
  for (const step of path) {
    if (distance(at, step) !== 1) illegal('Path steps must be adjacent');
    if (!enterable(state, step)) illegal('Path enters a blocked or occupied hex');
    at = step;
  }
  spend(a, 1);
  sv!.pos = at;
  emit('escort', `${w.name} escorts the surveyor ${path.length} hex${path.length > 1 ? 'es' : ''}.`, { walkerId: w.id, path });
  if (hexToOffset(at).row === surveyorExitRow(state)) {
    sv!.status = 'exited';
    const vp = surveyorDef(state).exitVp;
    state.vp[sv!.side] += vp;
    emit('surveyor', `The surveyor reaches the far edge! Side ${sv!.side} scores ${vp} VP.`, { side: sv!.side, vp });
  }
}

function useItem(ctx: Ctx, w: WalkerState, a: Activation, action: Extract<Action, { type: 'useItem' }>) {
  const { state, emit } = ctx;
  const item = w.items.find((it) => it.uid === action.itemUid) ?? illegal('No such item');
  if (!isWorking(w, item)) illegal('That item is destroyed');
  const def = getEquipment(item.id);
  if (item.uses !== null && item.uses <= 0) illegal(`${def.name} has no uses left`);
  const useUp = () => {
    if (item.uses !== null) item.uses -= 1;
  };
  switch (item.id) {
    case 'jump-jets': {
      if (w.prone) illegal('Prone war-walkers cannot jump');
      const dest = action.hex ?? illegal('Jump needs a destination hex');
      const d = distance(w.pos, dest);
      if (d < 1 || d > 3) illegal('Jump range is 1-3 hexes');
      if (!enterable(state, dest)) illegal('Cannot land there');
      spend(a, def.pressure);
      const from = w.pos;
      w.pos = dest;
      w.facing = action.facing ?? facingTowards(from, dest);
      w.anchored = false;
      a.moved = true;
      w.lastMoveDistance += d;
      emit('jump', `${w.name} jumps ${d} hexes.`, { walkerId: w.id, hex: dest });
      addOverpressure(ctx, w, 1);
      return;
    }
    case 'anchor-spikes': {
      if (w.prone) illegal('Prone war-walkers cannot anchor');
      if (w.anchored) illegal('Already anchored');
      spend(a, def.pressure);
      w.anchored = true;
      emit('anchor', `${w.name} drives in its anchor spikes.`, { walkerId: w.id });
      return;
    }
    case 'coolant-loop': {
      spend(a, def.pressure);
      w.overpressure = Math.max(0, w.overpressure - 2);
      emit('coolant', `${w.name} runs its coolant loop.`, { walkerId: w.id });
      return;
    }
    case 'smoke-launcher': {
      const hex = action.hex ?? w.pos;
      if (distance(w.pos, hex) > 1 || !hexInfo(state, hex)) illegal('Smoke must go in this or an adjacent hex');
      spend(a, def.pressure);
      useUp();
      if (!state.smoke.includes(hexKey(hex))) state.smoke.push(hexKey(hex));
      emit('smoke', `${w.name} lays smoke.`, { walkerId: w.id, hex });
      return;
    }
    case 'spotter-drone': {
      const t = getWalker(state, action.walkerId ?? illegal('Spotter needs a target'));
      if (t.destroyed || t.side === w.side) illegal('Spotter must mark an enemy');
      const d = distance(w.pos, t.pos);
      if (d > 8) illegal('Spotter range is 8');
      if (d > 4 && !lineOfSight(state, w.pos, t.pos).clear) illegal('Spotter needs line of sight beyond 4 hexes');
      spend(a, def.pressure);
      t.spottedBy = w.side;
      emit('spot', `${w.name}'s drone marks ${t.name}.`, { walkerId: w.id, targetId: t.id });
      return;
    }
    case 'field-repair-rig': {
      const t = action.walkerId ? getWalker(state, action.walkerId) : w;
      if (t.destroyed || t.side !== w.side || distance(w.pos, t.pos) > 1) illegal('Repair needs this or an adjacent friendly war-walker');
      const zone = action.zone ?? illegal('Repair needs a zone');
      const loc: Location = zone === 'coreFront' || zone === 'coreRear' ? 'core' : zone;
      if (t.destroyedLocations.includes(loc)) illegal('Cannot repair a destroyed location');
      spend(a, def.pressure);
      useUp();
      t.armour[zone] = Math.min(t.maxArmour[zone], t.armour[zone] + 2);
      emit('repair', `${w.name} patches ${t.name}'s ${zone}.`, { walkerId: w.id, targetId: t.id, zone });
      return;
    }
    default:
      illegal(`${def.name} is not used as an action`);
  }
}

function endActivation(ctx: Ctx, w: WalkerState, reactivate: boolean) {
  const { state, emit } = ctx;
  state.active = null;
  for (const it of w.items) it.firedThisActivation = false;
  if (reactivate) {
    if (w.trait !== 'tactician' || w.tacticianUsed) illegal('Only an unused Tactician can activate again');
    if (w.destroyed) illegal('Destroyed');
    w.tacticianUsed = true;
    state.pendingTactician = w.id;
    emit('tactician', `${w.name}'s Tactician driver presses on.`, { walkerId: w.id });
    return;
  }
  w.activated = true;
  emit('end', `${w.name} ends its activation.`, { walkerId: w.id });
  advanceTurn(ctx);
}

function advanceTurn(ctx: Ctx) {
  const { state } = ctx;
  if (state.phase === 'over') return;
  const other = (1 - state.activeSide) as Side;
  if (canActivate(state, other)) state.activeSide = other;
  else if (!canActivate(state, state.activeSide)) endPhase(ctx);
}

// ---------------------------------------------------------------- dice and damage

interface DieResult {
  roll: number;
  hit: boolean;
  crit: boolean;
}

function rollAttack(ctx: Ctx, w: WalkerState, dice: number, tn: number, critOn: number): DieResult[] {
  const { state, emit } = ctx;
  const judge = (roll: number): DieResult => {
    const hit = roll === 6 || (roll !== 1 && roll >= tn);
    return { roll, hit, crit: hit && roll >= critOn };
  };
  const results = Array.from({ length: dice }, () => judge(d6(state.rng)));
  const miss = results.findIndex((r) => !r.hit);
  if (miss >= 0 && w.trait === 'ace' && !w.aceUsed) {
    w.aceUsed = true;
    results[miss] = judge(d6(state.rng));
    emit('reroll', `${w.name}'s Ace driver rerolls a miss.`, { walkerId: w.id });
  }
  emit('roll', `Rolled ${results.map((r) => r.roll).join(', ')}: ${results.filter((r) => r.hit).length} hit(s).`, {
    rolls: results.map((r) => r.roll),
    tn,
  });
  return results;
}

interface HitProfile {
  damage: number;
  pierce: number;
  overpressure: number;
  drain: number;
}

function rollLocation(ctx: Ctx, attacker: WalkerState, t: WalkerState): { loc: Location; rear: boolean } {
  const arc = arcOf(t.pos, t.facing, attacker.pos);
  const roll = () => {
    const r = d6(ctx.state.rng);
    return r <= 2 ? 'legs' : r === 3 ? 'armLeft' : r === 4 ? 'armRight' : 'core';
  };
  let loc: Location = roll();
  if ((arc === 'left' && loc === 'armRight') || (arc === 'right' && loc === 'armLeft')) loc = roll();
  if (loc !== 'core' && t.destroyedLocations.includes(loc)) loc = 'core';
  return { loc, rear: arc === 'rear' };
}

function resolveHits(ctx: Ctx, attacker: WalkerState, t: WalkerState, rolls: DieResult[], hit: HitProfile) {
  const { state, emit } = ctx;
  for (const r of rolls) {
    if (!r.hit || t.destroyed) continue;
    if (!t.reactiveUsed && hasWorking(t, 'reactive-shell')) {
      t.reactiveUsed = true;
      emit('reactive', `${t.name}'s reactive shell shrugs off a hit.`, { walkerId: t.id });
      continue;
    }
    const { loc, rear } = rollLocation(ctx, attacker, t);
    let dmg = hit.damage;
    if (dmg > 0 && t.reserve > 0 && hasWorking(t, 'kinetic-shield')) {
      const blocked = Math.min(t.reserve, dmg);
      t.reserve -= blocked;
      dmg -= blocked;
      emit('shield', `${t.name}'s kinetic shield absorbs ${blocked} damage.`, { walkerId: t.id });
    }
    const zone: Zone = loc === 'core' ? (rear ? 'coreRear' : 'coreFront') : loc;
    const absorbable = Math.max(0, t.armour[zone] - hit.pierce);
    const toArmour = Math.min(dmg, absorbable);
    t.armour[zone] -= toArmour;
    const toStructure = dmg - toArmour;
    emit('hit', `${t.name} takes ${dmg} damage to the ${zone}${toStructure ? `, ${toStructure} to structure` : ''}.`, {
      walkerId: t.id,
      zone,
      damage: dmg,
      structure: toStructure,
    });
    if (toStructure > 0) damageStructure(ctx, t, loc, toStructure);
    if (hit.overpressure && !t.destroyed) addOverpressure(ctx, t, hit.overpressure);
    if (hit.drain && !t.destroyed) t.pendingDrain += hit.drain;
    let crits = (toStructure > 0 ? 1 : 0) + (r.crit ? 1 : 0);
    while (crits-- > 0 && !t.destroyed) critical(ctx, t, loc);
  }
  if (state.phase === 'over') state.active = null;
}

function damageStructure(ctx: Ctx, t: WalkerState, loc: Location, n: number) {
  if (t.destroyed) return;
  if (loc !== 'core' && t.destroyedLocations.includes(loc)) loc = 'core';
  t.structure[loc] = Math.max(0, t.structure[loc] - n);
  if (t.structure[loc] > 0) return;
  if (!t.destroyedLocations.includes(loc)) t.destroyedLocations.push(loc);
  if (loc === 'core') destroyWalker(ctx, t);
  else ctx.emit('location', `${t.name}'s ${loc} is destroyed.`, { walkerId: t.id, location: loc });
}

function critical(ctx: Ctx, t: WalkerState, hitLoc: Location) {
  const { state, emit } = ctx;
  const loc: Location = hitLoc !== 'core' && t.destroyedLocations.includes(hitLoc) ? 'core' : hitLoc;
  const roll = d6(state.rng);
  if (roll <= 2) {
    const candidates = workingItems(t).filter((it) => it.location === loc);
    if (candidates.length) {
      const it = pick(state.rng, candidates);
      it.destroyed = true;
      emit('critical', `Critical: ${t.name}'s ${getEquipment(it.id).name} is destroyed.`, { walkerId: t.id, itemUid: it.uid });
    } else {
      emit('critical', `Critical: ${t.name} takes 1 extra structure damage.`, { walkerId: t.id });
      damageStructure(ctx, t, loc, 1);
    }
  } else if (roll === 3) {
    emit('critical', `Critical: ${t.name}'s boiler is breached.`, { walkerId: t.id });
    addOverpressure(ctx, t, 2);
  } else if (roll === 4) {
    t.actuator[loc] = true;
    emit('critical', `Critical: ${t.name}'s ${loc} actuator is damaged.`, { walkerId: t.id, location: loc });
  } else if (roll === 5) {
    if (t.anchored && hasWorking(t, 'anchor-spikes')) {
      emit('critical', `Critical: ${t.name} is rocked but its anchors hold.`, { walkerId: t.id });
    } else {
      t.prone = true;
      emit('critical', `Critical: ${t.name} is knocked down.`, { walkerId: t.id });
    }
  } else {
    emit('critical', `Critical: a shot goes clean through ${t.name}'s core.`, { walkerId: t.id });
    damageStructure(ctx, t, 'core', 1);
  }
}

function addOverpressure(ctx: Ctx, w: WalkerState, n: number) {
  if (w.destroyed) return;
  w.overpressure += n;
  if (w.overpressure < OVERPRESSURE_LIMIT) return;
  w.overpressure = 0;
  const active = ctx.state.active?.walkerId === w.id;
  if (active) ctx.state.active!.forceEnd = true;
  else w.skipNext = true;
  ctx.emit('valve', `${w.name}'s safety valve blows!`, { walkerId: w.id });
}

function push(ctx: Ctx, attacker: WalkerState, t: WalkerState) {
  if (t.anchored && hasWorking(t, 'anchor-spikes')) return;
  const dir = directionTo(attacker.pos, t.pos);
  const dest = neighbor(t.pos, dir);
  if (!enterable(ctx.state, dest)) return;
  t.pos = dest;
  ctx.emit('push', `${t.name} is knocked back a hex.`, { walkerId: t.id, hex: dest });
}

function destroyWalker(ctx: Ctx, t: WalkerState) {
  const { state, emit } = ctx;
  t.destroyed = true;
  state.wrecks.push(hexKey(t.pos));
  const scorer = (1 - t.side) as Side;
  const vp = Math.ceil(t.cost / 4);
  state.vp[scorer] += vp;
  emit('destroyed', `${t.name} is destroyed! Side ${scorer} scores ${vp} VP.`, { walkerId: t.id, side: scorer, vp });
  if (state.pendingTactician === t.id) state.pendingTactician = null;
  if (aliveWalkers(state, t.side).length === 0) finish(ctx, scorer);
}

// ---------------------------------------------------------------- rounds

function startRound(state: GameState, events: GameEvent[]) {
  const best = (side: Side) => Math.max(0, ...aliveWalkers(state, side).map((w) => w.command));
  let r0 = 0;
  let r1 = 0;
  while (r0 === r1) {
    r0 = d6(state.rng) + best(0);
    r1 = d6(state.rng) + best(1);
  }
  state.activeSide = r0 > r1 ? 0 : 1;
  events.push({ type: 'round', text: `Round ${state.round}. Side ${state.activeSide} wins initiative (${r0} vs ${r1}).`, round: state.round });
}

function endPhase(ctx: Ctx) {
  const { state, emit } = ctx;
  for (const o of state.objectives) {
    // Control goes to the side with more total chassis Size on or next to the objective.
    const weight = (side: Side) =>
      aliveWalkers(state, side)
        .filter((w) => distance(w.pos, o.hex) <= 1)
        .reduce((sum, w) => sum + w.size, 0);
    const h0 = weight(0);
    const h1 = weight(1);
    if (h0 !== h1) {
      const side: Side = h0 > h1 ? 0 : 1;
      state.vp[side] += o.vp;
      emit('objective', `Side ${side} holds an objective for ${o.vp} VP.`, { side, vp: o.vp, hex: o.hex });
    }
  }
  for (const w of aliveWalkers(state)) {
    w.overpressure = Math.max(0, w.overpressure - 1);
    w.reserve = 0;
    w.spottedBy = null;
    w.activated = false;
    w.aceUsed = false;
    w.reactiveUsed = false;
  }
  state.smoke = [];
  state.passesUsed = [0, 0];
  emit('endPhase', `End of round ${state.round}. Score ${state.vp[0]} - ${state.vp[1]}.`, { vp: [...state.vp] });
  if (state.round >= state.rounds) {
    finish(ctx, state.vp[0] === state.vp[1] ? 'draw' : state.vp[0] > state.vp[1] ? 0 : 1);
    return;
  }
  state.round += 1;
  const events: GameEvent[] = [];
  startRound(state, events);
  for (const e of events) emit(e.type, e.text, e);
}

function finish(ctx: Ctx, winner: Side | 'draw') {
  const { state, emit } = ctx;
  if (state.phase === 'over') return;
  state.phase = 'over';
  state.winner = winner;
  state.active = null;
  emit('over', winner === 'draw' ? 'The Trial ends in a draw.' : `Side ${winner} wins the Charter.`, { winner });
}

// ---------------------------------------------------------------- legal actions

/**
 * Every legal action in the current state. Movement is reduced to one
 * cheapest path per reachable hex, ending with the facing that path gives.
 */
export function legalActions(state: GameState): Action[] {
  if (state.phase === 'over') return [];
  const candidates: Action[] = [];
  const a = state.active;
  if (state.phase === 'deployment') {
    const zone = deploymentZone(state, state.activeSide);
    for (const w of deployable(state)) for (const hex of zone) candidates.push({ type: 'deploy', walkerId: w.id, hex });
  } else if (!a) {
    for (const w of aliveWalkers(state, state.activeSide)) {
      if (w.activated) continue;
      for (let throttle = 0; throttle <= MAX_THROTTLE; throttle++) candidates.push({ type: 'activate', walkerId: w.id, throttle });
    }
    candidates.push({ type: 'pass' });
  } else {
    const w = getWalker(state, a.walkerId);
    candidates.push({ type: 'endActivation' }, { type: 'endActivation', reactivate: true });
    if (a.pressure > 0) {
      for (const { path } of reachable(state, w, moveAllowance(state, w)).values()) candidates.push({ type: 'move', path });
      for (let f = 0; f < 6; f++) if (f !== w.facing) candidates.push({ type: 'turn', facing: f as Facing });
      candidates.push({ type: 'brace' }, { type: 'bank' }, { type: 'standUp' });
      const enemies = aliveWalkers(state, (1 - w.side) as Side);
      for (const it of workingItems(w)) {
        const def = getEquipment(it.id);
        if (def.weapon) for (const e of enemies) candidates.push({ type: 'fire', itemUid: it.uid, targetId: e.id });
        else if (it.id === 'jump-jets') {
          for (const h of Object.keys(state.map.hexes)) {
            const [q, r] = h.split(',').map(Number);
            const d = distance(w.pos, { q, r });
            if (d >= 1 && d <= 3) candidates.push({ type: 'useItem', itemUid: it.uid, hex: { q, r } });
          }
        } else if (it.id === 'spotter-drone') {
          for (const e of enemies) candidates.push({ type: 'useItem', itemUid: it.uid, walkerId: e.id });
        } else if (it.id === 'smoke-launcher') {
          for (const h of [w.pos, ...neighbors(w.pos)]) candidates.push({ type: 'useItem', itemUid: it.uid, hex: h });
        } else if (it.id === 'field-repair-rig') {
          for (const f of aliveWalkers(state, w.side).filter((f) => distance(f.pos, w.pos) <= 1)) {
            for (const zone of ['coreFront', 'coreRear', 'armLeft', 'armRight', 'legs'] as Zone[]) {
              if (f.armour[zone] < f.maxArmour[zone]) candidates.push({ type: 'useItem', itemUid: it.uid, walkerId: f.id, zone });
            }
          }
        } else candidates.push({ type: 'useItem', itemUid: it.uid });
      }
      for (const e of enemies) if (distance(e.pos, w.pos) === 1) candidates.push({ type: 'ram', targetId: e.id });
      const sv = state.surveyor;
      if (sv?.status === 'active') {
        if (sv.side !== w.side) {
          for (const it of workingItems(w)) if (getEquipment(it.id).weapon) candidates.push({ type: 'fire', itemUid: it.uid, targetId: SURVEYOR_ID });
        } else if (distance(sv.pos, w.pos) === 1) {
          for (const n of neighbors(sv.pos)) {
            candidates.push({ type: 'escort', path: [n] });
            for (const m of neighbors(n)) if (!hexEq(m, sv.pos)) candidates.push({ type: 'escort', path: [n, m] });
          }
        }
      }
    }
  }
  return candidates.filter((action) => {
    try {
      applyAction(state, action);
      return true;
    } catch (e) {
      if (e instanceof IllegalAction) return false;
      throw e;
    }
  });
}
