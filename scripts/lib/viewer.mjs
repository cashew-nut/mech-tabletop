// Shared by the headless render scripts: start the web app's Vite dev server, open a page in headless Chromium
// (SwiftShader, so no GPU is needed), and shut both down afterwards. Run the scripts from the repo root.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';

// Playwright is not a project dependency; use a global install (npm i -g playwright).
const { chromium } = createRequire(import.meta.url)('playwright');

/**
 * Start Vite on `port`, wait until `probe` (a page of apps/web) answers, then open one page at `viewport`.
 * Returns the page, the server's base URL, and close(), which belongs in a finally block.
 */
export async function openViewer({ port, viewport, probe = 'render.html' }) {
  const server = spawn('npx', ['vite', '--port', String(port), '--strictPort'], { cwd: resolve('apps/web'), stdio: 'ignore', detached: true });
  const stop = () => process.kill(-server.pid);
  const base = `http://localhost:${port}/`;
  for (let i = 0; ; i++) {
    if (await fetch(base + probe).then((r) => r.ok, () => false)) break;
    if (i > 100) {
      stop();
      throw new Error('Vite dev server did not start');
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport });
  const close = async () => {
    await browser.close();
    stop();
  };
  return { page, base, close };
}
