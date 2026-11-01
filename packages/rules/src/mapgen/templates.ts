// Objective templates. A template is a set of objective spots closed under the
// half-turn, with the same VP on each partner. There is no single centre hex
// on an even board, so the centre objective is a two-hex zone made of the
// centre pair, which are neighbours and each other's partner.
import type { ObjectiveDef } from '../data';
import { distance, offsetToHex, type Offset } from '../hex';
import { nextFloat, type Rng } from '../rng';
import type { Board } from './board';

export type TemplateId = 'line' | 'diamond' | 'wells' | 'scatter';

interface PairSpec {
  cols: [number, number];
  rows: [number, number];
  vp: number;
}

export interface Template {
  id: TemplateId;
  code: string;
  label: string;
  centre: number | null; // VP on each centre hex, or no centre zone
  pairs: PairSpec[];
  rules: string;
}

// Spots are drawn in the generated half (rows 4-5 on a 12-row board), so each
// objective and its partner sit at least 2 hexes clear of both deployment zones.
export const TEMPLATES: Template[] = [
  {
    id: 'line',
    code: 'L',
    label: 'Hold the Line',
    centre: 1,
    pairs: [{ cols: [1, 4], rows: [4, 5], vp: 1 }],
    rules: 'The two centre objectives are worth 1 VP each. Each side has one flank objective close to home and one close to the enemy.',
  },
  {
    id: 'diamond',
    code: 'D',
    label: 'Diamond',
    centre: 1,
    pairs: [
      { cols: [2, 4], rows: [4, 4], vp: 1 },
      { cols: [10, 12], rows: [4, 4], vp: 1 },
    ],
    rules: 'Six objectives worth 1 VP each: the centre pair, two near each deployment zone. Spread out or win the middle.',
  },
  {
    id: 'wells',
    code: 'W',
    label: 'Twin Wells',
    centre: 1,
    pairs: [{ cols: [0, 2], rows: [4, 5], vp: 2 }],
    rules: 'Two aether wells on the flanks are worth 2 VP each; the two centre objectives are worth 1 VP each.',
  },
  {
    id: 'scatter',
    code: 'S',
    label: 'Scattered Claims',
    centre: null,
    pairs: [
      { cols: [0, 15], rows: [4, 5], vp: 1 },
      { cols: [0, 15], rows: [4, 5], vp: 1 },
      { cols: [0, 15], rows: [4, 5], vp: 1 },
    ],
    rules: 'Six claims worth 1 VP each, scattered across the middle of the board. Read the ground before you deploy.',
  },
];

export const getTemplate = (id: TemplateId) => TEMPLATES.find((t) => t.id === id)!;

/** Centre pair of hexes for a board: neighbours that are each other's partner. */
export function centrePair(board: Board): [Offset, Offset] {
  const a = { col: board.width / 2 - 1, row: board.height / 2 - 1 };
  return [a, board.partner(a.col, a.row)];
}

/** An objective may stand on open ground or light cover: passable at normal cost, never inside a wall. */
const standable = (board: Board, o: Offset) => {
  if (!board.inBounds(o.col, o.row)) return false;
  const t = board.get(o.col, o.row).terrain;
  return t === 'open' || t === 'light';
};

const hasCoverNear = (board: Board, o: Offset) => {
  const h = offsetToHex(o);
  for (const p of board.offsets()) {
    const t = board.get(p.col, p.row).terrain;
    if ((t === 'light' || t === 'heavy' || t === 'blocking') && distance(offsetToHex(p), h) <= 1 && !(p.col === o.col && p.row === o.row)) return true;
  }
  return false;
};

/**
 * Place a template's objectives. Each spot is drawn in its region, then
 * nudged up to one hex to stand beside cover. Returns null when a spot cannot
 * be placed (the candidate board is thrown away).
 */
export function placeObjectives(board: Board, template: Template, rng: Rng, depth: number): ObjectiveDef[] | null {
  const out: ObjectiveDef[] = [];
  const minRow = depth + 1;
  const maxRow = board.height - depth - 2;
  const taken: Offset[] = [];
  if (template.centre !== null) {
    const [a, b] = centrePair(board);
    // Clear the centre pair of anything that would stop it being held.
    if (!standable(board, a)) board.setPair(a.col, a.row, { terrain: 'open', elevation: board.get(a.col, a.row).elevation });
    out.push({ ...a, vp: template.centre }, { ...b, vp: template.centre });
    taken.push(a, b);
  }
  for (const spec of template.pairs) {
    let placed = false;
    for (let attempt = 0; attempt < 12 && !placed; attempt++) {
      const col = spec.cols[0] + Math.floor(nextFloat(rng) * (spec.cols[1] - spec.cols[0] + 1));
      const row = spec.rows[0] + Math.floor(nextFloat(rng) * (spec.rows[1] - spec.rows[0] + 1));
      const base = offsetToHex({ col, row });
      const options: Offset[] = [];
      for (const o of board.offsets()) {
        if (distance(offsetToHex(o), base) > 1 || o.row < minRow || o.row > maxRow || !standable(board, o)) continue;
        const p = board.partner(o.col, o.row);
        if (distance(offsetToHex(o), offsetToHex(p)) < 3) continue;
        if (taken.some((t) => distance(offsetToHex(t), offsetToHex(o)) < 3 || distance(offsetToHex(t), offsetToHex(p)) < 3)) continue;
        options.push(o);
      }
      if (!options.length) continue;
      const covered = options.filter((o) => hasCoverNear(board, o));
      const pool = covered.length ? covered : options;
      const o = pool[Math.floor(nextFloat(rng) * pool.length)];
      const p = board.partner(o.col, o.row);
      out.push({ ...o, vp: spec.vp }, { ...p, vp: spec.vp });
      taken.push(o, p);
      placed = true;
    }
    if (!placed) return null;
  }
  return out;
}
