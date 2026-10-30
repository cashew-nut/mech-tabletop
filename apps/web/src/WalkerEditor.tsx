import { Suspense, lazy } from 'react';
import {
  CHASSIS,
  EQUIPMENT,
  getChassis,
  getEquipment,
  itemCost,
  mountableItems,
  validateWalker,
  walkerCost,
  walkerStats,
  type CompanyDef,
  type Location,
  type TraitDef,
  type WalkerInput,
} from '@brass-charter/rules';

// Three.js is large, so the 3D view loads on demand.
const WalkerModel = lazy(() => import('./model/WalkerModel'));

const LOCATION_NAMES: Record<Location, string> = {
  armLeft: 'Left arm',
  core: 'Core',
  armRight: 'Right arm',
  legs: 'Legs',
};

const CATEGORY_NAMES = { weapon: 'Weapons', defence: 'Defence', mobility: 'Mobility', system: 'Systems' } as const;
const BAND_NAMES = { melee: 'Melee', short: 'Short', medium: 'Medium', long: 'Long' } as const;

interface Props {
  walker: WalkerInput;
  company: CompanyDef;
  commandCosts: Map<number, number>;
  traits: TraitDef[];
  onChange: (w: WalkerInput) => void;
}

export function WalkerEditor({ walker, company, commandCosts, traits, onChange }: Props) {
  const chassis = getChassis(walker.chassis);
  const errors = validateWalker(walker);
  const stats = walkerStats(walker);
  const cost = errors.length ? null : walkerCost(walker, company);

  const edit = (fn: (w: WalkerInput) => void) => {
    const next = structuredClone(walker);
    fn(next);
    onChange(next);
  };

  const addItem = (loc: Location, id: string) => edit((w) => void (w.loadout[loc] = [...(w.loadout[loc] ?? []), id]));
  const removeItem = (loc: Location, index: number) => edit((w) => void w.loadout[loc]!.splice(index, 1));
  const countOf = (id: string) => Object.values(walker.loadout).flat().filter((x) => x === id).length;

  const pressureOk = stats.fullTurnPressure <= stats.boiler;

  return (
    <div className="walker">
      <section className="panel identity">
        <label className="field grow">
          <span>Name</span>
          <input value={walker.name} onChange={(e) => edit((w) => void (w.name = e.target.value))} />
        </label>
        <label className="field">
          <span>Chassis</span>
          <select value={walker.chassis} onChange={(e) => edit((w) => void (w.chassis = e.target.value))}>
            {CHASSIS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.points} pts)
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Driver Command</span>
          <select
            value={walker.driver.command}
            onChange={(e) => edit((w) => void (w.driver.command = Number(e.target.value)))}
          >
            {[...commandCosts].map(([value, pts]) => (
              <option key={value} value={value}>
                {value} ({pts} pts)
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Driver trait</span>
          <select
            value={walker.driver.trait ?? ''}
            title={traits.find((t) => t.id === walker.driver.trait)?.rules}
            onChange={(e) => edit((w) => void (w.driver.trait = e.target.value || null))}
          >
            <option value="">None</option>
            {traits.map((t) => (
              <option key={t.id} value={t.id} title={t.rules}>
                {t.name} ({t.points} pts)
              </option>
            ))}
          </select>
        </label>
        <div className="cost-badge" aria-label="War-walker cost">
          <span>{cost ?? '?'}</span>
          <small>pts</small>
        </div>
      </section>
      {walker.driver.trait && <p className="trait-rule">{traits.find((t) => t.id === walker.driver.trait)?.rules}</p>}

      <section className="doll" aria-label="Loadout">
        {(['armLeft', 'core', 'armRight', 'legs'] as Location[]).map((loc) => {
          const items = walker.loadout[loc] ?? [];
          const free = stats.slotsFree[loc];
          const options = mountableItems(loc, EQUIPMENT);
          return (
            <div key={loc} className={`panel location loc-${loc} ${free < 0 ? 'overfull' : ''}`}>
              <div className="location-head">
                <h3>{LOCATION_NAMES[loc]}</h3>
                <span className="pips" aria-label={`${stats.slotsUsed[loc]} of ${chassis.slots[loc]} slots used`}>
                  {Array.from({ length: Math.max(chassis.slots[loc], stats.slotsUsed[loc]) }, (_, i) => (
                    <i key={i} className={i < stats.slotsUsed[loc] ? (i < chassis.slots[loc] ? 'full' : 'excess') : ''} />
                  ))}
                </span>
              </div>
              <ul className="items">
                {items.map((id, i) => {
                  const def = getEquipment(id);
                  return (
                    <li key={`${id}-${i}`} title={def.rules}>
                      <div>
                        <strong>{def.name}</strong>
                        <small>
                          {def.slots} slot{def.slots > 1 ? 's' : ''} · {def.pressure} Pressure · {itemCost(id, company)} pts
                        </small>
                      </div>
                      <button aria-label={`Remove ${def.name}`} onClick={() => removeItem(loc, i)}>
                        ✕
                      </button>
                    </li>
                  );
                })}
                {items.length === 0 && <li className="empty-slot">Empty</li>}
              </ul>
              {chassis.slots[loc] > 0 && (
                <select
                  aria-label={`Add item to ${LOCATION_NAMES[loc]}`}
                  value=""
                  onChange={(e) => e.target.value && addItem(loc, e.target.value)}
                >
                  <option value="">+ Fit item…</option>
                  {(Object.keys(CATEGORY_NAMES) as Array<keyof typeof CATEGORY_NAMES>).map((cat) => {
                    const group = options.filter((o) => o.category === cat);
                    if (!group.length) return null;
                    return (
                      <optgroup key={cat} label={CATEGORY_NAMES[cat]}>
                        {group.map((o) => {
                          const tooBig = o.slots > free;
                          const atMax = !!o.maxPerWalker && countOf(o.id) >= o.maxPerWalker;
                          return (
                            <option key={o.id} value={o.id} disabled={tooBig || atMax} title={o.rules}>
                              {o.name} · {itemCost(o.id, company)} pts{tooBig ? ` (needs ${o.slots} slots)` : ''}
                              {atMax ? ' (limit reached)' : ''}
                            </option>
                          );
                        })}
                      </optgroup>
                    );
                  })}
                </select>
              )}
            </div>
          );
        })}
      </section>

      <Suspense fallback={<section className="panel model"><p className="hint">Loading 3D view…</p></section>}>
        <WalkerModel
          walker={walker}
          company={company.id}
          onPaint={(colour) => edit((w) => void (colour ? (w.paint = colour) : delete w.paint))}
        />
      </Suspense>

      {errors.length > 0 && (
        <ul className="errors">
          {errors.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}

      <section className="stats">
        <div className="panel">
          <h3>Boiler and movement</h3>
          <dl className="readout">
            <div>
              <dt>Stride</dt>
              <dd>
                {stats.stride}
                {stats.sprintStride !== stats.stride && <small> ({stats.sprintStride} first move)</small>}
              </dd>
            </div>
            <div>
              <dt>Boiler</dt>
              <dd>{stats.boiler} Pressure</dd>
            </div>
            <div>
              <dt>Move + fire all</dt>
              <dd className={pressureOk ? '' : 'warn'}>{stats.fullTurnPressure} Pressure</dd>
            </div>
            <div>
              <dt>Faults from</dt>
              <dd>{stats.faultThreshold} Overpressure</dd>
            </div>
          </dl>
          <p className="hint">
            {pressureOk
              ? 'It can move once and fire every weapon in one activation.'
              : `Moving and firing everything needs ${stats.fullTurnPressure - stats.boiler} more Pressure than the boiler makes, so it must choose or Open the Throttle.`}
          </p>
        </div>

        <div className="panel">
          <h3>Armour and structure</h3>
          <table className="grid-table">
            <thead>
              <tr>
                <th>Location</th>
                <th>Armour</th>
                <th>Structure</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Core</td>
                <td>
                  {stats.armour.coreFront} front / {stats.armour.coreRear} rear
                </td>
                <td>{stats.structure.core}</td>
              </tr>
              {(['armLeft', 'armRight', 'legs'] as const).map((loc) => (
                <tr key={loc}>
                  <td>{LOCATION_NAMES[loc]}</td>
                  <td>{stats.armour[loc]}</td>
                  <td>{stats.structure[loc]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel wide">
          <h3>Weapons</h3>
          {stats.weapons.length === 0 ? (
            <p className="hint">No weapons fitted. It can still Ram for {chassis.size} damage per hit.</p>
          ) : (
            <>
              <table className="grid-table">
                <thead>
                  <tr>
                    <th>Weapon</th>
                    <th>Dice × Dmg</th>
                    <th>Pressure</th>
                    {(['melee', 'short', 'medium', 'long'] as const).map((b) => (
                      <th key={b}>{BAND_NAMES[b]}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {stats.weapons.map((w, i) => (
                    <tr key={`${w.id}-${i}`}>
                      <td>{w.name}</td>
                      <td>
                        {w.dice} × {w.damage}
                      </td>
                      <td>{w.pressure}</td>
                      {(['melee', 'short', 'medium', 'long'] as const).map((b) => (
                        <td key={b} className="num">
                          {w.expected[b] ?? '–'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="hint">Expected damage per attack against an unmodified target, before armour.</p>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
