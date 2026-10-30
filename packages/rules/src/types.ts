import type { Facing, Hex } from './hex';
import type { Location, Terrain } from './data';
import type { Rng } from './rng';

export type Side = 0 | 1;

/** Armour zones. The core has separate front and rear armour. */
export type Zone = 'coreFront' | 'coreRear' | 'armLeft' | 'armRight' | 'legs';

export interface ItemState {
  uid: string;
  id: string;
  location: Location;
  destroyed: boolean;
  ammo: number | null;
  uses: number | null;
  firedThisActivation: boolean;
}

export interface WalkerState {
  id: string;
  side: Side;
  name: string;
  chassis: string;
  size: number;
  cost: number;
  command: number;
  trait: string | null;
  pos: Hex;
  facing: Facing;
  items: ItemState[];
  armour: Record<Zone, number>;
  maxArmour: Record<Zone, number>;
  structure: Record<Location, number>;
  destroyedLocations: Location[];
  actuator: Record<Location, boolean>;
  overpressure: number;
  reserve: number;
  prone: boolean;
  anchored: boolean;
  braced: boolean;
  activated: boolean;
  destroyed: boolean;
  skipNext: boolean;
  /** Hexes moved in its current or most recent activation. */
  lastMoveDistance: number;
  pendingDrain: number;
  spottedBy: Side | null;
  aceUsed: boolean;
  reactiveUsed: boolean;
  tacticianUsed: boolean;
}

export type FaultId = 'valve-stick' | 'gear-seize' | 'breech-jam' | 'steam-scald' | 'gauge-failure' | 'boiler-surge';

export interface Activation {
  walkerId: string;
  pressure: number;
  started: boolean;
  moved: boolean;
  usedMoveAction: boolean;
  firstWeaponFired: boolean;
  braced: boolean;
  faults: FaultId[];
  jammedUid: string | null;
  /** Set when the safety valve blows mid-activation. */
  forceEnd: boolean;
}

export interface HexInfo {
  terrain: Terrain;
  elevation: number;
}

export interface Objective {
  hex: Hex;
  vp: number;
}

export interface GameEvent {
  type: string;
  text: string;
  [key: string]: unknown;
}

export interface GameState {
  rng: Rng;
  round: number;
  rounds: number;
  phase: 'activation' | 'over';
  scenario: string;
  map: { id: string; width: number; height: number; hexes: Record<string, HexInfo> };
  objectives: Objective[];
  smoke: string[];
  wrecks: string[];
  lances: Array<{ name: string; company: string }>;
  walkers: WalkerState[];
  vp: [number, number];
  activeSide: Side;
  active: Activation | null;
  passesUsed: [number, number];
  meridianUsed: [boolean, boolean];
  pendingTactician: string | null;
  winner: Side | 'draw' | null;
  log: GameEvent[];
}

export type Action =
  | { type: 'activate'; walkerId: string; throttle?: number }
  | { type: 'move'; path: Hex[]; facing?: Facing }
  | { type: 'turn'; facing: Facing }
  | { type: 'fire'; itemUid: string; targetId: string }
  | { type: 'brace' }
  | { type: 'bank' }
  | { type: 'standUp' }
  | { type: 'ram'; targetId: string }
  | { type: 'useItem'; itemUid: string; walkerId?: string; hex?: Hex; zone?: Zone; facing?: Facing }
  | { type: 'endActivation'; reactivate?: boolean }
  | { type: 'pass' };
