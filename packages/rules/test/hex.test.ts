import { describe, expect, it } from 'vitest';
import { arcOf, distance, facingTowards, hexToOffset, lineBetween, neighbor, offsetToHex } from '../src';

describe('hex grid', () => {
  it('round-trips offset coordinates', () => {
    for (let row = 0; row < 12; row++) {
      for (let col = 0; col < 16; col++) expect(hexToOffset(offsetToHex({ col, row }))).toEqual({ col, row });
    }
  });

  it('measures distance', () => {
    const a = { q: 0, r: 0 };
    expect(distance(a, { q: 3, r: 0 })).toBe(3);
    expect(distance(a, { q: 2, r: -3 })).toBe(3);
    expect(distance(a, { q: -2, r: 4 })).toBe(4);
  });

  it('draws lines including both ends', () => {
    const line = lineBetween({ q: 0, r: 0 }, { q: 4, r: 0 });
    expect(line).toHaveLength(5);
    expect(line[4]).toEqual({ q: 4, r: 0 });
  });

  it('classifies arcs relative to facing', () => {
    const o = { q: 0, r: 0 };
    // Facing east (0)
    expect(arcOf(o, 0, neighbor(o, 0))).toBe('front');
    expect(arcOf(o, 0, neighbor(o, 1))).toBe('front');
    expect(arcOf(o, 0, neighbor(o, 5))).toBe('front');
    expect(arcOf(o, 0, neighbor(o, 2))).toBe('left');
    expect(arcOf(o, 0, neighbor(o, 4))).toBe('right');
    expect(arcOf(o, 0, neighbor(o, 3))).toBe('rear');
  });

  it('finds the facing towards a hex', () => {
    const o = { q: 0, r: 0 };
    for (let d = 0; d < 6; d++) expect(facingTowards(o, neighbor(o, d))).toBe(d);
  });
});
