// Save preview renders of each chassis with a showcase loadout.
//   npm run render -- [outDir] [chassis...]
// ANGLES=35,145 picks the camera angles in degrees; PAINT=#1f5c63 sets the hull colour;
// SET=b swaps in the second showcase loadout; BACKDROP=foundries picks the world; ELEV=0.12 lowers the camera.
// KIT=force shows the Blender kit body with stand-ins in any gaps.
// Starts the web dev server, opens apps/web/render.html in headless Chromium
// (Playwright) and screenshots each walker from a few angles.
import { mkdirSync } from 'node:fs';
import { openViewer } from './lib/viewer.mjs';

const [outDir = 'renders', ...picked] = process.argv.slice(2);
const chassis = picked.length ? picked : ['lancer', 'sentinel', 'paladin', 'scavenger', 'brute', 'artillery', 'wraith', 'seer', 'goliath'];
const angles = (process.env.ANGLES ?? '35,145').split(',').map(Number);
const paint = (process.env.PAINT ? `&paint=${encodeURIComponent(process.env.PAINT)}` : '') + (process.env.SET ? `&set=${process.env.SET}` : '') +
  (process.env.BACKDROP ? `&backdrop=${process.env.BACKDROP}` : '') + (process.env.ELEV ? `&elev=${process.env.ELEV}` : '') + (process.env.KIT ? `&kit=${process.env.KIT}` : '');
mkdirSync(outDir, { recursive: true });

const { page, base, close } = await openViewer({ port: 5199, viewport: { width: 900, height: 900 } });
page.on('console', (m) => m.type() === 'error' && console.error(m.text()));
page.on('pageerror', (e) => console.error(e));
try {
  for (const id of chassis) {
    for (const angle of angles) {
      await page.goto(`${base}render.html?chassis=${id}&angle=${angle}${paint}`);
      await page.waitForSelector('body[data-ready="1"]', { timeout: 60000 });
      const file = `${outDir}/${id}${process.env.SET ? `-${process.env.SET}` : ''}${process.env.BACKDROP ? `-${process.env.BACKDROP}` : ''}-${angle}.png`;
      await page.locator('canvas').screenshot({ path: file });
      console.log(file);
    }
  }
} finally {
  await close();
}
