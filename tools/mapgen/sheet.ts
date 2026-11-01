// Contact sheet: many generated boards drawn as one SVG, for judging by eye.
//   npx vite-node tools/mapgen/sheet.ts -- [count=48] [firstSeed=1] [out=mapgen-sheet.svg]
import { writeFileSync } from 'node:fs';
import { generateBoard, offsetToHex, hexToPoint, type GeneratedBoard } from '@brass-charter/rules';

const args = process.argv.slice(2).filter((a) => a !== '--');
const count = Number(args[0] ?? 48);
const first = Number(args[1] ?? 1);
const out = args[2] ?? 'mapgen-sheet.svg';

const FILL: Record<string, string> = { open: '#d9cfb8', rough: '#a89a7a', light: '#8fae6e', heavy: '#5b6b45', blocking: '#4a4440' };
const S = 9; // hex size in px
const COLS = 6;

function boardSvg(g: GeneratedBoard, ox: number, oy: number): string {
  const parts: string[] = [];
  const w = g.board.width;
  const h = g.board.height;
  for (const { col, row } of g.board.offsets()) {
    const c = g.board.get(col, row);
    const p = hexToPoint(offsetToHex({ col, row }));
    const x = ox + S * 1.2 + p.x * S;
    const y = oy + 28 + -p.y * S;
    const pts = [0, 1, 2, 3, 4, 5].map((i) => {
      const a = (Math.PI / 180) * (60 * i - 30);
      return `${(x + S * Math.cos(a)).toFixed(1)},${(y + S * Math.sin(a)).toFixed(1)}`;
    });
    const zone = row < 3 ? '#c44' : row >= h - 3 ? '#36c' : null;
    parts.push(`<polygon points="${pts.join(' ')}" fill="${FILL[c.terrain]}" stroke="${zone ?? '#9c937e'}" stroke-width="${zone ? 1 : 0.4}"/>`);
    if (c.elevation) parts.push(`<text x="${x}" y="${y + 3}" font-size="8" text-anchor="middle" fill="#222">${'▲'.repeat(c.elevation)}</text>`);
  }
  for (const o of g.objectives) {
    const p = hexToPoint(offsetToHex(o));
    parts.push(`<circle cx="${ox + S * 1.2 + p.x * S}" cy="${oy + 28 + -p.y * S}" r="${3 + o.vp * 1.5}" fill="#f2c230" stroke="#000" stroke-width="1"/>`);
  }
  const label = `${g.map.name} · ${g.scenario.name}${g.fallback ? ' · FALLBACK' : ''}`;
  parts.push(`<text x="${ox}" y="${oy + 10}" font-size="10" font-family="sans-serif" font-weight="600">${label}</text>`);
  parts.push(`<text x="${ox}" y="${oy + 21}" font-size="8.5" font-family="monospace" fill="#555">${g.code}  score ${g.scores?.total.toFixed(2) ?? '-'}  pass ${g.passed}/${g.tried}</text>`);
  void w;
  return parts.join('');
}

const cellW = 16 * S * 1.75 + 30;
const cellH = 12 * S * 1.5 + 50;
const rows = Math.ceil(count / COLS);
const body: string[] = [];
for (let i = 0; i < count; i++) {
  const g = generateBoard(first + i);
  body.push(boardSvg(g, 10 + (i % COLS) * cellW, 10 + Math.floor(i / COLS) * cellH));
}
const W = Math.ceil(COLS * cellW + 20);
const H = Math.ceil(rows * cellH + 20);
writeFileSync(out, `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="100%" height="100%" fill="#fff"/>${body.join('')}</svg>`);
console.log(`wrote ${out} (${count} boards)`);
