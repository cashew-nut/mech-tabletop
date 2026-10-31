// The Charter Trial board as a low-resolution Three.js scene. Same props as HexMap, so Battle can swap one for the other.
// The canvas renders at 1/PIXEL of its CSS size and is upscaled with nearest-neighbour filtering for the pixel-art look.
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { SURVEYOR_ID, hexKey, type GameState, type Hex } from '@brass-charter/rules';
import { hexCentre, type Highlight } from './HexMap';

const PIXEL = 3;
const UNIT = 1 / 26; // hexCentre is in SVG units; the scene works in hex-size units
const ELEVATION_STEP = 0.35;

const TERRAIN_COLOUR: Record<string, number> = {
  open: 0xcdbf98,
  rough: 0xa99a74,
  light: 0x9fae7a,
  heavy: 0x6f7a5a,
  blocking: 0x3b342d,
};
const SIDE_COLOUR = [0x2d6e9c, 0x9c3a26];
const HIGHLIGHT_COLOUR: Record<Highlight, number> = { move: 0x2f9e8f, jump: 0xb8893b, smoke: 0xeeeeee };

interface Props {
  state: GameState;
  highlights: Map<string, Highlight>;
  selectedId: string | null;
  targetId: string | null;
  onHex: (hex: Hex) => void;
  onWalker: (id: string) => void;
}

const hexShape = new THREE.CylinderGeometry(1, 1, 1, 6, 1);
hexShape.rotateY(Math.PI / 6); // pointy-top, like the SVG map
const box = new THREE.BoxGeometry(1, 1, 1);

const mat = (color: number, extra: THREE.MeshLambertMaterialParameters = {}) => new THREE.MeshLambertMaterial({ color, flatShading: true, ...extra });
const world = (hex: Hex, y = 0) => {
  const { x, y: z } = hexCentre(hex);
  return new THREE.Vector3(x * UNIT, y, z * UNIT);
};
const heightOf = (state: GameState, hex: Hex) => (state.map.hexes[hexKey(hex)]?.elevation ?? 0) * ELEVATION_STEP;

function add(parent: THREE.Object3D, geo: THREE.BufferGeometry, material: THREE.Material, pos: [number, number, number], scale: [number, number, number]) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(...pos);
  m.scale.set(...scale);
  parent.add(m);
  return m;
}

function terrainProps(parent: THREE.Object3D, terrain: string, top: number, seed: number) {
  const rnd = (n: number) => ((Math.sin(seed * 12.9898 + n * 78.233) * 43758.5453) % 1 + 1) % 1;
  if (terrain === 'rough') {
    for (let i = 0; i < 4; i++) add(parent, box, mat(0x7d6f52), [(rnd(i) - 0.5) * 1.1, top + 0.08, (rnd(i + 9) - 0.5) * 1.1], [0.22, 0.16, 0.22]);
  } else if (terrain === 'light') {
    for (let i = 0; i < 3; i++) {
      const x = (rnd(i) - 0.5) * 1.1;
      const z = (rnd(i + 5) - 0.5) * 1.1;
      add(parent, box, mat(0x4d3a26), [x, top + 0.15, z], [0.1, 0.3, 0.1]);
      add(parent, box, mat(0x4f7a38), [x, top + 0.5, z], [0.38, 0.4, 0.38]);
    }
  } else if (terrain === 'heavy') {
    for (let i = 0; i < 3; i++) {
      const x = (rnd(i) - 0.5) * 0.9;
      const z = (rnd(i + 3) - 0.5) * 0.9;
      add(parent, box, mat(0x3f4a33), [x, top + 0.3, z], [0.35, 0.6, 0.35]);
      add(parent, box, mat(0x56673f), [x, top + 0.75, z], [0.5, 0.35, 0.5]);
    }
  } else if (terrain === 'blocking') {
    add(parent, box, mat(0x2a241f), [0, top + 0.6, 0], [1.3, 1.2, 1.3]);
    add(parent, box, mat(0x1e1b18), [0.2, top + 1.3, -0.1], [0.7, 0.5, 0.7]);
  }
}

// Placeholder pixel walker, sized by chassis Size. Stage 2 replaces this with per-class faction models.
function walkerMesh(side: number, size: number) {
  const g = new THREE.Group();
  const body = mat(SIDE_COLOUR[side]);
  const trim = mat(0xd4a956);
  const h = 0.5 + size * 0.12;
  add(g, box, body, [-0.18, h * 0.25, 0], [0.18, h * 0.5, 0.2]); // legs
  add(g, box, body, [0.18, h * 0.25, 0], [0.18, h * 0.5, 0.2]);
  add(g, box, body, [0, h * 0.75, 0], [0.55, h * 0.5, 0.35]); // torso
  add(g, box, trim, [0, h * 1.08, 0.02], [0.22, 0.16, 0.22]); // head
  add(g, box, trim, [0, h * 0.75, 0.3], [0.2, 0.12, 0.3]); // nose: faces +Z, rotated by facing below
  return g;
}

export function Board3D({ state, highlights, selectedId, targetId, onHex, onWalker }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const live = useRef({ state, highlights, selectedId, targetId, onHex, onWalker });
  live.current = { state, highlights, selectedId, targetId, onHex, onWalker };
  const api = useRef<{ rebuild: () => void } | null>(null);

  useEffect(() => {
    const el = host.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: false });
    renderer.setClearColor(0x1e1b18);
    const canvas = renderer.domElement;
    canvas.className = 'board3d-canvas';
    el.appendChild(canvas);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x1e1b18, 25, 60);
    scene.add(new THREE.HemisphereLight(0xfff1d6, 0x3a3128, 1.5));
    const sun = new THREE.DirectionalLight(0xffe2b0, 1.6);
    sun.position.set(-8, 14, 6);
    scene.add(sun);

    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 200);
    const controls = new OrbitControls(camera, canvas);
    controls.enablePan = false;
    controls.maxPolarAngle = Math.PI * 0.42;
    controls.minPolarAngle = Math.PI * 0.12;
    controls.minDistance = 6;
    controls.maxDistance = 40;

    const terrain = new THREE.Group();
    const dynamic = new THREE.Group();
    scene.add(terrain, dynamic);
    const pickables: THREE.Object3D[] = [];
    const pulsing: THREE.Mesh[] = [];

    let builtMap = '';
    const buildTerrain = () => {
      const { state } = live.current;
      terrain.clear();
      let sx = 0;
      let sz = 0;
      let n = 0;
      let i = 0;
      for (const key of Object.keys(state.map.hexes)) {
        const [q, r] = key.split(',').map(Number);
        const info = state.map.hexes[key];
        const base = world({ q, r });
        const top = info.elevation * ELEVATION_STEP;
        const tile = add(terrain, hexShape, mat(TERRAIN_COLOUR[info.terrain] + ((q + r) & 1 ? 0x040404 : 0)), [base.x, (top - 0.4) / 2, base.z], [0.97, top + 0.4, 0.97]);
        tile.userData.hex = { q, r };
        const props = new THREE.Group();
        props.position.set(base.x, 0, base.z);
        terrainProps(props, info.terrain, top, ++i);
        terrain.add(props);
        sx += base.x;
        sz += base.z;
        n++;
      }
      if (builtMap !== state.map.id) {
        builtMap = state.map.id;
        const span = Math.max(state.map.width, state.map.height) * 1.6;
        controls.target.set(sx / n, 0, sz / n);
        camera.position.set(sx / n, span * 1.0, sz / n - span * 0.95); // row 0 (your deployment edge) faces the camera
        controls.update();
      }
    };

    const rebuild = () => {
      const { state, highlights, selectedId, targetId } = live.current;
      if (builtMap !== state.map.id) buildTerrain();
      dynamic.clear();
      pickables.length = 0;
      pulsing.length = 0;
      pickables.push(...terrain.children.filter((c) => c.userData.hex));

      for (const [key, kind] of highlights) {
        const [q, r] = key.split(',').map(Number);
        const p = world({ q, r }, heightOf(state, { q, r }) + 0.03);
        const m = add(dynamic, hexShape, new THREE.MeshBasicMaterial({ color: HIGHLIGHT_COLOUR[kind], transparent: true, opacity: 0.55 }), [p.x, p.y, p.z], [0.9, 0.04, 0.9]);
        pulsing.push(m);
      }
      for (const o of state.objectives) {
        const p = world(o.hex, heightOf(state, o.hex) + 0.04);
        add(dynamic, hexShape, new THREE.MeshBasicMaterial({ color: 0xd4a956, transparent: true, opacity: 0.45 }), [p.x, p.y, p.z], [0.62, 0.03, 0.62]);
        add(dynamic, box, mat(0xd4a956), [p.x, p.y + 0.4, p.z], [0.08, 0.8, 0.08]);
        add(dynamic, box, mat(0xb8893b), [p.x + 0.17, p.y + 0.68, p.z], [0.3, 0.2, 0.04]);
      }
      for (const key of state.smoke) {
        const [q, r] = key.split(',').map(Number);
        const p = world({ q, r }, heightOf(state, { q, r }));
        for (let i = 0; i < 5; i++) add(dynamic, box, mat(0xe8e8e8, { transparent: true, opacity: 0.75 }), [p.x + Math.sin(i * 2.1) * 0.3, p.y + 0.25 + i * 0.12, p.z + Math.cos(i * 2.1) * 0.3], [0.45, 0.4, 0.45]);
      }
      state.wrecks.forEach((key, idx) => {
        const [q, r] = key.split(',').map(Number);
        const p = world({ q, r }, heightOf(state, { q, r }));
        add(dynamic, box, mat(0x2b2118), [p.x - 0.15, p.y + 0.12, p.z + 0.05 * idx], [0.5, 0.24, 0.4]).rotation.y = idx;
        add(dynamic, box, mat(0x4a3a2a), [p.x + 0.2, p.y + 0.2, p.z - 0.1], [0.2, 0.4, 0.2]).rotation.z = 0.4;
      });
      const sv = state.surveyor;
      if (sv?.status === 'active') {
        const p = world(sv.pos, heightOf(state, sv.pos) + 0.5);
        const g = new THREE.Group();
        g.position.copy(p);
        add(g, box, mat(0xd4a956), [0, 0, 0], [0.4, 0.4, 0.4]).rotation.set(0.6, 0.78, 0.6);
        g.userData.walkerId = SURVEYOR_ID;
        dynamic.add(g);
        pickables.push(g);
        if (targetId === SURVEYOR_ID) pulsing.push(add(dynamic, hexShape, new THREE.MeshBasicMaterial({ color: 0xffd34d }), [p.x, p.y - 0.45, p.z], [0.8, 0.03, 0.8]));
      }
      const activeId = state.active?.walkerId ?? null;
      for (const w of state.walkers) {
        if (w.destroyed) continue;
        const p = world(w.pos, heightOf(state, w.pos));
        const g = walkerMesh(w.side, w.size);
        g.position.copy(p);
        g.rotation.y = Math.PI / 2 + (60 * w.facing * Math.PI) / 180; // +Z nose -> SVG angle -60 * facing
        if (w.prone) {
          g.rotation.x = Math.PI / 2;
          g.position.y += 0.2;
        }
        g.userData.walkerId = w.id;
        if (w.activated) g.traverse((o) => ((o as THREE.Mesh).material && ((o as THREE.Mesh).material as THREE.MeshLambertMaterial).color.multiplyScalar(0.55)));
        dynamic.add(g);
        pickables.push(g);
        const ring = (colour: number, radius: number) => {
          const m = add(dynamic, hexShape, new THREE.MeshBasicMaterial({ color: colour }), [p.x, p.y + 0.02, p.z], [radius, 0.03, radius]);
          return m;
        };
        if (w.id === activeId) ring(0xf5f0d8, 0.8);
        if (w.id === selectedId) ring(0x2f9e8f, 0.7);
        if (w.id === targetId) pulsing.push(ring(0xffd34d, 0.75));
        for (let i = 0; i < w.overpressure; i++) add(dynamic, box, new THREE.MeshBasicMaterial({ color: 0xff8a3d }), [p.x - 0.4 + i * 0.12, p.y + 1.3, p.z], [0.08, 0.08, 0.08]);
      }
    };
    api.current = { rebuild };
    buildTerrain();
    rebuild();

    const resize = () => {
      const w = el.clientWidth;
      const h = Math.max(260, Math.round(w * 0.72));
      el.style.height = `${h}px`;
      renderer.setSize(Math.ceil(w / PIXEL), Math.ceil(h / PIXEL), false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(el);

    // A click is a pointer up that did not travel far from its pointer down (otherwise it was an orbit drag).
    const ray = new THREE.Raycaster();
    let down: { x: number; y: number } | null = null;
    const onDown = (e: PointerEvent) => (down = { x: e.clientX, y: e.clientY });
    const onUp = (e: PointerEvent) => {
      if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return;
      const rect = canvas.getBoundingClientRect();
      ray.setFromCamera(new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -(((e.clientY - rect.top) / rect.height) * 2 - 1)), camera);
      const hit = ray.intersectObjects(pickables, true)[0];
      if (!hit) return;
      let o: THREE.Object3D | null = hit.object;
      while (o && !o.userData.walkerId && !o.userData.hex) o = o.parent;
      if (!o) return;
      if (o.userData.walkerId) live.current.onWalker(o.userData.walkerId);
      else live.current.onHex(o.userData.hex);
    };
    canvas.addEventListener('pointerdown', onDown);
    canvas.addEventListener('pointerup', onUp);

    let raf = 0;
    const loop = (t: number) => {
      raf = requestAnimationFrame(loop);
      const k = 0.7 + 0.3 * Math.sin(t / 220);
      for (const m of pulsing) (m.material as THREE.MeshBasicMaterial).opacity = k * 0.8;
      controls.update();
      renderer.render(scene, camera);
    };
    raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointerup', onUp);
      controls.dispose();
      renderer.dispose();
      canvas.remove();
      api.current = null;
    };
  }, []);

  useEffect(() => api.current?.rebuild(), [state, highlights, selectedId, targetId]);

  return <div ref={host} className="board3d" />;
}
