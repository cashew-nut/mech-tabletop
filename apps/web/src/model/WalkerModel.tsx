// Interactive 3D view of the war-walker being built, with paint and export.
import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { WalkerInput } from '@brass-charter/rules';
import { FACTION_COLOURS, buildWalkerModel, ensureKitParts, loadPartLibrary, type PartLibrary } from './assemble';
import { exportGlb, exportStl } from './exporters';
import { baseMm } from './parts';
import { PartView } from './partview';
import { createStage, type Stage } from './stage';

/** Classes with closed composite kit parts, which the part view can pull apart. */
const KIT_CHASSIS = ['paladin', 'brute', 'seer'];

interface Props {
  walker: WalkerInput;
  faction: string;
  onPaint: (colour: string | undefined) => void;
}

export default function WalkerModel({ walker, faction, onPaint }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const scene = useRef<{ stage: Stage; model: THREE.Object3D | null; renderer: THREE.WebGLRenderer; camera: THREE.PerspectiveCamera; controls: OrbitControls } | null>(null);
  const view = useRef<PartView | null>(null);
  // The part view: explode, joint lines and part toggles, on the same model the builder shows.
  const [partsOn, setPartsOn] = useState(() => new URLSearchParams(location.search).get('parts') === '1');
  const [explode, setExplode] = useState(0); // where the slider and button want it: 0 together, 1 apart
  const [guides, setGuides] = useState(true);
  const [partList, setPartList] = useState<{ label: string; item: boolean; on: boolean }[]>([]);
  const goal = useRef(0);
  const flags = useRef({ on: false, guides: true });
  flags.current = { on: partsOn, guides };
  goal.current = explode;
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
    scene.current = { stage, model: null, renderer, camera, controls };
    loadPartLibrary(renderer).then(setLib);

    const resize = () => {
      const w = el.clientWidth;
      const h = Math.max(260, Math.min(window.innerHeight - 200, w * 0.75));
      renderer.setSize(w, h);
      stage.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    let frame = 0;
    let applied = 1;
    const loop = () => {
      frame = requestAnimationFrame(loop);
      const pv = view.current;
      if (pv) {
        if (Math.abs(pv.t - goal.current) > 1e-3) {
          // Ease toward the goal; the whole move takes about half a second.
          pv.t += (goal.current - pv.t) * 0.16;
          if (Math.abs(pv.t - goal.current) < 1e-3) pv.t = goal.current;
        }
        pv.showGuides = flags.current.guides;
        pv.apply();
        // Back the camera off as the figure opens, keeping the angle the viewer chose.
        const want = 1 + (pv.spread - 1) * pv.t;
        const off = camera.position.clone().sub(controls.target).multiplyScalar(want / applied);
        applied = want;
        camera.position.copy(controls.target).add(off);
      } else applied = 1;
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
    view.current?.dispose();
    view.current = null;
    if (s.model) s.stage.scene.remove(s.model);
    try {
      s.model = buildWalkerModel(walker, colour, lib, partsOn && KIT_CHASSIS.includes(walker.chassis) ? 'force' : 'auto');
      s.stage.scene.add(s.model);
      s.stage.fit(s.model);
      if (partsOn && KIT_CHASSIS.includes(walker.chassis)) {
        const pv = new PartView(s.model, s.stage.scene, walker.chassis);
        pv.t = goal.current;
        view.current = pv;
        setPartList(pv.parts.map((p) => ({ label: p.label, item: p.item, on: true })));
      } else setPartList([]);
    } catch (e) {
      console.error(e);
    }
  }, [walker, colour, lib, kitVersion, partsOn]);

  const hasKit = KIT_CHASSIS.includes(walker.chassis);
  const toggle = (i: number, on: boolean) => {
    const pv = view.current;
    if (!pv) return;
    pv.setVisible(pv.parts[i], on);
    setPartList((l) => l.map((x, j) => (j === i ? { ...x, on } : x)));
  };
  const toggleEquipment = (on: boolean) => {
    const pv = view.current;
    if (!pv) return;
    pv.parts.forEach((p) => p.item && (p.node.visible = on));
    pv.apply();
    setPartList((l) => l.map((x) => (x.item ? { ...x, on } : x)));
  };

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
          <button
            className="secondary"
            disabled={!hasKit}
            aria-pressed={partsOn && hasKit}
            onClick={() => setPartsOn((v) => !v)}
            title={hasKit ? 'Part view: pull the parts apart along their joints and hide any of them' : 'Part view covers the Paladin, Brute and Seer so far'}
          >
            Part view
          </button>
          <button disabled={failed} onClick={() => model() && exportStl(model()!, walker.name)} title="For 3D printing, in millimetres">
            STL
          </button>
          <button disabled={failed} onClick={() => model() && exportGlb(model()!, walker.name)} title="For Blender or other 3D tools">
            GLB
          </button>
        </div>
      </div>
      {failed ? <p className="hint">3D view needs WebGL, which this browser has turned off.</p> : <div ref={host} className="model-canvas" />}
      {partsOn && hasKit && (
        <div className="part-view">
          <div className="part-view-tools">
            <button id="explode-btn" aria-pressed={explode > 0.5} onClick={() => setExplode(explode > 0.5 ? 0 : 1)}>
              {explode > 0.5 ? 'Collapse' : 'Explode'}
            </button>
            <input type="range" min="0" max="1" step="0.01" value={explode} onChange={(e) => { setExplode(+e.target.value); if (view.current) view.current.t = +e.target.value; }} aria-label="Pull the parts apart" />
            <label><input type="checkbox" checked={guides} onChange={(e) => setGuides(e.target.checked)} /> Joint lines</label>
            <label><input type="checkbox" checked={partList.every((x) => !x.item || x.on)} onChange={(e) => toggleEquipment(e.target.checked)} /> Equipment</label>
          </div>
          <p className="hint">Each part slides off along the line from its parent, so the joint tree shows. The lines mark the joints. Part view always shows the closed kit body, even for a class whose kit is not finished, so the builder's model may differ for that class.</p>
          <div className="part-list">
            {partList.map((x, i) => (
              <label key={i} className={x.item ? 'item' : ''}>
                <input type="checkbox" checked={x.on} onChange={(e) => toggle(i, e.target.checked)} /> {x.label}
              </label>
            ))}
          </div>
        </div>
      )}
      <p className="hint">
        Drag to orbit, scroll to zoom. Parts are procedural until Blender models are added; the STL prints at tabletop scale on a{' '}
        {baseMm(walker.chassis)} mm base.
      </p>
    </section>
  );
}
