// The Charter Trial tab: setup, then the battle against the AI on the 2D or 3D board.
import { useEffect, useMemo, useState } from 'react';
import { chooseAction } from '@brass-charter/ai';
import { isTouch, timeAi } from './perf';
import {
  IllegalAction,
  SURVEYOR_ID,
  aliveWalkers,
  applyAction,
  deployable,
  deploymentZone,
  distance,
  facingTowards,
  getChassis,
  hexKey,
  neighbors,
  reachable,
  moveAllowance,
  workingItems,
  type Action,
  type GameState,
  type Hex,
} from '@brass-charter/rules';
import { ActivationPanel, type Mode } from './ActivationPanel';
import { Board3D } from './Board3D';
import { BoardHud } from './BoardHud';
import { CombatReplay, ReplayToggle, useCombatReplay } from './CombatReplay';
import { HexMap, type Highlight } from './HexMap';
import { Setup } from './Setup';
import { WalkerCard } from './WalkerCard';

function webglAvailable() {
  try {
    return !!document.createElement('canvas').getContext('webgl2');
  } catch {
    return false;
  }
}

const HUMAN = 0;
const AI_DELAY_MS = 450;

export function Battle() {
  const [game, setGame] = useState<GameState | null>(null);
  return game ? <Trial initial={game} onQuit={() => setGame(null)} /> : <Setup onStart={setGame} />;
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
  const replay = useCombatReplay(state);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [targetId, setTargetId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>('move');
  const [error, setError] = useState<string | null>(null);
  // On a touch screen the first tap on a hex only previews it (gold path and a Confirm bar); a second tap on it, or Confirm, commits.
  const [pending, setPending] = useState<Hex | null>(null);
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
    // Hold the AI back while a dice roll is being shown so each exchange can be followed.
    if (state.phase === 'over' || state.activeSide === HUMAN || replay.busy) return;
    const t = setTimeout(() => setState((s) => (s.activeSide === HUMAN || s.phase === 'over' ? s : applyAction(s, timeAi(() => chooseAction(s))).state)), AI_DELAY_MS);
    return () => clearTimeout(t);
  }, [state, replay.busy]);

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

  const smokeUid = mineActive ? workingItems(mineActive, 'smoke-launcher')[0]?.uid : undefined;

  const baseHighlights = useMemo(() => {
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
    if (mode === 'smoke' && smokeUid) {
      for (const k of Object.keys(state.map.hexes)) {
        const [q, r] = k.split(',').map(Number);
        if (distance(mineActive.pos, { q, r }) <= 1) h.set(k, 'smoke');
      }
    }
    return h;
  }, [mode, moves, escorts, state, mineActive, smokeUid, deploying, selectedId]);

  // The previewed move or escort path shows in gold over the blue reach hexes.
  const highlights = useMemo(() => {
    if (!pending) return baseHighlights;
    const h = new Map(baseHighlights);
    const path = mode === 'move' ? moves.get(hexKey(pending)) : mode === 'escort' ? escorts.get(hexKey(pending)) : undefined;
    for (const p of path ?? [pending]) h.set(hexKey(p), 'jump');
    return h;
  }, [baseHighlights, pending, mode, moves, escorts]);
  useEffect(() => setPending(null), [state, mode, selectedId, mineActive?.id]);

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

  const commitKey = (key: string) =>
    deploying
      ? !!selectedId && baseHighlights.has(key)
      : !!mineActive && (mode === 'escort' ? escorts.has(key) : mode === 'move' ? moves.has(key) : mode === 'smoke' && !!smokeUid && baseHighlights.has(key));
  const commitLabel = deploying ? 'Deploy here' : mode === 'escort' ? 'Escort the surveyor here' : mode === 'smoke' ? 'Throw smoke here' : 'Move here';
  const onHex = (hex: Hex) => {
    if (isTouch() && commitKey(hexKey(hex)) && (!pending || hexKey(pending) !== hexKey(hex))) {
      setPending(hex);
      return;
    }
    setPending(null);
    commitHex(hex);
  };
  const commitHex = (hex: Hex) => {
    const key = hexKey(hex);
    if (deploying && selectedId && baseHighlights.has(key)) {
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
    } else if (mode === 'smoke' && smokeUid && baseHighlights.has(key)) {
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
      <div className={view === '3d' ? 'board panel board-3d' : 'board panel'}>
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
        {pending && (
          <div className="confirm-bar" role="group" aria-label="Confirm the previewed hex">
            <span>{commitLabel}?</span>
            <button onClick={() => { setPending(null); commitHex(pending); }}>Confirm</button>
            <button className="secondary" onClick={() => setPending(null)}>Cancel</button>
          </div>
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
            <p className="hint">Pick a war-walker, then {isTouch() ? 'tap' : 'click'} a highlighted hex in your zone. The sides take turns.</p>
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
        <ReplayToggle replay={replay} />
        <Log state={state} />
        <button className="secondary" onClick={onQuit}>
          Abandon Trial
        </button>
      </div>
      <CombatReplay replay={replay} />
    </div>
  );
}

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
