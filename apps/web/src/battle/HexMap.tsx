import { SURVEYOR_ID, hexKey, type GameState, type Hex } from '@brass-charter/rules';

const SIZE = 26;
const SQRT3 = Math.sqrt(3);

export const hexCentre = ({ q, r }: Hex) => ({ x: SIZE * SQRT3 * (q + r / 2), y: SIZE * 1.5 * r });

function corners(cx: number, cy: number, size = SIZE) {
  return Array.from({ length: 6 }, (_, i) => {
    const a = ((60 * i - 30) * Math.PI) / 180;
    return `${(cx + size * Math.cos(a)).toFixed(1)},${(cy + size * Math.sin(a)).toFixed(1)}`;
  }).join(' ');
}

const TERRAIN_FILL: Record<string, string> = {
  open: '#cdbf98',
  rough: '#a99a74',
  light: '#9fae7a',
  heavy: '#6f7a5a',
  blocking: '#3b342d',
};

export type Highlight = 'move' | 'jump' | 'smoke';

interface Props {
  state: GameState;
  highlights: Map<string, Highlight>;
  selectedId: string | null;
  targetId: string | null;
  onHex: (hex: Hex) => void;
  onWalker: (id: string) => void;
}

export function HexMap({ state, highlights, selectedId, targetId, onHex, onWalker }: Props) {
  const hexes = Object.keys(state.map.hexes).map((k) => {
    const [q, r] = k.split(',').map(Number);
    return { hex: { q, r }, key: k, info: state.map.hexes[k] };
  });
  const xs = hexes.map((h) => hexCentre(h.hex).x);
  const ys = hexes.map((h) => hexCentre(h.hex).y);
  const pad = SIZE + 4;
  const minX = Math.min(...xs) - pad;
  const minY = Math.min(...ys) - pad;
  const width = Math.max(...xs) - minX + pad;
  const height = Math.max(...ys) - minY + pad;
  const objectiveKeys = new Map(state.objectives.map((o) => [hexKey(o.hex), o.vp]));
  const activeId = state.active?.walkerId ?? null;

  return (
    <svg className="hexmap" viewBox={`${minX} ${minY} ${width} ${height}`} role="img" aria-label="Battlefield">
      {hexes.map(({ hex, key, info }) => {
        const { x, y } = hexCentre(hex);
        const hl = highlights.get(key);
        return (
          <g key={key} onClick={() => onHex(hex)} className={hl ? `hex hl-${hl}` : 'hex'}>
            <polygon points={corners(x, y)} fill={TERRAIN_FILL[info.terrain]} stroke="#8c7b58" strokeWidth={1} />
            {info.elevation > 0 && (
              <polygon points={corners(x, y, SIZE - 5)} fill="none" stroke="#f4ead0" strokeWidth={info.elevation * 1.5} opacity={0.7} />
            )}
            {info.terrain === 'heavy' && <text x={x} y={y + 4} className="glyph">▲</text>}
            {info.terrain === 'light' && <text x={x} y={y + 4} className="glyph light">♣</text>}
            {info.terrain === 'rough' && <text x={x} y={y + 4} className="glyph">∴</text>}
            {hl && <polygon points={corners(x, y, SIZE - 2)} className="hl" />}
          </g>
        );
      })}
      {[...objectiveKeys].map(([key, vp]) => {
        const [q, r] = key.split(',').map(Number);
        const { x, y } = hexCentre({ q, r });
        return (
          <g key={`o${key}`} pointerEvents="none">
            <circle cx={x} cy={y} r={SIZE * 0.55} className="objective" />
            {vp > 1 && <text x={x} y={y - SIZE * 0.6} className="vp">{vp} VP</text>}
          </g>
        );
      })}
      {state.smoke.map((key) => {
        const [q, r] = key.split(',').map(Number);
        const { x, y } = hexCentre({ q, r });
        return <circle key={`s${key}`} cx={x} cy={y} r={SIZE * 0.85} className="smoke" pointerEvents="none" />;
      })}
      {state.wrecks.map((key, i) => {
        const [q, r] = key.split(',').map(Number);
        const { x, y } = hexCentre({ q, r });
        return (
          <text key={`w${key}${i}`} x={x} y={y + 6} className="wreck" pointerEvents="none">
            ✸
          </text>
        );
      })}
      {state.surveyor?.status === 'active' && (() => {
        const sv = state.surveyor;
        const { x, y } = hexCentre(sv.pos);
        const r = SIZE * 0.5;
        return (
          <g className={`surveyor ${targetId === SURVEYOR_ID ? 'targeted' : ''}`} onClick={() => onWalker(SURVEYOR_ID)}>
            <polygon points={`${x},${y - r} ${x + r},${y} ${x},${y + r} ${x - r},${y}`} />
            <text x={x} y={y + 4} className="initial">
              {sv.hp}
            </text>
          </g>
        );
      })()}
      {state.walkers
        .filter((w) => !w.destroyed)
        .map((w) => {
          const { x, y } = hexCentre(w.pos);
          const angle = (-60 * w.facing * Math.PI) / 180;
          const nx = x + Math.cos(angle) * SIZE * 0.78;
          const ny = y + Math.sin(angle) * SIZE * 0.78;
          const cls = [
            'token',
            `side${w.side}`,
            w.id === selectedId ? 'selected' : '',
            w.id === targetId ? 'targeted' : '',
            w.id === activeId ? 'active' : '',
            w.activated ? 'spent' : '',
          ].join(' ');
          return (
            <g key={w.id} className={cls} onClick={() => onWalker(w.id)}>
              <line x1={x} y1={y} x2={nx} y2={ny} className="nose" />
              <circle cx={x} cy={y} r={SIZE * 0.5 + w.size * 1.5} />
              <text x={x} y={y + 4} className="initial">
                {w.name.slice(0, 2)}
              </text>
              {w.prone && <text x={x + SIZE * 0.45} y={y - SIZE * 0.35} className="status">↓</text>}
              {w.overpressure > 0 && (
                <text x={x - SIZE * 0.5} y={y - SIZE * 0.35} className="status op">
                  {w.overpressure}
                </text>
              )}
            </g>
          );
        })}
    </svg>
  );
}
