// Screenshot the 3D battle board with real walkers (apps/web/render-battle.html).
//   node scripts/render-battle.mjs out.png "f0=covenant&f1=foundries&scale=0.07" ["angle..." out2.png ...]
// Pass several (out, query) pairs to reuse one browser. Starts its own Vite server on port 5198.
import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { openViewer } from './lib/viewer.mjs';

const args = process.argv.slice(2);
if (args.length < 2 || args.length % 2) throw new Error('usage: render-battle.mjs OUT.png QUERY [OUT.png QUERY ...]');

const { page, base, close } = await openViewer({ port: 5198, viewport: { width: 1000, height: 740 }, probe: 'render-battle.html' });
page.on('console', (m) => ['error', 'warning'].includes(m.type()) && console.error(m.text().slice(0, 200)));
page.on('pageerror', (e) => console.error(e));
try {
  for (let i = 0; i < args.length; i += 2) {
    mkdirSync(dirname(args[i]), { recursive: true });
    await page.goto(`${base}${process.env.PAGE ?? 'render-battle.html'}?${args[i + 1]}`);
    await page.waitForSelector('body[data-ready="1"]', { state: 'attached', timeout: 90000 });
    await page.screenshot({ path: args[i], clip: { x: 0, y: 0, width: 1000, height: 720 }, timeout: 120000 });
    console.log(args[i]);
  }
} finally {
  await close();
}
