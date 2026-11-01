// Render the fit review sets (scripts/fit-sets.json) for the classes with full models.
//   node scripts/fit-sheets.mjs [outDir] [class...]     ANGLES=35,145 sets the camera angles, FIT=off the old numbered mounts
// Writes <outDir>/<class>-<set>-<angle>.png. Join them with ImageMagick: montage <class>-*.png -tile 4x -geometry 600x600+2+2 sheet.png
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const { chromium } = createRequire(import.meta.url)('playwright');
const [outDir = 'renders/fit', ...picked] = process.argv.slice(2);
const sets = JSON.parse(readFileSync(new URL('./fit-sets.json', import.meta.url), 'utf8'));
const fitOff = process.env.FIT === 'off' ? '&fit=off' : '';
const angles = (process.env.ANGLES ?? '35,145').split(',').map(Number);
const classes = (picked.length ? picked : Object.keys(sets).filter((c) => !c.startsWith('$'))).filter((c) => sets[c]);
mkdirSync(outDir, { recursive: true });

const server = spawn('npx', ['vite', '--port', '5196', '--strictPort'], { cwd: resolve('apps/web'), stdio: 'ignore', detached: true });
for (let i = 0; ; i++) {
  if (await fetch('http://localhost:5196/render.html').then((r) => r.ok, () => false)) break;
  if (i > 100) throw new Error('Vite dev server did not start');
  await new Promise((r) => setTimeout(r, 300));
}
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 700, height: 700 } });
page.on('pageerror', (e) => console.error(e));
try {
  for (const cls of classes) {
    for (const [name, lo] of Object.entries(sets[cls])) {
      for (const angle of angles) {
        const q = `chassis=${cls}&w=700&h=700&angle=${angle}&elev=0.25${fitOff}&lo=${encodeURIComponent(JSON.stringify(lo))}`;
        await page.goto(`http://localhost:5196/render.html?${q}`);
        await page.waitForSelector('body[data-ready="1"]', { timeout: 90000 });
        const file = `${outDir}/${cls}-${name}-${angle}.png`;
        await page.locator('canvas').screenshot({ path: file });
        console.log(file);
      }
    }
  }
} finally {
  await browser.close();
  process.kill(-server.pid);
}
