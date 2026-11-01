// Hard rules (a failure rejects the board) and the measurements behind them.
// Works on any map, generated or hand-made, so the hand-made boards can be
// checked against the same rules.
import { RANGE_BANDS, type ObjectiveDef } from '../data';
import { lineOfSight } from '../engine';
import { distance, hexToOffset, neighbors, offsetToHex, type Hex, type Offset } from '../hex';
import { Board, Probe, objectiveKey } from './board';

export type RuleId = 'H1' | 'H2' | 'H3' | 'H4' | 'H5' | 'H6' | 'H7' | 'H8' | 'H9';

export const RULE_NAMES: Record<RuleId, string> = {
  H1: 'Symmetry',
  H2: 'Room to deploy',
  H3: 'Connected',
  H4: 'Objectives reachable',
  H5: 'Objectives contestable',
  H6: 'Objective spacing',
  H7: 'No shooting gallery',
  H8: 'Cover on the approach',
  H9: 'No dominant perch',
};

/** Thresholds for the hard rules. Starting values, tuned with the sweep and sims. */
export const LIMITS = {
  deployPassable: 0.75, // H2: share of each zone a walker can stand in
  reachCost: [2, 9] as [number, number], // H4: cheapest movement cost from a zone to each objective
  holdRing: 5, // H5: passable hexes among an objective and its 6 neighbours
  objectiveSpacing: 3, // H6
  zoneClearance: 2, // H6
  zoneLos: 0.35, // H7: share of zone-to-zone hex pairs in range with clear LOS
  coverReach: 2, // H8: cover within this many hexes of the approach path
  perchShare: 0.5, // H9: share of the enemy zone one elevated hex at home may see
};

export type Limits = typeof LIMITS;

export interface CheckOptions {
  /** Override thresholds (an archetype may allow more open sightlines, for example). */
  limits?: Partial<Limits>;
  /** Stop at the first failed rule. The generator uses this to skip the slow sight checks on boards already rejected. */
  stopOnFail?: boolean;
}

export interface RuleResult {
  rule: RuleId;
  ok: boolean;
  detail: string;
}

export interface BoardReport {
  ok: boolean;
  results: RuleResult[];
  /** Measurements reused by the soft scores. */
  zoneLos: number;
  /** Cheapest cost from each side's zone to each objective, in objective order. */
  reach: [number[], number[]];
}

export const zoneRows = (board: Board, depth: number, side: 0 | 1): [number, number] =>
  side === 0 ? [0, depth - 1] : [board.height - depth, board.height - 1];

export function zoneOffsets(board: Board, depth: number, side: 0 | 1): Offset[] {
  const [lo, hi] = zoneRows(board, depth, side);
  const out: Offset[] = [];
  for (let row = lo; row <= hi; row++) for (let col = 0; col < board.width; col++) out.push({ col, row });
  return out;
}

export interface PathField {
  cost: Float64Array;
  prev: Int32Array;
}

/** Cheapest movement cost from a set of start hexes to every hex, using the engine's step cost. */
export function costField(probe: Probe, starts: Offset[], blocked?: Set<number>): PathField {
  const b = probe.board;
  const n = b.width * b.height;
  const cost = new Float64Array(n).fill(Infinity);
  const prev = new Int32Array(n).fill(-1);
  const open: number[] = [];
  for (const s of starts) {
    const i = b.index(s.col, s.row);
    if (!probe.passable(s) || blocked?.has(i)) continue;
    cost[i] = 0;
    open.push(i);
  }
  const done = new Uint8Array(n);
  while (open.length) {
    let best = 0;
    for (let k = 1; k < open.length; k++) if (cost[open[k]] < cost[open[best]]) best = k;
    const i = open.splice(best, 1)[0];
    if (done[i]) continue;
    done[i] = 1;
    const o = { col: i % b.width, row: Math.floor(i / b.width) };
    const h = offsetToHex(o);
    for (const nh of neighbors(h)) {
      const no = hexToOffset(nh);
      if (!probe.passable(no)) continue;
      const j = b.index(no.col, no.row);
      if (blocked?.has(j)) continue;
      const c = cost[i] + probe.step(h, nh);
      if (c < cost[j]) {
        cost[j] = c;
        prev[j] = i;
        open.push(j);
      }
    }
  }
  return { cost, prev };
}

export function pathTo(field: PathField, board: Board, target: Offset): Offset[] {
  const out: Offset[] = [];
  let i = board.index(target.col, target.row);
  if (!Number.isFinite(field.cost[i])) return out;
  while (i >= 0) {
    out.unshift({ col: i % board.width, row: Math.floor(i / board.width) });
    i = field.prev[i];
  }
  return out;
}

const maxRange = RANGE_BANDS.long[1];

/** Clear line of sight between two hexes within long range, by the engine's rules. */
export const sees = (probe: Probe, a: Hex, b: Hex) => distance(a, b) <= maxRange && lineOfSight(probe.state, a, b).clear;

class Stop extends Error {}

export function checkBoard(board: Board, objectives: ObjectiveDef[], depth: number, options: CheckOptions = {}): BoardReport {
  const L: Limits = { ...LIMITS, ...options.limits };
  const probe = new Probe(board);
  const results: RuleResult[] = [];
  let zoneLos = 1;
  let reach: [number[], number[]] = [[], []];
  const add = (rule: RuleId, ok: boolean, detail: string) => {
    results.push({ rule, ok, detail });
    if (!ok && options.stopOnFail) throw new Stop();
  };
  try {
    runRules();
  } catch (e) {
    if (!(e instanceof Stop)) throw e;
  }
  results.sort((a, b) => Number(a.rule.slice(1)) - Number(b.rule.slice(1)));
  return { ok: results.every((r) => r.ok) && results.length === 9, results, zoneLos, reach };

  function runRules() {
  const zones = [zoneOffsets(board, depth, 0), zoneOffsets(board, depth, 1)] as const;

  // H1 Symmetry
  let asym = 0;
  for (const { col, row } of board.offsets()) {
    const p = board.partner(col, row);
    const a = board.get(col, row);
    const b = board.get(p.col, p.row);
    if (a.terrain !== b.terrain || a.elevation !== b.elevation) asym++;
  }
  const objVp = new Map(objectives.map((o) => [objectiveKey(o), o.vp]));
  const lopsided = objectives.filter((o) => objVp.get(objectiveKey(board.partner(o.col, o.row))) !== o.vp).length;
  add('H1', asym === 0 && lopsided === 0, `${asym} hexes and ${lopsided} objectives without a matching partner`);

  // H2 Room to deploy
  const room = zones.map((z) => z.filter((o) => probe.passable(o)).length / z.length);
  add('H2', room.every((r) => r >= L.deployPassable), `passable share of zones ${room.map((r) => r.toFixed(2)).join(' / ')}`);

  // H3 Connected
  const passableAll = [...board.offsets()].filter((o) => probe.passable(o));
  const fromFirst = costField(probe, passableAll.slice(0, 1));
  const pockets = passableAll.filter((o) => !Number.isFinite(fromFirst.cost[board.index(o.col, o.row)])).length;
  add('H3', pockets === 0, `${pockets} passable hexes cut off`);

  // H4 Objectives reachable
  const fields = [costField(probe, zones[0]), costField(probe, zones[1])] as const;
  reach = fields.map((f) => objectives.map((o) => f.cost[board.index(o.col, o.row)])) as [number[], number[]];
  const [lo, hi] = L.reachCost;
  const badReach = reach.flat().filter((c) => !(c >= lo && c <= hi)).length;
  add('H4', badReach === 0, `costs side 0 [${reach[0].join(', ')}], side 1 [${reach[1].join(', ')}]`);

  // H5 Objectives contestable
  const rings = objectives.map((o) => {
    const h = offsetToHex(o);
    return [h, ...neighbors(h)].filter((x) => probe.passable(hexToOffset(x))).length;
  });
  add('H5', rings.every((r) => r >= L.holdRing), `passable hexes around objectives [${rings.join(', ')}]`);

  // H6 Objective spacing
  let tooClose = 0;
  for (let i = 0; i < objectives.length; i++) {
    for (let j = i + 1; j < objectives.length; j++) {
      const a = objectives[i];
      const b = objectives[j];
      const p = board.partner(a.col, a.row);
      const centrePair = p.col === b.col && p.row === b.row && distance(offsetToHex(a), offsetToHex(b)) === 1;
      if (!centrePair && distance(offsetToHex(a), offsetToHex(b)) < L.objectiveSpacing) tooClose++;
    }
  }
  const nearZone = objectives.filter((o) => {
    const h = offsetToHex(o);
    return zones.some((z) => z.some((zo) => distance(offsetToHex(zo), h) < L.zoneClearance));
  }).length;
  add('H6', tooClose === 0 && nearZone === 0, `${tooClose} objective pairs too close, ${nearZone} objectives too near a zone`);

  // H7 No shooting gallery
  let pairs = 0;
  let clear = 0;
  const z0 = zones[0].filter((o) => probe.passable(o)).map(offsetToHex);
  const z1 = zones[1].filter((o) => probe.passable(o)).map(offsetToHex);
  // Sampled on alternate hexes of each zone (a quarter of the pairs): the share barely moves and the check is 4x faster.
  const alt = (h: Hex) => {
    const o = hexToOffset(h);
    return (o.col + o.row) % 2 === 0;
  };
  for (const a of z0.filter(alt)) {
    for (const b of z1.filter(alt)) {
      if (distance(a, b) > maxRange) continue;
      pairs++;
      if (lineOfSight(probe.state, a, b).clear) clear++;
    }
  }
  zoneLos = pairs ? clear / pairs : 0;
  add('H7', zoneLos <= L.zoneLos, `${(zoneLos * 100).toFixed(0)}% of zone-to-zone pairs in range have clear LOS`);

  // H8 Cover on the approach
  const isCover = (o: Offset) => {
    const t = board.get(o.col, o.row).terrain;
    return t === 'light' || t === 'heavy';
  };
  const coverHexes = [...board.offsets()].filter(isCover).map(offsetToHex);
  let bare = 0;
  for (const side of [0, 1] as const) {
    for (const o of objectives) {
      const path = pathTo(fields[side], board, o).map(offsetToHex);
      if (!path.length || !path.some((p) => coverHexes.some((c) => distance(c, p) <= L.coverReach))) bare++;
    }
  }
  add('H8', bare === 0, `${bare} approaches with no cover nearby`);

  // H9 No dominant perch
  let worst = 0;
  for (const o of board.offsets()) {
    if (board.get(o.col, o.row).elevation < 1 || !probe.passable(o)) continue;
    // Only firing positions a side reaches without leaving home: its zone and the row in front.
    const home0 = o.row <= depth;
    const home1 = o.row >= board.height - 1 - depth;
    if (!home0 && !home1) continue;
    const enemy = home0 ? z1 : z0;
    const h = offsetToHex(o);
    const seen = enemy.filter((e) => sees(probe, h, e)).length / Math.max(1, enemy.length);
    worst = Math.max(worst, seen);
  }
  add('H9', worst <= L.perchShare, `best perch sees ${(worst * 100).toFixed(0)}% of the enemy zone`);

  }
}
