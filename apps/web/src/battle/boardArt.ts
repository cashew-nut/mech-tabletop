// Procedural pixel art for the 3D board: canvas textures for the flagstones and the glowing hex markers, plus the ruin props.
// Everything is drawn at low resolution and sampled with nearest-neighbour filtering to match the pixel-art look.
import * as THREE from 'three';

const rndFrom = (seed: number) => (n: number) => ((Math.sin(seed * 12.9898 + n * 78.233) * 43758.5453) % 1 + 1) % 1;

function pixelTexture(size: number, draw: (g: CanvasRenderingContext2D, size: number) => void) {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const g = canvas.getContext('2d')!;
  g.imageSmoothingEnabled = false;
  draw(g, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.magFilter = THREE.NearestFilter;
  tex.minFilter = THREE.NearestFilter;
  tex.generateMipmaps = false;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

const shade = (hex: number, k: number) => {
  const c = new THREE.Color(hex);
  c.multiplyScalar(k);
  return `#${c.getHexString()}`;
};

/** Cobbled flagstones in the given base colour, with cracks and a few chips. */
export function stoneTexture(base: number, seed: number) {
  return pixelTexture(32, (g, s) => {
    const rnd = rndFrom(seed);
    g.fillStyle = shade(base, 0.62);
    g.fillRect(0, 0, s, s);
    let n = 0;
    for (let y = 0; y < s; y += 8) {
      let x = (y / 8) % 2 ? -4 : 0;
      while (x < s) {
        const w = 8 + Math.floor(rnd(n++) * 5);
        g.fillStyle = shade(base, 0.85 + rnd(n++) * 0.35);
        g.fillRect(x + 1, y + 1, w - 1, 7);
        g.fillStyle = shade(base, 1.18);
        g.fillRect(x + 1, y + 1, w - 1, 1); // lit top edge of each stone
        x += w;
      }
    }
    g.fillStyle = shade(base, 0.4);
    for (let i = 0; i < 5; i++) g.fillRect(Math.floor(rnd(n++) * s), Math.floor(rnd(n++) * s), 1 + Math.floor(rnd(n++) * 3), 1);
  });
}

let wallTex: THREE.Texture | null = null;
/** Blocks of dressed stone, shared by towers and walls. */
function wallTexture() {
  return (wallTex ??= pixelTexture(32, (g, s) => {
    const rnd = rndFrom(7);
    g.fillStyle = '#4a4843';
    g.fillRect(0, 0, s, s);
    let n = 0;
    for (let y = 0; y < s; y += 5) {
      let x = (y / 5) % 2 ? -3 : 0;
      while (x < s) {
        const w = 6 + Math.floor(rnd(n++) * 5);
        const v = 0.8 + rnd(n++) * 0.4;
        g.fillStyle = `rgb(${Math.round(150 * v)},${Math.round(148 * v)},${Math.round(140 * v)})`;
        g.fillRect(x + 1, y + 1, w - 1, 4);
        g.fillStyle = 'rgba(255,255,255,0.18)';
        g.fillRect(x + 1, y + 1, w - 1, 1);
        x += w;
      }
    }
  }));
}

/** Soft round falloff used for the additive bloom under markers. */
let bloomTex: THREE.Texture | null = null;
export function bloomTexture() {
  if (bloomTex) return bloomTex;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 64;
  const g = canvas.getContext('2d')!;
  const grad = g.createRadialGradient(32, 32, 8, 32, 32, 32);
  grad.addColorStop(0, 'rgba(255,255,255,0.55)');
  grad.addColorStop(0.6, 'rgba(255,255,255,0.18)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  bloomTex = new THREE.CanvasTexture(canvas);
  bloomTex.colorSpace = THREE.SRGBColorSpace;
  return bloomTex;
}

export type MarkerKind = 'attack' | 'move' | 'jump' | 'smoke';
export const MARKER_HEX: Record<MarkerKind, number> = { attack: 0xff5a1f, move: 0x3aa7ff, jump: 0xf3b640, smoke: 0xe8e8e8 };
const MARKER_COLOUR: Record<MarkerKind, string> = { attack: '#ff5a1f', move: '#3aa7ff', jump: '#f3b640', smoke: '#e8e8e8' };

/**
 * A glowing pointy-top hex marker: red crosshair for attack range, blue chevrons for movement.
 * The chevrons point to the top of the texture, which the board turns to face away from the camera.
 */
export function markerTexture(kind: MarkerKind) {
  return pixelTexture(64, (g) => {
    const colour = MARKER_COLOUR[kind];
    const R = 30;
    const hexPath = (r: number) => {
      g.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = ((60 * i - 90) * Math.PI) / 180;
        g.lineTo(32 + r * Math.cos(a), 32 + r * Math.sin(a));
      }
      g.closePath();
    };
    hexPath(R);
    g.fillStyle = 'rgba(8,10,16,0.55)';
    g.fill();
    g.strokeStyle = colour;
    g.globalAlpha = 0.35;
    g.lineWidth = 7;
    hexPath(R - 3);
    g.stroke();
    g.globalAlpha = 1;
    g.lineWidth = 3;
    hexPath(R - 2);
    g.stroke();
    g.strokeStyle = colour;
    g.fillStyle = colour;
    if (kind === 'attack') {
      g.lineWidth = 3;
      g.beginPath();
      g.arc(32, 32, 10, 0, Math.PI * 2);
      g.stroke();
      for (const [x, y, w, h] of [[30, 14, 4, 8], [30, 42, 4, 8], [14, 30, 8, 4], [42, 30, 8, 4]]) g.fillRect(x, y, w, h);
      g.fillRect(31, 31, 2, 2);
    } else if (kind === 'smoke') {
      g.beginPath();
      g.arc(32, 32, 9, 0, Math.PI * 2);
      g.fill();
    } else {
      for (const dy of [-10, 6]) {
        g.beginPath();
        g.moveTo(16, 32 + dy + 12);
        g.lineTo(32, 32 + dy - 2);
        g.lineTo(48, 32 + dy + 12);
        g.lineTo(48, 32 + dy + 20);
        g.lineTo(32, 32 + dy + 6);
        g.lineTo(16, 32 + dy + 20);
        g.closePath();
        g.fill();
      }
    }
  });
}

// ---------------------------------------------------------------- props

const box = new THREE.BoxGeometry(1, 1, 1);
const mats = new Map<number, THREE.MeshLambertMaterial>();
const mat = (color: number) => {
  let m = mats.get(color);
  if (!m) mats.set(color, (m = new THREE.MeshLambertMaterial({ color })));
  return m;
};
const glow = (color: number) => new THREE.MeshBasicMaterial({ color });

type Vec3 = [number, number, number];
function add(parent: THREE.Object3D, material: THREE.Material, pos: Vec3, scale: Vec3, rotY = 0) {
  const m = new THREE.Mesh(box, material);
  m.position.set(...pos);
  m.scale.set(...scale);
  m.rotation.y = rotY;
  parent.add(m);
  return m;
}

const STONE = [0x6b6962, 0x5d5b55, 0x77746b];
const DARK = 0x14161b;

const TRIM = 0x8a877c;
const GLOW = 0xffa43a;

/** Gothic lancet window on both long faces: stone surround, stepped pointed arch, central mullion and a sill. Some glow amber from inside. */
function windows(parent: THREE.Object3D, x: number, y: number, depth: number, w = 0.16, h = 0.42, lit = false) {
  for (const s of [1, -1]) {
    const z = s * (depth / 2);
    add(parent, mat(TRIM), [x, y + 0.02, z + s * 0.012], [w + 0.1, h + 0.12, 0.03]); // surround
    add(parent, mat(TRIM), [x, y + h / 2 + 0.1, z + s * 0.012], [w * 0.75, 0.1, 0.03]); // arch steps
    add(parent, mat(TRIM), [x, y + h / 2 + 0.17, z + s * 0.012], [w * 0.35, 0.08, 0.03]);
    const fill = glow(lit ? GLOW : DARK);
    add(parent, fill, [x, y, z + s * 0.03], [w, h, 0.02]);
    add(parent, fill, [x, y + h / 2 + 0.05, z + s * 0.03], [w * 0.6, 0.12, 0.02]);
    add(parent, mat(TRIM), [x, y + 0.04, z + s * 0.045], [0.025, h + 0.1, 0.02]); // mullion
    add(parent, mat(TRIM), [x, y + h * 0.18, z + s * 0.045], [w, 0.025, 0.02]); // transom
    add(parent, mat(TRIM), [x, y - h / 2 - 0.05, z + s * 0.04], [w + 0.14, 0.05, 0.07]); // sill
  }
}

const cone = new THREE.ConeGeometry(0.5, 1, 4);
cone.rotateY(Math.PI / 4);
function spire(parent: THREE.Object3D, material: THREE.Material, pos: Vec3, width: number, height: number) {
  const m = new THREE.Mesh(cone, material);
  m.position.set(pos[0], pos[1] + height / 2, pos[2]);
  m.scale.set(width, height, width);
  parent.add(m);
}

/** A slanting flying buttress from a wall face down to the ground. */
function flyingButtress(parent: THREE.Object3D, x: number, y: number, h: number, dir: 1 | -1) {
  const m = mat(0x56544e);
  add(parent, m, [x + dir * 0.28, y - h * 0.5 + 0.12, 0], [0.16, h, 0.16]).rotation.z = -dir * 0.0;
  const arm = add(parent, m, [x + dir * 0.14, y - 0.1, 0], [0.5, 0.1, 0.14]);
  arm.rotation.z = dir * 0.45;
}

/** Puffs register themselves here so the board can animate them. */
export interface Puff {
  mesh: THREE.Mesh;
  baseY: number;
  phase: number;
  drift: number;
}
export const PUFF = 'puff';

export function smokeStack(parent: THREE.Object3D, x: number, y: number, z: number, seed: number) {
  const rnd = rndFrom(seed);
  for (let i = 0; i < 6; i++) {
    const material = new THREE.MeshLambertMaterial({ color: i % 2 ? 0x8a8d92 : 0xb4b7bb, transparent: true, depthWrite: false });
    const m = new THREE.Mesh(box, material);
    m.position.set(x, y, z);
    m.userData[PUFF] = { baseY: y, phase: i / 6, drift: 0.25 + rnd(i) * 0.3 } as Omit<Puff, 'mesh'>;
    parent.add(m);
  }
}

/** Smoke puffs plus an ember glow above a chimney, at a position in the parent's space. */
export function chimneySmoke(parent: THREE.Object3D, pos: THREE.Vector3, seed: number) {
  smokeStack(parent, pos.x, pos.y + 0.05, pos.z, seed);
  const ember = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: bloomTexture(), color: 0xff7a2a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
  ember.rotation.x = -Math.PI / 2;
  ember.position.set(pos.x, pos.y - 0.02, pos.z);
  parent.add(ember);
}

/** A gothic tower with a spire, pinnacles and buttresses; optionally a smoking chimney instead of the spire. */
export function tower(parent: THREE.Object3D, top: number, seed: number, smoking = false) {
  const rnd = rndFrom(seed);
  const g = new THREE.Group();
  const stone = new THREE.MeshLambertMaterial({ map: wallTexture(), color: STONE[Math.floor(rnd(1) * 3)] + 0x707070 });
  const dark = mat(0x4e4c47);
  const h = 1.7 + rnd(2) * 0.7;
  const y0 = top + 0.36;
  add(g, dark, [0, top + 0.12, 0], [1.15, 0.24, 1.15]); // stepped plinth
  add(g, dark, [0, top + 0.3, 0], [1.0, 0.12, 1.0]);
  add(g, stone, [0, y0 + h / 2, 0], [0.82, h, 0.82]);
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    add(g, mat(0x56544e), [sx * 0.43, y0 + h / 2, sz * 0.43], [0.14, h + 0.04, 0.14]); // corner buttresses
    add(g, mat(0x5e5c56), [sx * 0.43, y0 + h * 0.5, sz * 0.43], [0.2, 0.05, 0.2]);
  }
  for (const x of [-1, 1]) {
    add(g, mat(0x56544e), [x * 0.5, y0 + 0.35, 0], [0.2, 0.7, 0.14]); // lower side buttresses
    add(g, mat(0x56544e), [x * 0.46, y0 + 0.8, 0], [0.12, 0.2, 0.14]);
  }
  const levels = Math.max(2, Math.floor(h / 0.75));
  for (let i = 0; i < levels; i++) {
    const y = y0 + 0.5 + i * 0.62;
    windows(g, 0, y, 0.82, 0.16, 0.34, rnd(10 + i) > 0.65);
    add(g, mat(TRIM), [0, y + 0.32, 0], [0.9, 0.05, 0.9]); // string course
    for (const s of [1, -1]) add(g, glow(DARK), [s * 0.41, y, 0], [0.02, 0.3, 0.16]); // side slits
  }
  add(g, mat(0x5e5c56), [0, y0 + h, 0], [0.96, 0.1, 0.96]); // corbel table
  for (const [x, z] of [[-0.42, -0.42], [0.42, -0.42], [-0.42, 0.42], [0.42, 0.42]]) {
    add(g, mat(0x5e5c56), [x, y0 + h + 0.2, z], [0.16, 0.3, 0.16]); // pinnacles
    spire(g, mat(0x3a3834), [x, y0 + h + 0.35, z], 0.2, 0.34);
  }
  if (smoking) {
    add(g, mat(0x3f3d39), [0.25, y0 + h + 0.55, 0.25], [0.24, 0.9, 0.24]); // chimney
    add(g, mat(0x2e2c29), [0.25, y0 + h + 1.03, 0.25], [0.3, 0.08, 0.3]);
    add(g, glow(0xff8a3d), [0.25, y0 + h + 1.08, 0.25], [0.18, 0.04, 0.18]);
    smokeStack(g, 0.25, y0 + h + 1.15, 0.25, seed);
    const ember = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: bloomTexture(), color: 0xff7a2a, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    ember.rotation.x = -Math.PI / 2;
    ember.position.set(0.25, y0 + h + 1.1, 0.25);
    g.add(ember); // cheap ember glow instead of a real light
  } else {
    add(g, mat(0x4a4843), [0, y0 + h + 0.35, 0], [0.62, 0.5, 0.62]); // belfry
    windows(g, 0, y0 + h + 0.35, 0.62, 0.12, 0.22);
    spire(g, mat(0x3a3834), [0, y0 + h + 0.6, 0], 0.7, 1.15);
    add(g, mat(0x2c2a27), [0, y0 + h + 1.9, 0], [0.04, 0.3, 0.04]); // finial
  }
  g.rotation.y = (rnd(3) - 0.5) * 0.4;
  parent.add(g);
}

/** A broken ruin wall with arched windows and a ragged top. */
export function ruinWall(parent: THREE.Object3D, top: number, seed: number, length = 1.5, rotY = 0) {
  const rnd = rndFrom(seed);
  const g = new THREE.Group();
  const stone = new THREE.MeshLambertMaterial({ map: wallTexture(), color: STONE[Math.floor(rnd(1) * 3)] + 0x707070 });
  const segs = Math.max(2, Math.round(length / 0.5));
  const segW = length / segs;
  for (let i = 0; i < segs; i++) {
    const h = 0.7 + rnd(i + 4) * 0.9;
    const x = -length / 2 + segW * (i + 0.5);
    add(g, stone, [x, top + h / 2, 0], [segW, h, 0.3]);
    if (h > 1.05) windows(g, x, top + h * 0.5, 0.3, 0.14, 0.34);
    add(g, mat(0x56544e), [x - segW / 2, top + h / 2 + 0.05, 0.1], [0.12, h + 0.1, 0.16]); // pier
    if (h > 1.2 && i % 2 === 0) flyingButtress(g, x, top + h, h, i % 4 === 0 ? 1 : -1);
  }
  add(g, mat(0x4e4c47), [0, top + 0.08, 0], [length + 0.1, 0.16, 0.42]);
  for (let i = 0; i < 3; i++) add(g, stone, [(rnd(i + 20) - 0.5) * length, top + 0.1, (rnd(i + 30) - 0.5) * 0.9], [0.2, 0.18, 0.2], rnd(i)); // fallen blocks
  g.rotation.y = rotY;
  parent.add(g);
}

export function rubble(parent: THREE.Object3D, top: number, seed: number, count = 5, spread = 1) {
  const rnd = rndFrom(seed);
  for (let i = 0; i < count; i++) {
    const s = 0.14 + rnd(i) * 0.2;
    add(parent, mat(STONE[i % 3]), [(rnd(i + 9) - 0.5) * spread, top + s / 2, (rnd(i + 19) - 0.5) * spread], [s * 1.3, s, s], rnd(i + 5) * 3);
  }
}

export function crate(parent: THREE.Object3D, pos: Vec3, size = 0.45, rotY = 0) {
  const g = new THREE.Group();
  g.position.set(...pos);
  g.rotation.y = rotY;
  add(g, mat(0x7a5632), [0, size / 2, 0], [size, size, size]);
  for (const s of [-1, 1]) {
    add(g, mat(0x4a3320), [s * size * 0.46, size / 2, 0], [size * 0.1, size * 1.02, size * 1.02]);
    add(g, mat(0x4a3320), [0, size / 2, s * size * 0.46], [size * 1.02, size * 1.02, size * 0.1]);
  }
  parent.add(g);
}

export function die(parent: THREE.Object3D, pos: Vec3, colour: number, rotY = 0) {
  const g = new THREE.Group();
  g.position.set(...pos);
  g.rotation.y = rotY;
  add(g, mat(colour), [0, 0.17, 0], [0.34, 0.34, 0.34]);
  const pip = colour === 0xf1ede2 ? 0x1b1b1b : 0xf1ede2;
  for (const [x, z] of [[-0.08, -0.08], [0.08, 0.08], [0, 0]]) add(g, glow(pip), [x, 0.345, z], [0.06, 0.01, 0.06]);
  parent.add(g);
}

/** A flat sheet of paper (rules card) lying on the table. */
export function card(parent: THREE.Object3D, pos: Vec3, rotY = 0) {
  const g = new THREE.Group();
  g.position.set(...pos);
  g.rotation.y = rotY;
  add(g, mat(0xd9cfb4), [0, 0.03, 0], [1.5, 0.05, 1.05]);
  for (let i = 0; i < 5; i++) add(g, glow(0x3a352c), [-0.1, 0.06, -0.35 + i * 0.16], [1.0 - (i % 2) * 0.3, 0.01, 0.05]);
  add(g, glow(0x7a1c1c), [0.52, 0.06, -0.3], [0.25, 0.01, 0.25]);
  parent.add(g);
}

// ---------------------------------------------------------------- wrecks, banners, tower footings

const hexPrism = new THREE.CylinderGeometry(1, 1, 1, 6, 1);
const rock = new THREE.IcosahedronGeometry(0.5, 0);
const tube = new THREE.CylinderGeometry(0.5, 0.5, 1, 10, 1);
const emberMat = new THREE.MeshBasicMaterial({ color: 0xff7a2a });
const emberGlow = () => emberMat;
function shape(parent: THREE.Object3D, geo: THREE.BufferGeometry, material: THREE.Material, pos: Vec3, scale: Vec3, rot: Vec3 = [0, 0, 0]) {
  const m = new THREE.Mesh(geo, material);
  m.position.set(...pos);
  m.scale.set(...scale);
  m.rotation.set(...rot);
  m.castShadow = true;
  m.receiveShadow = true;
  parent.add(m);
  return m;
}

const wreckMats = new Map<string, THREE.MeshStandardMaterial>();
/** Worn metal for the wreck: lit by the board's environment like the walkers, so the heap reads as armour and not as black boxes. */
const metal = (color: number, roughness = 0.55, metalness = 0.7) => {
  const key = `${color}|${roughness}|${metalness}`;
  let m = wreckMats.get(key);
  if (!m) wreckMats.set(key, (m = new THREE.MeshStandardMaterial({ color, roughness, metalness })));
  return m;
};
const scorchGeo = new THREE.CircleGeometry(0.72, 24);
const scorchMat = new THREE.MeshBasicMaterial({ color: 0x0d0c0b, transparent: true, opacity: 0.7, depthWrite: false });

/** What a destroyed walker leaves in its hex: a scorched, heaped hulk about as big as a hex and a head shorter than the walker
 * stood. `size` is the walker's chassis Size (1 to 4ish) and scales the heap; `sideColour` tints the surviving armour plates.
 * The group's origin is the hex centre on the ground. Wrecks block movement and sight, so they need real height. */
export function wreck(parent: THREE.Object3D, seed: number, size: number, sideColour: number) {
  const rnd = rndFrom(seed * 3.7 + 11);
  const g = new THREE.Group();
  const k = 0.82 + 0.09 * Math.min(4, Math.max(1, size)); // 0.91 to 1.18
  g.scale.setScalar(k);
  g.rotation.y = rnd(1) * Math.PI * 2;
  const iron = metal(0x44464b, 0.62, 0.65);
  const dark = metal(0x1f2023, 0.75, 0.5);
  const rust = metal(0x5a3a26, 0.85, 0.25);
  const plate = metal(new THREE.Color(sideColour).multiplyScalar(0.75).getHex(), 0.55, 0.4);
  const scorch = new THREE.Mesh(scorchGeo, scorchMat);
  scorch.rotation.x = -Math.PI / 2;
  scorch.position.y = 0.012;
  g.add(scorch);
  // Toppled torso with its furnace barrel torn out, resting on the heap.
  shape(g, box, iron, [-0.06, 0.3, 0.02], [0.78, 0.48, 0.58], [0.32, 0.25, 0.5]);
  shape(g, box, dark, [-0.16, 0.56, 0.0], [0.5, 0.14, 0.4], [0.32, 0.25, 0.5]); // shoulder yoke
  shape(g, box, plate, [0.0, 0.36, 0.36], [0.5, 0.32, 0.05], [0.32, 0.25, 0.5]); // surviving chest plate in the faction's colour
  shape(g, tube, rust, [0.34, 0.2, -0.28], [0.3, 0.72, 0.3], [0, 0, Math.PI / 2 - 0.2]); // furnace barrel on its side
  // A leg thrust skyward and a snapped arm: they give the heap its silhouette from the camera.
  shape(g, box, iron, [-0.38, 0.62, -0.14], [0.2, 0.95, 0.24], [0.15, 0.4, 0.5]);
  shape(g, box, dark, [-0.55, 0.34, -0.12], [0.3, 0.14, 0.32], [0.1, 0.4, 0.5]); // foot
  shape(g, tube, iron, [0.3, 0.52, 0.2], [0.17, 0.85, 0.17], [0.9, 0.2, -0.6]);
  shape(g, box, plate, [0.12, 0.7, 0.4], [0.44, 0.1, 0.34], [0.5, 0.3, -0.5]); // pauldron half
  for (let i = 0; i < 10; i++) { // scattered plates and chunks
    const a = rnd(i + 5) * Math.PI * 2;
    const r = 0.3 + rnd(i + 15) * 0.38;
    const s = 0.12 + rnd(i + 25) * 0.16;
    shape(g, i % 3 === 0 ? box : rock, i % 2 ? iron : i % 3 === 0 ? plate : rust, [Math.cos(a) * r, s * 0.4, Math.sin(a) * r], [s * 1.6, s * 0.7, s * 1.2], [rnd(i) * 2, rnd(i + 3) * 3, rnd(i + 8) * 2]);
  }
  for (let i = 0; i < 4; i++) shape(g, rock, emberGlow(), [(rnd(i + 40) - 0.5) * 0.7, 0.07 + rnd(i + 50) * 0.1, (rnd(i + 60) - 0.5) * 0.7], [0.06, 0.04, 0.06]); // glowing embers
  const glowPlane = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: bloomTexture(), color: 0xff6a1f, transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false }));
  glowPlane.rotation.x = -Math.PI / 2;
  glowPlane.position.y = 0.05;
  glowPlane.scale.setScalar(1.2);
  g.add(glowPlane);
  parent.add(g);
  return g;
}

let bannerTex: THREE.Texture | null = null;
/** The charter banner: a deep red swallow-tailed cloth with a gold gear-and-boiler seal, drawn once and alpha-cut. */
function bannerTexture() {
  if (bannerTex) return bannerTex;
  const w = 64;
  const h = 128;
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const g = canvas.getContext('2d')!;
  g.clearRect(0, 0, w, h);
  g.beginPath(); // swallow-tail outline
  g.moveTo(2, 0); g.lineTo(w - 2, 0); g.lineTo(w - 2, h - 2); g.lineTo(w / 2, h - 34); g.lineTo(2, h - 2); g.closePath();
  const cloth = g.createLinearGradient(0, 0, 0, h);
  cloth.addColorStop(0, '#8c1e1c');
  cloth.addColorStop(1, '#5a1010');
  g.fillStyle = cloth;
  g.fill();
  g.lineWidth = 3;
  g.strokeStyle = '#d4a956';
  g.stroke();
  g.strokeStyle = '#d4a956'; // inner border
  g.lineWidth = 1;
  g.strokeRect(8, 6, w - 16, 62);
  g.fillStyle = '#d4a956'; // seal: a cogged ring around a boiler dome
  g.beginPath(); g.arc(w / 2, 38, 15, 0, Math.PI * 2); g.fill();
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    g.fillRect(w / 2 + Math.cos(a) * 15 - 2.5, 38 + Math.sin(a) * 15 - 2.5, 5, 5);
  }
  g.fillStyle = '#6a1412';
  g.beginPath(); g.arc(w / 2, 38, 10, 0, Math.PI * 2); g.fill();
  g.fillStyle = '#d4a956';
  g.beginPath(); g.arc(w / 2, 40, 6, Math.PI, 0); g.fill();
  g.fillRect(w / 2 - 6, 40, 12, 4);
  g.fillRect(w / 2 - 1, 28, 2, 6);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return (bannerTex = tex);
}

export const BANNER_CLOTH = 'bannerCloth';
const bannerBrass = new THREE.MeshStandardMaterial({ color: 0xc9a04a, roughness: 0.35, metalness: 0.85 });
/** An objective marker sized to stand with the walkers: a brass pole about two thirds of a Paladin's height on a stepped plinth,
 * with a hanging charter banner that ripples (the board animates the cloth through its BANNER_CLOTH userData). */
export function objectiveBanner(parent: THREE.Object3D, seed: number) {
  const g = new THREE.Group();
  g.rotation.y = Math.PI + (rndFrom(seed)(1) - 0.5) * 0.3; // the cloth faces the camera at the start
  const height = 2.5;
  shape(g, hexPrism, mat(0x3b3a37), [0, 0.04, 0], [0.34, 0.08, 0.34]); // plinth steps
  shape(g, hexPrism, bannerBrass, [0, 0.11, 0], [0.22, 0.06, 0.22]);
  shape(g, tube, bannerBrass, [0, height / 2 + 0.1, 0], [0.08, height, 0.08]); // pole
  shape(g, rock, bannerBrass, [0, height + 0.18, 0], [0.22, 0.28, 0.22]); // finial
  shape(g, tube, bannerBrass, [0.3, height - 0.12, 0], [0.05, 0.64, 0.05], [0, 0, Math.PI / 2]); // cross-bar
  const geo = new THREE.PlaneGeometry(0.5, 1.15, 5, 10);
  geo.translate(0, -0.575, 0);
  const cloth = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ map: bannerTexture(), alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.9, metalness: 0 }));
  cloth.position.set(0.32, height - 0.17, 0);
  cloth.castShadow = true;
  cloth.userData[BANNER_CLOTH] = { base: Float32Array.from(geo.attributes.position.array), phase: rndFrom(seed)(2) * 6 };
  g.add(cloth);
  parent.add(g);
  return g;
}

/** Ripple a banner's cloth: the free edge swings most, the hem lags, and the top edge stays on the bar. */
export function rippleBanner(cloth: THREE.Mesh, t: number) {
  const d = cloth.userData[BANNER_CLOTH] as { base: Float32Array; phase: number };
  const pos = cloth.geometry.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const y = d.base[i * 3 + 1];
    const hang = Math.min(1, -y / 1.15); // 0 at the bar, 1 at the hem
    pos.setZ(i, Math.sin(t / 380 + d.phase + hang * 3.2 + d.base[i * 3] * 2.5) * 0.07 * hang);
  }
  pos.needsUpdate = true;
}

/** A buttress: sloped on its outer face, a stepped cap on top, `depth` out from the wall at its foot and `width` across. Built
 * in a local frame where +X is outward from the wall and the wall face is at x = 0 (the block sinks 0.1 into the wall). */
function buttressGeometry(depth: number, width: number, height: number) {
  const s = new THREE.Shape();
  s.moveTo(-0.1, 0);
  s.lineTo(depth, 0);
  s.lineTo(depth, height * 0.18); // vertical lower course
  s.lineTo(depth * 0.7, height * 0.34); // set-off
  s.lineTo(depth * 0.7, height * 0.5);
  s.lineTo(depth * 0.4, height * 0.78); // second set-off, then a short slope to the cap
  s.lineTo(depth * 0.4, height);
  s.lineTo(-0.1, height);
  s.closePath();
  const geo = new THREE.ExtrudeGeometry(s, { depth: width, bevelEnabled: false });
  geo.translate(0, 0, -width / 2);
  return geo;
}

/** A battered stone footing, and optionally four chunky buttresses, to wrap the base of a Meshy tower whose own buttresses came
 * out as ragged paper-thin fins. `apothem` is the half-width of the tower's footprint; `sides` is 8 for the octagonal tower, 16 for
 * the square one (whose Meshy footprint is turned a few degrees, so a round footing hides it best). Everything stays inside the hex (flats at 0.84) and is symmetrical under 90 degree turns, so the board can
 * spin the whole piece. */
export function towerFooting(material: THREE.Material, apothem: number, sides: 8 | 16, buttresses = true) {
  const g = new THREE.Group();
  const flat = 0.78; // footing half-width at the ground, to the flats
  const baseR = flat / Math.cos(Math.PI / sides);
  const plinth = new THREE.Mesh(new THREE.CylinderGeometry(baseR * 0.9, baseR, 0.34, sides, 1), material);
  plinth.rotation.y = Math.PI / sides; // flats towards +X/+Z
  plinth.position.y = 0.17;
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(baseR * 0.84, baseR * 0.9, 0.1, sides, 1), material);
  cap.rotation.y = Math.PI / sides;
  cap.position.y = 0.39;
  g.add(plinth, cap);
  if (buttresses) {
    const geo = buttressGeometry(0.83 - apothem, 0.4, 1.3);
    for (let i = 0; i < 4; i++) {
      const m = new THREE.Mesh(geo, material);
      const a = (i * Math.PI) / 2;
      m.rotation.y = a; // turns +X (outward) toward -Z for a quarter turn
      m.position.set(Math.cos(a) * apothem, 0.34, -Math.sin(a) * apothem);
      g.add(m);
    }
  }
  g.traverse((o) => {
    o.castShadow = true;
    o.receiveShadow = true;
  });
  return g;
}
