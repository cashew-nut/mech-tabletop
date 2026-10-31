// The Charter Trial board as a low-resolution Three.js scene. Same props as HexMap, so Battle can swap one for the other.
// The canvas renders at 1/PIXEL of its CSS size and is upscaled with nearest-neighbour filtering for the pixel-art look.
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { SURVEYOR_ID, hexKey, type GameState, type Hex } from '@brass-charter/rules';
import { hexCentre, type Highlight } from './HexMap';
import { PUFF, MARKER_HEX, bloomTexture, card, crate, die, markerTexture, rubble, ruinWall, stoneTexture, tower, type MarkerKind } from './boardArt';

const PIXEL = 3;
const UNIT = 1 / 26; // hexCentre is in SVG units; the scene works in hex-size units
const ELEVATION_STEP = 0.35;

// Dark ruined flagstones: open ground is grey slate, cover is mossier or more broken.
const TERRAIN_COLOUR: Record<string, number> = {
  open: 0x8d8b84,
  rough: 0x7d7566,
  light: 0x7b8668,
  heavy: 0x686f5c,
  blocking: 0x4f4c47,
};
const SIDE_COLOUR = [0x2d6e9c, 0x9c3a26];
const MARKER_OF: Record<Highlight, MarkerKind> = { move: 'move', jump: 'jump', smoke: 'smoke' };

interface Props {
  state: GameState;
  highlights: Map<string, Highlight>;
  selectedId: string | null;
  targetId: string | null;
  /** Hexes in weapon reach of the active walker; drawn as red target rings. */
  threat?: Set<string>;
  onHex: (hex: Hex) => void;
  onWalker: (id: string) => void;
}

const hexShape = new THREE.CylinderGeometry(1, 1, 1, 6, 1);
const box = new THREE.BoxGeometry(1, 1, 1);
const planeGeo = new THREE.PlaneGeometry(1.92, 1.92); // sized so the marker's hex outline (radius 30 of 64px) sits just inside a tile

const mat = (color: number, extra: THREE.MeshLambertMaterialParameters = {}) => new THREE.MeshLambertMaterial({ color, ...extra });
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
    rubble(parent, top, seed, 5, 1.1);
  } else if (terrain === 'light') {
    rubble(parent, top, seed, 3, 1);
    crate(parent, [(rnd(1) - 0.5) * 0.6, top, (rnd(2) - 0.5) * 0.6], 0.42, rnd(3) * 3);
    if (rnd(4) > 0.5) crate(parent, [(rnd(5) - 0.5) * 0.7, top + 0.42, (rnd(6) - 0.5) * 0.4], 0.3, rnd(7) * 3);
  } else if (terrain === 'heavy') {
    ruinWall(parent, top, seed, 1.5, Math.floor(rnd(1) * 3) * (Math.PI / 3));
    rubble(parent, top, seed + 3, 4, 1.2);
  } else if (terrain === 'blocking') {
    tower(parent, top, seed, rnd(9) > 0.55);
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

// The wargaming table around the board: a slate top in a wooden frame, with ruins on the far side and clutter nearer the camera.
function dressTable(parent: THREE.Object3D, lo: { x: number; z: number }, hi: { x: number; z: number }) {
  const margin = 3.4;
  const x0 = lo.x - margin;
  const x1 = hi.x + margin;
  const z0 = lo.z - margin;
  const z1 = hi.z + margin;
  const cx = (x0 + x1) / 2;
  const cz = (z0 + z1) / 2;
  add(parent, box, mat(0x3a4454), [cx, -0.62, cz], [x1 - x0, 0.4, z1 - z0]); // slate top
  const wood = mat(0x5a3b26);
  add(parent, box, wood, [cx, -0.6, z0 - 0.3], [x1 - x0 + 1.2, 0.5, 0.6]);
  add(parent, box, wood, [cx, -0.6, z1 + 0.3], [x1 - x0 + 1.2, 0.5, 0.6]);
  add(parent, box, wood, [x0 - 0.3, -0.6, cz], [0.6, 0.5, z1 - z0]);
  add(parent, box, wood, [x1 + 0.3, -0.6, cz], [0.6, 0.5, z1 - z0]);
  // Far side (high z) and flanks: the broken skyline.
  const rnd = (n: number) => ((Math.sin(n * 12.9898) * 43758.5453) % 1 + 1) % 1;
  for (let k = 0; k < 9; k++) {
    const x = x0 + 0.8 + ((x1 - x0 - 1.6) * (k + rnd(k + 1) * 0.5)) / 9;
    const g = new THREE.Group();
    g.position.set(x, -0.42, z1 - 1.0 - rnd(k + 20) * 0.9);
    if (k % 3 === 1) ruinWall(g, 0, 100 + k, 2.4, 0);
    else tower(g, 0, 200 + k, k % 3 === 2);
    parent.add(g);
  }
  for (const side of [x0 + 1.0, x1 - 1.0]) {
    for (let k = 0; k < 4; k++) {
      const g = new THREE.Group();
      g.position.set(side + (rnd(k + 40) - 0.5) * 0.6, -0.42, z0 + 2.5 + ((z1 - z0 - 5) * (k + 0.5)) / 4);
      if (k % 2) ruinWall(g, 0, 300 + k, 2.2, Math.PI / 2);
      else tower(g, 0, 400 + k + (side > cx ? 7 : 0), k === 2);
      parent.add(g);
    }
  }
  // Near side: crates, dice and rules cards.
  crate(parent, [cx - 4.5, -0.42, z0 + 1.0], 0.7, 0.3);
  crate(parent, [cx - 3.8, -0.42, z0 + 1.2], 0.55, 1.1);
  crate(parent, [cx - 4.2, -0.42 + 0.7, z0 + 1.05], 0.45, 0.8);
  crate(parent, [cx + 5.5, -0.42, z0 + 1.4], 0.6, 0.5);
  rubble(parent, -0.42, 77, 7, 2);
  die(parent, [cx + 3.2, -0.42, z0 + 1.1], 0xf1ede2, 0.4);
  die(parent, [cx + 3.7, -0.42, z0 + 0.8], 0x1f1f24, 1.2);
  die(parent, [x0 + 0.9, -0.42, cz + 1.5], 0xf1ede2, 0.9);
  die(parent, [x1 - 0.9, -0.42, cz - 2.5], 0x8e1f1f, 0.2);
  card(parent, [x0 + 1.4, -0.42, cz - 3.2], 0.5);
  card(parent, [x1 - 1.6, -0.42, z0 + 1.6], -0.3);
}

export function Board3D({ state, highlights, selectedId, targetId, threat, onHex, onWalker }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const live = useRef({ state, highlights, selectedId, targetId, threat, onHex, onWalker });
  live.current = { state, highlights, selectedId, targetId, threat, onHex, onWalker };
  const api = useRef<{ rebuild: () => void } | null>(null);

  useEffect(() => {
    const el = host.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: false });
    renderer.setClearColor(0x232a36);
    const canvas = renderer.domElement;
    canvas.className = 'board3d-canvas';
    el.appendChild(canvas);

    const scene = new THREE.Scene();
    scene.add(new THREE.HemisphereLight(0xdfe6f5, 0x3a3128, 1.35));
    const sun = new THREE.DirectionalLight(0xffd9a0, 1.9);
    sun.position.set(-8, 14, 6);
    scene.add(sun);

    // One flagstone texture per terrain; the side and underside are plain dark stone.
    const tileMats: Record<string, THREE.Material[]> = {};
    Object.entries(TERRAIN_COLOUR).forEach(([name, colour], i) => {
      tileMats[name] = [
        mat(0x3c3a36),
        new THREE.MeshLambertMaterial({ map: stoneTexture(colour, i + 1) }),
        mat(0x2a2825),
      ];
    });

    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 200);
    const controls = new OrbitControls(camera, canvas);
    controls.enablePan = false;
    controls.maxPolarAngle = Math.PI * 0.42;
    controls.minPolarAngle = Math.PI * 0.12;
    controls.minDistance = 6;
    controls.maxDistance = 32;

    const terrain = new THREE.Group();
    const dynamic = new THREE.Group();
    scene.add(terrain, dynamic);
    const pickables: THREE.Object3D[] = [];
    const pulsing: THREE.Mesh[] = [];

    const markerTextures = { attack: markerTexture('attack'), move: markerTexture('move'), jump: markerTexture('jump'), smoke: markerTexture('smoke') };
    const mapCentre = new THREE.Vector3();
    const focus = new THREE.Vector3();
    const puffs: THREE.Mesh[] = [];
    let builtMap = '';
    const buildTerrain = () => {
      const { state } = live.current;
      terrain.clear();
      let sx = 0;
      let sz = 0;
      let n = 0;
      let i = 0;
      const lo = { x: Infinity, z: Infinity };
      const hi = { x: -Infinity, z: -Infinity };
      for (const key of Object.keys(state.map.hexes)) {
        const [q, r] = key.split(',').map(Number);
        const info = state.map.hexes[key];
        const base = world({ q, r });
        const top = info.elevation * ELEVATION_STEP;
        const tile = add(terrain, hexShape, tileMats[info.terrain] as unknown as THREE.Material, [base.x, (top - 0.4) / 2, base.z], [0.97, top + 0.4, 0.97]);
        tile.userData.hex = { q, r };
        const props = new THREE.Group();
        props.position.set(base.x, 0, base.z);
        terrainProps(props, info.terrain, top, ++i);
        terrain.add(props);
        sx += base.x;
        sz += base.z;
        n++;
        lo.x = Math.min(lo.x, base.x);
        lo.z = Math.min(lo.z, base.z);
        hi.x = Math.max(hi.x, base.x);
        hi.z = Math.max(hi.z, base.z);
      }
      dressTable(terrain, lo, hi);
      puffs.length = 0;
      terrain.traverse((o) => o.userData[PUFF] && puffs.push(o as THREE.Mesh));
      if (builtMap !== state.map.id) {
        builtMap = state.map.id;
        // Close in on the action like the concept art, rather than showing the whole 16x12 map; the focus follows the selected walker.
        mapCentre.set(sx / n, 0, sz / n);
        mapCentre.z = lo.z + (hi.z - lo.z) * 0.3; // start on your deployment edge
        focus.copy(mapCentre);
        controls.target.copy(focus);
        camera.position.set(focus.x, 12, focus.z - 12.5); // row 0 (your deployment edge) faces the camera
        controls.update();
      }
    };

    const rebuild = () => {
      const { state, highlights, selectedId, targetId, threat } = live.current;
      if (builtMap !== state.map.id) buildTerrain();
      const focusWalker = state.walkers.find((w) => w.id === (selectedId ?? state.active?.walkerId)) ?? null;
      focus.copy(focusWalker && !focusWalker.destroyed ? world(focusWalker.pos) : mapCentre);
      dynamic.clear();
      pickables.length = 0;
      pulsing.length = 0;
      pickables.push(...terrain.children.filter((c) => c.userData.hex));

      // Glowing hex markers: blue chevrons for moves, red rings for weapon reach.
      const marker = (hex: Hex, kind: MarkerKind) => {
        const p = world(hex, heightOf(state, hex) + 0.03);
        const material = new THREE.MeshBasicMaterial({ map: markerTextures[kind], transparent: true, depthWrite: false, opacity: 0.9 });
        const m = new THREE.Mesh(planeGeo, material);
        m.rotation.order = 'YXZ';
        m.rotation.x = -Math.PI / 2;
        m.rotation.y = Math.PI; // chevrons point up the board, away from the camera
        m.position.copy(p);
        dynamic.add(m);
        pulsing.push(m);
        const bloom = new THREE.Mesh(planeGeo, new THREE.MeshBasicMaterial({ map: bloomTexture(), color: MARKER_HEX[kind], transparent: true, opacity: 0.7, blending: THREE.AdditiveBlending, depthWrite: false }));
        bloom.rotation.x = -Math.PI / 2;
        bloom.position.set(p.x, p.y + 0.01, p.z);
        bloom.scale.setScalar(1.45);
        dynamic.add(bloom);
      };
      for (const [key, kind] of highlights) {
        const [q, r] = key.split(',').map(Number);
        marker({ q, r }, MARKER_OF[kind]);
      }
      for (const key of threat ?? []) {
        if (highlights.has(key)) continue;
        const [q, r] = key.split(',').map(Number);
        marker({ q, r }, 'attack');
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
      for (const m of puffs) {
        const d = m.userData[PUFF] as { baseY: number; phase: number; drift: number };
        const f = (t / 4200 + d.phase) % 1;
        m.position.y = d.baseY + f * 1.5;
        m.position.x += (Math.sin(t / 900 + d.phase * 6) * 0.0015 + d.drift * 0.002);
        if (f < 0.02) m.position.x = 0.25; // restart above the chimney
        m.scale.setScalar(0.16 + f * 0.5);
        m.rotation.y = f * 3;
        (m.material as THREE.MeshLambertMaterial).opacity = Math.min(1, f * 6) * (1 - f) * 0.9;
      }
      const k = 0.7 + 0.3 * Math.sin(t / 220);
      for (const m of pulsing) (m.material as THREE.MeshBasicMaterial).opacity = Math.min(1, k * 1.05);
      const step = focus.clone().sub(controls.target).multiplyScalar(0.08); // glide to the new focus, carrying the camera with it
      controls.target.add(step);
      camera.position.add(step);
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

  useEffect(() => api.current?.rebuild(), [state, highlights, selectedId, targetId, threat]);

  return <div ref={host} className="board3d" />;
}
