// Save preview renders of each chassis with a showcase loadout.
//   npm run render -- [outDir] [chassis...]
// ANGLES=35,145 picks the camera angles in degrees; PAINT=#1f5c63 sets the hull colour;
// SET=b swaps in the second showcase loadout; BACKDROP=foundries picks the world; ELEV=0.12 lowers the camera.
// Starts the web dev server, opens apps/web/render.html in headless Chromium
// (Playwright) and screenshots each walker from a few angles.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

// Playwright is not a project dependency; use a global install (npm i -g playwright).
const { chromium } = createRequire(import.meta.url)('playwright');

const [outDir = 'renders', ...picked] = process.argv.slice(2);
const chassis = picked.length ? picked : ['lancer', 'sentinel', 'paladin', 'scavenger', 'brute', 'artillery', 'wraith', 'seer', 'goliath'];
const angles = (process.env.ANGLES ?? '35,145').split(',').map(Number);
const paint = (process.env.PAINT ? `&paint=${encodeURIComponent(process.env.PAINT)}` : '') + (process.env.SET ? `&set=${process.env.SET}` : '') +
  (process.env.BACKDROP ? `&backdrop=${process.env.BACKDROP}` : '') + (process.env.ELEV ? `&elev=${process.env.ELEV}` : '');
mkdirSync(outDir, { recursive: true });

const server = spawn('npx', ['vite', '--port', '5199', '--strictPort'], { cwd: resolve('apps/web'), stdio: 'ignore', detached: true });
for (let i = 0; ; i++) {
  if (await fetch('http://localhost:5199/render.html').then((r) => r.ok, () => false)) break;
  if (i > 100) throw new Error('Vite dev server did not start');
  await new Promise((r) => setTimeout(r, 300));
}
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 900, height: 900 } });
page.on('console', (m) => m.type() === 'error' && console.error(m.text()));
page.on('pageerror', (e) => console.error(e));
try {
  for (const id of chassis) {
    for (const angle of angles) {
      await page.goto(`http://localhost:5199/render.html?chassis=${id}&angle=${angle}${paint}`);
      await page.waitForSelector('body[data-ready="1"]', { timeout: 60000 });
      const file = `${outDir}/${id}${process.env.SET ? `-${process.env.SET}` : ''}${process.env.BACKDROP ? `-${process.env.BACKDROP}` : ''}-${angle}.png`;
      await page.locator('canvas').screenshot({ path: file });
      console.log(file);
    }
  }
} finally {
  await browser.close();
  process.kill(-server.pid);
}
