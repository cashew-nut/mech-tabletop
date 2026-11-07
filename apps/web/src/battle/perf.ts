// Graphics quality tier and an optional on-screen performance read-out, for phones.
//
//   ?quality=low | high   force a tier (default: low on a touch phone or small tablet, high elsewhere)
//   ?stats=1              show frames per second, frame time, draw calls, triangles, GPU textures and the AI's last think time
import type * as THREE from 'three';

export type Quality = 'low' | 'high';

const params = () => new URLSearchParams(location.search);

/** Phones and small touch tablets get the cheap settings; desktops and laptops keep the full look. */
export function qualityTier(): Quality {
  const forced = params().get('quality');
  if (forced === 'low' || forced === 'high') return forced;
  const coarse = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches;
  const shortSide = Math.min(screen.width, screen.height);
  return coarse && shortSide <= 900 ? 'low' : 'high';
}

export const statsEnabled = () => params().get('stats') === '1';

/** Milliseconds the AI spent on its last decision, shown in the read-out. Written by Battle, read by the overlay. */
let lastAiMs: number | null = null;
export const reportAiTime = (ms: number) => {
  lastAiMs = ms;
};

/** Run `fn` and record how long it took, when the read-out is on. Costs one clock read otherwise. */
export function timeAi<T>(fn: () => T): T {
  const t0 = performance.now();
  const out = fn();
  if (statsEnabled()) reportAiTime(performance.now() - t0);
  return out;
}

export interface PerfOverlay {
  /** Call once per frame, after the frame is drawn. */
  frame: (now: number) => void;
  /** Call just before drawing, so the draw call and triangle counts cover the whole frame (every composer pass). */
  begin: () => void;
  dispose: () => void;
}

/** A small fixed read-out in the corner of `host`. Returns null unless `?stats=1`. */
export function createPerfOverlay(host: HTMLElement, renderer: THREE.WebGLRenderer, tier: Quality): PerfOverlay | null {
  if (!statsEnabled()) return null;
  renderer.info.autoReset = false; // otherwise only the last composer pass is counted
  const box = document.createElement('div');
  box.style.cssText =
    'position:absolute;top:6px;left:6px;z-index:5;padding:4px 7px;border-radius:4px;background:rgba(0,0,0,.65);color:#9fe870;font:11px/1.35 monospace;pointer-events:none;white-space:pre';
  host.style.position = 'relative';
  host.appendChild(box);

  let frames = 0;
  let since = performance.now();
  let slowest = 0;
  let last = since;
  return {
    begin: () => renderer.info.reset(),
    frame: (now) => {
      frames++;
      slowest = Math.max(slowest, now - last);
      last = now;
      if (now - since < 500) return;
      const fps = (frames * 1000) / (now - since);
      const { render, memory } = renderer.info;
      box.textContent =
        `${tier} ${renderer.domElement.width}x${renderer.domElement.height}\n` +
        `${fps.toFixed(0)} fps, worst ${slowest.toFixed(0)} ms\n` +
        `${render.calls} calls, ${(render.triangles / 1000).toFixed(0)}k tris\n` +
        `${memory.textures} textures, ${memory.geometries} geometries` +
        (lastAiMs === null ? '' : `\nAI think ${lastAiMs.toFixed(0)} ms`);
      frames = 0;
      slowest = 0;
      since = now;
    },
    dispose: () => {
      box.remove();
      renderer.info.autoReset = true;
    },
  };
}
