// Overlays for the 3D board: a unit readout in the bottom-left and a minimap with the current order in the bottom-right.
import { hexKey, type GameState, type WalkerState } from '@brass-charter/rules';
import { getChassis } from '@brass-charter/rules';
import { hexCentre } from './HexMap';

const TERRAIN_FILL: Record<string, string> = { open: '#7b7a73', rough: '#6b6457', light: '#66714f', heavy: '#525a49', blocking: '#2c2a27' };
const SIDE_FILL = ['#3aa7ff', '#ff5a1f'];
const SIZE = 26;

function Minimap({ state, focus }: { state: GameState; focus: WalkerState | null }) {
  const cells = Object.keys(state.map.hexes).map((k) => {
    const [q, r] = k.split(',').map(Number);
    return { key: k, ...hexCentre({ q, r }), terrain: state.map.hexes[k].terrain };
  });
  const minX = Math.min(...cells.map((c) => c.x)) - SIZE;
  const minY = Math.min(...cells.map((c) => c.y)) - SIZE;
  const w = Math.max(...cells.map((c) => c.x)) + SIZE - minX;
  const h = Math.max(...cells.map((c) => c.y)) + SIZE - minY;
  const corners = Array.from({ length: 6 }, (_, i) => {
    const a = ((60 * i - 30) * Math.PI) / 180;
    return `${(SIZE * 0.94 * Math.cos(a)).toFixed(1)},${(SIZE * 0.94 * Math.sin(a)).toFixed(1)}`;
  }).join(' ');
  const dot = (pos: { q: number; r: number }) => hexCentre(pos);
  return (
    <svg viewBox={`${minX} ${minY} ${w} ${h}`} role="img" aria-label="Minimap">
      {cells.map((c) => (
        <polygon key={c.key} points={corners} transform={`translate(${c.x} ${c.y})`} fill={TERRAIN_FILL[c.terrain]} />
      ))}
      {state.objectives.map((o) => {
        const p = dot(o.hex);
        return <circle key={hexKey(o.hex)} cx={p.x} cy={p.y} r={9} fill="none" stroke="#f3b640" strokeWidth={4} />;
      })}
      {state.walkers
        .filter((wk) => !wk.destroyed)
        .map((wk) => {
          const p = dot(wk.pos);
          return (
            <circle key={wk.id} cx={p.x} cy={p.y} r={wk.id === focus?.id ? 15 : 11} fill={SIDE_FILL[wk.side]} stroke={wk.id === focus?.id ? '#fff' : '#101318'} strokeWidth={4} />
          );
        })}
    </svg>
  );
}

export function BoardHud({ state, focus, order }: { state: GameState; focus: WalkerState | null; order: string }) {
  const armour = focus ? Object.values(focus.armour).reduce((a, b) => a + b, 0) : 0;
  const maxArmour = focus ? Object.values(focus.maxArmour).reduce((a, b) => a + b, 0) : 0;
  return (
    <>
      <div className="hud hud-unit">
        {focus ? (
          <>
            <strong>{getChassis(focus.chassis).name.toUpperCase()}-CLASS</strong>
            <span className="hud-name">{focus.name}</span>
            <dl>
              <dt>ARMOUR</dt>
              <dd>
                {armour}/{maxArmour}
              </dd>
              <dt>OVERPRESSURE</dt>
              <dd className={focus.overpressure ? 'hot' : ''}>{focus.overpressure}</dd>
              <dt>RESERVE</dt>
              <dd>{focus.reserve}</dd>
            </dl>
          </>
        ) : (
          <span className="hud-name">Select a war-walker</span>
        )}
      </div>
      <div className="hud hud-map">
        <Minimap state={state} focus={focus} />
        <p>
          {focus ? `SELECTED: ${focus.name.toUpperCase()}` : 'NO SELECTION'}
          <br />
          ORDER: {order}
        </p>
      </div>
    </>
  );
}
