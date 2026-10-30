// Seeded dice (mulberry32). The RNG state lives in the game state so a game
// can be saved, replayed and simulated deterministically.

export interface Rng {
  state: number;
}

export function nextFloat(rng: Rng): number {
  rng.state = (rng.state + 0x6d2b79f5) | 0;
  let t = rng.state;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

export function d6(rng: Rng): number {
  return 1 + Math.floor(nextFloat(rng) * 6);
}

export function pick<T>(rng: Rng, items: readonly T[]): T {
  return items[Math.floor(nextFloat(rng) * items.length)];
}
