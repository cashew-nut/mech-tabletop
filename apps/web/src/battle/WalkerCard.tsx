// A war-walker's status card in the Trial sidebar: armour and structure by zone, Pressure, items and conditions.
import {
  getChassis,
  getEquipment,
  type WalkerState,
  type Zone,
} from '@brass-charter/rules';
import { ZONE_NAMES } from './labels';

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

export function WalkerCard({ walker }: { walker: WalkerState }) {
  const c = getChassis(walker.chassis);
  const structureMax = { core: c.structure.core, armLeft: c.structure.other, armRight: c.structure.other, legs: c.structure.other };
  const flags = [
    walker.destroyed && 'Destroyed',
    walker.prone && 'Prone',
    walker.braced && 'Braced',
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
