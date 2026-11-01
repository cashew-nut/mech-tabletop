// Board types. Each sets a terrain budget, a palette of pieces and an optional
// spine: one crossing feature through the centre that gives the board its
// identity at a glance.
import { nextFloat, type Rng } from '../rng';
import type { Board } from './board';
import type { PieceType } from './pieces';
import type { Limits } from './validate';

export type ArchetypeId = 'foundry' | 'canal' | 'chapel' | 'ridge' | 'plain';
export type SpineType = 'canal' | 'ridge';

export interface Archetype {
  id: ArchetypeId;
  /** Word used in share codes. */
  code: string;
  label: string;
  /** Share of hexes the pieces cover, low and high, on top of any spine. */
  budget: [number, number];
  /** Piece palette with weights. */
  pieces: Array<[PieceType, number]>;
  /** Empty hexes kept between pieces. */
  gap: number;
  spine: SpineType | null;
  /** Rows (in the generated half) where piece anchors may go. */
  anchorRows: [number, number];
  /** Hard-rule thresholds this board type relaxes. */
  limits?: Partial<Limits>;
}

export const ARCHETYPES: Archetype[] = [
  {
    id: 'foundry',
    code: 'FOUNDRY',
    label: 'Foundry yard',
    budget: [0.22, 0.28],
    pieces: [['building', 4], ['ruin', 2], ['scrap', 1], ['rubble', 2], ['crater', 1]],
    gap: 1,
    spine: null,
    anchorRows: [1, 6],
  },
  {
    id: 'canal',
    code: 'CANAL',
    label: 'Canal crossing',
    budget: [0.14, 0.2],
    pieces: [['building', 3], ['hedgerow', 2], ['scrap', 1], ['crater', 2], ['ruin', 2]],
    gap: 1,
    spine: 'canal',
    anchorRows: [1, 4],
  },
  {
    id: 'chapel',
    code: 'CHAPEL',
    label: 'Chapel ruins',
    budget: [0.16, 0.22],
    pieces: [['ruin', 5], ['rubble', 3], ['crater', 1], ['hedgerow', 1]],
    gap: 2,
    spine: null,
    anchorRows: [1, 6],
  },
  {
    id: 'ridge',
    code: 'RIDGE',
    label: 'Ridge line',
    budget: [0.14, 0.2],
    pieces: [['hill', 2], ['hedgerow', 3], ['scrap', 1], ['crater', 2], ['building', 1], ['ruin', 1]],
    gap: 1,
    spine: 'ridge',
    anchorRows: [1, 4],
  },
  {
    id: 'plain',
    code: 'PLAIN',
    label: 'Open plain',
    budget: [0.12, 0.16],
    pieces: [['hedgerow', 3], ['crater', 2], ['scrap', 2], ['building', 1]],
    gap: 1,
    spine: null,
    anchorRows: [2, 6],
    // The long-gun board: sightlines are its point, so it allows more of them.
    limits: { zoneLos: 0.5 },
  },
];

export const getArchetype = (id: ArchetypeId) => ARCHETYPES.find((a) => a.id === id)!;

export function weighted<T>(rng: Rng, items: Array<[T, number]>): T {
  const total = items.reduce((s, [, w]) => s + w, 0);
  let x = nextFloat(rng) * total;
  for (const [item, w] of items) {
    x -= w;
    if (x < 0) return item;
  }
  return items[items.length - 1][0];
}

/**
 * Draw the spine across the middle rows. It is laid along the left half of the
 * centre line and its partner copy completes it on the right, so it always
 * crosses the whole board.
 */
export function laySpine(board: Board, spine: SpineType, rng: Rng) {
  const mid = board.height / 2 - 1; // the last row of the generated half
  const half = board.width / 2;
  let shift = 0;
  const track: Array<{ col: number; rows: number[] }> = [];
  for (let col = 0; col < half; col++) {
    if (nextFloat(rng) < 0.3) shift = shift === 0 ? -1 : 0;
    const rows = spine === 'canal' ? [mid + shift, mid + 1 + shift] : [mid + shift];
    track.push({ col, rows });
  }
  if (spine === 'canal') {
    // One or two pairs of fords: open crossings that become chokepoints.
    const fords = new Set<number>();
    const n = nextFloat(rng) < 0.5 ? 1 : 2;
    while (fords.size < n) fords.add(1 + Math.floor(nextFloat(rng) * (half - 1)));
    for (const { col, rows } of track) {
      if (fords.has(col)) continue;
      for (const row of rows) board.setPair(col, row, { terrain: 'rough', elevation: 0 });
    }
    // The centre column pair is a ford a third of the time.
    if (nextFloat(rng) < 0.33) for (const row of track[half - 1].rows) board.setPair(half - 1, row, { terrain: 'open', elevation: 0 });
  } else {
    for (const { col, rows } of track) {
      if (nextFloat(rng) < 0.3) continue; // passes through the ridge
      for (const row of rows) board.setPair(col, row, { terrain: 'open', elevation: nextFloat(rng) < 0.25 ? 2 : 1 });
    }
  }
}
