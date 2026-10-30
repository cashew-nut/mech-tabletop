// Pointy-top hex grid. Positions are axial (q, r); the map is stored as
// offset columns and rows ("odd-r": odd rows shift half a hex right).
// Facing 0..5 = E, NE, NW, W, SW, SE (counter-clockwise, 60 degrees apart).

export interface Hex {
  q: number;
  r: number;
}

export interface Offset {
  col: number;
  row: number;
}

export type Facing = 0 | 1 | 2 | 3 | 4 | 5;

export const DIRECTIONS: readonly Hex[] = [
  { q: 1, r: 0 },
  { q: 1, r: -1 },
  { q: 0, r: -1 },
  { q: -1, r: 0 },
  { q: -1, r: 1 },
  { q: 0, r: 1 },
];

export const hexKey = (h: Hex): string => `${h.q},${h.r}`;
export const hexEq = (a: Hex, b: Hex): boolean => a.q === b.q && a.r === b.r;
export const hexAdd = (a: Hex, b: Hex): Hex => ({ q: a.q + b.q, r: a.r + b.r });

export function neighbor(h: Hex, dir: number): Hex {
  return hexAdd(h, DIRECTIONS[((dir % 6) + 6) % 6]);
}

export function neighbors(h: Hex): Hex[] {
  return DIRECTIONS.map((d) => hexAdd(h, d));
}

export function distance(a: Hex, b: Hex): number {
  const dq = a.q - b.q;
  const dr = a.r - b.r;
  return (Math.abs(dq) + Math.abs(dr) + Math.abs(dq + dr)) / 2;
}

export function offsetToHex({ col, row }: Offset): Hex {
  return { q: col - (row - (row & 1)) / 2, r: row };
}

export function hexToOffset({ q, r }: Hex): Offset {
  return { col: q + (r - (r & 1)) / 2, row: r };
}

/** Hex centre in a y-up plane, hex size 1. */
export function hexToPoint({ q, r }: Hex): { x: number; y: number } {
  return { x: Math.sqrt(3) * (q + r / 2), y: -1.5 * r };
}

/** Direction index of the step from a to an adjacent hex b, or -1. */
export function directionTo(a: Hex, b: Hex): number {
  return DIRECTIONS.findIndex((d) => d.q === b.q - a.q && d.r === b.r - a.r);
}

/** Facing that points most directly from a towards b. */
export function facingTowards(a: Hex, b: Hex): Facing {
  const pa = hexToPoint(a);
  const pb = hexToPoint(b);
  const deg = (Math.atan2(pb.y - pa.y, pb.x - pa.x) * 180) / Math.PI;
  return (((Math.round(deg / 60) % 6) + 6) % 6) as Facing;
}

export type Arc = 'front' | 'left' | 'right' | 'rear';

/** Which arc of a unit at `from` facing `facing` the hex `to` lies in. */
export function arcOf(from: Hex, facing: Facing, to: Hex): Arc {
  const pa = hexToPoint(from);
  const pb = hexToPoint(to);
  const deg = (Math.atan2(pb.y - pa.y, pb.x - pa.x) * 180) / Math.PI;
  let rel = deg - facing * 60;
  rel = ((((rel + 180) % 360) + 360) % 360) - 180;
  const eps = 1e-6;
  if (Math.abs(rel) <= 90 + eps) return 'front';
  if (Math.abs(rel) >= 150 - eps) return 'rear';
  return rel > 0 ? 'left' : 'right';
}

function cubeRound(q: number, r: number): Hex {
  const s = -q - r;
  let rq = Math.round(q);
  let rr = Math.round(r);
  const rs = Math.round(s);
  const dq = Math.abs(rq - q);
  const dr = Math.abs(rr - r);
  const ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs;
  else if (dr > ds) rr = -rq - rs;
  return { q: rq + 0, r: rr + 0 };
}

/**
 * Hexes on the line from a to b, inclusive, nudged to one side. Calling with
 * nudge +1 and -1 gives the two candidate lines when the true line runs along
 * a hex edge.
 */
export function lineBetween(a: Hex, b: Hex, nudge: 1 | -1 = 1): Hex[] {
  const n = distance(a, b);
  const eps = 1e-6 * nudge;
  const out: Hex[] = [];
  for (let i = 0; i <= n; i++) {
    const t = n === 0 ? 0 : i / n;
    const q = a.q + eps + (b.q - a.q) * t;
    const r = a.r + eps + (b.r - a.r) * t;
    out.push(cubeRound(q, r));
  }
  return out;
}
