// Typed access to the JSON game data in /data.
import chassisJson from '../../../data/chassis.json';
import equipmentJson from '../../../data/equipment.json';
import driversJson from '../../../data/drivers.json';
import factionsJson from '../../../data/factions.json';
import scenariosJson from '../../../data/scenarios.json';
import mapsJson from '../../../data/maps.json';

export type Location = 'armLeft' | 'armRight' | 'core' | 'legs';
export const LOCATIONS: readonly Location[] = ['armLeft', 'armRight', 'core', 'legs'];

export type RangeBand = 'melee' | 'short' | 'medium' | 'long';

export interface ChassisDef {
  id: string;
  name: string;
  /** Each class belongs to one faction. */
  faction: string;
  role: string;
  /** The 3D model skeleton this class is built on. */
  frame: string;
  size: number;
  points: number;
  stride: number;
  boiler: number;
  slots: Record<Location, number>;
  armour: { coreFront: number; coreRear: number; arm: number; legs: number };
  structure: { core: number; other: number };
}

export interface WeaponStats {
  dice: number;
  damage: number;
  range: RangeBand;
  ammo?: number;
  pierce?: number;
  minRange?: number;
  critOn?: number;
}

export interface EquipmentDef {
  id: string;
  name: string;
  /** Signature gear only that faction can fit. Shared gear has none. */
  faction?: string;
  category: 'weapon' | 'defence' | 'mobility' | 'system';
  mount: Array<'arm' | 'core' | 'legs' | 'any'>;
  slots: number;
  pressure: number;
  points: number;
  uses?: number;
  maxPerWalker?: number;
  weapon?: WeaponStats;
  tags?: string[];
  rules: string;
}

export interface TraitDef {
  id: string;
  name: string;
  points: number;
  rules: string;
}

export interface FactionDef {
  id: string;
  name: string;
  motto: string;
  identity: string;
  doctrine: string;
  pointModifiers: Record<string, number>;
  /** Added to the cost of every Driver trait (minimum 1). */
  traitModifier?: number;
}

export interface ObjectiveDef {
  col: number;
  row: number;
  vp: number;
}

export interface SurveyorDef {
  /** The side escorting it. */
  side: 0 | 1;
  col: number;
  row: number;
  hp: number;
  exitVp: number;
  destroyVp: number;
}

export interface ScenarioDef {
  id: string;
  name: string;
  objectives: ObjectiveDef[];
  surveyor?: SurveyorDef;
  rules: string;
}

export type Terrain = 'open' | 'rough' | 'light' | 'heavy' | 'blocking';

export interface MapDef {
  id: string;
  name: string;
  width: number;
  height: number;
  /** Non-open hexes; everything else is open ground at elevation 0. */
  hexes: Array<{ col: number; row: number; terrain?: Terrain; elevation?: number }>;
}

export const RANGE_BANDS = equipmentJson.rangeBands as Record<'short' | 'medium' | 'long', [number, number]>;
export const CHASSIS = chassisJson.chassis as ChassisDef[];
export const EQUIPMENT = equipmentJson.equipment as EquipmentDef[];
export const COMMAND_COST = new Map(driversJson.command.map((c) => [c.value, c.points]));
export const TRAITS = driversJson.traits as TraitDef[];
export const FACTIONS = factionsJson.factions as FactionDef[];
export const SCENARIOS = scenariosJson.scenarios as ScenarioDef[];
export const MAPS = mapsJson.maps as MapDef[];
export const RULES = {
  rounds: scenariosJson.rounds,
  map: scenariosJson.map,
  lance: scenariosJson.lance,
};

const byId = <T extends { id: string }>(list: T[]) => new Map(list.map((x) => [x.id, x]));
const chassisById = byId(CHASSIS);
const equipmentById = byId(EQUIPMENT);
const traitById = byId(TRAITS);
const factionById = byId(FACTIONS);
const scenarioById = byId(SCENARIOS);
const mapById = byId(MAPS);

function lookup<T>(map: Map<string, T>, id: string, kind: string): T {
  const v = map.get(id);
  if (!v) throw new Error(`Unknown ${kind} "${id}"`);
  return v;
}

export const getChassis = (id: string) => lookup(chassisById, id, 'chassis');
export const getEquipment = (id: string) => lookup(equipmentById, id, 'equipment');
export const getTrait = (id: string) => lookup(traitById, id, 'trait');
export const getFaction = (id: string) => lookup(factionById, id, 'faction');
export const getScenario = (id: string) => lookup(scenarioById, id, 'scenario');
export const getMap = (id: string) => lookup(mapById, id, 'map');
export const hasEquipment = (id: string) => equipmentById.has(id);
export const hasTrait = (id: string) => traitById.has(id);
