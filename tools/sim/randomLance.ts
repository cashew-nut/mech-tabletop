// Random legal lances, so the simulator can test every chassis and item,
// not only the hand-built examples.
import {
  CHASSIS,
  COMPANIES,
  EQUIPMENT,
  RULES,
  TRAITS,
  mountableItems,
  nextFloat,
  validateLance,
  walkerCost,
  type LanceInput,
  type Location,
  type Rng,
  type WalkerInput,
} from '@brass-charter/rules';

const pick = <T>(rng: Rng, xs: readonly T[]): T => xs[Math.floor(nextFloat(rng) * xs.length)];
const LOCS: Location[] = ['armLeft', 'armRight', 'core', 'legs'];

function randomWalker(rng: Rng, name: string, budget: number, company: (typeof COMPANIES)[number]): WalkerInput | null {
  const chassisOptions = CHASSIS.filter((c) => c.points <= budget);
  if (!chassisOptions.length) return null;
  const c = pick(rng, chassisOptions);
  const w: WalkerInput = { name, chassis: c.id, driver: { command: 0, trait: null }, loadout: {} };
  const free = { ...c.slots };
  // Weapons first so most walkers can fight, then anything else.
  for (let tries = 0; tries < 12; tries++) {
    const loc = tries < 2 ? pick(rng, ['armLeft', 'armRight'] as Location[]) : pick(rng, LOCS);
    const options = mountableItems(loc, EQUIPMENT).filter((e) => e.slots <= free[loc] && (tries >= 2 || e.weapon));
    if (!options.length) continue;
    const item = pick(rng, options);
    const trial = structuredClone(w);
    trial.loadout[loc] = [...(trial.loadout[loc] ?? []), item.id];
    if (walkerCost(trial, company) > budget) continue;
    if (item.maxPerWalker && Object.values(trial.loadout).flat().filter((x) => x === item.id).length > item.maxPerWalker) continue;
    Object.assign(w, trial);
    free[loc] -= item.slots;
    if (nextFloat(rng) < 0.25) break;
  }
  if (nextFloat(rng) < 0.3) {
    const trial = structuredClone(w);
    trial.driver.trait = pick(rng, TRAITS).id;
    if (walkerCost(trial, company) <= budget) Object.assign(w, trial);
  }
  if (nextFloat(rng) < 0.3) {
    const trial = structuredClone(w);
    trial.driver.command = 1;
    if (walkerCost(trial, company) <= budget) Object.assign(w, trial);
  }
  return w;
}

export function randomLance(rng: Rng, name: string): LanceInput {
  const { budget, minWalkers, maxWalkers } = RULES.lance;
  for (;;) {
    const company = pick(rng, COMPANIES);
    const count = minWalkers + Math.floor(nextFloat(rng) * (maxWalkers - minWalkers + 1));
    const walkers: WalkerInput[] = [];
    let left = budget;
    for (let i = 0; i < count; i++) {
      const share = Math.floor(left / (count - i));
      // Allow lopsided lances: one walker may take up to 1.6x its share.
      const w = randomWalker(rng, `${name}-${i}`, Math.min(left - (count - i - 1) * 12, Math.floor(share * (1 + nextFloat(rng) * 0.6))), company);
      if (!w) break;
      walkers.push(w);
      left -= walkerCost(w, company);
    }
    const lance = { name, company: company.id, walkers };
    // Keep lances that spend most of the budget, so comparisons are fair.
    const report = validateLance(lance);
    if (!report.errors.length && report.total >= budget - 6) return lance;
  }
}
