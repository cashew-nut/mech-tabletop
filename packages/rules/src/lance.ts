// Lance building: costs and legality, shared by the engine, builder and tools.
import {
  COMMAND_COST,
  LOCATIONS,
  RULES,
  getChassis,
  getCompany,
  getEquipment,
  getTrait,
  hasEquipment,
  hasTrait,
  type CompanyDef,
  type Location,
} from './data';

export interface DriverInput {
  command: number;
  trait: string | null;
}

export interface WalkerInput {
  name: string;
  chassis: string;
  driver: DriverInput;
  loadout: Partial<Record<Location, string[]>>;
  /** Optional hull colour for the 3D model (#rrggbb). No effect on the rules. */
  paint?: string;
}

export interface LanceInput {
  name: string;
  company: string;
  walkers: WalkerInput[];
}

const MOUNT_OF: Record<Location, 'arm' | 'core' | 'legs'> = {
  armLeft: 'arm',
  armRight: 'arm',
  core: 'core',
  legs: 'legs',
};

export function itemCost(itemId: string, company: CompanyDef | null): number {
  const base = getEquipment(itemId).points;
  return Math.max(1, base + (company?.pointModifiers[itemId] ?? 0));
}

/** Points cost of one war-walker. Throws on unknown ids; use validateWalker first. */
export function walkerCost(walker: WalkerInput, company: CompanyDef | null): number {
  let total = getChassis(walker.chassis).points;
  total += COMMAND_COST.get(walker.driver.command) ?? 0;
  if (walker.driver.trait) total += getTrait(walker.driver.trait).points;
  for (const loc of LOCATIONS) {
    for (const id of walker.loadout[loc] ?? []) total += itemCost(id, company);
  }
  return total;
}

/** Problems with one war-walker's build, empty when legal. */
export function validateWalker(walker: WalkerInput): string[] {
  const errors: string[] = [];
  let chassis;
  try {
    chassis = getChassis(walker.chassis);
  } catch {
    return [`unknown chassis "${walker.chassis}"`];
  }
  if (!COMMAND_COST.has(walker.driver.command)) errors.push(`invalid driver command ${walker.driver.command}`);
  if (walker.driver.trait && !hasTrait(walker.driver.trait)) errors.push(`unknown trait "${walker.driver.trait}"`);

  const counts = new Map<string, number>();
  for (const [loc, items] of Object.entries(walker.loadout)) {
    if (!LOCATIONS.includes(loc as Location)) {
      errors.push(`unknown location "${loc}"`);
      continue;
    }
    let used = 0;
    for (const id of items ?? []) {
      if (!hasEquipment(id)) {
        errors.push(`unknown item "${id}"`);
        continue;
      }
      const e = getEquipment(id);
      if (!e.mount.includes('any') && !e.mount.includes(MOUNT_OF[loc as Location])) {
        errors.push(`${e.name} cannot be mounted in ${loc}`);
      }
      used += e.slots;
      counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    const free = chassis.slots[loc as Location];
    if (used > free) errors.push(`${loc} uses ${used} slots but ${chassis.name} has ${free}`);
  }
  for (const [id, n] of counts) {
    const max = getEquipment(id).maxPerWalker;
    if (max && n > max) errors.push(`${getEquipment(id).name} fitted ${n} times, max ${max}`);
  }
  return errors;
}

export interface LanceReport {
  total: number;
  costs: number[];
  errors: string[];
}

export function validateLance(lance: LanceInput, budget = RULES.lance.budget): LanceReport {
  const errors: string[] = [];
  let company: CompanyDef | null = null;
  try {
    company = getCompany(lance.company);
  } catch {
    errors.push(`unknown company "${lance.company}"`);
  }
  const { minWalkers, maxWalkers } = RULES.lance;
  const n = lance.walkers.length;
  if (n < minWalkers || n > maxWalkers) errors.push(`has ${n} war-walkers, needs ${minWalkers}-${maxWalkers}`);

  const costs = lance.walkers.map((w) => {
    const problems = validateWalker(w);
    errors.push(...problems.map((p) => `${w.name}: ${p}`));
    return problems.length ? 0 : walkerCost(w, company);
  });
  const total = costs.reduce((a, b) => a + b, 0);
  if (total > budget) errors.push(`costs ${total} points, budget is ${budget}`);
  return { total, costs, errors };
}
