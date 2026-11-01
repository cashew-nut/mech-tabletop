// Soft scores that rank boards which pass every hard rule, and a distance
// between boards used to check that seeds give different ground.
import { RANGE_BANDS, type ObjectiveDef } from '../data';
import { distance, offsetToHex, type Offset } from '../hex';
import { Board, Probe } from './board';
import { costField, pathTo, sees, zoneOffsets, type BoardReport } from './validate';

export interface SoftScores {
  routes: number;
  objectiveCover: number;
  sightlines: number;
  rangeMix: number;
  flanks: number;
  tension: number;
  budget: number;
  closed: number;
  total: number;
}

const WEIGHTS: Omit<SoftScores, 'total'> = {
  routes: 3,
  objectiveCover: 2,
  sightlines: 2,
  rangeMix: 1,
  flanks: 2,
  tension: 2,
  budget: 2,
  closed: 1,
};

/** 1 inside [lo, hi], falling away linearly over `soft` outside it. */
const band = (x: number, lo: number, hi: number, soft: number) => (x < lo ? Math.max(0, 1 - (lo - x) / soft) : x > hi ? Math.max(0, 1 - (x - hi) / soft) : 1);

export const nonOpenShare = (board: Board) => board.cells.filter((c) => c.terrain !== 'open' || c.elevation !== 0).length / board.cells.length;

/** Routes from side 0's zone to the middle that share at most their last two hexes. */
export function countRoutes(board: Board, depth: number, target: Offset): number {
  const probe = new Probe(board);
  const zone = zoneOffsets(board, depth, 0);
  const blocked = new Set<number>();
  let first = Infinity;
  let routes = 0;
  for (let k = 0; k < 4; k++) {
    const field = costField(probe, zone, blocked);
    const c = field.cost[board.index(target.col, target.row)];
    if (!Number.isFinite(c) || c > first + 2) break;
    first = Math.min(first, c);
    routes++;
    const path = pathTo(field, board, target);
    for (const o of path.slice(0, -2)) if (o.row >= depth) blocked.add(board.index(o.col, o.row));
  }
  return routes;
}

export function softScores(board: Board, objectives: ObjectiveDef[], depth: number, report: BoardReport, budget: [number, number], zoneLosLimit = 0.35): SoftScores {
  const probe = new Probe(board);
  const passable = [...board.offsets()].filter((o) => probe.passable(o)).map(offsetToHex);
  const centre = { col: board.width / 2 - 1, row: board.height / 2 - 1 };

  const routes = (Math.min(countRoutes(board, depth, centre), 4) - 1) / 3;

  const seenShare = objectives.map((o) => {
    const h = offsetToHex(o);
    return passable.filter((p) => sees(probe, h, p)).length / passable.length;
  });
  const avgSeen = seenShare.reduce((s, x) => s + x, 0) / Math.max(1, seenShare.length);
  const sightlines = band(avgSeen, 0.35, 0.5, 0.2);

  const bands = new Set<string>();
  for (const z of zoneOffsets(board, depth, 0)) {
    if (!probe.passable(z)) continue;
    const zh = offsetToHex(z);
    for (const o of objectives) {
      const oh = offsetToHex(o);
      if (!sees(probe, zh, oh)) continue;
      const d = distance(zh, oh);
      bands.add(d <= RANGE_BANDS.short[1] ? 'short' : d <= RANGE_BANDS.medium[1] ? 'medium' : 'long');
    }
  }
  const rangeMix = bands.size / 3;

  const thirds = [0, 0, 0];
  for (const { col, row } of board.offsets()) {
    if (board.isOpen(col, row)) continue;
    thirds[Math.min(2, Math.floor((col * 3) / board.width))]++;
  }
  const totalFeatures = thirds.reduce((s, x) => s + x, 0);
  const flanks = totalFeatures ? Math.min(1, (Math.min(...thirds) / totalFeatures) * 3) : 0;

  // Tension: in each objective pair, how much nearer one is than the other.
  const gaps: number[] = [];
  objectives.forEach((o, i) => {
    const p = board.partner(o.col, o.row);
    const j = objectives.findIndex((x) => x.col === p.col && x.row === p.row);
    if (j > i && distance(offsetToHex(o), offsetToHex(p)) > 1) gaps.push(Math.abs(report.reach[0][i] - report.reach[0][j]));
  });
  const tension = gaps.length ? gaps.reduce((s, g) => s + band(g, 2, 4, 3), 0) / gaps.length : 1;

  const budgetScore = band(nonOpenShare(board), budget[0], budget[1], 0.08);
  const closed = Math.max(0, 1 - report.zoneLos / zoneLosLimit);

  // Objectives with cover or a wall right next to them make fights around them.
  const coverTypes = new Set(['light', 'heavy', 'blocking']);
  const objectiveCover =
    objectives.filter((o) => {
      const h = offsetToHex(o);
      return [...board.offsets()].some((p) => coverTypes.has(board.get(p.col, p.row).terrain) && distance(offsetToHex(p), h) === 1);
    }).length / Math.max(1, objectives.length);

  const parts = { routes, objectiveCover, sightlines, rangeMix, flanks, tension, budget: budgetScore, closed };
  const wsum = Object.values(WEIGHTS).reduce((s, w) => s + w, 0);
  const total = (Object.keys(WEIGHTS) as Array<keyof typeof WEIGHTS>).reduce((s, k) => s + parts[k] * WEIGHTS[k], 0) / wsum;
  return { ...parts, total };
}

/**
 * Distance between two boards: 0 is identical, 1 is nothing in common.
 * Mostly the share of featured hexes that differ, plus how many objectives
 * have no counterpart within one hex on the other board.
 */
export function boardDistance(a: { board: Board; objectives: ObjectiveDef[] }, b: { board: Board; objectives: ObjectiveDef[] }): number {
  const feat = (x: Board) => {
    const s = new Set<string>();
    for (const { col, row } of x.offsets()) {
      const c = x.get(col, row);
      if (c.terrain !== 'open' || c.elevation !== 0) s.add(`${col},${row},${c.terrain},${c.elevation}`);
    }
    return s;
  };
  const fa = feat(a.board);
  const fb = feat(b.board);
  let both = 0;
  for (const k of fa) if (fb.has(k)) both++;
  const union = fa.size + fb.size - both;
  const terrain = union ? 1 - both / union : 0;
  const unmatched = (xs: ObjectiveDef[], ys: ObjectiveDef[]) =>
    xs.filter((x) => !ys.some((y) => distance(offsetToHex(x), offsetToHex(y)) <= 1)).length;
  const total = a.objectives.length + b.objectives.length;
  const objectives = total ? (unmatched(a.objectives, b.objectives) + unmatched(b.objectives, a.objectives)) / total : 0;
  return 0.8 * terrain + 0.2 * objectives;
}
