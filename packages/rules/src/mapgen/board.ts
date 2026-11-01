// A board under construction: terrain per hex in offset coordinates, plus
// helpers for the half-turn symmetry every generated board obeys.
//
// On a pointy-top "odd-r" grid with an even number of rows, turning the board
// half a turn about its centre maps hex (col, row) exactly onto
// (width - 1 - col, height - 1 - row). Row parity flips, which cancels the
// half-hex shift of odd rows, and no hex maps onto itself. So every hex has
// exactly one partner, and a board that matches its partners is the same
// ground seen from either side.
import type { MapDef, ObjectiveDef, Terrain } from '../data';
import { passable, stepCost } from '../engine';
import { hexKey, hexToOffset, neighbors, offsetToHex, type Hex, type Offset } from '../hex';
import type { GameState, HexInfo } from '../types';

export interface Cell {
  terrain: Terrain;
  elevation: number;
}

export const OPEN: Cell = { terrain: 'open', elevation: 0 };

export class Board {
  readonly cells: Cell[];
  constructor(
    readonly width: number,
    readonly height: number,
  ) {
    if (height % 2) throw new Error('Generated boards need an even number of rows for exact symmetry');
    this.cells = Array.from({ length: width * height }, () => ({ ...OPEN }));
  }

  inBounds = (col: number, row: number) => col >= 0 && col < this.width && row >= 0 && row < this.height;
  index = (col: number, row: number) => row * this.width + col;
  get = (col: number, row: number): Cell => this.cells[this.index(col, row)];
  partner = (col: number, row: number): Offset => ({ col: this.width - 1 - col, row: this.height - 1 - row });
  isOpen = (col: number, row: number) => {
    const c = this.get(col, row);
    return c.terrain === 'open' && c.elevation === 0;
  };

  /** Set a hex and its partner together, so the board stays symmetric. */
  setPair(col: number, row: number, cell: Cell) {
    const p = this.partner(col, row);
    this.cells[this.index(col, row)] = { ...cell };
    this.cells[this.index(p.col, p.row)] = { ...cell };
  }

  clone(): Board {
    const b = new Board(this.width, this.height);
    this.cells.forEach((c, i) => (b.cells[i] = { ...c }));
    return b;
  }

  /** Every hex, in row order. */
  *offsets(): Generator<Offset> {
    for (let row = 0; row < this.height; row++) for (let col = 0; col < this.width; col++) yield { col, row };
  }

  /** The sparse list a MapDef stores: every hex that is not flat open ground. */
  toMapHexes(): MapDef['hexes'] {
    const out: MapDef['hexes'] = [];
    for (const { col, row } of this.offsets()) {
      const c = this.get(col, row);
      if (c.terrain === 'open' && c.elevation === 0) continue;
      out.push({ col, row, ...(c.terrain !== 'open' ? { terrain: c.terrain } : {}), ...(c.elevation ? { elevation: c.elevation } : {}) });
    }
    return out;
  }

  static fromMap(map: Pick<MapDef, 'width' | 'height' | 'hexes'>): Board {
    const b = new Board(map.width, map.height);
    for (const h of map.hexes) b.cells[b.index(h.col, h.row)] = { terrain: h.terrain ?? 'open', elevation: h.elevation ?? 0 };
    return b;
  }

  /**
   * A stand-in game state holding only this terrain, so the engine's own
   * movement and line-of-sight code can measure the board. The checks and the
   * game can then never disagree about what blocks what.
   */
  terrainState(): GameState {
    const hexes: Record<string, HexInfo> = {};
    for (const { col, row } of this.offsets()) hexes[hexKey(offsetToHex({ col, row }))] = { ...this.get(col, row) };
    return { map: { id: 'probe', width: this.width, height: this.height, hexes }, wrecks: [], smoke: [], walkers: [], surveyor: null } as unknown as GameState;
  }
}

/**
 * Movement and sight queries over a fixed board, built once per candidate.
 * Sight goes through the engine's own lineOfSight. Movement uses array-indexed
 * copies of the engine's passable and stepCost, because the checks call them
 * hundreds of thousands of times; `engineAgrees` and a test keep the copies
 * identical to the engine.
 */
export class Probe {
  readonly state: GameState;
  constructor(readonly board: Board) {
    this.state = board.terrainState();
  }
  passable = (o: Offset) => this.board.inBounds(o.col, o.row) && this.board.get(o.col, o.row).terrain !== 'blocking';
  step = (from: Hex, to: Hex) => {
    const a = hexToOffset(from);
    const t = hexToOffset(to);
    const b = this.board.get(t.col, t.row);
    const base = b.terrain === 'rough' || b.terrain === 'heavy' ? 2 : 1;
    return base + Math.max(0, b.elevation - this.board.get(a.col, a.row).elevation);
  };

  /** True when the fast copies match the engine on every hex and step of this board. */
  engineAgrees(): boolean {
    for (const o of this.board.offsets()) {
      const h = offsetToHex(o);
      if (this.passable(o) !== passable(this.state, h)) return false;
      for (const n of neighbors(h)) {
        const no = hexToOffset(n);
        if (this.board.inBounds(no.col, no.row) && this.step(h, n) !== stepCost(this.state, h, n)) return false;
      }
    }
    return true;
  }
}

export const objectiveKey = (o: Pick<ObjectiveDef, 'col' | 'row'>) => `${o.col},${o.row}`;
