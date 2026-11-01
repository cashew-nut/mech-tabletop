// Render the art for the Paladin card faces from the existing GLBs, with the headless renderer.
//   node scripts/render-card-art.mjs [outDir] [artKey...]      (default outDir: cards/art)
// Body parts are the Paladin's composite kit parts, each shown alone (solo=1: closed solids, no body behind them); items are the class's own item GLB
// on its own. Both go through apps/web/render.html (see apps/web/src/model/preview.ts). Needs Playwright installed
// globally, like scripts/render-walkers.mjs. Costs nothing: no Meshy.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');

const W = 1100;
const H = 920; // the 55 x 46 mm art window on the card, at about 500 dpi
const BODY = 'chassis=paladin&kit=force&plain=1&solo=1';
const ITEM = 'plain=1&angle=35';
const SPECS = {
  'paladin-legs': `${BODY}&show=thigh,shin,foot&angle=30&zoom=1.05`,
  'paladin-torso': `${BODY}&show=torso,pelvis&angle=30&zoom=1.0`,
  'paladin-helm': `${BODY}&show=helm&angle=20&zoom=1.3`,
  'paladin-pauldrons': `${BODY}&show=pauldron&side=L&angle=20&zoom=1.05`,
  'paladin-arms': `${BODY}&show=arm,forearm,hand&side=L&angle=25&zoom=0.95`,
  'paladin-crown-back': `${BODY}&show=back&angle=150&zoom=1.3`,
  'paladin-lance': `part=item_lance@paladin&${ITEM}&roll=-58&zoom=1.05`,
  'paladin-carapace-gun': `part=item_carapace-gun@paladin&${ITEM}&zoom=1.1`,
  'paladin-gyro-stabilisers': `part=item_gyro-stabilisers@covenant&${ITEM}&zoom=1.1`,
  'paladin-targeting-array': `part=item_targeting-array@covenant&${ITEM}&zoom=1.1`,
};

const [outDir = 'cards/art', ...picked] = process.argv.slice(2);
const keys = picked.length ? picked : Object.keys(SPECS);
mkdirSync(outDir, { recursive: true });

const server = spawn('npx', ['vite', '--port', '5199', '--strictPort'], { cwd: resolve('apps/web'), stdio: 'ignore', detached: true });
for (let i = 0; ; i++) {
  if (await fetch('http://localhost:5199/render.html').then((r) => r.ok, () => false)) break;
  if (i > 100) throw new Error('Vite dev server did not start');
  await new Promise((r) => setTimeout(r, 300));
}
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: W, height: H } });
page.on('pageerror', (e) => console.error(e));
try {
  for (const key of keys) {
    if (!SPECS[key]) throw new Error(`Unknown art key ${key}`);
    await page.goto(`http://localhost:5199/render.html?${SPECS[key]}&w=${W}&h=${H}`);
    await page.waitForSelector('body[data-ready="1"]', { timeout: 90000 });
    const file = `${outDir}/${key}.jpg`;
    await page.locator('canvas').screenshot({ path: file, type: 'jpeg', quality: 86 });
    console.log(file);
  }
} finally {
  await browser.close();
  process.kill(-server.pid);
}
