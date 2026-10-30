import { useEffect, useMemo, useRef, useState } from 'react';
import {
  CHASSIS,
  COMMAND_COST,
  COMPANIES,
  RULES,
  TRAITS,
  getCompany,
  validateLance,
  validateWalker,
  walkerCost,
  type LanceInput,
  type WalkerInput,
} from '@brass-charter/rules';
import examples from '../../../data/lances/examples.json';
import { WalkerEditor } from './WalkerEditor';
import { downloadLance, loadDraft, loadSaved, parseLance, saveDraft, storeSaved } from './storage';

const EXAMPLES = examples.lances as LanceInput[];
const NAMES = ['Gimbal', 'Sprocket', 'Tallow', 'Ember', 'Ratchet', 'Cinder', 'Flue', 'Piston', 'Rook', 'Valve'];

const newWalker = (taken: string[]): WalkerInput => ({
  name: NAMES.find((n) => !taken.includes(n)) ?? `Walker ${taken.length + 1}`,
  chassis: 'scout',
  driver: { command: 0, trait: null },
  loadout: {},
});

const emptyLance = (): LanceInput => ({ name: 'New Lance', company: 'halvorsen', walkers: [] });

export function App() {
  const [lance, setLance] = useState<LanceInput>(() => loadDraft() ?? structuredClone(EXAMPLES[1]));
  const [selected, setSelected] = useState(0);
  const [saved, setSaved] = useState<Record<string, LanceInput>>(loadSaved);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => saveDraft(lance), [lance]);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 3000);
    return () => clearTimeout(t);
  }, [notice]);

  const report = useMemo(() => validateLance(lance), [lance]);
  const company = getCompany(lance.company);
  const budget = RULES.lance.budget;
  const { minWalkers, maxWalkers } = RULES.lance;
  const current = lance.walkers[selected] as WalkerInput | undefined;

  const update = (fn: (l: LanceInput) => void) =>
    setLance((prev) => {
      const next = structuredClone(prev);
      fn(next);
      return next;
    });

  const replaceLance = (l: LanceInput) => {
    setLance(structuredClone(l));
    setSelected(0);
  };

  const addWalker = () => {
    update((l) => l.walkers.push(newWalker(l.walkers.map((w) => w.name))));
    setSelected(lance.walkers.length);
  };

  const removeWalker = (i: number) => {
    update((l) => l.walkers.splice(i, 1));
    setSelected((s) => Math.max(0, s >= i ? s - 1 : s));
  };

  const duplicateWalker = (i: number) => {
    update((l) => {
      const copy = structuredClone(l.walkers[i]);
      copy.name = newWalker(l.walkers.map((w) => w.name)).name;
      l.walkers.splice(i + 1, 0, copy);
    });
    setSelected(i + 1);
  };

  const saveLance = () => {
    const next = { ...saved, [lance.name]: structuredClone(lance) };
    setSaved(next);
    storeSaved(next);
    setNotice(`Saved "${lance.name}".`);
  };

  const deleteSaved = (name: string) => {
    const next = { ...saved };
    delete next[name];
    setSaved(next);
    storeSaved(next);
  };

  const importFile = async (file: File) => {
    try {
      replaceLance(parseLance(await file.text()));
      setNotice(`Imported "${file.name}".`);
    } catch (e) {
      setNotice(e instanceof Error ? e.message : 'Could not read that file.');
    }
  };

  const pct = Math.min(100, (report.total / budget) * 100);
  const over = report.total > budget;
  const lanceErrors = report.errors.filter((e) => !lance.walkers.some((w) => e.startsWith(`${w.name}: `)));

  return (
    <div className="app">
      <header className="masthead">
        <div>
          <h1>Brass Charter</h1>
          <p className="subtitle">Lance Ledger · Charter Trial muster</p>
        </div>
        <div className="masthead-actions">
          <select
            aria-label="Load an example lance"
            value=""
            onChange={(e) => {
              const ex = EXAMPLES.find((x) => x.name === e.target.value);
              if (ex) replaceLance(ex);
            }}
          >
            <option value="">Load example…</option>
            {EXAMPLES.map((ex) => (
              <option key={ex.name}>{ex.name}</option>
            ))}
          </select>
          <button onClick={() => replaceLance(emptyLance())}>New lance</button>
          <button onClick={saveLance}>Save</button>
          <button onClick={() => downloadLance(lance)}>Export</button>
          <button onClick={() => fileInput.current?.click()}>Import</button>
          <input
            ref={fileInput}
            type="file"
            accept="application/json,.json"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) importFile(f);
              e.target.value = '';
            }}
          />
        </div>
      </header>

      {notice && <div className="notice">{notice}</div>}

      <div className="layout">
        <aside className="panel lance">
          <label className="field">
            <span>Lance name</span>
            <input value={lance.name} onChange={(e) => update((l) => void (l.name = e.target.value))} />
          </label>
          <label className="field">
            <span>Company</span>
            <select value={lance.company} onChange={(e) => update((l) => void (l.company = e.target.value))}>
              {COMPANIES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <p className="doctrine">
            <strong>{company.specialty}.</strong> {company.doctrine}
          </p>

          <div className={`budget ${over ? 'over' : ''}`}>
            <div className="budget-head">
              <span>Points</span>
              <strong>
                {report.total} / {budget}
              </strong>
            </div>
            <div className="gauge" role="meter" aria-valuemin={0} aria-valuemax={budget} aria-valuenow={report.total}>
              <div style={{ width: `${pct}%` }} />
            </div>
            <div className="budget-foot">
              {lance.walkers.length} war-walker{lance.walkers.length === 1 ? '' : 's'} (needs {minWalkers}–{maxWalkers})
            </div>
          </div>

          <ol className="roster">
            {lance.walkers.map((w, i) => {
              const ok = validateWalker(w).length === 0;
              return (
                <li key={i} className={i === selected ? 'active' : ''}>
                  <button className="roster-main" onClick={() => setSelected(i)}>
                    <span className="roster-name">
                      {w.name}
                      {!ok && <span className="flag" title="This build has problems"> !</span>}
                    </span>
                    <span className="roster-meta">
                      {CHASSIS.find((c) => c.id === w.chassis)?.name ?? w.chassis} · {ok ? walkerCost(w, company) : '?'} pts
                    </span>
                  </button>
                  <span className="roster-tools">
                    <button title="Duplicate" aria-label={`Duplicate ${w.name}`} onClick={() => duplicateWalker(i)}>
                      ⧉
                    </button>
                    <button title="Remove" aria-label={`Remove ${w.name}`} onClick={() => removeWalker(i)}>
                      ✕
                    </button>
                  </span>
                </li>
              );
            })}
          </ol>
          <button className="add" onClick={addWalker} disabled={lance.walkers.length >= maxWalkers}>
            + Add war-walker
          </button>

          {lanceErrors.length > 0 && (
            <ul className="errors">
              {lanceErrors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          )}
          {report.errors.length === 0 && <p className="ready">Ready for a Charter Trial.</p>}

          {Object.keys(saved).length > 0 && (
            <div className="saved">
              <h3>Saved lances</h3>
              <ul>
                {Object.entries(saved).map(([name, l]) => (
                  <li key={name}>
                    <button className="link" onClick={() => replaceLance(l)}>
                      {name}
                    </button>
                    <button title="Delete" aria-label={`Delete ${name}`} onClick={() => deleteSaved(name)}>
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        <main className="editor">
          {current ? (
            <WalkerEditor
              walker={current}
              company={company}
              commandCosts={COMMAND_COST}
              traits={TRAITS}
              onChange={(w) => update((l) => void (l.walkers[selected] = w))}
            />
          ) : (
            <div className="panel empty">
              <p>No war-walkers yet. Add one to start building your lance.</p>
              <button className="add" onClick={addWalker}>
                + Add war-walker
              </button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
