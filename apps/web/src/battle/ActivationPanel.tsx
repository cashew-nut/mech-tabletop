// The controls for the war-walker the player is activating: facing, weapons, utilities and the end of the activation.
import {
  distance,
  getEquipment,
  previewAttack,
  moveAllowance,
  workingItems,
  type Action,
  type Facing,
  type GameState,
  type WalkerState,
} from '@brass-charter/rules';

export type Mode = 'move' | 'smoke' | 'escort';

const FACING_ARROWS = ['→', '↗', '↖', '←', '↙', '↘'];

interface PanelProps {
  state: GameState;
  walker: WalkerState;
  target: WalkerState | null;
  targetId: string | null;
  targetName?: string;
  mode: Mode;
  setMode: (m: Mode) => void;
  act: (a: Action) => void;
  can: (a: Action) => boolean;
  smokeUid?: string;
}

export function ActivationPanel({ state, walker, target, targetId, targetName, mode, setMode, act, can, smokeUid }: PanelProps) {
  const a = state.active!;
  const sv = state.surveyor;
  const canEscort = sv?.status === 'active' && sv.side === walker.side && distance(sv.pos, walker.pos) === 1 && a.pressure >= 1;
  const weapons = workingItems(walker).filter((it) => getEquipment(it.id).weapon);
  const utilities: Array<{ label: string; action: Action; title: string }> = [];
  for (const it of workingItems(walker)) {
    const def = getEquipment(it.id);
    if (it.id === 'coolant-loop') utilities.push({ label: def.name, action: { type: 'useItem', itemUid: it.uid }, title: def.rules });
    if (it.id === 'spotter-drone' && target) utilities.push({ label: `${def.name} → ${target.name}`, action: { type: 'useItem', itemUid: it.uid, walkerId: target.id }, title: def.rules });
  }

  return (
    <div className="panel activation">
      <div className="activation-head">
        <h3>{walker.name}</h3>
        <span className="pressure" aria-label={`${a.pressure} Pressure left`}>
          {a.pressure} <small>Pressure</small>
        </span>
      </div>
      {a.faults.length > 0 && <p className="bad">Fault: {a.faults.join(', ').replaceAll('-', ' ')}</p>}
      <p className="hint">
        {mode === 'move'
          ? a.pressure < 1
            ? 'Out of Pressure: end the activation.'
            : `Click a highlighted hex to move up to ${moveAllowance(state, walker)} hexes for 1 Pressure. You can move again while Pressure lasts, and you end facing the nearest enemy.`
          : mode === 'escort'
            ? 'Click a highlighted hex to move the surveyor there (1 Pressure, up to 2 hexes).'
            : 'Click this or an adjacent hex to lay smoke.'}
      </p>

      <div className="turns" role="group" aria-label="Turn to face (1 Pressure)">
        <span>Turn</span>
        {FACING_ARROWS.map((arrow, f) => (
          <button
            key={f}
            disabled={f === walker.facing || !can({ type: 'turn', facing: f as Facing })}
            onClick={() => act({ type: 'turn', facing: f as Facing })}
            aria-label={`Face ${arrow}`}
          >
            {arrow}
          </button>
        ))}
      </div>

      <h4>Weapons {targetName ? `vs ${targetName}` : ''}</h4>
      <ul className="weapons">
        {weapons.length === 0 && <li className="hint">No working weapons.</li>}
        {weapons.map((it) => {
          const def = getEquipment(it.id);
          const p = targetId ? previewAttack(state, it.uid, targetId) : null;
          return (
            <li key={it.uid}>
              <div>
                <strong>{def.name}</strong>
                <small>
                  {def.pressure} Pressure{it.ammo !== null ? ` · ${it.ammo} ammo` : ''}
                  {it.firedThisActivation ? ' · fired' : ''}
                </small>
                <small className={p?.ok ? 'good' : 'bad'}>
                  {!targetId ? 'Click an enemy to target it' : p!.ok ? `${p!.dice} dice, hit on ${p!.tn}+${p!.indirect ? ' (indirect)' : ''}` : p!.reason}
                </small>
              </div>
              <button disabled={!p?.ok} onClick={() => targetId && act({ type: 'fire', itemUid: it.uid, targetId })}>
                Fire
              </button>
            </li>
          );
        })}
      </ul>

      <div className="action-grid">
        {target && (
          <button disabled={!can({ type: 'ram', targetId: target.id })} onClick={() => act({ type: 'ram', targetId: target.id })} title="2 Pressure: 2 dice at TN 4, damage equal to chassis size">
            Ram
          </button>
        )}
        <button disabled={!can({ type: 'brace' })} onClick={() => act({ type: 'brace' })} title="1 Pressure: +1 to be hit until your next activation">
          Brace
        </button>
        <button disabled={!can({ type: 'bank' })} onClick={() => act({ type: 'bank' })} title="1 Pressure into Reserve (max 2) for the Kinetic Shield">
          Bank ({walker.reserve})
        </button>
        {walker.prone && (
          <button disabled={!can({ type: 'standUp' })} onClick={() => act({ type: 'standUp' })}>
            Stand up
          </button>
        )}
        {canEscort && (
          <button className={mode === 'escort' ? 'on' : ''} onClick={() => setMode(mode === 'escort' ? 'move' : 'escort')} title="1 Pressure: move the surveyor up to 2 hexes">
            Escort surveyor
          </button>
        )}
        {smokeUid && (
          <button className={mode === 'smoke' ? 'on' : ''} disabled={a.pressure < 1} onClick={() => setMode(mode === 'smoke' ? 'move' : 'smoke')}>
            Smoke
          </button>
        )}
        {utilities.map((u) => (
          <button key={u.label} title={u.title} disabled={!can(u.action)} onClick={() => act(u.action)}>
            {u.label}
          </button>
        ))}
      </div>

      <div className="end-row">
        {walker.trait === 'tactician' && !walker.tacticianUsed && (
          <button className="secondary" onClick={() => act({ type: 'endActivation', reactivate: true })}>
            End and go again (Tactician)
          </button>
        )}
        <button className="end" onClick={() => act({ type: 'endActivation' })}>
          End activation
        </button>
      </div>
    </div>
  );
}
