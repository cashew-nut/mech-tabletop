// Interactive 3D view of the war-walker being built, with paint and export.
import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { WalkerInput } from '@brass-charter/rules';
import { FACTION_COLOURS, buildWalkerModel, ensureKitParts, loadPartLibrary, type PartLibrary } from './assemble';
import { exportGlb, exportStl } from './exporters';
import { baseMm } from './parts';
import { createStage, type Stage } from './stage';

interface Props {
  walker: WalkerInput;
  faction: string;
  onPaint: (colour: string | undefined) => void;
}

export default function WalkerModel({ walker, faction, onPaint }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const scene = useRef<{ stage: Stage; model: THREE.Object3D | null; renderer: THREE.WebGLRenderer } | null>(null);
  const [lib, setLib] = useState<PartLibrary | null>(null);
  const [kitVersion, setKitVersion] = useState(0);
  const [failed, setFailed] = useState(false);
  const colour = walker.paint ?? FACTION_COLOURS[faction] ?? '#7a2e22';

  // One renderer for the life of the component.
  useEffect(() => {
    const el = host.current!;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    } catch {
      setFailed(true);
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    const stage = createStage(renderer);
        const camera = new THREE.PerspectiveCamera(35, 1, 1, 4000);
    camera.position.set(80, 40, 100);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 22, 0);
    controls.enableDamping = true;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 1.2;
    controls.addEventListener('start', () => (controls.autoRotate = false));
    scene.current = { stage, model: null, renderer };
    loadPartLibrary(renderer).then(setLib);

    const resize = () => {
      const w = el.clientWidth;
      const h = Math.max(260, Math.min(420, w * 0.75));
      renderer.setSize(w, h);
      stage.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    let frame = 0;
    const loop = () => {
      frame = requestAnimationFrame(loop);
      controls.update();
      stage.render(camera);
    };
    loop();
    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
      controls.dispose();
      stage.dispose();
      renderer.dispose();
      el.removeChild(renderer.domElement);
      scene.current = null;
    };
  }, []);

  // Fetch this class's Blender kit parts, if it has any, then rebuild.
  useEffect(() => {
    if (!lib) return;
    let live = true;
    ensureKitParts(lib, walker.chassis).then((added) => live && added && setKitVersion((v) => v + 1));
    return () => {
      live = false;
    };
  }, [lib, walker.chassis]);

  // Rebuild the model whenever the build or paint changes.
  useEffect(() => {
    const s = scene.current;
    if (!s) return;
    if (s.model) s.stage.scene.remove(s.model);
    try {
      s.model = buildWalkerModel(walker, colour, lib);
      s.stage.scene.add(s.model);
      s.stage.fit(s.model);
    } catch (e) {
      console.error(e);
    }
  }, [walker, colour, lib, kitVersion]);

  const model = () => scene.current?.model ?? null;

  return (
    <section className="panel model">
      <div className="model-head">
        <h3>Model</h3>
        <div className="model-tools">
          <label className="paint">
            <span>Hull paint</span>
            <input type="color" value={colour} onChange={(e) => onPaint(e.target.value)} aria-label="Hull paint colour" />
          </label>
          {walker.paint && (
            <button className="secondary" onClick={() => onPaint(undefined)}>
              Faction livery
            </button>
          )}
          <button disabled={failed} onClick={() => model() && exportStl(model()!, walker.name)} title="For 3D printing, in millimetres">
            STL
          </button>
          <button disabled={failed} onClick={() => model() && exportGlb(model()!, walker.name)} title="For Blender or other 3D tools">
            GLB
          </button>
        </div>
      </div>
      {failed ? <p className="hint">3D view needs WebGL, which this browser has turned off.</p> : <div ref={host} className="model-canvas" />}
      <p className="hint">
        Drag to orbit, scroll to zoom. Parts are procedural until Blender models are added; the STL prints at tabletop scale on a{' '}
        {baseMm(walker.chassis)} mm base.
      </p>
    </section>
  );
}
