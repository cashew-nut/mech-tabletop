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

export type MarkerKind = 'attack' | 'move' | 'jump' | 'smoke';
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

/** Pointed-arch window (dark recess) on the +Z and -Z faces of a wall or tower segment. */
function windows(parent: THREE.Object3D, x: number, y: number, depth: number, w = 0.16, h = 0.42) {
  for (const s of [1, -1]) {
    add(parent, glow(DARK), [x, y, s * (depth / 2 + 0.005)], [w, h, 0.02]);
    add(parent, glow(DARK), [x, y + h / 2 + 0.05, s * (depth / 2 + 0.005)], [w * 0.55, 0.12, 0.02]);
    add(parent, mat(0x8a877c), [x, y - h / 2 - 0.03, s * (depth / 2 + 0.02)], [w + 0.1, 0.05, 0.05]); // sill
  }
}

/** A gothic tower, optionally with a smoking chimney stack and an ember glow. */
export function tower(parent: THREE.Object3D, top: number, seed: number, smoking = false) {
  const rnd = rndFrom(seed);
  const g = new THREE.Group();
  const stone = mat(STONE[Math.floor(rnd(1) * 3)]);
  const h = 1.7 + rnd(2) * 0.7;
  add(g, mat(0x4e4c47), [0, top + 0.18, 0], [1.05, 0.36, 1.05]); // plinth
  add(g, stone, [0, top + 0.36 + h / 2, 0], [0.82, h, 0.82]);
  for (const x of [-0.36, 0.36]) add(g, mat(0x56544e), [x, top + 0.36 + h / 2, 0], [0.12, h + 0.02, 0.86]); // buttresses
  const levels = Math.max(2, Math.floor(h / 0.7));
  for (let i = 0; i < levels; i++) windows(g, 0, top + 0.75 + i * 0.62, 0.82);
  for (const [x, z] of [[-0.4, -0.4], [0.4, -0.4], [-0.4, 0.4], [0.4, 0.4]]) add(g, stone, [x, top + 0.36 + h + 0.18, z], [0.16, 0.36, 0.16]); // battlements
  if (smoking) {
    add(g, mat(0x3f3d39), [0.28, top + 0.36 + h + 0.5, 0.28], [0.22, 0.9, 0.22]); // chimney
    add(g, glow(0xff8a3d), [0.28, top + 0.36 + h + 0.97, 0.28], [0.16, 0.06, 0.16]);
    for (let i = 0; i < 5; i++) add(g, mat(i % 2 ? 0x8a8d92 : 0xa6a9ad), [0.3 + i * 0.07, top + 0.36 + h + 1.2 + i * 0.28, 0.28 + i * 0.03], [0.22 + i * 0.07, 0.22, 0.22 + i * 0.07]);
  } else {
    add(g, stone, [0, top + 0.36 + h + 0.55, 0], [0.5, 0.5, 0.5]); // spire base
    add(g, mat(0x44423d), [0, top + 0.36 + h + 0.95, 0], [0.3, 0.4, 0.3]);
    add(g, mat(0x3a3834), [0, top + 0.36 + h + 1.3, 0], [0.12, 0.35, 0.12]);
  }
  g.rotation.y = (rnd(3) - 0.5) * 0.4;
  parent.add(g);
}

/** A broken ruin wall with arched windows and a ragged top. */
export function ruinWall(parent: THREE.Object3D, top: number, seed: number, length = 1.5, rotY = 0) {
  const rnd = rndFrom(seed);
  const g = new THREE.Group();
  const stone = mat(STONE[Math.floor(rnd(1) * 3)]);
  const segs = Math.max(2, Math.round(length / 0.5));
  const segW = length / segs;
  for (let i = 0; i < segs; i++) {
    const h = 0.7 + rnd(i + 4) * 0.9;
    const x = -length / 2 + segW * (i + 0.5);
    add(g, stone, [x, top + h / 2, 0], [segW, h, 0.3]);
    if (h > 1.1) windows(g, x, top + h * 0.55, 0.3, 0.14, 0.36);
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
