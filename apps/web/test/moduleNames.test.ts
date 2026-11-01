import { readdirSync, statSync } from 'node:fs';
import { join, parse } from 'node:path';
import { describe, expect, it } from 'vitest';

// Vite resolves `./Foo` by trying `Foo.ts` before `Foo.tsx`. On a case-insensitive
// filesystem (macOS, Windows) `./CombatReplay` then lands on `combatReplay.ts`, so
// the import fails with "does not provide an export named ...". Linux and CI never
// show it, so guard against two modules in one folder whose names differ only by case.
function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

describe('module names', () => {
  it('no two source modules in a folder differ only by letter case', () => {
    const seen = new Map<string, string>();
    const clashes: string[] = [];
    for (const file of walk(join(__dirname, '../src'))) {
      const { dir, name, ext } = parse(file);
      if (!/^\.(ts|tsx|js|jsx|mjs)$/.test(ext)) continue;
      const key = join(dir, name.toLowerCase());
      const prev = seen.get(key);
      if (prev) clashes.push(`${prev} vs ${file}`);
      else seen.set(key, file);
    }
    expect(clashes).toEqual([]);
  });
});
