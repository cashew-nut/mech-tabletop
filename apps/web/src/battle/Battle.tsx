import { useEffect, useMemo, useState } from 'react';
import { chooseAction } from '@brass-charter/ai';
import {
  IllegalAction,
  MAPS,
  SURVEYOR_ID,
  SCENARIOS,
  aliveWalkers,
  applyAction,
  createGame,
  deployable,
  deploymentZone,
  distance,
  facingTowards,
  getChassis,
  getEquipment,
  hexKey,
  neighbors,
  previewAttack,
  reachable,
  moveAllowance,
  validateLance,
  workingItems,
  type Action,
  type Facing,
  type GameState,
  type Hex,
  type LanceInput,
  type WalkerState,
  type Zone,
} from '@brass-charter/rules';
import examples from '../../../../data/lances/examples.json';
import { loadDraft, loadSaved } from '../storage';
import { Board3D } from './Board3D';
import { BoardHud } from './BoardHud';
import { HexMap, type Highlight } from './HexMap';

function webglAvailable() {
  try {
    return !!document.createElement('canvas').getContext('webgl2');
  } catch {
    return false;
  }
}

const EXAMPLES = examples.lances as LanceInput[];
const HUMAN = 0;
const AI_DELAY_MS = 450;
const FACING_ARROWS = ['→', '↗', '↖', '←', '↙', '↘'];
const ZONE_NAMES: Record<Zone, string> = {
  coreFront: 'Core',
  coreRear: 'Core (rear)',
  armLeft: 'Left arm',
  armRight: 'Right arm',
  legs: 'Legs',
};
const PLAYABLE_SCENARIOS = SCENARIOS;

interface Choice {
  label: string;
  lance: LanceInput;
}

function lanceChoices(): Choice[] {
  const out: Choice[] = [];
  const draft = loadDraft();
  if (draft) out.push({ label: `Your current lance: ${draft.name}`, lance: draft });
  for (const [name, l] of Object.entries(loadSaved())) out.push({ label: `Saved: ${name}`, lance: l });
  for (const l of EXAMPLES) out.push({ label: `Example: ${l.name}`, lance: l });
  return out;
}

export function Battle() {
  const [game, setGame] = useState<GameState | null>(null);
  return game ? <Trial initial={game} onQuit={() => setGame(null)} /> : <Setup onStart={setGame} />;
}

function Setup({ onStart }: { onStart: (g: GameState) => void }) {
  const choices = useMemo(lanceChoices, []);
  const [mine, setMine] = useState(0);
  const [theirs, setTheirs] = useState(Math.max(0, choices.findIndex((c) => c.lance.name === EXAMPLES[2].name)));
  const [scenario, setScenario] = useState(PLAYABLE_SCENARIOS[0].id);
  const [map, setMap] = useState('chapel-ruins');
  const [deploy, setDeploy] = useState<'alternate' | 'auto'>('alternate');
  const myErrors = validateLance(choices[mine].lance).errors;
  const theirErrors = validateLance(choices[theirs].lance).errors;

  const start = () => {
    const seed = Math.floor(Math.random() * 2 ** 31);
    onStart(createGame({ seed, scenario, map, deploy, lances: [choices[mine].lance, choices[theirs].lance] }));
  };

  return (
    <div className="setup panel">
      <h2>Muster a Charter Trial</h2>
      <p className="hint">You command the first lance. The rival AI commands the second.</p>
      <div className="setup-grid">
        <label className="field">
          <span>Your lance</span>
          <select value={mine} onChange={(e) => setMine(Number(e.target.value))}>
            {choices.map((c, i) => (
              <option key={i} value={i}>
                {c.label}
              </option>
            ))}
          </select>
          {myErrors.length > 0 && <small className="bad">Not legal yet: {myErrors[0]}</small>}
        </label>
        <label className="field">
          <span>Opponent</span>
          <select value={theirs} onChange={(e) => setTheirs(Number(e.target.value))}>
            {choices.map((c, i) => (
              <option key={i} value={i}>
                {c.label}
              </option>
            ))}
          </select>
          {theirErrors.length > 0 && <small className="bad">Not legal yet: {theirErrors[0]}</small>}
        </label>
        <label className="field">
          <span>Scenario</span>
          <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
            {PLAYABLE_SCENARIOS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Battlefield</span>
          <select value={map} onChange={(e) => setMap(e.target.value)}>
            {MAPS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="field">
        <span>Deployment</span>
        <select value={deploy} onChange={(e) => setDeploy(e.target.value as 'alternate' | 'auto')}>
          <option value="alternate">Take turns placing war-walkers</option>
          <option value="auto">Quick: line up on each edge</option>
        </select>
      </label>
      <p className="hint">{SCENARIOS.find((s) => s.id === scenario)?.rules || 'Hold objectives at the end of each round to score.'}</p>
      {scenario === 'surveyor-escort' && <p className="hint">You escort the surveyor; the AI tries to stop it.</p>}
      <button className="start" disabled={myErrors.length > 0 || theirErrors.length > 0} onClick={start}>
        Begin the Trial
      </button>
    </div>
  );
}

function tryApply(state: GameState, action: Action): GameState | null {
  try {
    return applyAction(state, action).state;
  } catch (e) {
    if (e instanceof IllegalAction) return null;
    throw e;
  }
}

function Trial({ initial, onQuit }: { initial: GameState; onQuit: () => void }) {
  const [state, setState] = useState(initial);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [targetId, setTargetId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>('move');
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<'3d' | '2d'>(() => (localStorage.getItem('boardView') === '2d' || !webglAvailable() ? '2d' : '3d'));
  const chooseView = (v: '3d' | '2d') => {
    localStorage.setItem('boardView', v);
    setView(v);
  };

  const act = (action: Action) => {
    try {
      setState(applyAction(state, action).state);
      setError(null);
    } catch (e) {
      if (e instanceof IllegalAction) setError(e.message);
      else throw e;
    }
  };
  const can = (action: Action) => tryApply(state, action) !== null;

  // The AI plays its side on a short timer so you can follow what it does.
  useEffect(() => {
    if (state.phase === 'over' || state.activeSide === HUMAN) return;
    const t = setTimeout(() => setState((s) => (s.activeSide === HUMAN || s.phase === 'over' ? s : applyAction(s, chooseAction(s)).state)), AI_DELAY_MS);
    return () => clearTimeout(t);
  }, [state]);

  const active = state.active ? state.walkers.find((w) => w.id === state.active!.walkerId)! : null;
  const mineActive = active && active.side === HUMAN ? active : null;

  useEffect(() => {
    if (mineActive) setSelectedId(mineActive.id);
    setMode('move');
  }, [mineActive?.id]);

  // Default target: the nearest enemy to the active walker.
  useEffect(() => {
    if (!mineActive) return;
    const t = targetId ? state.walkers.find((w) => w.id === targetId) : null;
    if (t && !t.destroyed) return;
    const enemies = aliveWalkers(state, 1).sort((a, b) => distance(a.pos, mineActive.pos) - distance(b.pos, mineActive.pos));
    setTargetId(enemies[0]?.id ?? null);
  }, [state, mineActive?.id]);

  const moves = useMemo(() => {
    if (!mineActive || !state.active || state.active.pressure < 1 || mineActive.prone) return new Map<string, Hex[]>();
    const r = reachable(state, mineActive, moveAllowance(state, mineActive));
    return new Map([...r].map(([k, v]) => [k, v.path]));
  }, [state, mineActive]);

  const deploying = state.phase === 'deployment' && state.activeSide === HUMAN;
  const toDeploy = deploying ? deployable(state) : [];
  useEffect(() => {
    if (deploying && !toDeploy.some((w) => w.id === selectedId)) setSelectedId(toDeploy[0]?.id ?? null);
  }, [state]);

  const escorts = useMemo(
    () => (mineActive && mode === 'escort' ? escortMoves(state, can) : new Map<string, Hex[]>()),
    [state, mineActive, mode],
  );

  const jetUid = mineActive ? workingItems(mineActive, 'jump-jets')[0]?.uid : undefined;
  const smokeUid = mineActive ? workingItems(mineActive, 'smoke-launcher')[0]?.uid : undefined;

  const highlights = useMemo(() => {
    const h = new Map<string, Highlight>();
    if (deploying && selectedId) {
      for (const hex of deploymentZone(state, HUMAN)) {
        if (can({ type: 'deploy', walkerId: selectedId, hex })) h.set(hexKey(hex), 'move');
      }
      return h;
    }
    if (!mineActive) return h;
    if (mode === 'escort') for (const k of escorts.keys()) h.set(k, 'jump');
    if (mode === 'move') for (const k of moves.keys()) h.set(k, 'move');
    if (mode === 'jump' && jetUid) {
      for (const k of Object.keys(state.map.hexes)) {
        const [q, r] = k.split(',').map(Number);
        if (can({ type: 'useItem', itemUid: jetUid, hex: { q, r } })) h.set(k, 'jump');
      }
    }
    if (mode === 'smoke' && smokeUid) {
      for (const k of Object.keys(state.map.hexes)) {
        const [q, r] = k.split(',').map(Number);
        if (distance(mineActive.pos, { q, r }) <= 1) h.set(k, 'smoke');
      }
    }
    return h;
  }, [mode, moves, escorts, state, mineActive, jetUid, smokeUid, deploying, selectedId]);

  // Red target rings: everything within short range of the active walker.
  const threat = useMemo(() => {
    const t = new Set<string>();
    if (!mineActive || mode !== 'move') return t;
    for (const k of Object.keys(state.map.hexes)) {
      const [q, r] = k.split(',').map(Number);
      const d = distance(mineActive.pos, { q, r });
      if (d >= 1 && d <= 3) t.add(k);
    }
    return t;
  }, [state, mineActive, mode]);

  const onHex = (hex: Hex) => {
    const key = hexKey(hex);
    if (deploying && selectedId && highlights.has(key)) {
      act({ type: 'deploy', walkerId: selectedId, hex });
      return;
    }
    if (!mineActive) return;
    if (mode === 'escort' && escorts.has(key)) {
      act({ type: 'escort', path: escorts.get(key)! });
      setMode('move');
      return;
    }
    if (mode === 'move' && moves.has(key)) {
      const enemy = aliveWalkers(state, 1).sort((a, b) => distance(a.pos, hex) - distance(b.pos, hex))[0];
      act({ type: 'move', path: moves.get(key)!, facing: enemy ? facingTowards(hex, enemy.pos) : undefined });
    } else if (mode === 'jump' && jetUid && highlights.has(key)) {
      const enemy = aliveWalkers(state, 1).sort((a, b) => distance(a.pos, hex) - distance(b.pos, hex))[0];
      act({ type: 'useItem', itemUid: jetUid, hex, facing: enemy ? facingTowards(hex, enemy.pos) : undefined });
      setMode('move');
    } else if (mode === 'smoke' && smokeUid && highlights.has(key)) {
      act({ type: 'useItem', itemUid: smokeUid, hex });
      setMode('move');
    }
  };

  const onWalker = (id: string) => {
    if (id === SURVEYOR_ID) {
      if (state.surveyor?.side !== HUMAN) setTargetId(id);
      else if (mineActive) setMode(mode === 'escort' ? 'move' : 'escort');
      return;
    }
    const w = state.walkers.find((x) => x.id === id)!;
    if (w.side !== HUMAN) {
      setTargetId(id);
      if (!mineActive) setSelectedId(id);
    } else if (!mineActive) setSelectedId(id);
    else if (mode !== 'move') onHex(w.pos);
  };

  const selected = state.walkers.find((w) => w.id === selectedId) ?? null;
  const target = state.walkers.find((w) => w.id === targetId) ?? null;
  const targetName = targetId === SURVEYOR_ID ? 'the surveyor' : target?.name;
  const sv = state.surveyor;
  const myTurn = state.phase !== 'over' && state.activeSide === HUMAN;

  return (
    <div className="trial">
      <div className="board panel">
        <div className="scoreline">
          <span className="side0">
            {state.lances[0].name} <strong>{state.vp[0]}</strong>
          </span>
          <span className="round">
            {state.phase === 'deployment' ? 'Deployment' : `Round ${Math.min(state.round, state.rounds)} of ${state.rounds}`}
            {sv && (
              <small>
                {' · '}Surveyor {sv.status === 'active' ? `${sv.hp} hits left` : sv.status === 'exited' ? 'escaped' : 'destroyed'}
              </small>
            )}
          </span>
          <span className="side1">
            <strong>{state.vp[1]}</strong> {state.lances[1].name}
          </span>
        </div>
        <div className="view-toggle" role="group" aria-label="Board view">
          <button className={view === '3d' ? 'on' : ''} onClick={() => chooseView('3d')}>3D</button>
          <button className={view === '2d' ? 'on' : ''} onClick={() => chooseView('2d')}>Flat map</button>
        </div>
        {view === '3d' ? (
          <div className="board3d-wrap">
            <Board3D state={state} highlights={highlights} selectedId={selectedId} targetId={targetId} threat={threat} onHex={onHex} onWalker={onWalker} />
            <BoardHud state={state} focus={selected ?? mineActive} order={deploying ? 'DEPLOY' : mode.toUpperCase()} />
          </div>
        ) : (
          <HexMap state={state} highlights={highlights} selectedId={selectedId} targetId={targetId} onHex={onHex} onWalker={onWalker} />
        )}
        <p className="legend">
          Rough ∴ costs 2 to enter · Light cover ♣ +1 TN · Heavy cover ▲ +2 TN, blocks sight through it · Dark hexes are impassable · Rings
          mark high ground · Gold circles are objectives{sv ? ' · The brass diamond is the surveyor' : ''}
        </p>
      </div>

      <div className="side-panel">
        {state.phase === 'over' ? (
          <div className="panel result">
            <h2>{state.winner === 'draw' ? 'A drawn Trial' : state.winner === HUMAN ? 'The Charter is yours' : 'The Charter is lost'}</h2>
            <p>
              Final score {state.vp[0]} to {state.vp[1]}.
            </p>
            <button onClick={onQuit}>New Trial</button>
          </div>
        ) : deploying ? (
          <div className="panel">
            <h3>Deploy your war-walkers</h3>
            <p className="hint">Pick a war-walker, then click a highlighted hex in your zone. The sides take turns.</p>
            <ul className="activate-list">
              {toDeploy.map((w) => (
                <li key={w.id} className={w.id === selectedId ? 'active' : ''}>
                  <button className="link" onClick={() => setSelectedId(w.id)}>
                    {w.name}
                  </button>
                  <small>{getChassis(w.chassis).name}</small>
                </li>
              ))}
            </ul>
            {state.lances[HUMAN].faction === 'reliquary' && (
              <p className="hint">From the Veil: your last war-walker deploys after the enemy has finished.</p>
            )}
          </div>
        ) : !myTurn ? (
          <div className="panel">
            <h3>Opponent's turn</h3>
            <p className="hint">
              {state.phase === 'deployment' ? 'The rival AI is deploying…' : active ? `${active.name} is acting…` : 'The rival AI is choosing…'}
            </p>
          </div>
        ) : mineActive ? (
          <ActivationPanel
            state={state}
            walker={mineActive}
            target={target}
            targetId={targetId}
            targetName={targetName}
            mode={mode}
            setMode={setMode}
            act={act}
            can={can}
            jetUid={jetUid}
            smokeUid={smokeUid}
          />
        ) : (
          <div className="panel">
            <h3>Your turn: choose a war-walker</h3>
            <ul className="activate-list">
              {aliveWalkers(state, HUMAN)
                .filter((w) => !w.activated)
                .map((w) => (
                  <li key={w.id} className={w.id === selectedId ? 'active' : ''}>
                    <button className="link" onClick={() => setSelectedId(w.id)}>
                      {w.name}
                    </button>
                    <span>
                      {[0, 1, 2].map((t) => (
                        <button
                          key={t}
                          disabled={!can({ type: 'activate', walkerId: w.id, throttle: t })}
                          title={t ? `Open the Throttle: +${t} Pressure, +${t} Overpressure` : 'Activate'}
                          onClick={() => act({ type: 'activate', walkerId: w.id, throttle: t })}
                        >
                          {t === 0 ? 'Activate' : `+${t}`}
                        </button>
                      ))}
                    </span>
                  </li>
                ))}
            </ul>
            {can({ type: 'pass' }) && (
              <button className="secondary" onClick={() => act({ type: 'pass' })}>
                Pass (once per round)
              </button>
            )}
          </div>
        )}

        {error && <div className="errors">{error}</div>}
        {selected && <WalkerCard walker={selected} />}
        {target && target.id !== selected?.id && <WalkerCard walker={target} />}
        <Log state={state} />
        <button className="secondary" onClick={onQuit}>
          Abandon Trial
        </button>
      </div>
    </div>
  );
}

type Mode = 'move' | 'jump' | 'smoke' | 'escort';

/** Hexes the friendly surveyor can be escorted to from here, with the path to each. */
function escortMoves(state: GameState, can: (a: Action) => boolean): Map<string, Hex[]> {
  const out = new Map<string, Hex[]>();
  const sv = state.surveyor;
  if (sv?.status !== 'active') return out;
  for (const n of neighbors(sv.pos)) {
    if (!can({ type: 'escort', path: [n] })) continue;
    out.set(hexKey(n), [n]);
    for (const m of neighbors(n)) {
      if (!out.has(hexKey(m)) && can({ type: 'escort', path: [n, m] })) out.set(hexKey(m), [n, m]);
    }
  }
  return out;
}

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
  jetUid?: string;
  smokeUid?: string;
}

function ActivationPanel({ state, walker, target, targetId, targetName, mode, setMode, act, can, jetUid, smokeUid }: PanelProps) {
  const a = state.active!;
  const sv = state.surveyor;
  const canEscort = sv?.status === 'active' && sv.side === walker.side && distance(sv.pos, walker.pos) === 1 && a.pressure >= 1;
  const weapons = workingItems(walker).filter((it) => getEquipment(it.id).weapon);
  const damagedZone = (Object.keys(walker.armour) as Zone[]).find((z) => walker.armour[z] < walker.maxArmour[z]);
  const utilities: Array<{ label: string; action: Action; title: string }> = [];
  for (const it of workingItems(walker)) {
    const def = getEquipment(it.id);
    if (it.id === 'coolant-loop' || it.id === 'anchor-spikes') utilities.push({ label: def.name, action: { type: 'useItem', itemUid: it.uid }, title: def.rules });
    if (it.id === 'spotter-drone' && target) utilities.push({ label: `${def.name} → ${target.name}`, action: { type: 'useItem', itemUid: it.uid, walkerId: target.id }, title: def.rules });
    if (it.id === 'field-repair-rig' && damagedZone)
      utilities.push({ label: `Repair ${ZONE_NAMES[damagedZone]}`, action: { type: 'useItem', itemUid: it.uid, zone: damagedZone }, title: def.rules });
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
          : mode === 'jump'
            ? 'Click a highlighted hex to jump (2 Pressure, +1 Overpressure).'
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
        {jetUid && (
          <button className={mode === 'jump' ? 'on' : ''} disabled={a.pressure < 2} onClick={() => setMode(mode === 'jump' ? 'move' : 'jump')}>
            Jump Jets
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

function Bar({ value, max, label }: { value: number; max: number; label: string }) {
  return (
    <div className="bar" aria-label={`${label}: ${value} of ${max}`}>
      <div style={{ width: `${max ? (value / max) * 100 : 0}%` }} />
      <span>
        {value}/{max}
      </span>
    </div>
  );
}

function WalkerCard({ walker }: { walker: WalkerState }) {
  const c = getChassis(walker.chassis);
  const structureMax = { core: c.structure.core, armLeft: c.structure.other, armRight: c.structure.other, legs: c.structure.other };
  const flags = [
    walker.destroyed && 'Destroyed',
    walker.prone && 'Prone',
    walker.braced && 'Braced',
    walker.anchored && 'Anchored',
    walker.spottedBy !== null && 'Spotted',
    walker.activated && 'Activated',
  ].filter(Boolean);
  return (
    <div className={`panel card side${walker.side}`}>
      <div className="card-head">
        <h3>{walker.name}</h3>
        <small>
          {c.name} · {walker.cost} pts
        </small>
      </div>
      <table className="grid-table compact">
        <thead>
          <tr>
            <th>Location</th>
            <th>Armour</th>
            <th>Structure</th>
          </tr>
        </thead>
        <tbody>
          {(['coreFront', 'coreRear', 'armLeft', 'armRight', 'legs'] as Zone[]).map((z) => {
            const loc = z === 'coreFront' || z === 'coreRear' ? 'core' : z;
            return (
              <tr key={z} className={walker.destroyedLocations.includes(loc) ? 'gone' : ''}>
                <td>{ZONE_NAMES[z]}</td>
                <td>
                  <Bar value={walker.armour[z]} max={walker.maxArmour[z]} label="Armour" />
                </td>
                <td>{z === 'coreRear' ? '' : <Bar value={walker.structure[loc]} max={structureMax[loc]} label="Structure" />}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="hint">
        Overpressure {walker.overpressure}/6 · Reserve {walker.reserve}
        {flags.length ? ` · ${flags.join(', ')}` : ''}
      </p>
      <p className="items-line">
        {walker.items.map((it) => (
          <span key={it.uid} className={it.destroyed || walker.destroyedLocations.includes(it.location) ? 'gone' : ''}>
            {getEquipment(it.id).name}
          </span>
        ))}
      </p>
    </div>
  );
}

function Log({ state }: { state: GameState }) {
  const entries = state.log.slice(-60).reverse();
  return (
    <div className="panel log">
      <h3>Trial record</h3>
      <ol>
        {entries.map((e, i) => (
          <li key={state.log.length - i} className={`log-${e.type}`}>
            {e.text}
          </li>
        ))}
      </ol>
    </div>
  );
}
