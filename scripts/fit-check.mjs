// Fit check: puts each item on each class that has full models, at every hardpoint position it can take, and flags
// placements that look wrong. Needs headless Chromium (Playwright), so it is run by hand, not in CI.
//   node scripts/fit-check.mjs [class...]        FIT=off checks the old numbered mounts for comparison
// Flags: HEAD (item centre inside the head box), GROUND (below the base), FLOAT (item box more than 0.22 body heights
// from every joint, so it hangs in the air), MISSING (item not found).
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');
const root = new URL('..', import.meta.url);
const equipment = JSON.parse(readFileSync(new URL('data/equipment.json', root), 'utf8')).equipment;
const chassis = JSON.parse(readFileSync(new URL('data/chassis.json', root), 'utf8')).chassis;
const kit = JSON.parse(readFileSync(new URL('data/model-kit.json', root), 'utf8'));
const fitClasses = Object.keys(kit.fit.classes);
const picked = process.argv.slice(2);
const classes = (picked.length ? picked : fitClasses).filter((c) => fitClasses.includes(c));
const fitOff = process.env.FIT === 'off' ? '&fit=off' : '';
const FILL = { armLeft: 'lance', armRight: 'lance' };

const server = spawn('npx', ['vite', '--port', '5195', '--strictPort'], { cwd: resolve('apps/web'), stdio: 'ignore', detached: true });
for (let i = 0; ; i++) {
  if (await fetch('http://localhost:5195/render.html').then((r) => r.ok, () => false)) break;
  if (i > 100) throw new Error('Vite dev server did not start');
  await new Promise((r) => setTimeout(r, 300));
}
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 200, height: 200 } });
const dump = async (cls, lo) => {
  await page.goto(`http://localhost:5195/render.html?chassis=${cls}&w=200&h=200&dump=1${fitOff}&lo=${encodeURIComponent(JSON.stringify(lo))}`);
  await page.waitForSelector('body[data-ready="1"]', { timeout: 90000 });
  return JSON.parse(await page.evaluate(() => document.body.dataset.dump));
};
const dist = (min, max, p) => Math.hypot(...[0, 1, 2].map((i) => Math.max(min[i] - p[i], 0, p[i] - max[i])));
let flagged = 0;
try {
  for (const cls of classes) {
    const c = chassis.find((x) => x.id === cls);
    console.log(`\n${cls} (${c.frame})`);
    for (const e of equipment) {
      if (e.faction && e.faction !== c.faction) continue;
      if (kit.fit.cardOnly.includes(e.id)) continue; // no model, nothing to place
      const kinds = e.mount.includes('any') ? ['armLeft', 'core', 'legs'] : e.mount.flatMap((m) => (m === 'arm' ? ['armLeft', 'armRight'] : [m]));
      for (const loc of kinds) {
        // Arms: the item first, then second and third behind a filler, to check the whole ladder.
        const variants = loc.startsWith('arm') ? [[e.id], [FILL[loc], e.id], [FILL[loc], FILL[loc], e.id]] : [[e.id]];
        for (const list of variants) {
          const d = await dump(cls, { [loc]: list });
          const H = d.joints.joint_head[1];
          const hits = d.items.filter((i) => i.id === e.id);
          if (!hits.length) { console.log(`  MISSING ${e.id} @ ${loc} ${list.length}`); flagged++; continue; }
          for (const it of hits) {
            const ctr = [0, 1, 2].map((i) => (it.min[i] + it.max[i]) / 2);
            const flags = [];
            const hd = d.joints.joint_head;
            if (Math.abs(ctr[0]) < 0.1 * H && ctr[1] > hd[1] - 0.03 * H && Math.abs(ctr[2] - hd[2]) < 0.12 * H) flags.push('HEAD');
            if (it.min[1] < -0.02 * H) flags.push('GROUND');
            const near = Math.min(...Object.values(d.joints).map((p) => dist(it.min, it.max, p)));
            if (near > 0.22 * H) flags.push('FLOAT');
            if (flags.length) flagged++;
            const r = (v) => v.map((x) => (x / H).toFixed(2)).join(',');
            console.log(`  ${flags.length ? 'FLAG' : 'ok  '} ${e.id.padEnd(18)} ${loc.padEnd(8)} #${list.length} ${it.hp.padEnd(15)} ctr/H ${r(ctr)} near ${(near / H).toFixed(2)} ${flags.join(' ')}`);
          }
        }
      }
    }
  }
} finally {
  await browser.close();
  process.kill(-server.pid);
}
console.log(`\n${flagged} flagged`);
process.exitCode = flagged ? 1 : 0;
