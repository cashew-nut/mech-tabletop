// Animated dice and combat cards. Whenever an action rolled dice, the target's card is brought up,
// the dice tumble and settle, and the damage drains out of the card's bars. Only dice and cards
// animate: the board, the walkers and the rules are untouched.
import { useCallback, useEffect, useRef, useState } from 'react';
import { getChassis, getEquipment, type GameState, type WalkerState, type Zone } from '@brass-charter/rules';
import { buildExchanges, type Die, type Exchange } from './combatReplay';
import './combatReplay.css';

const STORAGE_KEY = 'diceAnimations';
const ZONES: Array<[Zone, string]> = [
  ['coreFront', 'Core'],
  ['coreRear', 'Core (rear)'],
  ['armLeft', 'Left arm'],
  ['armRight', 'Right arm'],
  ['legs', 'Legs'],
];
const LOC: Record<Zone, 'core' | 'armLeft' | 'armRight' | 'legs'> = { coreFront: 'core', coreRear: 'core', armLeft: 'armLeft', armRight: 'armRight', legs: 'legs' };
const PIPS: Record<number, number[]> = { 1: [4], 2: [0, 8], 3: [0, 4, 8], 4: [0, 2, 6, 8], 5: [0, 2, 4, 6, 8], 6: [0, 2, 3, 5, 6, 8] };

const reducedMotion = () => typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

export interface Replay {
  current: Exchange | null;
  queued: number;
  busy: boolean;
  enabled: boolean;
  setEnabled: (on: boolean) => void;
  done: () => void;
}

/**
 * Watches the game state and queues a replay for every dice roll the engine logged since the last render.
 * `busy` is true while one is playing, so the caller can hold the AI back until it finishes.
 */
export function useCombatReplay(state: GameState): Replay {
  const last = useRef(state);
  const [queue, setQueue] = useState<Exchange[]>([]);
  const [enabled, setEnabledState] = useState(() => localStorage.getItem(STORAGE_KEY) !== 'off');
  const setEnabled = (on: boolean) => {
    localStorage.setItem(STORAGE_KEY, on ? 'on' : 'off');
    setEnabledState(on);
    if (!on) setQueue([]);
  };

  useEffect(() => {
    const before = last.current;
    last.current = state;
    if (before === state || !enabled || state.log.length <= before.log.length) return;
    const found = buildExchanges(before, state);
    if (found.length) setQueue((q) => [...q, ...found]);
  }, [state, enabled]);

  const done = useCallback(() => setQueue((q) => q.slice(1)), []);
  return { current: queue[0] ?? null, queued: queue.length, busy: queue.length > 0, enabled, setEnabled, done };
}

export function ReplayToggle({ replay }: { replay: Replay }) {
  return (
    <label className="replay-toggle">
      <input type="checkbox" checked={replay.enabled} onChange={(e) => replay.setEnabled(e.target.checked)} /> Animate dice and combat cards
    </label>
  );
}

export function CombatReplay({ replay }: { replay: Replay }) {
  const ex = replay.current;
  if (!ex) return null;
  return <ExchangeView key={ex.id} ex={ex} fast={replay.queued > 1} onDone={replay.done} />;
}

type Phase = 'roll' | 'impact' | 'exit';

function ExchangeView({ ex, fast, onDone }: { ex: Exchange; fast: boolean; onDone: () => void }) {
  const calm = useRef(reducedMotion()).current;
  const speed = calm ? 0.5 : fast ? 0.6 : 1;
  const [phase, setPhase] = useState<Phase>('roll');
  const [skipped, setSkipped] = useState(false);
  const hits = ex.dice.filter((d) => d.hit).length;
  const lastSettle = (calm ? 0 : 650) + (ex.dice.length - 1) * 150;

  useEffect(() => {
    const ms = phase === 'roll' ? (lastSettle + 650) * speed : phase === 'impact' ? (ex.impacts.length || ex.notes.length ? 1900 : 1200) * speed : 320;
    const t = setTimeout(() => (phase === 'roll' ? setPhase('impact') : phase === 'impact' ? setPhase('exit') : onDone()), ms);
    return () => clearTimeout(t);
  }, [phase]);

  const skip = () => {
    setSkipped(true);
    setPhase((p) => (p === 'roll' ? 'impact' : 'exit'));
  };

  const weapon = ex.kind === 'ram' ? 'Ram' : ex.kind === 'blast' ? 'Blast' : ex.itemId ? getEquipment(ex.itemId).name : 'Weapon';
  const attacker = ex.attackerAfter ?? ex.attackerBefore;
  const summary = `${ex.headline} ${hits} of ${ex.dice.length} dice hit.`;

  return (
    <div className={`replay replay-${phase}`} onClick={skip} role="status" aria-live="polite">
      <span className="sr-only">{summary}</span>
      <div className="replay-stage" aria-hidden="true">
        <div className="replay-plate">
          <strong>{attacker?.name ?? 'Attack'}</strong>
          <span>
            {weapon} · {ex.dice.length} {ex.dice.length === 1 ? 'die' : 'dice'} · hit on {ex.tn}+
          </span>
        </div>

        <div className="replay-dice">
          {ex.dice.map((d, i) => (
            <DieView key={i} die={d} index={i} settleMs={(calm ? 0 : 650 + i * 150) * speed} skipped={skipped} />
          ))}
        </div>
        <p className={`replay-tally ${phase === 'roll' ? '' : 'on'} ${hits ? 'good' : 'bad'}`}>
          {phase === 'roll' ? ' ' : hits ? `${hits} hit${hits > 1 ? 's' : ''}${ex.rerolled ? ' (Ace reroll)' : ''}` : `No hits${ex.rerolled ? ' (Ace reroll)' : ''}`}
        </p>

        {ex.surveyorHp ? (
          <SurveyorCard ex={ex} impact={phase !== 'roll'} />
        ) : ex.targetBefore && ex.targetAfter ? (
          <ReplayCard before={ex.targetBefore} after={ex.targetAfter} ex={ex} impact={phase !== 'roll'} />
        ) : null}
      </div>
    </div>
  );
}

function DieView({ die, index, settleMs, skipped }: { die: Die; index: number; settleMs: number; skipped: boolean }) {
  const [face, setFace] = useState(() => ((index * 5 + 2) % 6) + 1);
  const [settled, setSettled] = useState(settleMs === 0);
  useEffect(() => {
    if (settled) return;
    if (skipped) return void setSettled(true);
    const spin = setInterval(() => setFace((f) => ((f + 1 + Math.floor(Math.random() * 4)) % 6) + 1), 70);
    const stop = setTimeout(() => setSettled(true), settleMs);
    return () => {
      clearInterval(spin);
      clearTimeout(stop);
    };
  }, [settled, skipped]);
  const shown = settled ? die.value : face;
  const cls = !settled ? 'rolling' : die.crit ? 'hit crit' : die.hit ? 'hit' : 'miss';
  return (
    <div className={`die ${cls}`} style={{ animationDelay: `${index * 40}ms` }} aria-hidden="true">
      {PIPS[shown].map((p) => (
        <i key={p} style={{ gridArea: `${Math.floor(p / 3) + 1} / ${(p % 3) + 1}` }} />
      ))}
    </div>
  );
}

function Bar({ value, max }: { value: number; max: number }) {
  return (
    <div className="rbar">
      <div style={{ width: `${max ? (value / max) * 100 : 0}%` }} />
      <span>
        {value}/{max}
      </span>
    </div>
  );
}

function ReplayCard({ before, after, ex, impact }: { before: WalkerState; after: WalkerState; ex: Exchange; impact: boolean }) {
  const c = getChassis(after.chassis);
  const structMax = { core: c.structure.core, armLeft: c.structure.other, armRight: c.structure.other, legs: c.structure.other };
  const shown = impact ? after : before;
  const dealt = (z: Zone) => ex.impacts.filter((i) => i.zone === z).reduce((n, i) => n + i.damage, 0);
  return (
    <div className={`panel card replay-card side${after.side}`}>
      <div className="card-head">
        <h3>{after.name}</h3>
        <small>
          {c.name} · {after.cost} pts
        </small>
      </div>
      <table className="grid-table compact">
        <tbody>
          {ZONES.map(([z, label]) => {
            const loc = LOC[z];
            const gone = impact && after.destroyedLocations.includes(loc);
            const dmg = dealt(z);
            return (
              <tr key={z} className={`${gone ? 'gone' : ''} ${impact && dmg > 0 ? 'struck' : ''}`}>
                <td>{label}</td>
                <td>
                  <Bar value={shown.armour[z]} max={after.maxArmour[z]} />
                </td>
                <td>{z === 'coreRear' ? '' : <Bar value={shown.structure[loc]} max={structMax[loc]} />}</td>
                <td className="dmg">{impact && dmg > 0 ? <b>−{dmg}</b> : ''}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="hint">
        Overpressure {shown.overpressure}/6 · Reserve {shown.reserve}
        {after.destroyed && impact ? ' · Destroyed' : after.prone && impact ? ' · Prone' : ''}
      </p>
      <Notes ex={ex} show={impact} />
    </div>
  );
}

function SurveyorCard({ ex, impact }: { ex: Exchange; impact: boolean }) {
  const hp = ex.surveyorHp!;
  const shown = impact ? hp.after : hp.before;
  return (
    <div className="panel card replay-card">
      <div className="card-head">
        <h3>The surveyor</h3>
        <small>{hp.max} hits to destroy</small>
      </div>
      <Bar value={shown} max={hp.max} />
      <Notes ex={ex} show={impact} />
    </div>
  );
}

function Notes({ ex, show }: { ex: Exchange; show: boolean }) {
  if (!show) return <ul className="replay-notes" />;
  const shown = ex.notes.filter((n) => n.type !== 'hit' || ex.surveyorHp);
  return (
    <ul className="replay-notes">
      {shown.map((n, i) => (
        <li key={i} className={`note-${n.type}`} style={{ animationDelay: `${i * 160}ms` }}>
          {n.text}
        </li>
      ))}
    </ul>
  );
}
