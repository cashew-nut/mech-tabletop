import { describe, expect, it } from 'vitest';
import {
  ARCHETYPES,
  Board,
  Probe,
  RULES,
  TEMPLATES,
  boardFromCode,
  checkBoard,
  createGame,
  generateBoard,
  hexKey,
  hexToPoint,
  legalActions,
  offsetToHex,
  parseBoardCode,
  type ObjectiveDef,
  type RuleId,
} from '../src';
import { lance, walker } from './helpers';

const depth = RULES.map.deploymentDepth;
const failed = (board: Board, objectives: ObjectiveDef[]): RuleId[] =>
  checkBoard(board, objectives, depth).results.filter((r) => !r.ok).map((r) => r.rule);

/** A symmetric, fairly closed board that passes every rule, to break one rule at a time. */
function goodBoard(): { board: Board; objectives: ObjectiveDef[] } {
  const g = generateBoard(1);
  return { board: g.board.clone(), objectives: g.objectives.map((o) => ({ ...o })) };
}

describe('board symmetry', () => {
  it('maps every hex onto its exact half-turn partner', () => {
    const b = new Board(16, 12);
    const centre = { x: 0, y: 0 };
    const pts = [...b.offsets()].map((o) => {
      const p = hexToPoint(offsetToHex(o));
      const q = hexToPoint(offsetToHex(b.partner(o.col, o.row)));
      return { x: p.x + q.x, y: p.y + q.y, self: o.col === b.partner(o.col, o.row).col && o.row === b.partner(o.col, o.row).row };
    });
    centre.x = pts[0].x;
    centre.y = pts[0].y;
    for (const p of pts) {
      expect(p.x).toBeCloseTo(centre.x, 9);
      expect(p.y).toBeCloseTo(centre.y, 9);
      expect(p.self).toBe(false);
    }
  });
});

describe('board generator', () => {
  it('gives the same board for the same seed', () => {
    const a = generateBoard(42);
    const b = generateBoard(42);
    expect(JSON.stringify([a.map, a.scenario])).toBe(JSON.stringify([b.map, b.scenario]));
    expect(JSON.stringify(generateBoard(43).map)).not.toBe(JSON.stringify(a.map));
  });

  it('round-trips share codes, including forced choices', () => {
    const g = generateBoard(0xbeef, { archetype: 'canal', template: 'wells' });
    expect(g.code).toBe('G1-CANAL-W-BEEF');
    expect(parseBoardCode(g.code)).toEqual({ seed: 0xbeef, archetype: 'canal', template: 'wells' });
    expect(JSON.stringify(boardFromCode(g.code)!.map)).toBe(JSON.stringify(g.map));
    expect(parseBoardCode('nonsense')).toBeNull();
  });

  it('can build every archetype and template', () => {
    for (const a of ARCHETYPES) {
      for (const t of TEMPLATES) {
        const g = generateBoard(7, { archetype: a.id, template: t.id });
        expect(g.fallback, g.code).toBe(false);
      }
    }
  }, 60_000);

  // A light version of the 10,000-seed sweep (tools/mapgen/sweep.ts), so a rules change that breaks boards fails CI.
  it('passes every hard rule on a run of seeds, with no fallbacks', () => {
    for (let seed = 1; seed <= 30; seed++) {
      const g = generateBoard(seed);
      expect(g.fallback, g.code).toBe(false);
      const arch = ARCHETYPES.find((a) => a.id === g.archetype)!;
      const report = checkBoard(Board.fromMap(g.map), g.scenario.objectives, depth, { limits: arch.limits });
      expect(report.results.filter((r) => !r.ok), g.code).toEqual([]);
    }
  }, 60_000);

  it('measures movement exactly as the engine does', () => {
    for (const seed of [1, 2, 3, 4, 5]) expect(new Probe(generateBoard(seed).board).engineAgrees()).toBe(true);
  });
});

describe('board validator', () => {
  it('passes a generated board', () => {
    const { board, objectives } = goodBoard();
    expect(failed(board, objectives)).toEqual([]);
  });

  it('rejects a lopsided hex or objective (H1)', () => {
    const { board, objectives } = goodBoard();
    const free = [...board.offsets()].find((o) => o.row === 4 && board.isOpen(o.col, o.row) && !objectives.some((x) => x.col === o.col && x.row === o.row))!;
    board.cells[board.index(free.col, free.row)] = { terrain: 'light', elevation: 0 };
    expect(failed(board, objectives)).toContain('H1');
    const g = goodBoard();
    g.objectives[0].vp = 3;
    expect(failed(g.board, g.objectives)).toContain('H1');
  });

  it('rejects a walled-in deployment zone (H3)', () => {
    const { board, objectives } = goodBoard();
    for (let col = 0; col < 16; col++) board.setPair(col, 3, { terrain: 'blocking', elevation: 0 });
    expect(failed(board, objectives)).toContain('H3');
  });

  it('rejects a cramped deployment zone (H2)', () => {
    const { board, objectives } = goodBoard();
    for (let col = 0; col < 14; col++) board.setPair(col, 1, { terrain: 'blocking', elevation: 0 });
    expect(failed(board, objectives)).toContain('H2');
  });

  it('rejects an objective that cannot be gathered around (H5)', () => {
    const { board, objectives } = goodBoard();
    const o = objectives.find((x) => x.vp === 1 && x.row < 6)!;
    const h = offsetToHex(o);
    for (const d of [
      { q: 1, r: 0 },
      { q: 0, r: 1 },
      { q: -1, r: 1 },
    ]) {
      const off = { q: h.q + d.q, r: h.r + d.r };
      const col = off.q + (off.r - (off.r & 1)) / 2;
      board.setPair(col, off.r, { terrain: 'blocking', elevation: 0 });
    }
    expect(failed(board, objectives)).toContain('H5');
  });

  it('rejects objectives too close together or to a zone (H6)', () => {
    const { board } = goodBoard();
    expect(failed(board, [{ col: 4, row: 3, vp: 1 }, { col: 11, row: 8, vp: 1 }])).toContain('H6');
  });

  it('rejects an open board as a shooting gallery (H7) with bare approaches (H8)', () => {
    const board = new Board(16, 12);
    const fails = failed(board, [
      { col: 3, row: 5, vp: 1 },
      { col: 12, row: 6, vp: 1 },
    ]);
    expect(fails).toContain('H7');
    expect(fails).toContain('H8');
  });

  it('rejects a hill at home that sees the enemy zone (H9)', () => {
    const board = new Board(16, 12);
    board.setPair(7, 2, { terrain: 'open', elevation: 2 });
    expect(failed(board, [])).toContain('H9');
  });
});

describe('engine with a generated board', () => {
  it('builds a game on a generated map and scenario', () => {
    const g = generateBoard(5);
    const a = lance('A', [walker('a1', 'scavenger'), walker('a2', 'scavenger'), walker('a3', 'scavenger')]);
    const b = lance('B', [walker('b1', 'scavenger'), walker('b2', 'scavenger'), walker('b3', 'scavenger')]);
    const state = createGame({ seed: 1, map: g.map, scenario: g.scenario, lances: [a, b], deploy: 'alternate' });
    expect(state.map.id).toBe(g.map.id);
    expect(state.scenario).toBe(g.scenario.id);
    expect(state.objectives).toHaveLength(g.objectives.length);
    for (const h of g.map.hexes) expect(state.map.hexes[hexKey(offsetToHex(h))].terrain).toBe(h.terrain ?? 'open');
    expect(legalActions(state).length).toBeGreaterThan(0);
  });
});
