// The Trial's setup screen: pick both lances, the scenario and the map.
import { useMemo, useState } from 'react';
import {
  MAPS,
  SCENARIOS,
  createGame,
  validateLance,
  type GameState,
  type LanceInput,
} from '@brass-charter/rules';
import examples from '../../../../data/lances/examples.json';
import { loadDraft, loadSaved } from '../storage';

const EXAMPLES = examples.lances as LanceInput[];

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

export function Setup({ onStart }: { onStart: (g: GameState) => void }) {
  const choices = useMemo(lanceChoices, []);
  const [mine, setMine] = useState(0);
  const [theirs, setTheirs] = useState(Math.max(0, choices.findIndex((c) => c.lance.name === EXAMPLES[2].name)));
  const [scenario, setScenario] = useState(SCENARIOS[0].id);
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
            {SCENARIOS.map((s) => (
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
