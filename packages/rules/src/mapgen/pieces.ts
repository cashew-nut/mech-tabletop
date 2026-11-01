// Hand-authored terrain pieces. Each is a small shape in axial offsets from an
// anchor hex, with a little seeded variation so no two ruins are quite alike.
// Boards are built from these, never from per-hex noise.
import { nextFloat, type Rng } from '../rng';
import { distance, hexToOffset, offsetToHex, type Hex } from '../hex';
import { Board, type Cell } from './board';

export type PieceType = 'ruin' | 'building' | 'hedgerow' | 'rubble' | 'hill' | 'crater' | 'scrap';

export interface PieceCell extends Hex {
  cell: Cell;
}

const chance = (rng: Rng, p: number) => nextFloat(rng) < p;
const int = (rng: Rng, lo: number, hi: number) => lo + Math.floor(nextFloat(rng) * (hi - lo + 1));

const at = (q: number, r: number, terrain: Cell['terrain'], elevation = 0): PieceCell => ({ q, r, cell: { terrain, elevation } });

// Axial neighbour steps, counter-clockwise from east.
const RING: Hex[] = [
  { q: 1, r: 0 },
  { q: 1, r: -1 },
  { q: 0, r: -1 },
  { q: -1, r: 0 },
  { q: -1, r: 1 },
  { q: 0, r: 1 },
];

export const PIECES: Record<PieceType, (rng: Rng) => PieceCell[]> = {
  /** Blocking core with a heavy rim: breaks long sightlines and makes a corner to fight around. */
  ruin: (rng) => {
    const core = [at(0, 0, 'blocking'), at(1, 0, 'blocking')];
    if (chance(rng, 0.5)) core.push(at(0, 1, 'blocking'));
    const rim = [at(-1, 0, 'heavy'), at(2, 0, 'heavy'), at(1, -1, 'heavy'), at(-1, 1, 'heavy'), at(0, -1, 'heavy'), at(1, 1, 'heavy')];
    return [...core, ...rim.filter(() => chance(rng, 0.55))];
  },
  /** Blocking walls, light cover at the doors. */
  building: (rng) => {
    const cells = [at(0, 0, 'blocking'), at(1, 0, 'blocking')];
    if (chance(rng, 0.4)) cells.push(at(2, 0, 'blocking'));
    cells.push(at(0, 1, 'light'));
    if (chance(rng, 0.5)) cells.push(at(1, -1, 'light'));
    return cells;
  },
  /** A line of light cover that does not block sight. */
  hedgerow: (rng) => {
    const n = int(rng, 3, 5);
    const bend = chance(rng, 0.4) ? int(rng, 1, n - 1) : n;
    const out: PieceCell[] = [];
    let q = 0;
    let r = 0;
    for (let i = 0; i < n; i++) {
      out.push(at(q, r, 'light'));
      if (i + 1 === bend) r -= 1;
      else q += 1;
    }
    return out;
  },
  /** Slows a flank without hiding it. */
  rubble: (rng) => {
    const out = [at(0, 0, 'rough')];
    for (const d of RING) if (chance(rng, 0.45)) out.push(at(d.q, d.r, chance(rng, 0.25) ? 'light' : 'rough'));
    return out;
  },
  /** A firing position that is slow to reach. */
  hill: (rng) => {
    const crest = chance(rng, 0.5) ? 2 : 1;
    const out = [at(0, 0, 'open', crest)];
    for (const d of RING) if (chance(rng, 0.7)) out.push(at(d.q, d.r, chance(rng, 0.15) ? 'light' : 'open', 1));
    return out;
  },
  /** Cheap cover near objectives. */
  crater: (rng) => {
    const out = [at(0, 0, 'rough')];
    const lip = int(rng, 1, 2);
    const start = int(rng, 0, 5);
    for (let i = 0; i < lip; i++) {
      const d = RING[(start + i * 2) % 6];
      out.push(at(d.q, d.r, 'light'));
    }
    return out;
  },
  /** Heaps of wreckage: heavy cover that blocks sight but can be climbed through. */
  scrap: (rng) => {
    const out = [at(0, 0, 'heavy')];
    const n = int(rng, 1, 2);
    const start = int(rng, 0, 5);
    for (let i = 0; i < n; i++) {
      const d = RING[(start + i) % 6];
      out.push(at(d.q, d.r, 'heavy'));
    }
    return out;
  },
};

/** Turn a shape by `turns` sixths of a circle about its anchor. */
function rotate(cells: PieceCell[], turns: number): PieceCell[] {
  return cells.map((c) => {
    let { q, r } = c;
    for (let i = 0; i < turns; i++) [q, r] = [-r, q + r];
    return { q, r, cell: c.cell };
  });
}

/**
 * Try to place a piece with its anchor at (col, row). The piece is written
 * with its partner copy. Returns false and leaves the board alone when the
 * piece would leave the board, overlap its own copy, or come closer than
 * `gap` empty hexes to terrain already placed.
 */
export function placePiece(board: Board, shape: PieceCell[], col: number, row: number, turns: number, gap: number): boolean {
  const anchor = offsetToHex({ col, row });
  const cells = rotate(shape, turns).map((c) => ({ hex: { q: anchor.q + c.q, r: anchor.r + c.r }, cell: c.cell }));
  const keys = new Set<string>();
  const placed: Hex[] = [];
  for (const { hex } of cells) {
    const o = hexToOffset(hex);
    if (!board.inBounds(o.col, o.row)) return false;
    const p = board.partner(o.col, o.row);
    const k = `${o.col},${o.row}`;
    const pk = `${p.col},${p.row}`;
    if (keys.has(k) || keys.has(pk) || k === pk) return false;
    keys.add(k);
    keys.add(pk);
    placed.push(hex, offsetToHex(p));
  }
  // Keep clear of what is already there (including the partner copy we are about to write).
  for (const { col: c, row: r } of board.offsets()) {
    if (board.isOpen(c, r)) continue;
    const h = offsetToHex({ col: c, row: r });
    if (placed.some((x) => distance(x, h) <= gap)) return false;
  }
  for (const { hex, cell } of cells) {
    const o = hexToOffset(hex);
    board.setPair(o.col, o.row, cell);
  }
  return true;
}
