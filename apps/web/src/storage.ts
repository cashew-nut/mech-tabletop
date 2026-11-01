// Per-browser persistence for lances. Every access is guarded because storage
// can be unavailable (private windows, blocked site data).
import { CHASSIS, hasEquipment, type LanceInput } from '@brass-charter/rules';

const DRAFT_KEY = 'brass-charter:draft';
const SAVED_KEY = 'brass-charter:saved';

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage unavailable: the builder still works for this session.
  }
}

// Lances saved before the three factions named a Company and the old chassis and items.
const FACTION_OF_COMPANY: Record<string, string> = { halvorsen: 'foundries', meridian: 'reliquary', 'calloway-vane': 'reliquary' };
const CLASS_OF_FRAME: Record<string, Record<string, string>> = {
  covenant: { scout: 'lancer', striker: 'lancer', bulwark: 'sentinel', titan: 'paladin' },
  foundries: { scout: 'scavenger', striker: 'brute', bulwark: 'brute', titan: 'artillery' },
  reliquary: { scout: 'wraith', striker: 'seer', bulwark: 'goliath', titan: 'goliath' },
};
const RENAMED_ITEMS: Record<string, string> = {
  'beam-cutter': 'carapace-gun',
  'rail-lance': 'rail-cannon',
  'arc-mortar': 'rocket-pod',
  'ion-lance': 'arc-cannon',
  'impact-hammer': 'industrial-claw',
  'shear-blade': 'melee-blade',
  'static-choir': 'soul-lantern',
};

// Items cut from the game (docs/rules.md, v0.6). A saved lance that still carries one loses it rather than failing to load.
const CUT_ITEMS = new Set(['melee-blade', 'hellfire-missiles', 'anchor-spikes', 'jump-jets', 'overcharged-boiler', 'field-repair-rig']);

const withoutCutItems = <T extends { walkers: LanceInput['walkers'] }>(lance: T): T => ({
  ...lance,
  walkers: lance.walkers.map((w) => ({
    ...w,
    loadout: Object.fromEntries(Object.entries(w.loadout).map(([loc, ids]) => [loc, (ids ?? []).filter((id) => !CUT_ITEMS.has(id))])),
  })),
});

/** Bring an old Company lance up to the faction rules. Gear from another faction stays and shows as an error to fix. */
export function migrateLance(saved: LanceInput & { company?: string }): LanceInput {
  const lance = withoutCutItems(saved);
  if (lance.faction) return lance;
  const faction = FACTION_OF_COMPANY[lance.company ?? ''] ?? 'foundries';
  const { company: _, ...rest } = lance;
  return {
    ...rest,
    faction,
    walkers: lance.walkers.map((w) => ({
      ...w,
      chassis: CHASSIS.some((c) => c.id === w.chassis) ? w.chassis : (CLASS_OF_FRAME[faction][w.chassis] ?? CLASS_OF_FRAME[faction].scout),
      loadout: Object.fromEntries(
        Object.entries(w.loadout).map(([loc, ids]) => [loc, (ids ?? []).map((id) => RENAMED_ITEMS[id] ?? id).filter(hasEquipment)]),
      ),
    })),
  };
}

export const loadDraft = () => {
  const draft = read<LanceInput | null>(DRAFT_KEY, null);
  return draft && migrateLance(draft);
};
export const saveDraft = (lance: LanceInput) => write(DRAFT_KEY, lance);
export const loadSaved = () =>
  Object.fromEntries(Object.entries(read<Record<string, LanceInput>>(SAVED_KEY, {})).map(([k, l]) => [k, migrateLance(l)]));
export const storeSaved = (saved: Record<string, LanceInput>) => write(SAVED_KEY, saved);

/** Parse and shape-check a lance from imported JSON text. */
export function parseLance(text: string): LanceInput {
  const data = JSON.parse(text);
  const lance = Array.isArray(data?.lances) ? data.lances[0] : data;
  const allegiance = lance?.faction ?? lance?.company;
  if (!lance || typeof lance.name !== 'string' || typeof allegiance !== 'string' || !Array.isArray(lance.walkers)) {
    throw new Error('That file does not look like a lance.');
  }
  return migrateLance(lance);
}

export function downloadLance(lance: LanceInput) {
  const blob = new Blob([JSON.stringify(lance, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${lance.name.replace(/[^a-z0-9]+/gi, '-').toLowerCase() || 'lance'}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
