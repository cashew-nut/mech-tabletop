// Per-browser persistence for lances. Every access is guarded because storage
// can be unavailable (private windows, blocked site data).
import type { LanceInput } from '@brass-charter/rules';

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

export const loadDraft = () => read<LanceInput | null>(DRAFT_KEY, null);
export const saveDraft = (lance: LanceInput) => write(DRAFT_KEY, lance);
export const loadSaved = () => read<Record<string, LanceInput>>(SAVED_KEY, {});
export const storeSaved = (saved: Record<string, LanceInput>) => write(SAVED_KEY, saved);

/** Parse and shape-check a lance from imported JSON text. */
export function parseLance(text: string): LanceInput {
  const data = JSON.parse(text);
  const lance = Array.isArray(data?.lances) ? data.lances[0] : data;
  if (!lance || typeof lance.name !== 'string' || typeof lance.company !== 'string' || !Array.isArray(lance.walkers)) {
    throw new Error('That file does not look like a lance.');
  }
  return lance as LanceInput;
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
