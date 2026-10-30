// A greedy utility AI for Brass Charter. Each call picks one action for the
// side to move: activate the war-walker with the best opportunity, move to
// the hex that best trades damage dealt against damage risked and objective
// value, fire the best shots it can afford, then spend what is left.
import {
  IllegalAction,
  aliveWalkers,
  applyAction,
  distance,
  facingTowards,
  getChassis,
  getEquipment,
  hexKey,
  hexInfo,
  hitChance,
  lineOfSight,
  moveAllowance,
  previewAttack,
  rangeBand,
  reachable,
  workingItems,
  type Action,
  type Facing,
  type GameState,
  type Hex,
  type Side,
  type WalkerState,
} from '@brass-charter/rules';

export interface AiOptions {
  /** How much the AI fears incoming fire relative to dealing damage (default 0.4). */
  caution?: number;
}

const BAND_TN = { melee: 4, short: 4, medium: 5, long: 6 } as const;

function legal(state: GameState, action: Action): boolean {
  try {
    applyAction(state, action);
    return true;
  } catch (e) {
    if (e instanceof IllegalAction) return false;
    throw e;
  }
}

/** Value of one attack: expected damage, plus a little for side effects, weighted to finish fragile targets. */
function shotValue(state: GameState, itemUid: string, attacker: WalkerState, target: WalkerState): { value: number; pressure: number } | null {
  const p = previewAttack(state, itemUid, target.id);
  if (!p.ok) return null;
  const def = getEquipment(attacker.items.find((i) => i.uid === itemUid)!.id);
  const wp = def.weapon!;
  const hits = p.dice * hitChance(p.tn);
  let perHit = wp.damage + (wp.pierce ?? 0) * 0.4;
  if (def.tags?.includes('overpressure')) perHit += 0.4;
  if (def.tags?.includes('drain')) perHit += 0.8;
  if (def.tags?.includes('blast')) perHit += 0.3;
  const toughness = target.armour.coreFront + target.structure.core;
  return { value: hits * perHit * (1 + 3 / Math.max(1, toughness)), pressure: p.pressure };
}

/** Best total shot value the active walker could get from its current position with `budget` Pressure. */
function attackPlanValue(state: GameState, w: WalkerState, budget: number): number {
  const enemies = aliveWalkers(state, (1 - w.side) as Side);
  const options: Array<{ uid: string; value: number; pressure: number }> = [];
  for (const it of workingItems(w)) {
    if (!getEquipment(it.id).weapon || it.firedThisActivation) continue;
    let best: { value: number; pressure: number } | null = null;
    for (const e of enemies) {
      const v = shotValue(state, it.uid, w, e);
      if (v && (!best || v.value > best.value)) best = v;
    }
    if (best) options.push({ uid: it.uid, ...best });
  }
  options.sort((a, b) => b.value / Math.max(1, b.pressure) - a.value / Math.max(1, a.pressure));
  let total = 0;
  let left = budget;
  for (const o of options) {
    if (o.pressure <= left) {
      total += o.value;
      left -= o.pressure;
    }
  }
  return total;
}

/** Rough expected damage the enemy could pour into a hex next turn. */
function threatAt(state: GameState, w: WalkerState, hex: Hex): number {
  let threat = 0;
  for (const e of aliveWalkers(state, (1 - w.side) as Side)) {
    const d = distance(e.pos, hex);
    for (const it of workingItems(e)) {
      const wp = getEquipment(it.id).weapon;
      if (!wp) continue;
      // Enemies can usually close one move before firing.
      const reach = wp.range === 'melee' ? 1 : wp.range === 'short' ? 3 : wp.range === 'medium' ? 7 : 12;
      const closing = getChassis(e.chassis).stride;
      if (d > reach + closing) continue;
      const band = wp.range === 'melee' ? 'melee' : rangeBand(Math.max(1, d - closing)) ?? 'long';
      const indirect = getEquipment(it.id).tags?.includes('indirect');
      if (!indirect && wp.range !== 'melee' && d > closing + 1 && !lineOfSight(state, e.pos, hex).clear) continue;
      threat += wp.dice * hitChance(BAND_TN[band] + 1) * wp.damage;
    }
  }
  return threat;
}

function objectiveValue(state: GameState, hex: Hex): number {
  if (!state.objectives.length) return 0;
  let value = 0;
  let nearest = Infinity;
  for (const o of state.objectives) {
    const d = distance(o.hex, hex);
    if (d <= 1) value += 2 * o.vp;
    nearest = Math.min(nearest, d);
  }
  return value - 0.15 * nearest;
}

function coverValue(state: GameState, hex: Hex): number {
  const t = hexInfo(state, hex)?.terrain;
  return t === 'heavy' ? 1 : t === 'light' ? 0.5 : 0;
}

function nearestEnemy(state: GameState, w: WalkerState, from: Hex): WalkerState | null {
  let best: WalkerState | null = null;
  for (const e of aliveWalkers(state, (1 - w.side) as Side)) {
    if (!best || distance(from, e.pos) < distance(from, best.pos)) best = e;
  }
  return best;
}

interface Spot {
  hex: Hex;
  facing: Facing;
  path: Hex[] | null;
  score: number;
}

/** Score staying put and every reachable hex for the active walker. */
function bestSpot(state: GameState, w: WalkerState, caution: number): { stay: Spot; best: Spot } {
  const eval_ = structuredClone(state);
  const ew = eval_.walkers.find((x) => x.id === w.id)!;
  const a = eval_.active!;
  const pressure = a.pressure;
  a.pressure = 99;

  const score = (hex: Hex, facing: Facing, moved: boolean, budget: number) => {
    ew.pos = hex;
    ew.facing = facing;
    a.moved = moved || state.active!.moved;
    const enemy = nearestEnemy(eval_, ew, hex);
    const approach = enemy ? -0.08 * distance(hex, enemy.pos) : 0;
    return (
      attackPlanValue(eval_, ew, budget) - caution * threatAt(eval_, ew, hex) + objectiveValue(eval_, hex) + coverValue(eval_, hex) + approach
    );
  };

  const facingFor = (hex: Hex): Facing => {
    const e = nearestEnemy(eval_, ew, hex);
    return e ? facingTowards(hex, e.pos) : ew.facing;
  };

  const stay: Spot = { hex: w.pos, facing: w.facing, path: null, score: score(w.pos, w.facing, false, pressure) };
  let best = stay;
  if (!w.prone && pressure >= 1) {
    // Look up to four Move actions ahead, but only ever take the first one.
    const allowance = moveAllowance(state, w);
    const stride = getChassis(w.chassis).stride;
    const maxMoves = Math.min(pressure, 4);
    const firstStep = reachable(state, w, allowance);
    for (const { cost, path } of reachable(state, w, allowance + stride * (maxMoves - 1)).values()) {
      const moves = cost <= allowance ? 1 : 1 + Math.ceil((cost - allowance) / stride);
      if (moves > pressure) continue;
      const hex = path[path.length - 1];
      const facing = facingFor(hex);
      const s = score(hex, facing, true, pressure - moves);
      if (s > best.score + 0.2) {
        let cut = path.length;
        while (cut > 1 && !firstStep.has(hexKey(path[cut - 1]))) cut--;
        best = { hex, facing, path: path.slice(0, cut), score: s };
      }
    }
  }
  return { stay, best };
}

function chooseActivation(state: GameState, caution: number): Action {
  const side = state.activeSide;
  let best: { action: Action; score: number } | null = null;
  for (const w of aliveWalkers(state, side)) {
    if (w.activated || (state.pendingTactician && state.pendingTactician !== w.id)) continue;
    if (w.skipNext) return { type: 'activate', walkerId: w.id };
    const needs = workingItems(w)
      .map((it) => getEquipment(it.id))
      .filter((d) => d.weapon)
      .reduce((sum, d) => sum + d.pressure, 1);
    const throttle = w.overpressure <= 1 && needs > getChassis(w.chassis).boiler ? 1 : 0;
    const action: Action = { type: 'activate', walkerId: w.id, throttle };
    let next: GameState;
    try {
      next = applyAction(state, action).state;
    } catch {
      continue;
    }
    if (!next.active) {
      if (!best) best = { action, score: -Infinity };
      continue;
    }
    const nw = next.walkers.find((x) => x.id === w.id)!;
    const { best: spot, stay } = bestSpot(next, nw, caution);
    // Prefer walkers that have something to shoot now, then those that gain most by moving.
    const s = Math.max(spot.score, stay.score) + 0.5 * attackPlanValue(next, nw, next.active.pressure);
    if (!best || s > best.score) best = { action, score: s };
  }
  return best?.action ?? { type: 'pass' };
}

function chooseWalkerAction(state: GameState, caution: number): Action {
  const a = state.active!;
  const w = state.walkers.find((x) => x.id === a.walkerId)!;
  const enemies = aliveWalkers(state, (1 - w.side) as Side);
  const tryAll = (actions: Action[]) => actions.find((x) => legal(state, x));

  if (w.prone && a.pressure >= 1) return { type: 'standUp' };

  if (a.pressure >= 1) {
    const { best, stay } = bestSpot(state, w, caution);
    if (best.path && best.score > stay.score) {
      const end = best.path[best.path.length - 1];
      const reachedGoal = hexKey(end) === hexKey(best.hex);
      const enemy = nearestEnemy(state, w, end);
      const facing = reachedGoal ? best.facing : enemy ? facingTowards(end, enemy.pos) : best.facing;
      return { type: 'move', path: best.path, facing };
    }
  }

  // Best affordable shot.
  let shot: { action: Action; value: number } | null = null;
  for (const it of workingItems(w)) {
    if (!getEquipment(it.id).weapon) continue;
    for (const e of enemies) {
      const v = shotValue(state, it.uid, w, e);
      if (v && v.value > 0.05 && (!shot || v.value > shot.value)) shot = { action: { type: 'fire', itemUid: it.uid, targetId: e.id }, value: v.value };
    }
  }
  if (shot) return shot.action;

  // Nothing to shoot: turn to face the nearest enemy if that opens up shots.
  const target = nearestEnemy(state, w, w.pos);
  if (target && a.pressure >= 2) {
    const facing = facingTowards(w.pos, target.pos);
    if (facing !== w.facing) {
      const turned = structuredClone(state);
      const tw = turned.walkers.find((x) => x.id === w.id)!;
      tw.facing = facing;
      if (attackPlanValue(turned, tw, a.pressure - 1) > 0.3) return { type: 'turn', facing };
    }
  }

  if (target && distance(target.pos, w.pos) === 1) {
    const ram = tryAll([{ type: 'ram', targetId: target.id }]);
    if (ram && a.pressure >= 2) return ram;
  }

  const utility: Action[] = [];
  for (const it of workingItems(w)) {
    if (it.id === 'coolant-loop' && w.overpressure >= 3) utility.push({ type: 'useItem', itemUid: it.uid });
    if (it.id === 'spotter-drone') {
      const mark = enemies.filter((e) => e.spottedBy !== w.side && distance(e.pos, w.pos) <= 8).sort((x, y) => distance(x.pos, w.pos) - distance(y.pos, w.pos))[0];
      if (mark) utility.push({ type: 'useItem', itemUid: it.uid, walkerId: mark.id });
    }
    if (it.id === 'field-repair-rig') {
      const zones = Object.entries(w.armour).filter(([z, v]) => v < w.maxArmour[z as keyof typeof w.maxArmour]);
      if (zones.length) utility.push({ type: 'useItem', itemUid: it.uid, zone: zones[0][0] as keyof typeof w.armour });
    }
    if (it.id === 'anchor-spikes' && !w.anchored && a.moved === false) utility.push({ type: 'useItem', itemUid: it.uid });
  }
  if (w.reserve < 2 && workingItems(w, 'kinetic-shield').length) utility.push({ type: 'bank' });
  if (!a.braced && enemies.some((e) => distance(e.pos, w.pos) <= 8)) utility.push({ type: 'brace' });
  return tryAll(utility) ?? { type: 'endActivation' };
}

/** Pick one action for the side whose turn it is. Always returns a legal action. */
export function chooseAction(state: GameState, options: AiOptions = {}): Action {
  const caution = options.caution ?? 0.4;
  const action = state.active ? chooseWalkerAction(state, caution) : chooseActivation(state, caution);
  if (legal(state, action)) return action;
  // Fall back to something that is always available.
  const fallback: Action[] = state.active
    ? [{ type: 'endActivation' }]
    : aliveWalkers(state, state.activeSide)
        .filter((w) => !w.activated)
        .map((w) => ({ type: 'activate', walkerId: w.id }) as Action);
  return fallback.find((x) => legal(state, x)) ?? { type: 'pass' };
}

/** Play a whole Trial with the AI on both sides (for tests and the balance simulator). */
export function playOut(state: GameState, options: [AiOptions?, AiOptions?] = [], maxSteps = 4000): GameState {
  let s = state;
  for (let i = 0; i < maxSteps && s.phase !== 'over'; i++) s = applyAction(s, chooseAction(s, options[s.activeSide])).state;
  return s;
}

