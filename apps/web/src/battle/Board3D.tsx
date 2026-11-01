// The Charter Trial board as a low-resolution Three.js scene. Same props as HexMap, so Battle can swap one for the other.
// The canvas renders at 1/PIXEL of its CSS size and is upscaled with nearest-neighbour filtering for the pixel-art look.
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import { SURVEYOR_ID, hexKey, type GameState, type Hex } from '@brass-charter/rules';
import { hexCentre, type Highlight } from './HexMap';
import { loadBoardKit, type Kit, type KitPiece } from './boardKit';
import { WalkerLibrary } from './boardWalkers';
import { PUFF, chimneySmoke, MARKER_HEX, bloomTexture, card, crate, die, markerTexture, rubble, ruinWall, stoneTexture, tower, type MarkerKind } from './boardArt';

// Render scale: 1 draws at full resolution so the walker textures stay crisp (?pixel=2 gives the old half-resolution look).
const PIXEL = Number(new URLSearchParams(location.search).get('pixel') ?? 1);
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

const rnd01 = (n: number) => ((Math.sin(n * 12.9898) * 43758.5453) % 1 + 1) % 1;
const hexShape = new THREE.CylinderGeometry(1, 1, 1, 6, 1);
const box = new THREE.BoxGeometry(1, 1, 1);
const planeGeo = new THREE.PlaneGeometry(1.92, 1.92); // sized so the marker's hex outline (radius 30 of 64px) sits just inside a tile

const mat = (color: number, extra: THREE.MeshLambertMaterialParameters = {}) => new THREE.MeshLambertMaterial({ color, ...extra });
const world = (hex: Hex, y = 0) => {
  const { x, y: z } = hexCentre(hex);
  return new THREE.Vector3(x * UNIT, y, z * UNIT);
};
/** A tower for hex `n`: the Meshy hero towers when they are loaded (most of the time), otherwise the procedural ones. */
const TOWERS: KitPiece[] = ['tower_spire', 'tower_chimney', 'tower_ruined'];
const pickTower = (kit: Kit, n: number): KitPiece => {
  const heroes = (['hero_tower', 'hero_chimney'] as KitPiece[]).filter((p) => kit.has(p));
  const r = rnd01(n * 1.7 + 2);
  if (heroes.length && r < 0.75) return heroes[Math.floor(rnd01(n * 4.1 + 1) * heroes.length)];
  return TOWERS[Math.floor(r * 3)];
};
let tileLift = 0; // the kit's flagstones stand a little proud of y = 0
const heightOf = (state: GameState, hex: Hex) => (state.map.hexes[hexKey(hex)]?.elevation ?? 0) * ELEVATION_STEP + tileLift;

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
function dressTable(parent: THREE.Object3D, lo: { x: number; z: number }, hi: { x: number; z: number }, kit: Kit | null) {
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
    if (kit) {
      const piece = kit.make(k % 3 === 1 ? (kit.has('hero_wall') && k % 2 ? 'hero_wall' : 'wall_long') : pickTower(kit, k + 30));
      g.add(piece);
      const anchor = piece.getObjectByName('smoke');
      if (anchor) chimneySmoke(piece, anchor.position, 200 + k);
    } else if (k % 3 === 1) ruinWall(g, 0, 100 + k, 2.4, 0);
    else tower(g, 0, 200 + k, k % 3 === 2);
    parent.add(g);
  }
  for (const side of [x0 + 1.0, x1 - 1.0]) {
    for (let k = 0; k < 4; k++) {
      const g = new THREE.Group();
      g.position.set(side + (rnd(k + 40) - 0.5) * 0.6, -0.42, z0 + 2.5 + ((z1 - z0 - 5) * (k + 0.5)) / 4);
      if (kit) {
        const piece = kit.make(k % 2 ? 'wall_long' : pickTower(kit, k + (side > cx ? 50 : 40)));
        if (k % 2) piece.rotation.y = Math.PI / 2;
        g.add(piece);
        const anchor = piece.getObjectByName('smoke');
        if (anchor) chimneySmoke(piece, anchor.position, 400 + k);
      } else if (k % 2) ruinWall(g, 0, 300 + k, 2.2, Math.PI / 2);
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
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    const canvas = renderer.domElement;
    canvas.className = 'board3d-canvas';
    el.appendChild(canvas);

    const scene = new THREE.Scene();
    // A soft studio environment so the walkers' metal and gilding catch light as they do in the Lance Ledger.
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environmentIntensity = 0.45;
    scene.add(new THREE.HemisphereLight(0xdfe6f5, 0x4a4036, 0.5));
    const sun = new THREE.DirectionalLight(0xffd9a0, 1.4);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, { left: -16, right: 16, top: 16, bottom: -16, near: 1, far: 60 });
    sun.shadow.bias = -0.0008;
    sun.shadow.normalBias = 0.02;
    const sunOffset = new THREE.Vector3(-10, 18, -7);
    scene.add(sun, sun.target);
    const rim = new THREE.DirectionalLight(0x6f8cff, 0.5); // cool fill from the other side
    rim.position.set(12, 8, 10);
    scene.add(rim);

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
    // Bloom picks up only the brightest things: hex markers, furnace mouths and the walkers' glowing eyes.
    const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(2, 2, { type: THREE.HalfFloatType, samples: 4 }));
    const bloom = new UnrealBloomPass(new THREE.Vector2(2, 2), 0.35, 0.5, 0.92);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(bloom);
    composer.addPass(new OutputPass());
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

    const walkerLib = new WalkerLibrary(renderer, () => api.current?.rebuild());
    const markerTextures = { attack: markerTexture('attack'), move: markerTexture('move'), jump: markerTexture('jump'), smoke: markerTexture('smoke') };
    let kit: Kit | null = null;
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
        if (kit) {
          const objective = state.objectives.some((o) => o.hex.q === q && o.hex.r === r);
          const pick = (list: KitPiece[]) => list[Math.floor(rnd01(i * 7.3 + 1) * list.length)];
          const terrainTile: Record<string, KitPiece[]> = {
            open: ['tile_plain_1', 'tile_plain_2', 'tile_plain_1', 'tile_cracked_3', 'tile_slab_4'],
            rough: ['tile_rough_6', 'tile_rubble_7'],
            light: ['tile_moss_5', 'tile_moss_5', 'tile_plain_2'],
            heavy: ['tile_plain_2', 'tile_cracked_3'],
            blocking: ['tile_scorched_9'],
          };
          const tile = kit.make(objective ? 'tile_plate_8' : pick(terrainTile[info.terrain]));
          tile.position.set(base.x, top, base.z);
          tile.rotation.y = Math.floor(rnd01(i * 3.1 + 5) * 6) * (Math.PI / 3);
          tile.userData.hex = { q, r };
          terrain.add(tile);
          if (top > 0) add(terrain, hexShape, tileMats.blocking[0], [base.x, (top - 0.4) / 2 - 0.02, base.z], [0.95, top + 0.4, 0.95]); // plinth under raised ground
          const prop = new THREE.Group();
          prop.position.set(base.x, top, base.z);
          if (info.terrain === 'blocking') {
            const t = kit.make(pickTower(kit, i));
            t.rotation.y = Math.floor(rnd01(i * 5.3) * 4) * (Math.PI / 2);
            prop.add(t);
            const anchor = t.getObjectByName('smoke');
            if (anchor) chimneySmoke(t, anchor.position, i);
          } else if (info.terrain === 'heavy') {
            const w = kit.make(kit.has('hero_wall') && rnd01(i * 6.1 + 3) < 0.6 ? 'hero_wall' : 'wall_arched');
            w.scale.setScalar(1.2); // ruins stand tall beside the walkers, as in the concept art
            w.rotation.y = Math.floor(rnd01(i * 2.9) * 3) * (Math.PI / 3);
            prop.add(w);
          } else if (info.terrain === 'light') {
            const c = kit.make('crate');
            c.position.set((rnd01(i) - 0.5) * 0.7, 0, (rnd01(i + 4) - 0.5) * 0.7);
            c.rotation.y = rnd01(i + 8) * 3;
            prop.add(c);
          } else if (info.terrain === 'rough') {
            const r2 = kit.make('rubble_pile');
            r2.rotation.y = rnd01(i + 2) * 6;
            prop.add(r2);
          }
          terrain.add(prop);
          i++;
        } else {
        const tile = add(terrain, hexShape, tileMats[info.terrain] as unknown as THREE.Material, [base.x, (top - 0.4) / 2, base.z], [0.97, top + 0.4, 0.97]);
        tile.userData.hex = { q, r };
        const props = new THREE.Group();
        props.position.set(base.x, 0, base.z);
        terrainProps(props, info.terrain, top, ++i);
        terrain.add(props);
        }
        sx += base.x;
        sz += base.z;
        n++;
        lo.x = Math.min(lo.x, base.x);
        lo.z = Math.min(lo.z, base.z);
        hi.x = Math.max(hi.x, base.x);
        hi.z = Math.max(hi.z, base.z);
      }
      dressTable(terrain, lo, hi, kit);
      puffs.length = 0;
      terrain.traverse((o) => o.userData[PUFF] && puffs.push(o as THREE.Mesh));
      if (builtMap !== state.map.id) {
        builtMap = state.map.id;
        // Close in on the action like the concept art, rather than showing the whole 16x12 map; the focus follows the selected walker.
        mapCentre.set(sx / n, 0, sz / n);
        mapCentre.z = lo.z + (hi.z - lo.z) * 0.3; // start on your deployment edge
        focus.copy(mapCentre);
        controls.target.copy(focus);
        camera.position.set(focus.x, 14, focus.z - 15); // row 0 (your deployment edge) faces the camera
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
        // The kit model once its parts have loaded; a pixel box until then and for any class without a model.
        const bw = walkerLib.get(w);
        let g: THREE.Object3D;
        let top = 1.3;
        if (bw) {
          g = bw.group;
          bw.setDim(w.activated);
          top = bw.height + 0.35;
          g.position.copy(p);
          g.rotation.set(0, Math.PI / 2 + (60 * w.facing * Math.PI) / 180, 0); // +Z nose -> SVG angle -60 * facing
          bw.setProne(w.prone);
          pickables.push(bw.proxy);
        } else {
          g = walkerMesh(w.side, w.size);
          g.traverse((o) => (o.castShadow = true));
          g.position.copy(p);
          g.rotation.y = Math.PI / 2 + (60 * w.facing * Math.PI) / 180;
          if (w.prone) {
            g.rotation.x = Math.PI / 2;
            g.position.y += 0.2;
          }
          g.userData.walkerId = w.id;
          if (w.activated) g.traverse((o) => ((o as THREE.Mesh).material && ((o as THREE.Mesh).material as THREE.MeshLambertMaterial).color.multiplyScalar(0.55)));
          pickables.push(g);
        }
        dynamic.add(g);
        const ringBase = bw ? bw.radius + 0.12 : 0.8;
        const ring = (colour: number, radius: number) => {
          const m = add(dynamic, hexShape, new THREE.MeshBasicMaterial({ color: colour }), [p.x, p.y + 0.02, p.z], [radius, 0.03, radius]);
          return m;
        };
        if (w.id === activeId) ring(0xf5f0d8, ringBase);
        if (w.id === selectedId) ring(0x2f9e8f, ringBase - 0.1);
        if (w.id === targetId) pulsing.push(ring(0xffd34d, ringBase - 0.05));
        for (let i = 0; i < w.overpressure; i++) add(dynamic, box, new THREE.MeshBasicMaterial({ color: 0xff8a3d }), [p.x - 0.4 + i * 0.12, p.y + top, p.z], [0.08, 0.08, 0.08]);
      }
    };
    api.current = { rebuild };
    buildTerrain();
    rebuild();
    loadBoardKit().then((k) => {
      if (!k || disposed) return;
      kit = k;
      tileLift = 0.05;
      builtMap = '';
      rebuild();
    });

    const resize = () => {
      const w = el.clientWidth;
      const h = Math.max(260, Math.round(w * 0.72));
      el.style.height = `${h}px`;
      renderer.setSize(Math.ceil(w / PIXEL), Math.ceil(h / PIXEL), false);
      composer.setSize(Math.ceil(w / PIXEL), Math.ceil(h / PIXEL));
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

    let disposed = false;
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
      sun.target.position.copy(controls.target);
      sun.position.copy(controls.target).add(sunOffset);
      controls.update();
      composer.render();
    };
    raf = requestAnimationFrame(loop);

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointerup', onUp);
      controls.dispose();
      composer.dispose();
      renderer.dispose();
      canvas.remove();
      api.current = null;
    };
  }, []);

  useEffect(() => api.current?.rebuild(), [state, highlights, selectedId, targetId, threat]);

  return <div ref={host} className="board3d" />;
}
