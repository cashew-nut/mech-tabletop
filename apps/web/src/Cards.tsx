// Printable unit cards: one per war-walker, with tick boxes for armour,
// structure, ammo and Overpressure, plus a lance card and a quick reference.
import {
  LOCATIONS,
  getChassis,
  getFaction,
  getEquipment,
  getTrait,
  hasTrait,
  validateLance,
  validateWalker,
  walkerCost,
  walkerStats,
  type LanceInput,
  type Location,
  type WalkerInput,
  type Zone,
} from '@brass-charter/rules';
import { loadDraft } from './storage';

const ZONES: Array<{ zone: Zone; label: string; structure?: Location }> = [
  { zone: 'coreFront', label: 'Core front', structure: 'core' },
  { zone: 'coreRear', label: 'Core rear' },
  { zone: 'armLeft', label: 'Left arm', structure: 'armLeft' },
  { zone: 'armRight', label: 'Right arm', structure: 'armRight' },
  { zone: 'legs', label: 'Legs', structure: 'legs' },
];
const LOCATION_NAMES: Record<Location, string> = { armLeft: 'L arm', armRight: 'R arm', core: 'Core', legs: 'Legs' };
const RANGE_NAMES = { melee: 'Melee', short: 'Short 1–3', medium: 'Medium ≤7', long: 'Long ≤12' } as const;

const Boxes = ({ n, label }: { n: number; label: string }) => (
  <span className="boxes" aria-label={`${label}: ${n} boxes`}>
    {Array.from({ length: n }, (_, i) => (
      <i key={i} />
    ))}
  </span>
);

function UnitCard({ walker, lance }: { walker: WalkerInput; lance: LanceInput }) {
  const c = getChassis(walker.chassis);
  const faction = getFaction(lance.faction);
  const stats = walkerStats(walker);
  const trait = walker.driver.trait && hasTrait(walker.driver.trait) ? getTrait(walker.driver.trait) : null;
  const items = LOCATIONS.flatMap((loc) => (walker.loadout[loc] ?? []).map((id) => ({ loc, def: getEquipment(id) })));
  const weapons = items.filter((x) => x.def.weapon);
  const systems = items.filter((x) => !x.def.weapon);

  return (
    <article className="unit-card" style={walker.paint ? { borderTopColor: walker.paint } : undefined}>
      <header>
        <div>
          <h3>{walker.name}</h3>
          <small>
            {c.name} · Size {c.size} · Command {walker.driver.command}
            {trait ? ` · ${trait.name}` : ''}
          </small>
        </div>
        <span className="card-cost">{walkerCost(walker, faction)}</span>
      </header>

      <dl className="card-stats">
        <div>
          <dt>Stride</dt>
          <dd>
            {stats.stride}
            {stats.sprintStride !== stats.stride ? ` (${stats.sprintStride})` : ''}
          </dd>
        </div>
        <div>
          <dt>Boiler</dt>
          <dd>{stats.boiler}</dd>
        </div>
        <div>
          <dt>Faults at</dt>
          <dd>{stats.faultThreshold}+</dd>
        </div>
        <div>
          <dt>Kill VP</dt>
          <dd>{Math.ceil(walkerCost(walker, faction) / 4)}</dd>
        </div>
      </dl>

      <table className="card-table">
        <thead>
          <tr>
            <th />
            <th>Armour</th>
            <th>Structure</th>
          </tr>
        </thead>
        <tbody>
          {ZONES.map(({ zone, label, structure }) => (
            <tr key={zone}>
              <td>{label}</td>
              <td>
                <Boxes n={stats.armour[zone]} label={`${label} armour`} />
              </td>
              <td>{structure && <Boxes n={stats.structure[structure]} label={`${label} structure`} />}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="card-tracks">
        <span>
          Overpressure <Boxes n={6} label="Overpressure" />
        </span>
        <span>
          Reserve <Boxes n={2} label="Reserve" />
        </span>
      </div>

      {weapons.length > 0 && (
        <table className="card-table weapons">
          <thead>
            <tr>
              <th>Weapon</th>
              <th>Range</th>
              <th>Dice×Dmg</th>
              <th>P</th>
              <th>Ammo</th>
            </tr>
          </thead>
          <tbody>
            {weapons.map(({ loc, def }, i) => (
              <tr key={i} title={def.rules}>
                <td>
                  {def.name} <small>{LOCATION_NAMES[loc]}</small>
                </td>
                <td>{RANGE_NAMES[def.weapon!.range]}</td>
                <td>
                  {def.weapon!.dice}×{def.weapon!.damage}
                  {def.weapon!.pierce ? ` P${def.weapon!.pierce}` : ''}
                </td>
                <td>{def.pressure}</td>
                <td>{def.weapon!.ammo ? <Boxes n={def.weapon!.ammo} label={`${def.name} ammo`} /> : '–'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <ul className="card-rules">
        {weapons
          .filter(({ def }) => def.rules)
          .map(({ def }, i) => (
            <li key={`w${i}`}>
              <strong>{def.name}:</strong> {def.rules}
            </li>
          ))}
        {systems.map(({ loc, def }, i) => (
          <li key={`s${i}`}>
            <strong>
              {def.name} ({LOCATION_NAMES[loc]}
              {def.pressure ? `, ${def.pressure} P` : ''}):
            </strong>{' '}
            {def.rules}
            {def.uses ? (
              <>
                {' '}
                <Boxes n={def.uses} label={`${def.name} uses`} />
              </>
            ) : null}
          </li>
        ))}
        {trait && (
          <li>
            <strong>{trait.name} Driver:</strong> {trait.rules}
          </li>
        )}
      </ul>
    </article>
  );
}

function LanceCard({ lance }: { lance: LanceInput }) {
  const faction = getFaction(lance.faction);
  const report = validateLance(lance);
  return (
    <article className="unit-card lance-card">
      <header>
        <div>
          <h3>{lance.name}</h3>
          <small>{faction.name}</small>
        </div>
        <span className="card-cost">{report.total}</span>
      </header>
      <p>
        <strong>Doctrine.</strong> {faction.doctrine}
      </p>
      <ol className="card-roster">
        {lance.walkers.map((w, i) => (
          <li key={i}>
            {w.name} <small>{getChassis(w.chassis).name}</small> <span>{report.costs[i]}</span>
          </li>
        ))}
      </ol>
      <h4>Each round</h4>
      <ol className="card-ref">
        <li>Initiative: d6 + best Command. Winner activates first.</li>
        <li>Alternate activations. The side with fewer war-walkers may pass once.</li>
        <li>End phase: score objectives (more Size within 1 hex), vent 1 Overpressure, clear Reserve.</li>
      </ol>
      <h4>Spending Pressure</h4>
      <table className="card-table">
        <tbody>
          <tr>
            <td>Move up to Stride</td>
            <td>1</td>
            <td>Turn</td>
            <td>1</td>
          </tr>
          <tr>
            <td>Brace (+1 TN vs you)</td>
            <td>1</td>
            <td>Bank to Reserve</td>
            <td>1</td>
          </tr>
          <tr>
            <td>Stand up</td>
            <td>1</td>
            <td>Ram (2 dice, TN 4)</td>
            <td>2</td>
          </tr>
          <tr>
            <td>Open the Throttle</td>
            <td colSpan={3}>+1 or +2 Pressure, same in Overpressure</td>
          </tr>
        </tbody>
      </table>
      <h4>To hit: TN 4, then</h4>
      <p className="card-small">
        +1 medium, +2 long · +1/+2 light/heavy cover · +1 if you moved (+2 static weapons) · +1 target braced or moved 4+ · −1 from
        high ground, prone target, Targeting Array, spotted. 6 always hits, 1 always misses.
      </p>
    </article>
  );
}

export function Cards() {
  const lance = loadDraft();
  if (!lance || lance.walkers.length === 0) {
    return (
      <div className="panel empty">
        <p>Build a lance in the Lance Ledger first. Its cards will appear here.</p>
      </div>
    );
  }
  const errors = validateLance(lance).errors;
  return (
    <div className="cards-page">
      <div className="cards-tools panel">
        <div>
          <h2>Unit cards</h2>
          <p className="hint">Cards for your current lance, ready to print and track with a pencil.</p>
          {errors.length > 0 && <p className="bad">This lance is not legal yet: {errors[0]}</p>}
        </div>
        <button onClick={() => window.print()}>Print</button>
      </div>
      <div className="cards-grid">
        <LanceCard lance={lance} />
        {lance.walkers.map((w, i) =>
          validateWalker(w).length === 0 ? (
            <UnitCard key={i} walker={w} lance={lance} />
          ) : (
            <article key={i} className="unit-card">
              <h3>{w.name}</h3>
              <p className="bad">Fix this build in the Lance Ledger to print its card.</p>
            </article>
          ),
        )}
      </div>
    </div>
  );
}
