// Stylised pixel war-walkers for the 3D board. Each walker is built in code from boxes and tapered prisms, one bold
// silhouette per class and one palette and motif per faction (see docs/concept-art):
//   Iron Covenant: black, gold and crimson gothic knights with crested helms, tabards, banners and cathedral spires.
//   Ashen Foundries: rust and signal-red industrial hulks with stencilled hull numbers, smokestacks and furnace chests.
//   Reliquary: bone-white and gold relic walkers with hoods, spiked halos, long limbs, robes and teal soul-glow.
// Walkers face +Z. Limbs hang from pivot groups listed in userData.parts so the animation stage can swing them. All the
// boxes on one pivot are merged into at most three meshes (lit body, unlit glow, back-face ink outline), so a walker is
// a couple of dozen draw calls however detailed it gets. The merged geometry is cached per build, so rebuilding the
// board every state change reuses it.
import * as THREE from 'three';
import type { WalkerState } from '@brass-charter/rules';

export interface WalkerParts {
  root: THREE.Group;
  torso: THREE.Group;
  head: THREE.Group;
  armL: THREE.Group;
  armR: THREE.Group;
  legL: THREE.Group;
  legR: THREE.Group;
  /** Muzzle point of the main weapon on each arm, for flashes and projectiles. */
  muzzleL: THREE.Object3D;
  muzzleR: THREE.Object3D;
}

/** A slow idle motion for an ornament (halo, lantern, drone): spin about an axis and/or bob up and down. */
export interface WalkerSpinner {
  object: THREE.Object3D;
  spin: number;
  bob: number;
  axis: 'y' | 'z';
}

export const SIDE_COLOUR = [0x2d6e9c, 0x9c3a26];

type V3 = [number, number, number];
type WalkerInput = Pick<WalkerState, 'chassis' | 'size' | 'side' | 'items' | 'destroyedLocations' | 'prone'>;

interface Palette {
  hull: number; // main armour
  hull2: number; // raised plates, a step lighter or darker than the hull
  trim: number; // gold or brass edging
  trimDk: number;
  dark: number; // joints, under-structure
  metal: number; // gun metal
  cloth: number; // tabards, banners, robes
  clothDk: number;
  accent: number; // a second signature colour: Covenant ivory, Foundries signal red, Reliquary teal enamel
  glow: number;
  steel: number; // blade edges
  hazard: number;
}

const FACTION: Record<string, Palette> = {
  covenant: {
    hull: 0x302f3a, hull2: 0x4c4b58, trim: 0xe3b65a, trimDk: 0x9a7432, dark: 0x131218, metal: 0x5e5c68,
    cloth: 0xb01f33, clothDk: 0x701525, accent: 0xefe6d2, glow: 0xffc85a, steel: 0xc9ced8, hazard: 0xe0b45a,
  },
  foundries: {
    hull: 0xa4502b, hull2: 0x74371f, trim: 0xd09442, trimDk: 0x8a5a2a, dark: 0x2a2421, metal: 0x4f4743,
    cloth: 0xcc3420, clothDk: 0x8a2416, accent: 0xf1e6cc, glow: 0xff6a1a, steel: 0xb9b2a8, hazard: 0xf0c02c,
  },
  reliquary: {
    hull: 0xebe2c8, hull2: 0xc8bb98, trim: 0xd8a84c, trimDk: 0x8e6a2c, dark: 0x25242c, metal: 0x3b3c46,
    cloth: 0x2e6a66, clothDk: 0x1d4442, accent: 0x2c8a83, glow: 0x52f6e2, steel: 0xe4d6aa, hazard: 0xd8a84c,
  },
};

const INK = 0x0c0a0d;
/** Ink outline thickness in world units: about one low-res pixel at the board's default camera. */
const OUTLINE = 0.026;

// ---------------------------------------------------------------------------------------------------------------------
// Kit: collects primitives for one pivot, then bakes them into merged geometry.

interface PrimOpts {
  rot?: V3;
  /** Scale of the top face (+Y end) relative to the bottom: one number or [x, z]. 0 makes a point. */
  taper?: number | [number, number];
  /** Offset of the top face in x and z, for leaning shapes. */
  shift?: [number, number];
  glow?: boolean;
  /** Draw the ink outline (default: yes for lit parts, no for glow). */
  line?: boolean;
}

interface Prim {
  m: THREE.Matrix4;
  size: V3;
  taper: [number, number];
  shift: [number, number];
  color: number;
  glow: boolean;
  line: boolean;
}

const tmpQ = new THREE.Quaternion();
const tmpE = new THREE.Euler();
const UP = new THREE.Vector3(0, 1, 0);

function compose(pos: V3, rot: V3 = [0, 0, 0], scale: V3 = [1, 1, 1]) {
  return new THREE.Matrix4().compose(new THREE.Vector3(...pos), tmpQ.setFromEuler(tmpE.set(...rot)).clone(), new THREE.Vector3(...scale));
}

class Kit {
  prims: Prim[] = [];
  private stack: THREE.Matrix4[] = [new THREE.Matrix4()];

  private get top() {
    return this.stack[this.stack.length - 1];
  }

  push(pos: V3 = [0, 0, 0], rot: V3 = [0, 0, 0], scale: V3 = [1, 1, 1]) {
    this.stack.push(this.top.clone().multiply(compose(pos, rot, scale)));
    return this;
  }

  pop() {
    this.stack.pop();
    return this;
  }

  at(pos: V3, rot: V3, fn: () => void) {
    this.push(pos, rot);
    fn();
    this.pop();
  }

  private add(local: THREE.Matrix4, color: number, size: V3, o: PrimOpts) {
    const t = o.taper ?? 1;
    this.prims.push({
      m: this.top.clone().multiply(local),
      size,
      taper: typeof t === 'number' ? [t, t] : t,
      shift: o.shift ?? [0, 0],
      color,
      glow: !!o.glow,
      line: o.line ?? !o.glow,
    });
  }

  box(color: number, size: V3, pos: V3, o: PrimOpts = {}) {
    this.add(compose(pos, o.rot), color, size, o);
  }

  /** A box running from a to b (its local +Y), w wide and d deep; taper narrows the b end. */
  seg(color: number, a: V3, b: V3, w: number, d: number, o: PrimOpts = {}) {
    const A = new THREE.Vector3(...a);
    const B = new THREE.Vector3(...b);
    const dir = B.clone().sub(A);
    const len = dir.length();
    const q = new THREE.Quaternion().setFromUnitVectors(UP, dir.normalize());
    if (o.rot) q.multiply(tmpQ.setFromEuler(tmpE.set(...o.rot)));
    const local = new THREE.Matrix4().compose(A.add(B).multiplyScalar(0.5), q, new THREE.Vector3(1, 1, 1));
    this.add(local, color, [w, len, d], { ...o, rot: undefined });
  }

  /** A point in this kit's pivot space, through the current transform stack. */
  point(p: V3) {
    return new THREE.Vector3(...p).applyMatrix4(this.top);
  }
}

// Corner i of a unit prim: bit 0 is +x, bit 1 is +y (top), bit 2 is +z.
const FACES = [
  [1, 3, 7, 5],
  [0, 4, 6, 2],
  [2, 6, 7, 3],
  [0, 1, 5, 4],
  [4, 5, 7, 6],
  [0, 2, 3, 1],
];

function corners(p: Prim, grow: number) {
  const [w, h, d] = p.size;
  const out: THREE.Vector3[] = [];
  for (let i = 0; i < 8; i++) {
    const top = (i & 2) !== 0;
    const sx = i & 1 ? 1 : -1;
    const sz = i & 4 ? 1 : -1;
    const hx = (w / 2) * (top ? p.taper[0] : 1) + grow;
    const hz = (d / 2) * (top ? p.taper[1] : 1) + grow;
    const v = new THREE.Vector3(sx * hx + (top ? p.shift[0] : 0), (top ? 1 : -1) * (h / 2 + grow), sz * hz + (top ? p.shift[1] : 0));
    out.push(v.applyMatrix4(p.m));
  }
  return out;
}

const col = new THREE.Color();

function bakeGeometry(prims: Prim[], mode: 'solid' | 'glow' | 'line', grow: number) {
  const pos: number[] = [];
  const nor: number[] = [];
  const clr: number[] = [];
  const a = new THREE.Vector3();
  const b = new THREE.Vector3();
  const n = new THREE.Vector3();
  const fc = new THREE.Vector3();
  for (const p of prims) {
    if (mode === 'solid' && p.glow) continue;
    if (mode === 'glow' && !p.glow) continue;
    if (mode === 'line' && !p.line) continue;
    const c = corners(p, mode === 'line' ? grow : 0);
    const centre = c.reduce((s, v) => s.add(v), new THREE.Vector3()).multiplyScalar(1 / 8);
    for (const f of FACES) {
      const q = f.map((i) => c[i]);
      a.subVectors(q[1], q[0]);
      b.subVectors(q[2], q[0]);
      n.crossVectors(a, b);
      if (n.lengthSq() < 1e-12) {
        a.subVectors(q[2], q[0]);
        b.subVectors(q[3], q[0]);
        n.crossVectors(a, b);
      }
      if (n.lengthSq() < 1e-12) continue; // a face collapsed to a point
      n.normalize();
      fc.copy(q[0]).add(q[1]).add(q[2]).add(q[3]).multiplyScalar(0.25).sub(centre);
      const order = fc.dot(n) < 0 ? [0, 3, 2, 0, 2, 1] : [0, 1, 2, 0, 2, 3];
      if (fc.dot(n) < 0) n.negate();
      // Baked pixel-art shading: tops a touch brighter, undersides darker, on top of the scene lighting.
      const shade = mode === 'solid' ? (n.y >= 0 ? 1 + 0.12 * n.y : 1 + 0.38 * n.y) : 1;
      col.setHex(p.color).multiplyScalar(shade);
      for (const i of order) {
        pos.push(q[i].x, q[i].y, q[i].z);
        nor.push(n.x, n.y, n.z);
        clr.push(col.r, col.g, col.b);
      }
    }
  }
  if (!pos.length) return null;
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  if (mode !== 'line') g.setAttribute('color', new THREE.Float32BufferAttribute(clr, 3));
  g.computeBoundingSphere();
  return g;
}

const SHARED_MATS = {
  solid: new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true }),
  glow: new THREE.MeshBasicMaterial({ vertexColors: true }),
  line: new THREE.MeshBasicMaterial({ color: INK, side: THREE.BackSide }),
};

function bake(group: THREE.Object3D, kit: Kit, grow: number) {
  for (const mode of ['line', 'solid', 'glow'] as const) {
    const g = bakeGeometry(kit.prims, mode, grow);
    if (!g) continue;
    const m = new THREE.Mesh(g, SHARED_MATS[mode]);
    m.userData.kind = mode;
    group.add(m);
  }
}

// ---------------------------------------------------------------------------------------------------------------------
// Shared motifs.

const DIGITS: Record<string, string[]> = {
  '0': ['111', '101', '101', '101', '111'],
  '1': ['010', '110', '010', '010', '111'],
  '2': ['111', '001', '111', '100', '111'],
  '3': ['111', '001', '011', '001', '111'],
  '4': ['101', '101', '111', '001', '001'],
  '5': ['111', '100', '111', '001', '111'],
  '7': ['111', '001', '010', '010', '010'],
  '9': ['111', '101', '111', '001', '111'],
};

/** Stencilled hull number on a plane facing +Z, centred on pos. */
function stencil(k: Kit, text: string, color: number, pos: V3, px: number) {
  const w = text.length * 4 - 1;
  text.split('').forEach((ch, ci) => {
    DIGITS[ch]?.forEach((row, ry) => {
      row.split('').forEach((bit, rx) => {
        if (bit !== '1') return;
        const x = pos[0] + (ci * 4 + rx - (w - 1) / 2) * px;
        const y = pos[1] + (2 - ry) * px;
        k.box(color, [px, px, 0.012], [x, y, pos[2]], { line: false });
      });
    });
  });
}

/** Alternating hazard stripes along x on a plane facing +Z. */
function hazard(k: Kit, P: Palette, w: number, h: number, pos: V3, n = 5) {
  const sw = w / n;
  for (let i = 0; i < n; i++) k.box(i % 2 ? P.dark : P.hazard, [sw, h, 0.014], [pos[0] - w / 2 + sw * (i + 0.5), pos[1], pos[2]], { line: false, rot: [0, 0, 0.0] });
}

function rivets(k: Kit, color: number, pts: V3[], r = 0.022) {
  for (const p of pts) k.box(color, [r, r, r], p, { line: false });
}

/** A spiked ring in the XY plane, centred on the origin: the Reliquary halo. */
function halo(k: Kit, P: Palette, r: number, spikes: number, spikeLen: number, thick: number, gems = 4) {
  const n = 16;
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const len = 2 * r * Math.tan(Math.PI / n) + thick * 0.4;
    k.box(P.trim, [len, thick, thick * 0.8], [Math.cos(a) * r, Math.sin(a) * r, 0], { rot: [0, 0, a + Math.PI / 2] });
  }
  for (let i = 0; i < spikes; i++) {
    const a = (i / spikes) * Math.PI * 2 + Math.PI / 2;
    const long = i % 2 === 0 ? 1 : 0.55;
    const r0 = r + thick * 0.3;
    const r1 = r + spikeLen * long;
    k.seg(P.trim, [Math.cos(a) * r0, Math.sin(a) * r0, 0], [Math.cos(a) * r1, Math.sin(a) * r1, 0], thick * 0.9, thick * 0.6, { taper: 0 });
  }
  for (let i = 0; i < gems; i++) {
    const a = (i / gems) * Math.PI * 2 + Math.PI / 4;
    k.box(P.glow, [thick * 1.2, thick * 1.2, thick * 1.1], [Math.cos(a) * r, Math.sin(a) * r, 0], { glow: true, rot: [0, 0, Math.PI / 4] });
  }
  // inner cross spokes, faint
  for (const a of [0, Math.PI / 2]) k.box(P.trimDk, [thick * 0.35, r * 2, thick * 0.35], [0, 0, -0.01], { rot: [0, 0, a], line: false });
}

/** A gothic spire: a square shaft, a lit lancet window, a gold-capped pyramid. y is the base. */
function spire(k: Kit, P: Palette, x: number, y: number, z: number, h: number, w: number) {
  k.box(P.hull, [w, h * 0.62, w], [x, y + h * 0.31, z]);
  k.box(P.trim, [w * 1.25, w * 0.35, w * 1.25], [x, y + h * 0.62, z]);
  k.box(P.glow, [w * 0.35, h * 0.24, 0.01], [x, y + h * 0.4, z + w / 2 + 0.006], { glow: true });
  k.box(P.glow, [w * 0.35, h * 0.24, 0.01], [x, y + h * 0.4, z - w / 2 - 0.006], { glow: true });
  k.box(P.hull2, [w * 1.05, h * 0.38, w * 1.05], [x, y + h * 0.81, z], { taper: 0 });
  k.seg(P.trim, [x, y + h * 0.9, z], [x, y + h * 1.12, z], w * 0.18, w * 0.18, { taper: 0.4 });
  k.box(P.trim, [w * 0.45, w * 0.1, w * 0.1], [x, y + h * 1.03, z]);
}

/** A smokestack with a brass rim, a glowing throat and a few frozen smoke puffs. y is the base. */
function smokestack(k: Kit, P: Palette, x: number, y: number, z: number, h: number, w: number, smoke = true) {
  k.box(P.metal, [w, h, w], [x, y + h / 2, z], { taper: 1.12 });
  k.box(P.trim, [w * 1.3, w * 0.28, w * 1.3], [x, y + h * 0.15, z]);
  k.box(P.dark, [w * 1.35, w * 0.3, w * 1.35], [x, y + h, z]);
  k.box(P.glow, [w * 0.8, 0.02, w * 0.8], [x, y + h + 0.15 * w + 0.008, z], { glow: true });
  for (let i = 0; i < 3; i++) k.box(P.hazard, [w * 1.06, w * 0.08, w * 1.06], [x, y + h * (0.45 + i * 0.12), z], { line: false });
  if (smoke) {
    // A drifting trail of soot puffs, darkest at the stack, thinning and paling as it blows back.
    const puffs: [number, number, number, number, number][] = [
      [1.5, 0.0, 1.0, -0.3, 0x5e5852],
      [1.25, 0.5, 1.9, -1.2, 0x77716a],
      [1.0, 0.1, 2.6, -2.1, 0x928c84],
      [0.65, 0.6, 3.1, -2.9, 0xaaa49c],
    ];
    puffs.forEach(([sz, dx, dy, dz, colr], i) =>
      k.box(colr, [w * sz, w * sz * 0.85, w * sz], [x + w * dx, y + h + w * dy, z + w * dz], { rot: [0.3 * i, 0.6 + i, 0.2], line: i === 0 }),
    );
  }
}

/** A hanging cloth strip from top down by len, swinging back by sway, narrowing to taper at the bottom. */
function cloth(k: Kit, color: number, top: V3, len: number, w: number, sway = 0, taper = 0.8, thick = 0.025) {
  k.seg(color, top, [top[0], top[1] - len, top[2] + sway], w, thick, { taper: [taper, 1] });
}

/** A flaring three-panel cape hanging from top, swinging back by sway, with a gold hem and a cross on its back. */
function cape(k: Kit, P: Palette, top: V3, len: number, w: number, sway: number, flare: number, emblem: number) {
  const pw = w / 3;
  for (let i = 0; i < 3; i++) {
    const off = i - 1;
    const l = len * (off === 0 ? 1 : 0.88);
    const x0 = top[0] + off * pw;
    const x1 = x0 + off * pw * (flare - 1) * 1.1;
    const z1 = top[2] + sway * (off === 0 ? 1 : 0.85);
    const zt = top[2] - Math.abs(off) * 0.012;
    k.seg(off === 0 ? P.cloth : P.clothDk, [x0, top[1], zt], [x1, top[1] - l, z1], pw * 1.04, 0.03, { taper: [flare, 1] });
    const hw = (pw * flare) / 2;
    k.seg(P.trim, [x1 - hw, top[1] - l + 0.02, z1 - 0.018], [x1 + hw, top[1] - l + 0.02, z1 - 0.018], 0.035, 0.012, { line: false });
  }
  if (emblem > 0) {
    const t = 0.42;
    const tilt = Math.atan2(-sway, len);
    k.at([top[0], top[1] - len * t, top[2] + sway * t - 0.02], [-tilt, Math.PI, 0], () => heraldicCross(k, P.trim, [0, 0, 0], emblem));
  }
}

/** Covenant heraldic cross on a plane facing +Z. */
function heraldicCross(k: Kit, color: number, pos: V3, s: number) {
  k.box(color, [s * 0.22, s, 0.012], pos, { line: false });
  k.box(color, [s * 0.7, s * 0.22, 0.012], [pos[0], pos[1] + s * 0.15, pos[2]], { line: false });
  k.box(color, [s * 0.4, s * 0.4, 0.012], [pos[0], pos[1] + s * 0.15, pos[2] - 0.001], { line: false, rot: [0, 0, Math.PI / 4] });
}

/** Foundries gear badge on a plane facing +Z. */
function gearBadge(k: Kit, color: number, pos: V3, s: number) {
  k.box(color, [s * 0.6, s * 0.6, 0.012], pos, { line: false });
  k.box(color, [s * 0.6, s * 0.6, 0.012], pos, { line: false, rot: [0, 0, Math.PI / 4] });
}

// ---------------------------------------------------------------------------------------------------------------------
// Limbs. Leg and arm kits are built in a mirrored frame (scale x by side) so +x is always outward.

type LegStyle = 'knight' | 'piston' | 'bird' | 'relic' | 'spider';

interface LegSpec {
  style: LegStyle;
  /** Hip height. */
  len: number;
  w: number;
}

function leg(k: Kit, P: Palette, spec: LegSpec, sideColour: number, items: string[]) {
  const L = spec.len;
  const w = spec.w;
  const g = -L; // ground in pivot space
  if (spec.style === 'knight') {
    k.box(P.dark, [w * 0.95, w * 0.85, w * 0.95], [0, 0, 0]);
    k.seg(P.hull, [0, -0.02, 0], [0, -L * 0.46, 0.03], w * 1.05, w * 1.15, { taper: [0.82, 0.9] });
    k.seg(P.hull2, [w * 0.5, -0.02, 0], [w * 0.48, -L * 0.36, 0.02], w * 0.12, w * 0.9, {}); // outer thigh plate
    k.seg(P.trim, [0, -L * 0.06, w * 0.6], [0, -L * 0.4, w * 0.58], w * 0.18, 0.02, {}); // gold ridge
    k.box(P.dark, [w * 0.8, w * 0.8, w * 0.8], [0, -L * 0.48, 0.03]);
    k.box(P.hull2, [w * 1.0, w * 0.95, w * 0.5], [0, -L * 0.48, w * 0.55], { taper: [0.5, 0.6], rot: [-0.3, 0, 0] }); // poleyn
    k.box(P.trim, [w * 1.05, w * 0.18, w * 0.52], [0, -L * 0.42, w * 0.58], { line: false });
    k.seg(P.hull, [0, g + w * 0.45, 0], [0, -L * 0.5, 0.03], w * 1.2, w * 1.25, { taper: [0.75, 0.75] }); // greave
    k.seg(P.trim, [0, g + w * 0.6, w * 0.64], [0, -L * 0.55, w * 0.52], w * 0.16, 0.02, {});
    k.box(sideColour, [w * 1.28, w * 0.2, w * 1.32], [0, g + w * 0.6, 0], { line: false });
    k.box(P.hull, [w * 1.15, w * 0.45, w * 1.9], [0, g + w * 0.225, w * 0.3], { taper: [0.8, 0.7] }); // sabaton
    k.seg(P.hull2, [0, g + w * 0.18, w * 1.2], [0, g + w * 0.12, w * 2.0], w * 0.9, w * 0.32, { taper: 0.1 }); // pointed toe
    k.box(P.trim, [w * 1.2, w * 0.1, w * 0.2], [0, g + w * 0.4, w * 0.9], { line: false });
    k.seg(P.hull2, [0, g + w * 0.2, -w * 0.6], [0, g + w * 0.08, -w * 1.15], w * 0.3, w * 0.25, { taper: 0.2 }); // spur
  } else if (spec.style === 'piston') {
    k.box(P.dark, [w, w, w], [0, 0, 0]);
    k.seg(P.hull2, [0, 0, 0], [0, -L * 0.42, 0.02], w * 1.15, w * 1.15, { taper: 0.85 });
    k.box(P.hull, [w * 1.35, w * 0.9, w * 1.25], [0, -L * 0.46, 0.05]); // knee block
    k.box(P.cloth, [w * 1.38, w * 0.4, w * 0.2], [0, -L * 0.44, w * 0.7]);
    rivets(k, P.dark, [[-w * 0.5, -L * 0.36, w * 0.68], [w * 0.5, -L * 0.36, w * 0.68], [-w * 0.5, -L * 0.56, w * 0.68], [w * 0.5, -L * 0.56, w * 0.68]]);
    k.seg(P.hull, [0, g + w * 0.4, 0], [0, -L * 0.52, 0.03], w * 1.35, w * 1.35, { taper: 0.82 }); // shin
    hazard(k, P, w * 1.1, w * 0.22, [0, g + w * 0.85, w * 0.66], 5);
    k.seg(P.metal, [w * 0.55, -L * 0.5, -w * 0.55], [w * 0.55, g + w * 0.5, -w * 0.55], w * 0.22, w * 0.22, {}); // piston
    k.seg(P.steel, [w * 0.55, -L * 0.5, -w * 0.55], [w * 0.55, -L * 0.72, -w * 0.55], w * 0.12, w * 0.12, { line: false });
    k.box(sideColour, [w * 1.5, w * 0.16, w * 1.5], [0, g + w * 0.42, 0], { line: false });
    k.box(P.dark, [w * 1.7, w * 0.35, w * 1.9], [0, g + w * 0.175, w * 0.2], { taper: [0.85, 0.85] }); // foot
    for (const x of [-0.55, 0, 0.55]) k.box(P.hull2, [w * 0.45, w * 0.28, w * 0.5], [x * w, g + w * 0.14, w * 1.25], { taper: [0.8, 0.6] });
  } else if (spec.style === 'bird') {
    const knee: V3 = [0, -L * 0.42, L * 0.24];
    const ankle: V3 = [0, -L * 0.82, -L * 0.12];
    k.box(P.dark, [w * 1.1, w, w], [0, 0, 0]);
    k.seg(P.hull, [0, 0, 0], knee, w * 1.2, w * 1.3, { taper: 0.8 });
    k.seg(P.hull2, [w * 0.62, -0.02, 0], [w * 0.6, knee[1] * 0.8, knee[2] * 0.8], w * 0.12, w * 0.9);
    k.box(P.dark, [w * 0.9, w * 0.9, w * 0.9], knee);
    k.box(P.hull2, [w * 1.0, w * 0.8, w * 0.5], [0, knee[1], knee[2] + w * 0.4], { taper: 0.6 });
    k.seg(P.hull, knee, ankle, w * 0.95, w * 1.0, { taper: 0.85 });
    k.seg(P.metal, [0, knee[1] + 0.05, knee[2] - w * 0.6], [0, ankle[1] + 0.05, ankle[2] - w * 0.6], w * 0.2, w * 0.2); // tendon piston
    k.box(sideColour, [w * 1.05, w * 0.18, w * 1.05], [0, ankle[1] + w * 0.4, ankle[2] + w * 0.08], { line: false });
    k.box(P.dark, [w * 0.8, w * 0.8, w * 0.8], ankle);
    k.seg(P.hull2, ankle, [0, g + w * 0.25, -L * 0.05], w * 0.8, w * 0.8);
    for (const x of [-0.5, 0.5]) k.seg(P.hull, [x * w, g + w * 0.25, -L * 0.05], [x * w * 1.4, g + w * 0.1, L * 0.18], w * 0.45, w * 0.3, { taper: [0.6, 0.6] });
    k.seg(P.hull, [0, g + w * 0.25, -L * 0.05], [0, g + w * 0.08, -L * 0.24], w * 0.4, w * 0.3, { taper: 0.5 });
    if (items.includes('anchor-spikes')) k.seg(P.steel, [0, g + w * 0.4, -L * 0.15], [0, g - 0.02, -L * 0.34], w * 0.2, w * 0.2, { taper: 0 });
  } else if (spec.style === 'relic') {
    k.box(P.trim, [w * 1.4, w * 1.2, w * 1.4], [0, 0, 0], { taper: 0.8 });
    k.seg(P.hull, [0, -0.02, 0], [0, -L * 0.46, 0.02], w * 1.0, w * 1.1, { taper: [0.7, 0.8] });
    k.seg(P.hull2, [0, -L * 0.05, w * 0.55], [0, -L * 0.38, w * 0.5], w * 0.4, 0.02);
    for (const y of [0.16, 0.3]) k.box(P.trim, [w * 1.12, w * 0.22, w * 1.18], [0, -L * y, 0.01], { line: false });
    k.box(P.trim, [w * 1.15, w * 1.15, w * 1.15], [0, -L * 0.48, 0.02], { rot: [Math.PI / 4, 0, 0] }); // gold knee orb
    k.seg(P.trim, [0, -L * 0.48, -w * 0.4], [0, -L * 0.42, -w * 2.1], w * 0.3, w * 0.3, { taper: 0 }); // knee spike back
    k.seg(P.hull, [0, g + w * 0.6, -0.01], [0, -L * 0.5, 0.02], w * 1.05, w * 1.1, { taper: 0.6 });
    k.seg(P.dark, [0, g + w * 0.8, -w * 0.45], [0, -L * 0.55, -w * 0.4], w * 0.35, w * 0.35, { line: false }); // tendon
    k.box(P.trim, [w * 1.1, w * 0.25, w * 1.15], [0, -L * 0.75, 0], { line: false });
    k.box(sideColour, [w * 1.3, w * 0.22, w * 1.3], [0, g + w * 0.7, 0], { line: false });
    k.box(P.trim, [w * 1.0, w * 0.35, w * 1.2], [0, g + w * 0.35, 0.02]);
    k.seg(P.hull, [0, g + w * 0.15, w * 0.3], [0, g + w * 0.06, w * 2.6], w * 1.0, w * 0.3, { taper: 0.05 }); // long pointed foot
    k.seg(P.hull2, [0, g + w * 0.2, -w * 0.3], [0, g + w * 0.05, -w * 1.5], w * 0.5, w * 0.3, { taper: 0.1 });
  } else {
    // spider: a front and a rear leg per side, splayed out from one hip mount.
    k.box(P.dark, [w * 1.4, w * 1.2, w * 2.2], [0, 0, 0]);
    k.box(P.trim, [w * 1.5, w * 0.3, w * 2.25], [0, w * 0.4, 0], { line: false });
    for (const dz of [1, -1]) {
      const kneeP: V3 = [L * 0.75, L * 0.35, dz * L * 0.55];
      const foot: V3 = [L * 1.05, g, dz * L * 0.95];
      k.seg(P.hull, [w * 0.3, 0, dz * w * 0.6], kneeP, w * 0.9, w * 0.9, { taper: 0.85 });
      k.box(P.dark, [w * 0.9, w * 0.9, w * 0.9], kneeP);
      k.box(P.trim, [w * 0.6, w * 0.6, w * 0.6], [kneeP[0], kneeP[1] + w * 0.5, kneeP[2]], { taper: 0 });
      k.seg(P.hull2, kneeP, [foot[0], foot[1] + w * 0.5, foot[2]], w * 0.75, w * 0.75, { taper: 0.6 });
      k.seg(P.metal, [foot[0], foot[1] + w * 0.6, foot[2]], foot, w * 0.4, w * 0.4, { taper: 0.2 });
      k.box(sideColour, [w * 0.8, w * 0.2, w * 0.8], [kneeP[0] + (foot[0] - kneeP[0]) * 0.75, kneeP[1] + (foot[1] - kneeP[1]) * 0.75 + 0.05, kneeP[2] + (foot[2] - kneeP[2]) * 0.75], { line: false });
    }
  }
  if (items.includes('jump-jets') && spec.style !== 'spider') {
    k.box(P.metal, [w * 0.6, w * 1.6, w * 0.6], [w * 0.7, -L * 0.62, -w * 0.5], { taper: 1.3 });
    k.box(P.glow, [w * 0.5, 0.02, w * 0.5], [w * 0.7, -L * 0.62 - w * 0.81, -w * 0.5], { glow: true });
  }
  if (items.includes('sprint-servos') && spec.style !== 'spider') {
    k.box(P.trim, [w * 0.3, w * 1.4, w * 0.3], [w * 0.7, -L * 0.26, w * 0.1]);
    k.box(P.glow, [w * 0.1, w * 1.0, w * 0.1], [w * 0.86, -L * 0.26, w * 0.1], { glow: true });
  }
  if (items.includes('anchor-spikes') && spec.style !== 'bird') {
    k.seg(P.steel, [w * 0.4, g + w * 0.5, -w * 0.6], [w * 0.6, g - 0.02, -w * 1.4], w * 0.22, w * 0.22, { taper: 0 });
  }
  if (items.includes('gyro-stabilisers')) {
    k.box(P.trim, [w * 0.25, w * 0.9, w * 0.9], [w * 0.7, -L * 0.05, 0], { rot: [Math.PI / 4, 0, 0] });
    k.box(P.glow, [w * 0.27, w * 0.35, w * 0.35], [w * 0.72, -L * 0.05, 0], { glow: true, rot: [Math.PI / 4, 0, 0] });
  }
}

type ArmStyle = 'gauntlet' | 'hydraulic' | 'bone';
type Pose = 'gun' | 'melee' | 'claw' | 'idle' | 'staff';

interface ArmSpec {
  style: ArmStyle;
  upper: number;
  fore: number;
  w: number;
  /** Size of the hand / weapon props relative to a medium walker. */
  heft: number;
}

const GUNS = new Set(['carapace-gun', 'missile-rack', 'autocannon', 'rail-cannon', 'rocket-pod', 'arc-cannon', 'hellfire-missiles']);
const CLAWS = new Set(['industrial-claw', 'kinetic-claws']);

function poseFor(item: string | undefined): Pose {
  if (!item) return 'idle';
  if (item === 'lance') return 'gun';
  if (item === 'melee-blade') return 'melee';
  if (CLAWS.has(item)) return 'claw';
  if (item === 'kinetic-shield') return 'idle';
  return 'gun';
}

/** Builds an arm (shoulder at the origin) and its weapons; returns the muzzle point in arm space. */
function arm(k: Kit, P: Palette, faction: string, spec: ArmSpec, armItems: string[], unarmed: Pose | 'talon'): THREE.Vector3 {
  const { upper: u, fore: f, w, heft } = spec;
  const weapons = armItems.filter((i) => i !== 'kinetic-shield' && i !== 'ablative-plating');
  const primary = weapons[0];
  let pose = poseFor(primary);
  if (!primary && unarmed === 'staff') pose = 'staff';
  const elbow: V3 = pose === 'idle' ? [0.02, -u, 0.02] : pose === 'gun' || pose === 'staff' ? [0.02, -u * 0.94, u * 0.3] : [0.02, -u * 0.97, u * 0.2];
  const dir: Record<Pose, V3> = { gun: [0, -0.06, 1], melee: [0, -0.55, 0.84], claw: [0, -0.35, 0.94], idle: [0.02, -0.96, 0.28], staff: [0, -0.2, 0.98] };
  const d = new THREE.Vector3(...dir[pose]).normalize().multiplyScalar(f);
  const hand: V3 = [elbow[0] + d.x, elbow[1] + d.y, elbow[2] + d.z];

  // Upper arm and elbow.
  if (spec.style === 'gauntlet') {
    k.box(P.dark, [w * 1.1, w * 1.1, w * 1.1], [0, 0, 0]);
    k.seg(P.hull, [0, -w * 0.3, 0], elbow, w, w * 1.05, { taper: 0.9 });
    k.box(P.trim, [w * 1.12, w * 0.18, w * 1.15], [elbow[0] * 0.5, -u * 0.55, 0], { line: false });
    k.box(P.dark, [w * 0.95, w * 0.95, w * 0.95], elbow);
    k.box(P.trim, [w * 0.6, w * 0.6, w * 0.4], [elbow[0], elbow[1], elbow[2] - w * 0.55], { taper: 0, rot: [-Math.PI / 2, 0, 0] }); // elbow spike
    k.seg(P.hull2, elbow, hand, w * 1.15, w * 1.2, { taper: [1.12, 1.1] }); // vambrace
    k.seg(P.trim, [elbow[0] + w * 0.6, elbow[1], elbow[2]], [hand[0] + w * 0.65, hand[1], hand[2]], 0.02, w * 0.5);
  } else if (spec.style === 'hydraulic') {
    k.box(P.dark, [w * 1.2, w * 1.2, w * 1.2], [0, 0, 0]);
    k.seg(P.metal, [0, 0, 0], elbow, w * 0.8, w * 0.8);
    k.seg(P.steel, [w * 0.5, -w * 0.2, w * 0.3], [w * 0.5, elbow[1] + w * 0.2, w * 0.3], w * 0.2, w * 0.2, { line: false });
    k.box(P.hull2, [w * 1.15, w * 1.1, w * 1.15], elbow);
    k.seg(P.hull, elbow, hand, w * 1.5, w * 1.55, { taper: [1.12, 1.15] }); // big forearm
    k.at(elbow, [0, 0, 0], () => {
      const q = new THREE.Quaternion().setFromUnitVectors(UP, d.clone().normalize());
      const e = new THREE.Euler().setFromQuaternion(q);
      k.push([0, 0, 0], [e.x, e.y, e.z]);
      hazard(k, P, w * 1.4, w * 0.3, [0, f * 0.75, w * 0.84], 5);
      k.box(P.cloth, [w * 0.04, f * 0.5, w * 1.2], [w * 0.8, f * 0.4, 0], { line: false });
      k.pop();
    });
  } else {
    k.box(P.trim, [w * 1.2, w * 1.2, w * 1.2], [0, 0, 0], { rot: [0, Math.PI / 4, 0] });
    k.seg(P.hull, [0, -w * 0.3, 0], elbow, w * 0.8, w * 0.85, { taper: 0.8 });
    for (const t of [0.35, 0.65]) k.box(P.trim, [w * 0.95, w * 0.2, w * 0.95], [elbow[0] * t, elbow[1] * t, 0], { line: false });
    k.box(P.trim, [w, w, w], elbow, { rot: [Math.PI / 4, 0, 0] });
    k.seg(P.hull2, elbow, hand, w * 0.95, w, { taper: 0.75 });
    k.seg(P.trim, [elbow[0], elbow[1], elbow[2] - w * 0.4], [hand[0] * 0.7, elbow[1] + d.y * 0.6, elbow[2] + d.z * 0.6 - w * 0.4], 0.02, 0.02, { line: false });
  }

  // Shield on the forearm's outer side.
  if (armItems.includes('kinetic-shield')) {
    const mid: V3 = [elbow[0] + d.x * 0.5 + w * 0.9, elbow[1] + d.y * 0.5, elbow[2] + d.z * 0.5];
    k.at(mid, [0, 0, 0], () => {
      const sh = 0.6 * heft;
      const face = faction === 'covenant' ? P.cloth : faction === 'foundries' ? P.hull : P.hull;
      k.box(face, [0.05, sh * 1.25, sh * 0.85], [0, -sh * 0.15, 0.04], { taper: [1, 1.0] });
      k.seg(face, [0, -sh * 0.77, 0.04], [0, -sh * 1.1, 0.04], 0.05, sh * 0.85, { taper: [1, 0.05] });
      k.box(P.trim, [0.05, sh * 1.3, sh * 0.06], [0.004, -sh * 0.17, 0.04], { line: false });
      k.box(P.trim, [0.06, sh * 1.3, 0.03], [0.005, -sh * 0.15, 0.04 + sh * 0.43], { line: false });
      k.box(P.trim, [0.06, sh * 1.3, 0.03], [0.005, -sh * 0.15, 0.04 - sh * 0.43], { line: false });
      k.box(P.glow, [0.06, sh * 0.5, sh * 0.12], [0.012, -sh * 0.1, 0.04], { glow: true });
      k.box(P.glow, [0.06, sh * 0.12, sh * 0.4], [0.012, sh * 0.02, 0.04], { glow: true });
    });
  }

  // Hand frame: +Z along the weapon.
  const lookDir = pose === 'idle' ? new THREE.Vector3(0, -0.2, 1).normalize() : d.clone().normalize();
  if (pose === 'gun') lookDir.set(0, 0, 1);
  const e = new THREE.Euler().setFromQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), lookDir));
  k.push(hand, [e.x, e.y, e.z]);
  let tip: V3 = [0, 0, 0.1];
  if (!primary) tip = emptyHand(k, P, faction, spec, unarmed);
  else tip = weapon(k, P, faction, primary, heft, w);
  const muzzle = k.point(tip);
  // Second and third weapons ride on top of and under the forearm.
  weapons.slice(1).forEach((id, i) => {
    k.push([0, (i === 0 ? 1 : -1) * w * 1.3, -f * 0.3]);
    weapon(k, P, faction, id, heft * 0.85, w);
    k.pop();
  });
  k.pop();
  return muzzle;
}

function emptyHand(k: Kit, P: Palette, faction: string, spec: ArmSpec, unarmed: Pose | 'talon'): V3 {
  const w = spec.w;
  if (unarmed === 'staff') {
    // Reliquary relic staff: a long gold rod with a small spiked halo and a lit orb.
    k.box(P.dark, [w * 0.9, w * 0.9, w * 0.9], [0, 0, 0]);
    k.seg(P.trim, [0, -0.55, 0.03], [0, 0.95, 0.03], 0.035, 0.035);
    k.at([0, 1.05, 0.03], [0, 0, 0], () => halo(k, P, 0.11, 8, 0.07, 0.025, 0));
    k.box(P.glow, [0.06, 0.06, 0.06], [0, 1.05, 0.03], { glow: true, rot: [0, 0, Math.PI / 4] });
    k.seg(P.trim, [0, -0.55, 0.03], [0, -0.68, 0.03], 0.05, 0.05, { taper: 0 });
    return [0, 1.05, 0.03];
  }
  if (faction === 'covenant') {
    k.box(P.dark, [w * 1.0, w * 0.9, w * 1.1], [0, 0, w * 0.2]);
    k.box(P.hull2, [w * 1.1, w * 0.5, w * 0.8], [0, w * 0.2, w * 0.2]);
    k.box(P.trim, [w * 1.12, w * 0.12, w * 0.6], [0, w * 0.45, w * 0.2], { line: false });
    for (const x of [-0.3, 0, 0.3]) k.box(P.dark, [w * 0.25, w * 0.25, w * 0.5], [x * w, -w * 0.3, w * 0.55]);
    return [0, 0, w];
  }
  if (faction === 'foundries') {
    k.box(P.dark, [w * 1.4, w * 0.8, w * 1.2], [0, 0, w * 0.2]);
    k.seg(P.metal, [w * 0.45, -w * 0.2, w * 0.4], [w * 0.5, -w * 1.1, w * 0.9], w * 0.35, w * 0.4, { taper: 0.6 });
    k.seg(P.metal, [-w * 0.45, -w * 0.2, w * 0.4], [-w * 0.5, -w * 1.1, w * 0.9], w * 0.35, w * 0.4, { taper: 0.6 });
    k.box(P.hazard, [w * 1.42, w * 0.18, w * 0.4], [0, w * 0.3, w * 0.2], { line: false });
    return [0, -w, w];
  }
  // Reliquary talons: long, thin, curving gold fingers.
  k.box(P.dark, [w * 0.9, w * 0.7, w * 0.9], [0, 0, 0]);
  const reach = unarmed === 'talon' ? 2.4 : 1.4;
  for (const x of [-0.35, 0, 0.35]) {
    const m: V3 = [x * w, -w * 0.5 * reach, w * 0.8 * reach];
    k.seg(P.trim, [x * w, 0, w * 0.3], m, w * 0.18, w * 0.2);
    k.seg(P.trim, m, [x * w * 1.3, -w * 1.5 * reach, w * 1.0 * reach], w * 0.16, w * 0.18, { taper: 0.1 });
  }
  k.seg(P.trim, [w * 0.45, 0, 0], [w * 0.7, -w * 0.8 * reach, w * 0.3 * reach], w * 0.16, w * 0.16, { taper: 0.1 });
  return [0, -w * 1.4 * reach, w * reach];
}

/** A weapon in a hand frame: grip at the origin, firing or pointing along +Z. Returns the muzzle/tip. */
function weapon(k: Kit, P: Palette, faction: string, id: string, heft: number, w: number): V3 {
  const h = heft;
  switch (id) {
    case 'lance': {
      // Couched jousting lance: gold vamplate, crimson pennant, a long tapering steel point with gold rings.
      k.box(P.dark, [w, w, w * 1.1], [0, 0, 0]);
      k.seg(P.dark, [0, 0, -0.3 * h], [0, 0, 0.2 * h], 0.05 * h, 0.05 * h, {});
      k.seg(P.trim, [0, 0, 0.12 * h], [0, 0, 0.32 * h], 0.24 * h, 0.24 * h, { taper: 0.35 }); // vamplate
      k.seg(P.metal, [0, 0, 0.3 * h], [0, 0, 1.15 * h], 0.13 * h, 0.13 * h, { taper: 0.55 });
      k.seg(P.steel, [0, 0, 1.15 * h], [0, 0, 1.8 * h], 0.0715 * h, 0.0715 * h, { taper: 0.02 });
      for (const t of [0.5, 0.8, 1.15]) k.box(P.trim, [(0.135 - t * 0.055) * h, (0.135 - t * 0.055) * h, 0.04], [0, 0, t * h], { line: false });
      k.seg(P.trim, [0, 0.045 * h, 0.4 * h], [0, 0.03 * h, 1.1 * h], 0.02 * h, 0.02, { line: false });
      k.box(P.cloth, [0.012, 0.18 * h, 0.26 * h], [0, -0.14 * h, 0.5 * h], { taper: [1, 0.3] });
      k.box(P.trim, [0.014, 0.02, 0.26 * h], [0, -0.05 * h, 0.5 * h], { line: false });
      return [0, 0, 1.8 * h];
    }
    case 'melee-blade': {
      // Two-handed greatsword: gold crossguard, a long steel blade with a dark fuller, pointed tip.
      k.box(P.dark, [w, w, w], [0, 0, 0]);
      k.seg(P.dark, [0, 0, -0.14 * h], [0, 0, 0.1 * h], 0.05 * h, 0.05 * h);
      k.box(P.trim, [0.08 * h, 0.08 * h, 0.08 * h], [0, 0, -0.16 * h], { rot: [0, Math.PI / 4, 0] });
      k.box(P.trim, [0.36 * h, 0.06 * h, 0.07 * h], [0, 0, 0.12 * h], { taper: [1, 1] });
      k.seg(P.trim, [0.18 * h, 0, 0.12 * h], [0.24 * h, 0, 0.2 * h], 0.05 * h, 0.05 * h, { taper: 0.2 });
      k.seg(P.trim, [-0.18 * h, 0, 0.12 * h], [-0.24 * h, 0, 0.2 * h], 0.05 * h, 0.05 * h, { taper: 0.2 });
      k.seg(P.steel, [0, 0, 0.15 * h], [0, 0, 1.05 * h], 0.13 * h, 0.03 * h, { taper: [0.8, 1] });
      k.seg(P.steel, [0, 0, 1.05 * h], [0, 0, 1.3 * h], 0.104 * h, 0.03 * h, { taper: [0, 1] });
      k.seg(faction === 'reliquary' ? P.glow : P.metal, [0, 0, 0.2 * h], [0, 0, 0.95 * h], 0.03 * h, 0.034 * h, { line: false, glow: faction === 'reliquary' });
      return [0, 0, 1.3 * h];
    }
    case 'carapace-gun': {
      // Rotary cannon: a cluster of barrels in a gold-banded shroud with a crimson ammo housing.
      k.box(P.hull, [0.26 * h, 0.24 * h, 0.4 * h], [0, 0, 0.05 * h]);
      k.box(P.cloth, [0.27 * h, 0.12 * h, 0.2 * h], [0, 0.02 * h, 0.05 * h], { line: false });
      k.box(P.trim, [0.28 * h, 0.04 * h, 0.42 * h], [0, 0.12 * h, 0.05 * h], { line: false });
      for (const [x, y] of [[-0.05, 0.05], [0.05, 0.05], [-0.05, -0.05], [0.05, -0.05]]) k.box(P.metal, [0.07 * h, 0.07 * h, 0.55 * h], [x * h, y * h, 0.5 * h]);
      for (const z of [0.36, 0.72]) k.box(P.trim, [0.22 * h, 0.22 * h, 0.05 * h], [0, 0, z * h]);
      k.box(P.dark, [0.08 * h, 0.08 * h, 0.02], [0, 0, 0.78 * h], { line: false });
      return [0, 0, 0.8 * h];
    }
    case 'missile-rack': {
      // Gothic missile box: black housing, gold frame, a 3x2 grid of crimson-tipped warheads.
      k.box(P.dark, [w * 0.9, w * 0.9, w], [0, 0, 0]);
      k.box(P.hull, [0.3 * h, 0.24 * h, 0.42 * h], [0, 0.04 * h, 0.2 * h], { taper: [1, 0.9] });
      k.box(P.trim, [0.32 * h, 0.03 * h, 0.44 * h], [0, 0.17 * h, 0.2 * h], { line: false });
      k.box(P.dark, [0.33 * h, 0.27 * h, 0.04 * h], [0, 0.04 * h, 0.42 * h]);
      k.box(P.trim, [0.34 * h, 0.03 * h, 0.05 * h], [0, -0.1 * h, 0.42 * h], { line: false });
      for (const x of [-0.09, 0, 0.09]) for (const y of [-0.01, 0.09]) k.box(P.cloth, [0.06 * h, 0.06 * h, 0.07 * h], [x * h, y * h, 0.46 * h], { taper: 0.3, rot: [Math.PI / 2, 0, 0], line: false });
      k.box(P.cloth, [0.012, 0.12 * h, 0.2 * h], [0.155 * h, 0.04 * h, 0.2 * h], { line: false });
      k.box(P.trim, [0.014, 0.05 * h, 0.012 * h * 3], [0.157 * h, 0.04 * h, 0.2 * h], { line: false });
      return [0, 0.04 * h, 0.46 * h];
    }
    case 'autocannon': {
      // Long heavy barrel on a boxy receiver, ammo drum underneath, perforated muzzle brake.
      k.box(P.dark, [w * 1.1, w * 1.1, w * 1.1], [0, 0, 0]);
      k.box(P.hull, [0.2 * h, 0.22 * h, 0.4 * h], [0, 0.02 * h, 0.14 * h]);
      k.box(P.cloth, [0.21 * h, 0.08 * h, 0.2 * h], [0, 0.09 * h, 0.14 * h], { line: false });
      k.box(P.metal, [0.16 * h, 0.16 * h, 0.16 * h], [0, -0.14 * h, 0.08 * h]); // drum
      k.box(P.metal, [0.08 * h, 0.08 * h, 0.7 * h], [0, 0.04 * h, 0.65 * h]);
      k.box(P.trim, [0.11 * h, 0.11 * h, 0.04 * h], [0, 0.04 * h, 0.45 * h]);
      k.box(P.dark, [0.13 * h, 0.13 * h, 0.14 * h], [0, 0.04 * h, 1.02 * h]);
      k.box(P.glow, [0.05 * h, 0.05 * h, 0.01], [0, 0.04 * h, 1.095 * h], { glow: true });
      return [0, 0.04 * h, 1.1 * h];
    }
    case 'rail-cannon': {
      // Very long twin rails with a glowing coil track between them and a heavy capacitor block.
      k.box(P.dark, [w * 1.1, w * 1.1, w * 1.1], [0, 0, 0]);
      k.box(P.hull2, [0.24 * h, 0.26 * h, 0.5 * h], [0, 0.02 * h, 0.1 * h]);
      k.box(P.cloth, [0.25 * h, 0.1 * h, 0.3 * h], [0, 0.1 * h, 0.1 * h], { line: false });
      stencil(k, '12', P.accent, [0, 0.05 * h, 0.354 * h], 0.012 * h);
      for (const y of [0.09, -0.05]) k.box(P.metal, [0.14 * h, 0.05 * h, 1.3 * h], [0, y * h, 0.95 * h]);
      k.box(P.glow, [0.06 * h, 0.07 * h, 1.2 * h], [0, 0.02 * h, 0.95 * h], { glow: true });
      for (const z of [0.5, 0.9, 1.3]) k.box(P.trim, [0.17 * h, 0.22 * h, 0.04 * h], [0, 0.02 * h, z * h]);
      return [0, 0.02 * h, 1.6 * h];
    }
    case 'rocket-pod': {
      // Chunky red box of rocket tubes with hazard band.
      k.box(P.dark, [w, w, w], [0, 0, 0]);
      k.box(P.cloth, [0.34 * h, 0.3 * h, 0.4 * h], [0, 0.06 * h, 0.18 * h]);
      hazard(k, P, 0.34 * h, 0.05 * h, [0, -0.07 * h, 0.385 * h], 6);
      for (const x of [-0.1, 0, 0.1]) for (const y of [0.0, 0.12]) k.box(P.dark, [0.075 * h, 0.075 * h, 0.02], [x * h, y * h + 0.02 * h, 0.385 * h], { line: false });
      k.box(P.metal, [0.36 * h, 0.04 * h, 0.42 * h], [0, 0.22 * h, 0.18 * h]);
      return [0, 0.08 * h, 0.4 * h];
    }
    case 'industrial-claw': {
      // Big brass-jawed scrap claw: a wrist block and three heavy hooked fingers.
      k.box(P.dark, [0.24 * h, 0.22 * h, 0.22 * h], [0, 0, 0.05 * h]);
      k.box(P.hazard, [0.25 * h, 0.06 * h, 0.1 * h], [0, 0.08 * h, 0.05 * h], { line: false });
      for (const [x, y] of [[0.1, 0.06], [-0.1, 0.06], [0, -0.1]]) {
        const s = Math.sign(x) || 0;
        const mid: V3 = [x * h * 1.6, y * h * 1.5, 0.3 * h];
        k.seg(P.metal, [x * h * 0.6, y * h * 0.6, 0.12 * h], mid, 0.08 * h, 0.08 * h);
        k.seg(P.trim, mid, [x * h * 0.5 - s * 0.01, y * h * 0.4, 0.5 * h], 0.07 * h, 0.07 * h, { taper: 0.2 });
      }
      return [0, 0, 0.45 * h];
    }
    case 'arc-cannon': {
      // Relic rod: dark shaft threaded with glowing teal coil rings, forked prongs and an orb at the tip.
      k.box(P.dark, [w, w, w], [0, 0, 0]);
      k.box(P.dark, [0.15 * h, 0.15 * h, 0.2 * h], [0, 0, -0.05 * h]);
      k.seg(P.metal, [0, 0, 0], [0, 0, 1.0 * h], 0.07 * h, 0.07 * h);
      for (const z of [0.25, 0.45, 0.65]) {
        k.box(P.trim, [0.16 * h, 0.16 * h, 0.06 * h], [0, 0, z * h]);
        k.box(P.glow, [0.17 * h, 0.17 * h, 0.02 * h], [0, 0, z * h + 0.04 * h], { glow: true });
      }
      for (const x of [-1, 1]) k.seg(P.trim, [x * 0.04 * h, 0, 0.95 * h], [x * 0.08 * h, 0, 1.18 * h], 0.03 * h, 0.03 * h, { taper: 0.2 });
      k.box(P.glow, [0.08 * h, 0.08 * h, 0.08 * h], [0, 0, 1.1 * h], { glow: true, rot: [0, 0, Math.PI / 4] });
      k.box(P.trim, [0.04 * h, 0.12 * h, 0.12 * h], [0, 0, -0.16 * h], { rot: [Math.PI / 4, 0, 0] });
      return [0, 0, 1.15 * h];
    }
    case 'hellfire-missiles': {
      // A curved black horn caged in gold, with a teal-lit seeker eye.
      k.box(P.dark, [w, w, w], [0, 0, 0]);
      k.box(P.dark, [0.12 * h, 0.14 * h, 0.12 * h], [0, -0.05 * h, 0.05 * h]);
      k.seg(P.metal, [0, 0.05 * h, -0.1 * h], [0, 0.1 * h, 0.4 * h], 0.22 * h, 0.22 * h, { taper: 0.7 });
      k.seg(P.metal, [0, 0.1 * h, 0.4 * h], [0, 0.04 * h, 0.85 * h], 0.154 * h, 0.154 * h, { taper: 0.05 });
      for (const [z, r] of [[0.08, 0.235], [0.3, 0.2], [0.52, 0.14], [0.7, 0.09]]) k.box(P.trim, [r * h, r * h, 0.035 * h], [0, 0.09 * h - z * 0.07 * h, z * h], { line: false, rot: [0.1, 0, 0] });
      k.box(P.glow, [0.1 * h, 0.1 * h, 0.02], [0, 0.07 * h, -0.11 * h], { glow: true });
      k.seg(P.trim, [0, 0.18 * h, 0.0], [0, 0.26 * h, 0.3 * h], 0.03 * h, 0.03 * h, { taper: 0.3 });
      k.box(P.glow, [0.06 * h, 0.06 * h, 0.06 * h], [0, 0.17 * h, 0.12 * h], { glow: true });
      return [0, 0.04 * h, 0.85 * h];
    }
    case 'kinetic-claws': {
      // Gauntlet with four long scything gold blades.
      k.box(P.dark, [0.2 * h, 0.16 * h, 0.24 * h], [0, 0, 0.05 * h]);
      k.box(P.accent, [0.18 * h, 0.04 * h, 0.16 * h], [0, 0.09 * h, 0.05 * h]);
      k.box(P.glow, [0.05 * h, 0.05 * h, 0.05 * h], [0, 0.12 * h, 0.05 * h], { glow: true });
      for (const x of [-0.075, -0.025, 0.025, 0.075]) {
        const m: V3 = [x * h * 1.9, -0.03 * h, 0.45 * h];
        k.seg(P.trim, [x * h, 0, 0.12 * h], m, 0.04 * h, 0.045 * h);
        k.seg(P.trim, m, [x * h * 2.6, -0.28 * h, 0.8 * h], 0.036 * h, 0.04 * h, { taper: 0.15 });
        k.seg(P.steel, [x * h * 1.9, -0.01 * h, 0.47 * h], [x * h * 2.5, -0.24 * h, 0.76 * h], 0.012 * h, 0.05 * h, { line: false });
      }
      return [0, -0.1 * h, 0.75 * h];
    }
    default: {
      k.box(P.dark, [0.16 * h, 0.16 * h, 0.3 * h], [0, 0, 0.1 * h]);
      k.box(P.metal, [0.08 * h, 0.08 * h, 0.5 * h], [0, 0, 0.45 * h]);
      return [0, 0, 0.7 * h];
    }
  }
}

/** The soul lantern: a tall teal-lit lantern with a dark pointed cap, hanging from a hooked gold crook. */
function soulLantern(k: Kit, P: Palette, s: number) {
  k.box(P.dark, [0.12 * s, 0.05 * s, 0.12 * s], [0, 0.11 * s, 0]);
  k.box(P.dark, [0.13 * s, 0.1 * s, 0.13 * s], [0, 0.18 * s, 0], { taper: 0.1 });
  k.box(P.trim, [0.03 * s, 0.05 * s, 0.03 * s], [0, 0.25 * s, 0]);
  k.box(P.glow, [0.09 * s, 0.17 * s, 0.09 * s], [0, 0, 0], { glow: true });
  for (const [x, z] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) k.box(P.trim, [0.018 * s, 0.19 * s, 0.018 * s], [x * 0.05 * s, 0, z * 0.05 * s], { line: false });
  k.box(P.dark, [0.12 * s, 0.05 * s, 0.12 * s], [0, -0.11 * s, 0]);
  k.box(P.dark, [0.08 * s, 0.04 * s, 0.08 * s], [0, -0.15 * s, 0], { taper: 0.4 });
}

// ---------------------------------------------------------------------------------------------------------------------
// Walker assembly.

interface Ctx {
  P: Palette;
  faction: string;
  side: number;
  items: Record<string, string[]>;
  torso: Kit;
  head: Kit;
  halo: Kit;
  float: Kit; // floating ornaments that bob (lanterns, drones, relic shards), in torso space
  armL: Kit;
  armR: Kit;
  legL: Kit;
  legR: Kit;
}

interface Layout {
  hipY: number;
  hipX: number;
  /** Head pivot in torso space. */
  neck: V3;
  /** Left shoulder pivot in torso space (+x is the walker's left). */
  shoulder: V3;
  /** Halo centre in head space, if there is a halo. */
  halo?: V3;
  /** Overall size multiplier for the whole walker (default 1). */
  scale?: number;
  /** Forward lean of the torso, radians. */
  lean?: number;
  leg: LegSpec;
  arm: ArmSpec;
  unarmed: Pose | 'talon';
  /** Where core weapons ride: a shoulder-top point in torso space for the left side. */
  mount: V3;
  /** Back centre in torso space for back-mounted systems. */
  back: V3;
  height: number;
}

type ClassBuilder = (c: Ctx) => Layout;

const has = (c: Ctx, id: string) => Object.values(c.items).some((l) => l.includes(id));

// --- Iron Covenant ---------------------------------------------------------------------------------------------------

/** A crested great helm with a T-visor. crest: 'fin' (swept plume), 'crown' (spired crown and horns), 'bucket'. */
function covenantHelm(k: Kit, P: Palette, s: number, crest: 'fin' | 'crown' | 'bucket') {
  k.box(P.dark, [0.1 * s, 0.06 * s, 0.1 * s], [0, 0.0, 0]);
  if (crest === 'bucket') {
    k.box(P.hull, [0.2 * s, 0.17 * s, 0.2 * s], [0, 0.1 * s, 0], { taper: 0.9 });
    k.box(P.trim, [0.21 * s, 0.03 * s, 0.21 * s], [0, 0.175 * s, 0], { line: false });
    k.box(P.dark, [0.16 * s, 0.12 * s, 0.02], [0, 0.1 * s, 0.1 * s]);
    k.box(P.glow, [0.14 * s, 0.03 * s, 0.01], [0, 0.12 * s, 0.1 * s + 0.012], { glow: true });
    k.box(P.glow, [0.03 * s, 0.1 * s, 0.01], [0, 0.095 * s, 0.1 * s + 0.012], { glow: true });
    for (const x of [-0.07, 0, 0.07]) k.box(P.trim, [0.03 * s, 0.05 * s, 0.03 * s], [x * s, 0.21 * s, 0], { taper: 0 });
    return;
  }
  k.box(P.hull, [0.17 * s, 0.2 * s, 0.2 * s], [0, 0.1 * s, -0.005 * s], { taper: [0.82, 0.88] });
  k.box(P.hull2, [0.15 * s, 0.13 * s, 0.05 * s], [0, 0.08 * s, 0.09 * s], { taper: [1.1, 1], rot: [0.12, 0, 0] }); // face plate
  k.seg(P.hull2, [0, 0.03 * s, 0.11 * s], [0, -0.03 * s, 0.13 * s], 0.08 * s, 0.03 * s, { taper: 0.2 }); // chin point
  k.box(P.glow, [0.12 * s, 0.025 * s, 0.01], [0, 0.115 * s, 0.118 * s], { glow: true });
  k.box(P.glow, [0.025 * s, 0.07 * s, 0.01], [0, 0.08 * s, 0.118 * s], { glow: true });
  k.box(P.trim, [0.025 * s, 0.2 * s, 0.215 * s], [0, 0.12 * s, 0.0], { line: false }); // gold centre ridge
  if (crest === 'fin') {
    k.box(P.trim, [0.025 * s, 0.1 * s, 0.32 * s], [0, 0.22 * s, -0.08 * s], { taper: [1, 0.4], shift: [0, -0.1 * s] });
    k.box(P.cloth, [0.02 * s, 0.14 * s, 0.2 * s], [0, 0.15 * s, -0.2 * s], { taper: [1, 0.6], rot: [-0.4, 0, 0] });
    for (const x of [-1, 1]) k.seg(P.trim, [x * 0.07 * s, 0.13 * s, 0.03 * s], [x * 0.14 * s, 0.24 * s, -0.1 * s], 0.035 * s, 0.035 * s, { taper: 0 });
  } else {
    for (const x of [-0.06, 0, 0.06]) k.seg(P.trim, [x * s, 0.18 * s, 0], [x * s * 1.3, (x === 0 ? 0.36 : 0.29) * s, -0.01 * s], 0.035 * s, 0.035 * s, { taper: 0 });
    k.box(P.trim, [0.18 * s, 0.03 * s, 0.2 * s], [0, 0.19 * s, 0], { line: false });
    for (const x of [-1, 1]) {
      k.seg(P.hull2, [x * 0.08 * s, 0.13 * s, 0], [x * 0.2 * s, 0.2 * s, 0.02 * s], 0.05 * s, 0.05 * s, { taper: 0.6 });
      k.seg(P.trim, [x * 0.2 * s, 0.2 * s, 0.02 * s], [x * 0.24 * s, 0.33 * s, 0.0], 0.035 * s, 0.035 * s, { taper: 0 });
    }
  }
}

/** Tall swept knightly pauldron in arm space (+x outward). */
function covenantPauldron(k: Kit, P: Palette, s: number, kind: 'swept' | 'tower' | 'sunburst') {
  if (kind === 'swept') {
    k.box(P.hull, [0.2 * s, 0.1 * s, 0.24 * s], [0.03 * s, 0.05 * s, 0], { rot: [0, 0, -0.35], taper: [0.8, 0.85] });
    k.box(P.trim, [0.2 * s, 0.025 * s, 0.25 * s], [0.04 * s, 0.0, 0], { rot: [0, 0, -0.35], line: false });
    k.box(P.hull2, [0.18 * s, 0.07 * s, 0.22 * s], [0.06 * s, -0.04 * s, 0], { rot: [0, 0, -0.6] });
    k.box(P.cloth, [0.14 * s, 0.03 * s, 0.17 * s], [0.03 * s, 0.1 * s, 0], { rot: [0, 0, -0.35] });
    k.seg(P.trim, [0.02 * s, 0.08 * s, -0.02 * s], [0.06 * s, 0.32 * s, -0.08 * s], 0.04 * s, 0.05 * s, { taper: 0 });
    k.seg(P.cloth, [0.12 * s, 0.02 * s, -0.08 * s], [0.14 * s, -0.25 * s, -0.12 * s], 0.08 * s, 0.015, { taper: [0.5, 1] });
  } else if (kind === 'tower') {
    k.box(P.hull, [0.24 * s, 0.26 * s, 0.32 * s], [0.06 * s, 0.06 * s, 0], { taper: [0.85, 0.9] });
    k.box(P.trim, [0.25 * s, 0.03 * s, 0.33 * s], [0.06 * s, 0.19 * s, 0], { line: false });
    k.box(P.cloth, [0.02, 0.2 * s, 0.22 * s], [0.18 * s, 0.04 * s, 0]);
    k.at([0.192 * s, 0.04 * s, 0], [0, Math.PI / 2, 0], () => heraldicCross(k, P.trim, [0, 0, 0], 0.13 * s));
    for (const z of [-0.1, 0.1]) k.box(P.trim, [0.05 * s, 0.07 * s, 0.05 * s], [0.06 * s, 0.24 * s, z * s], { taper: 0 }); // merlons
    k.box(P.trim, [0.05 * s, 0.07 * s, 0.05 * s], [0.15 * s, 0.24 * s, 0], { taper: 0 });
  } else {
    // Big rounded pauldron with a gold sunburst boss and a ring of spikes.
    k.box(P.hull, [0.28 * s, 0.2 * s, 0.34 * s], [0.06 * s, 0.07 * s, 0], { taper: [0.7, 0.75] });
    k.box(P.hull2, [0.3 * s, 0.1 * s, 0.36 * s], [0.07 * s, -0.04 * s, 0], { rot: [0, 0, -0.3], taper: [0.9, 0.9] });
    k.box(P.trim, [0.31 * s, 0.03 * s, 0.37 * s], [0.08 * s, -0.09 * s, 0], { rot: [0, 0, -0.3], line: false });
    k.box(P.cloth, [0.2 * s, 0.04 * s, 0.24 * s], [0.04 * s, 0.17 * s, 0], { taper: 0.8 });
    k.at([0.19 * s, 0.07 * s, 0], [0, 0, -0.5], () => {
      k.box(P.cloth, [0.03 * s, 0.17 * s, 0.22 * s], [-0.01 * s, 0, 0]);
      k.box(P.trim, [0.04 * s, 0.1 * s, 0.1 * s], [0, 0, 0], { rot: [Math.PI / 4, 0, 0] });
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        k.box(P.trim, [0.02 * s, 0.025 * s, 0.11 * s], [0.01 * s, Math.sin(a) * 0.07 * s, Math.cos(a) * 0.07 * s], { rot: [a, 0, 0], line: false });
      }
    });
    for (const z of [-0.12, 0, 0.12]) k.seg(P.trim, [0.02 * s, 0.16 * s, z * s], [0.0, (z === 0 ? 0.42 : 0.32) * s, z * s * 1.2 - 0.03 * s], 0.045 * s, 0.045 * s, { taper: 0 });
  }
}

const lancer: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  const s = 1;
  // Waist, abdomen and a V-shaped chest.
  t.box(P.dark, [0.28, 0.14, 0.2], [0, 0.0, 0]);
  t.box(P.dark, [0.18, 0.12, 0.15], [0, 0.12, 0]);
  t.box(P.hull, [0.26, 0.12, 0.2], [0, 0.2, 0], { taper: [1.15, 1.05] });
  t.box(P.trim, [0.27, 0.025, 0.21], [0, 0.155, 0], { line: false });
  t.box(P.hull, [0.36, 0.3, 0.27], [0, 0.39, 0], { taper: [1.3, 1.05] });
  t.box(P.hull2, [0.26, 0.24, 0.04], [0, 0.4, 0.14], { taper: [1.35, 1], rot: [-0.08, 0, 0] });
  t.box(P.trim, [0.04, 0.26, 0.02], [0, 0.4, 0.163], { line: false, rot: [-0.08, 0, 0] });
  t.box(P.glow, [0.05, 0.08, 0.02], [0, 0.42, 0.165], { glow: true });
  t.box(P.glow, [0.05, 0.04, 0.02], [0, 0.48, 0.16], { glow: true, taper: [0.1, 1] });
  t.box(P.trim, [0.32, 0.05, 0.24], [0, 0.56, -0.01], { taper: 0.8 });
  // Tabard and faulds.
  cloth(t, P.cloth, [0, -0.02, 0.12], 0.62, 0.17, 0.06, 0.85);
  t.box(P.trim, [0.15, 0.025, 0.03], [0, -0.6, 0.18], { line: false, rot: [0.1, 0, 0] });
  heraldicCross(t, P.accent, [0, -0.22, 0.152], 0.11);
  for (const x of [-1, 1]) {
    t.box(P.hull, [0.12, 0.2, 0.2], [x * 0.17, -0.08, 0], { rot: [0, 0, x * 0.22], taper: [1, 0.9] });
    t.box(P.trim, [0.125, 0.025, 0.205], [x * 0.19, -0.17, 0], { rot: [0, 0, x * 0.22], line: false });
  }
  // Back: pack, short cape and two streamer poles.
  t.box(P.hull, [0.24, 0.24, 0.12], [0, 0.4, -0.18]);
  t.box(P.trim, [0.25, 0.03, 0.13], [0, 0.5, -0.18], { line: false });
  cape(t, P, [0, 0.54, -0.2], 0.9, 0.3, -0.2, 1.55, 0.12);
  // Blade-wings: black, gold-edged fins swept up and back from the pack, crimson streamers hanging off them.
  for (const x of [-1, 1]) {
    t.seg(P.hull, [x * 0.08, 0.4, -0.24], [x * 0.42, 1.12, -0.5], 0.13, 0.03, { taper: [0.05, 1] });
    t.seg(P.trim, [x * 0.04, 0.42, -0.25], [x * 0.38, 1.14, -0.52], 0.03, 0.04, { taper: 0.2 });
    t.seg(P.hull2, [x * 0.1, 0.36, -0.24], [x * 0.5, 0.8, -0.46], 0.12, 0.03, { taper: [0.05, 1] });
    t.seg(P.cloth, [x * 0.3, 0.86, -0.42], [x * 0.33, 0.42, -0.52], 0.07, 0.015, { taper: [0.3, 1] });
  }
  covenantHelm(c.head, P, 1.0, 'fin');
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    covenantPauldron(k, P, 1.0, 'swept');
    k.pop();
  }
  return {
    hipY: 0.92, hipX: 0.14, neck: [0, 0.58, 0.01], shoulder: [0.25, 0.5, 0], lean: 0.04,
    leg: { style: 'knight', len: 0.92, w: 0.13 },
    arm: { style: 'gauntlet', upper: 0.25, fore: 0.24, w: 0.09, heft: 0.9 },
    unarmed: 'idle', mount: [0.15, 0.6, -0.05], back: [0, 0.4, -0.25], height: 2.0 * s,
  };
};

const sentinel: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  // A squat fortress: wide pelvis, a broad chest with a lit gothic window, battlements across the shoulders.
  t.box(P.dark, [0.42, 0.14, 0.3], [0, 0.0, 0]);
  t.box(P.hull, [0.46, 0.14, 0.34], [0, 0.13, 0]);
  t.box(P.trim, [0.47, 0.03, 0.35], [0, 0.19, 0], { line: false });
  t.box(P.hull, [0.7, 0.42, 0.46], [0, 0.42, 0], { taper: [1.08, 1] });
  t.box(P.hull2, [0.5, 0.34, 0.04], [0, 0.42, 0.24]);
  t.box(P.trim, [0.52, 0.03, 0.05], [0, 0.6, 0.24], { line: false });
  t.box(P.trim, [0.52, 0.03, 0.05], [0, 0.25, 0.24], { line: false });
  // Gothic window: an arched lit grille.
  t.box(P.dark, [0.18, 0.24, 0.02], [0, 0.42, 0.262]);
  t.box(P.glow, [0.14, 0.16, 0.02], [0, 0.4, 0.266], { glow: true });
  t.box(P.glow, [0.14, 0.06, 0.02], [0, 0.51, 0.266], { glow: true, taper: [0.1, 1] });
  for (const x of [-0.035, 0.035]) t.box(P.trim, [0.015, 0.2, 0.03], [x, 0.42, 0.272], { line: false });
  t.box(P.trim, [0.15, 0.015, 0.03], [0, 0.4, 0.272], { line: false });
  // Battlements.
  for (let i = 0; i < 5; i++) t.box(P.hull2, [0.09, 0.08, 0.1], [-0.28 + i * 0.14, 0.67, 0.18], { taper: [1, 1] });
  t.box(P.trim, [0.72, 0.03, 0.12], [0, 0.635, 0.18], { line: false });
  // Tabard, faulds.
  cloth(t, P.cloth, [0, 0.06, 0.18], 0.48, 0.24, 0.05, 0.9);
  heraldicCross(t, P.accent, [0, -0.12, 0.205], 0.14);
  t.box(P.trim, [0.22, 0.025, 0.03], [0, -0.41, 0.235], { line: false });
  for (const x of [-1, 1]) {
    t.box(P.hull, [0.16, 0.22, 0.3], [x * 0.24, -0.04, 0], { rot: [0, 0, x * 0.18] });
    t.box(P.trim, [0.165, 0.025, 0.305], [x * 0.26, -0.14, 0], { rot: [0, 0, x * 0.18], line: false });
  }
  // The great banner on a T-pole, raised from the back.
  t.box(P.hull, [0.34, 0.34, 0.16], [0, 0.42, -0.3]);
  t.box(P.trim, [0.35, 0.03, 0.17], [0, 0.56, -0.3], { line: false });
  t.seg(P.dark, [0.3, 0.35, -0.34], [0.3, 1.6, -0.34], 0.04, 0.04);
  t.box(P.trim, [0.5, 0.04, 0.04], [0.3, 1.5, -0.34]);
  t.seg(P.trim, [0.3, 1.6, -0.34], [0.3, 1.75, -0.34], 0.07, 0.07, { taper: 0 });
  for (const x of [0.07, 0.53]) t.box(P.trim, [0.05, 0.05, 0.05], [x, 1.5, -0.34], { rot: [0, 0, Math.PI / 4] });
  t.box(P.cloth, [0.42, 0.55, 0.02], [0.3, 1.2, -0.34]);
  t.seg(P.cloth, [0.3, 0.925, -0.34], [0.3, 0.8, -0.34], 0.42, 0.02, { taper: [0.05, 1] });
  t.box(P.trim, [0.43, 0.025, 0.025], [0.3, 1.46, -0.34], { line: false });
  for (const zz of [-0.352, -0.328]) heraldicCross(t, P.trim, [0.3, 1.18, zz], 0.2);
  covenantHelm(c.head, P, 1.05, 'bucket');
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    covenantPauldron(k, P, 1.0, 'tower');
    k.pop();
  }
  return {
    hipY: 0.66, hipX: 0.22, neck: [0, 0.66, 0.1], shoulder: [0.42, 0.52, 0],
    leg: { style: 'knight', len: 0.66, w: 0.19 },
    arm: { style: 'gauntlet', upper: 0.25, fore: 0.26, w: 0.14, heft: 1.1 },
    unarmed: 'idle', mount: [0.22, 0.7, -0.05], back: [0, 0.42, -0.38], height: 1.9,
  };
};

const paladin: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  t.box(P.dark, [0.42, 0.16, 0.3], [0, 0.0, 0]);
  t.box(P.dark, [0.3, 0.14, 0.24], [0, 0.14, 0]);
  t.box(P.hull, [0.42, 0.16, 0.32], [0, 0.24, 0], { taper: [1.2, 1.05] });
  t.box(P.trim, [0.44, 0.03, 0.33], [0, 0.18, 0], { line: false });
  t.box(P.hull, [0.62, 0.42, 0.42], [0, 0.52, 0], { taper: [1.28, 1.05] });
  t.box(P.hull2, [0.48, 0.34, 0.05], [0, 0.53, 0.22], { taper: [1.3, 1], rot: [-0.1, 0, 0] });
  // Gold sunburst on the breastplate, a lit furnace heart at its centre.
  t.at([0, 0.55, 0.252], [-0.1, 0, 0], () => {
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      t.box(P.trim, [0.025, 0.2, 0.012], [Math.sin(a) * 0.05, Math.cos(a) * 0.05, 0], { rot: [0, 0, -a], taper: [0.2, 1], line: false });
    }
    t.box(P.dark, [0.09, 0.09, 0.02], [0, 0, 0.004], { rot: [0, 0, Math.PI / 4] });
    t.box(P.glow, [0.06, 0.06, 0.02], [0, 0, 0.01], { glow: true, rot: [0, 0, Math.PI / 4] });
  });
  t.box(P.trim, [0.5, 0.06, 0.36], [0, 0.74, -0.01], { taper: 0.85 });
  // Tabard, faulds, long crimson cape.
  cloth(t, P.cloth, [0, 0.0, 0.18], 0.74, 0.24, 0.1, 0.85);
  t.box(P.trim, [0.21, 0.025, 0.03], [0, -0.72, 0.29], { line: false, rot: [0.13, 0, 0] });
  heraldicCross(t, P.accent, [0, -0.25, 0.212], 0.16);
  for (const x of [-1, 1]) {
    t.box(P.hull, [0.18, 0.28, 0.32], [x * 0.25, -0.08, 0], { rot: [0, 0, x * 0.2], taper: [1, 0.9] });
    t.box(P.trim, [0.185, 0.03, 0.325], [x * 0.28, -0.21, 0], { rot: [0, 0, x * 0.2], line: false });
  }
  cape(t, P, [0, 0.72, -0.28], 1.45, 0.56, -0.32, 1.4, 0.2);
  // Cathedral spires rising from the back.
  t.box(P.hull, [0.46, 0.3, 0.16], [0, 0.6, -0.3]);
  spire(t, P, 0, 0.72, -0.34, 0.85, 0.12);
  spire(t, P, 0.17, 0.66, -0.32, 0.6, 0.09);
  spire(t, P, -0.17, 0.66, -0.32, 0.6, 0.09);
  spire(t, P, 0.3, 0.6, -0.3, 0.38, 0.07);
  spire(t, P, -0.3, 0.6, -0.3, 0.38, 0.07);
  covenantHelm(c.head, P, 1.2, 'crown');
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    covenantPauldron(k, P, 1.25, 'sunburst');
    k.pop();
  }
  return {
    hipY: 0.96, hipX: 0.21, neck: [0, 0.76, 0.03], shoulder: [0.4, 0.66, 0],
    leg: { style: 'knight', len: 0.96, w: 0.2 },
    arm: { style: 'gauntlet', upper: 0.32, fore: 0.3, w: 0.15, heft: 1.3 },
    unarmed: 'idle', mount: [0.24, 0.8, -0.05], back: [0, 0.55, -0.4], height: 2.6,
  };
};

// --- Ashen Foundries -------------------------------------------------------------------------------------------------

/** Foundry head: a riveted welding-mask box with a slot eye or a cyclops lamp. */
function foundryHead(k: Kit, P: Palette, s: number, kind: 'slot' | 'cyclops' | 'sensor') {
  if (kind === 'sensor') {
    k.box(P.hull2, [0.16 * s, 0.1 * s, 0.16 * s], [0, 0.05 * s, 0]);
    k.box(P.dark, [0.1 * s, 0.1 * s, 0.08 * s], [0.04 * s, 0.07 * s, 0.1 * s]);
    k.box(P.glow, [0.06 * s, 0.06 * s, 0.01], [0.04 * s, 0.07 * s, 0.145 * s], { glow: true });
    k.box(P.dark, [0.06 * s, 0.06 * s, 0.06 * s], [-0.05 * s, 0.06 * s, 0.1 * s]);
    k.box(P.glow, [0.035 * s, 0.035 * s, 0.01], [-0.05 * s, 0.06 * s, 0.135 * s], { glow: true });
    k.seg(P.metal, [-0.05 * s, 0.1 * s, -0.04 * s], [-0.08 * s, 0.55 * s, -0.08 * s], 0.02, 0.02);
    k.box(P.cloth, [0.05, 0.05, 0.05], [-0.08 * s, 0.56 * s, -0.08 * s], { rot: [0.5, 0.5, 0] });
    k.seg(P.metal, [0.05 * s, 0.1 * s, -0.04 * s], [0.06 * s, 0.32 * s, -0.04 * s], 0.02, 0.02);
    k.box(P.trim, [0.18 * s, 0.1 * s, 0.02], [0.06 * s, 0.34 * s, -0.04 * s], { rot: [0.3, 0, 0] }); // dish
    return;
  }
  k.box(P.hull2, [0.2 * s, 0.15 * s, 0.2 * s], [0, 0.07 * s, 0], { taper: [0.9, 0.85] });
  k.box(P.dark, [0.16 * s, 0.09 * s, 0.03], [0, 0.07 * s, 0.1 * s]);
  if (kind === 'slot') k.box(P.glow, [0.13 * s, 0.03 * s, 0.01], [0, 0.08 * s, 0.117 * s], { glow: true });
  else {
    k.box(P.glow, [0.06 * s, 0.06 * s, 0.01], [0, 0.08 * s, 0.117 * s], { glow: true });
    k.box(P.trim, [0.09 * s, 0.09 * s, 0.02], [0, 0.08 * s, 0.112 * s]);
  }
  for (const y of [0.02, 0.035]) k.box(P.metal, [0.14 * s, 0.008, 0.01], [0, y * s, 0.118 * s], { line: false });
  rivets(k, P.trim, [[-0.08 * s, 0.13 * s, 0.09 * s], [0.08 * s, 0.13 * s, 0.09 * s]]);
}

/** Furnace chest: a dark frame, a glowing core and grille bars. pos is the front-face centre. */
function furnace(k: Kit, P: Palette, pos: V3, w: number, h: number) {
  k.box(P.dark, [w * 1.25, h * 1.25, 0.05], [pos[0], pos[1], pos[2]]);
  k.box(P.glow, [w, h, 0.02], [pos[0], pos[1], pos[2] + 0.02], { glow: true });
  k.box(0xffd27a, [w * 0.45, h * 0.45, 0.02], [pos[0], pos[1], pos[2] + 0.024], { glow: true });
  const n = 4;
  for (let i = 0; i < n; i++) k.box(P.dark, [w / (n * 3), h * 1.05, 0.02], [pos[0] - w / 2 + (w / n) * (i + 0.5), pos[1], pos[2] + 0.035], { line: false });
  k.box(P.trim, [w * 1.3, 0.025, 0.06], [pos[0], pos[1] + h * 0.64, pos[2] + 0.005], { line: false });
  k.box(P.trim, [w * 1.3, 0.025, 0.06], [pos[0], pos[1] - h * 0.64, pos[2] + 0.005], { line: false });
}

/** A signal-red hull plate with a stencilled number, on a plane facing +Z centred on pos. */
function numberPlate(k: Kit, P: Palette, pos: V3, w: number, h: number, text: string) {
  k.box(P.cloth, [w, h, 0.03], pos);
  k.box(P.clothDk, [w, h * 0.12, 0.032], [pos[0], pos[1] - h * 0.44, pos[2]], { line: false });
  stencil(k, text, P.accent, [pos[0], pos[1] + h * 0.04, pos[2] + 0.017], Math.min(w / (text.length * 4 + 1), h / 7));
  rivets(k, P.dark, [[pos[0] - w * 0.42, pos[1] + h * 0.4, pos[2] + 0.016], [pos[0] + w * 0.42, pos[1] + h * 0.4, pos[2] + 0.016]], 0.018);
}

const brute: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  // A hunched furnace-gorilla: tiny legs, an enormous barrel chest and shoulders, head sunk low at the front.
  t.box(P.dark, [0.5, 0.16, 0.36], [0, 0.02, 0]);
  t.box(P.hull2, [0.6, 0.16, 0.42], [0, 0.14, 0.0]);
  hazard(t, P, 0.58, 0.05, [0, 0.14, 0.215], 8);
  t.box(P.hull, [0.86, 0.5, 0.62], [0, 0.46, 0], { taper: [1.12, 0.92] });
  t.box(P.hull2, [0.92, 0.12, 0.66], [0, 0.73, -0.02], { taper: [0.82, 0.85] });
  t.box(P.dark, [0.3, 0.03, 0.26], [0, 0.8, 0.02]); // engine grille
  for (let i = 0; i < 4; i++) t.box(P.glow, [0.26, 0.012, 0.03], [0, 0.812, -0.07 + i * 0.06], { glow: true });
  for (let i = 0; i < 5; i++) t.box(P.metal, [0.28, 0.02, 0.018], [0, 0.82, -0.1 + i * 0.06], { line: false });
  rivets(t, P.trim, [[-0.3, 0.8, 0.2], [0.3, 0.8, 0.2], [-0.3, 0.8, -0.2], [0.3, 0.8, -0.2]]);
  furnace(t, P, [0, 0.42, 0.315], 0.24, 0.2);
  numberPlate(t, P, [0.29, 0.52, 0.31], 0.2, 0.24, '07');
  numberPlate(t, P, [-0.29, 0.52, 0.31], 0.2, 0.24, '07');
  rivets(t, P.trim, [[-0.4, 0.3, 0.29], [0.4, 0.3, 0.29], [-0.4, 0.66, 0.31], [0.4, 0.66, 0.31], [0, 0.66, 0.32]]);
  // Skirt plates.
  for (const x of [-0.22, 0, 0.22]) t.box(P.hull2, [0.2, 0.22, 0.05], [x, -0.04, 0.22], { rot: [0.12, 0, 0] });
  for (const x of [-1, 1]) t.box(P.hull2, [0.05, 0.22, 0.34], [x * 0.33, -0.04, 0], { rot: [0, 0, x * 0.15] });
  // Back: boiler drum and twin smokestacks.
  t.box(P.metal, [0.6, 0.4, 0.22], [0, 0.48, -0.38]);
  for (const y of [0.36, 0.6]) t.box(P.trim, [0.62, 0.03, 0.24], [0, y, -0.38], { line: false });
  t.box(P.glow, [0.3, 0.04, 0.01], [0, 0.42, -0.495], { glow: true });
  gearBadge(t, P.trim, [0, 0.54, -0.495], 0.12);
  hazard(t, P, 0.5, 0.05, [0, 0.29, -0.5], 7);
  rivets(t, P.trim, [[-0.27, 0.66, -0.49], [0.27, 0.66, -0.49], [-0.27, 0.3, -0.49], [0.27, 0.3, -0.49]]);
  smokestack(t, P, 0.2, 0.7, -0.36, 0.55, 0.1);
  smokestack(t, P, -0.2, 0.7, -0.36, 0.45, 0.1);
  foundryHead(c.head, P, 1.0, 'slot');
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    // Huge hunched pauldron rising above the hull, a signal-red cap with a stencilled stripe.
    k.box(P.hull, [0.34, 0.34, 0.42], [0.04, 0.08, 0], { taper: [0.75, 0.8] });
    k.box(P.cloth, [0.27, 0.1, 0.35], [0.04, 0.27, 0], { taper: [0.8, 0.85] });
    k.box(P.accent, [0.3, 0.025, 0.38], [0.04, 0.2, 0], { line: false });
    k.box(P.hull2, [0.36, 0.08, 0.44], [0.04, -0.1, 0]);
    rivets(k, P.dark, [[0.22, 0.04, 0.12], [0.22, 0.04, -0.12], [0.22, -0.04, 0]]);
    k.box(P.cloth, [0.02, 0.14, 0.16], [0.215, 0.06, 0]);
    k.at([0.226, 0.06, 0], [0, Math.PI / 2, 0], () => {
      k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]); // un-mirror the lettering on the right side
      stencil(k, '07', P.accent, [0, 0, 0], 0.016);
      k.pop();
    });
    k.pop();
  }
  return {
    hipY: 0.5, hipX: 0.25, neck: [0, 0.64, 0.28], shoulder: [0.55, 0.6, 0.02], lean: 0.22,
    leg: { style: 'piston', len: 0.5, w: 0.2 },
    arm: { style: 'hydraulic', upper: 0.24, fore: 0.32, w: 0.15, heft: 1.2 },
    unarmed: 'idle', mount: [0.25, 0.8, -0.1], back: [0, 0.45, -0.5], height: 1.75,
  };
};

const artillery: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  // A walking gun platform on bird legs: a wide armoured hull carrying a huge siege cannon.
  t.box(P.dark, [0.42, 0.14, 0.36], [0, 0.0, 0]);
  t.box(P.hull, [0.7, 0.36, 0.66], [0, 0.26, 0], { taper: [0.95, 0.88] });
  t.box(P.hull2, [0.74, 0.1, 0.7], [0, 0.1, 0]);
  hazard(t, P, 0.7, 0.05, [0, 0.1, 0.355], 9);
  numberPlate(t, P, [-0.2, 0.3, 0.3], 0.2, 0.2, '12');
  furnace(t, P, [0.15, 0.27, 0.295], 0.12, 0.1);
  rivets(t, P.trim, [[-0.32, 0.4, 0.27], [0.32, 0.4, 0.27], [0, 0.42, 0.26]]);
  // The siege cannon on a turret ring, angled up over the front.
  t.at([0, 0.5, -0.1], [-0.45, 0, 0], () => {
    t.box(P.hull2, [0.32, 0.2, 0.44], [0, 0.0, 0]);
    t.box(P.cloth, [0.33, 0.08, 0.3], [0, 0.07, -0.04], { line: false });
    stencil(t, '12', P.accent, [0, 0.07, 0.225], 0.014);
    t.box(P.metal, [0.2, 0.2, 0.7], [0, 0.03, 0.55]);
    t.box(P.metal, [0.15, 0.15, 0.9], [0, 0.03, 1.2]);
    for (const z of [0.3, 0.6, 0.92, 1.3]) t.box(P.trim, [z < 0.9 ? 0.24 : 0.19, z < 0.9 ? 0.24 : 0.19, 0.05], [0, 0.03, z]);
    t.box(P.dark, [0.24, 0.24, 0.24], [0, 0.03, 1.72]);
    for (const z of [1.66, 1.76]) t.box(P.dark, [0.3, 0.07, 0.04], [0, 0.03, z]);
    t.box(P.glow, [0.1, 0.1, 0.01], [0, 0.03, 1.841], { glow: true });
    t.seg(P.metal, [0.12, -0.05, 0.1], [0.12, 0.0, 0.6], 0.05, 0.05); // recoil piston
    t.seg(P.metal, [-0.12, -0.05, 0.1], [-0.12, 0.0, 0.6], 0.05, 0.05);
  });
  t.box(P.metal, [0.36, 0.06, 0.36], [0, 0.45, -0.05]);
  // Back: ammo hopper, smokestacks.
  t.box(P.metal, [0.5, 0.3, 0.2], [0, 0.3, -0.4]);
  for (let i = 0; i < 4; i++) t.box(P.trim, [0.07, 0.07, 0.12], [-0.17 + i * 0.113, 0.3, -0.52], { rot: [Math.PI / 2, 0, 0], taper: 0.5 });
  smokestack(t, P, 0.27, 0.42, -0.3, 0.42, 0.09);
  smokestack(t, P, -0.27, 0.42, -0.3, 0.5, 0.09);
  foundryHead(c.head, P, 0.9, 'cyclops');
  c.head.seg(P.metal, [0.08, 0.12, -0.04], [0.11, 0.38, -0.08], 0.02, 0.02); // rangefinder mast
  c.head.box(P.dark, [0.12, 0.05, 0.05], [0.11, 0.38, -0.08]);
  c.head.box(P.glow, [0.03, 0.03, 0.01], [0.16, 0.38, -0.05], { glow: true });
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    k.box(P.hull2, [0.2, 0.16, 0.26], [0.04, 0.04, 0]);
    k.box(P.cloth, [0.21, 0.05, 0.27], [0.04, 0.1, 0], { line: false });
    k.pop();
  }
  return {
    hipY: 0.7, hipX: 0.24, neck: [0, 0.42, 0.26], shoulder: [0.4, 0.3, 0.06],
    leg: { style: 'bird', len: 0.7, w: 0.15 },
    arm: { style: 'hydraulic', upper: 0.16, fore: 0.24, w: 0.11, heft: 1.05 },
    unarmed: 'idle', mount: [0.3, 0.46, -0.12], back: [0, 0.3, -0.5], height: 1.9,
  };
};

const scavenger: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  // A scuttling four-legged salvager: low cab, fuel drum, sensor mast and long crane arms.
  t.box(P.dark, [0.32, 0.1, 0.3], [0, 0.0, 0]);
  t.box(P.hull, [0.38, 0.22, 0.4], [0, 0.14, 0.02], { taper: [0.9, 0.8] });
  t.box(P.hull2, [0.4, 0.06, 0.42], [0, 0.04, 0.02]);
  hazard(t, P, 0.38, 0.04, [0, 0.04, 0.235], 7);
  numberPlate(t, P, [0.0, 0.16, 0.2], 0.14, 0.12, '03');
  // Back: fuel drum and a single stack.
  t.box(P.metal, [0.26, 0.18, 0.18], [0, 0.18, -0.22], { rot: [0, 0, Math.PI / 2] });
  for (const x of [-0.09, 0.09]) t.box(P.trim, [0.03, 0.19, 0.19], [x, 0.18, -0.22], { rot: [0, 0, Math.PI / 2], line: false });
  t.box(P.cloth, [0.1, 0.1, 0.01], [0, 0.18, -0.315], { line: false });
  smokestack(t, P, -0.12, 0.25, -0.18, 0.32, 0.07);
  // Salvage crane: a hazard-striped boom rising over the back, a cable and a hook.
  t.box(P.dark, [0.1, 0.08, 0.1], [0.12, 0.28, -0.12]);
  t.seg(P.hazard, [0.12, 0.3, -0.12], [0.16, 0.85, -0.02], 0.045, 0.045);
  t.seg(P.dark, [0.16, 0.85, -0.02], [0.17, 0.82, 0.3], 0.04, 0.04);
  t.box(P.trim, [0.06, 0.06, 0.06], [0.16, 0.85, -0.02], { rot: [0, Math.PI / 4, 0] });
  t.seg(P.metal, [0.17, 0.81, 0.3], [0.17, 0.55, 0.32], 0.012, 0.012, { line: false });
  t.seg(P.trim, [0.17, 0.56, 0.32], [0.17, 0.48, 0.36], 0.03, 0.03, { taper: 0.4 });
  t.seg(P.trim, [0.17, 0.48, 0.36], [0.17, 0.5, 0.29], 0.025, 0.025, { taper: 0.2 });
  foundryHead(c.head, P, 1.0, 'sensor');
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    k.box(P.hull2, [0.12, 0.1, 0.14], [0.02, 0.02, 0]);
    k.box(P.hazard, [0.125, 0.025, 0.145], [0.02, 0.06, 0], { line: false });
    k.pop();
  }
  return {
    hipY: 0.42, hipX: 0.17, neck: [0, 0.25, 0.14], shoulder: [0.22, 0.2, 0.14],
    leg: { style: 'spider', len: 0.42, w: 0.1 },
    arm: { style: 'hydraulic', upper: 0.22, fore: 0.28, w: 0.06, heft: 0.75 },
    unarmed: 'idle', mount: [0.13, 0.27, -0.05], back: [0, 0.2, -0.3], height: 1.3,
  };
};

// --- Reliquary -------------------------------------------------------------------------------------------------------

/** Hooded relic mask: a deep hood, a dark face recess, a long gold or bone mask with two teal eyes. */
function reliquaryHood(k: Kit, P: Palette, s: number, mask: 'gold' | 'bone' | 'beak') {
  k.box(P.dark, [0.08 * s, 0.08 * s, 0.08 * s], [0, 0.02 * s, 0]);
  k.box(P.hull, [0.2 * s, 0.26 * s, 0.22 * s], [0, 0.13 * s, -0.01 * s], { taper: [0.3, 0.55], shift: [0, -0.04 * s] });
  k.box(P.trim, [0.21 * s, 0.03 * s, 0.03 * s], [0, 0.04 * s, 0.1 * s], { line: false });
  k.seg(P.trim, [0, 0.03 * s, 0.11 * s], [0, 0.25 * s, 0.03 * s], 0.025 * s, 0.025 * s, { line: false }); // hood seam
  k.box(P.dark, [0.13 * s, 0.15 * s, 0.03], [0, 0.11 * s, 0.098 * s], { taper: [0.7, 1] });
  const mc = mask === 'bone' ? P.hull2 : P.trim;
  if (mask === 'beak') {
    k.box(mc, [0.08 * s, 0.11 * s, 0.04 * s], [0, 0.1 * s, 0.11 * s], { taper: [1.2, 1] });
    k.seg(mc, [0, 0.07 * s, 0.12 * s], [0, -0.02 * s, 0.17 * s], 0.06 * s, 0.04 * s, { taper: 0.1 });
  } else {
    k.box(mc, [0.08 * s, 0.13 * s, 0.03 * s], [0, 0.1 * s, 0.11 * s], { taper: [1.3, 1] });
    k.seg(mc, [0, 0.04 * s, 0.11 * s], [0, -0.01 * s, 0.11 * s], 0.06 * s, 0.03 * s, { taper: 0.15 });
  }
  for (const x of [-1, 1]) k.box(P.glow, [0.025 * s, 0.018 * s, 0.01], [x * 0.022 * s, 0.13 * s, 0.128 * s], { glow: true });
  k.box(P.trim, [0.012 * s, 0.06 * s, 0.01], [0, 0.07 * s, 0.128 * s], { line: false });
}

/** Robe strips hanging from the waist all round, uneven like tattered vestments. */
function robes(k: Kit, P: Palette, w: number, d: number, len: number, front = true) {
  const strips: [number, number, number, number][] = [
    [0, d / 2 + 0.01, len, w * 0.4],
    [-w * 0.32, d / 2 - 0.01, len * 0.8, w * 0.22],
    [w * 0.32, d / 2 - 0.01, len * 0.85, w * 0.22],
    [0, -d / 2 - 0.01, len * 1.05, w * 0.5],
    [-w * 0.35, -d / 2, len * 0.9, w * 0.24],
    [w * 0.35, -d / 2, len * 0.75, w * 0.24],
  ];
  strips.forEach(([x, z, l, sw], i) => {
    if (!front && i < 3) return;
    const back = z < 0;
    cloth(k, i === 0 ? P.cloth : P.clothDk, [x, 0, z], l, sw, back ? -0.08 : 0.05, i === 0 ? 0.6 : 0.4);
    if (i === 0) {
      k.box(P.trim, [sw * 1.02, 0.025, 0.03], [x, -0.03, z + 0.005], { line: false });
      k.box(P.trim, [0.02, l * 0.7, 0.03], [x, -l * 0.42, z + 0.02 + 0.03 * 0.3], { line: false, rot: [-0.05, 0, 0] });
    }
  });
}

/** Ribcage torso: a dark core, bone ribs across it and a teal soul-heart. y is the cage centre. */
function ribcage(k: Kit, P: Palette, w: number, h: number, d: number, y: number) {
  k.box(P.dark, [w * 0.7, h, d * 0.8], [0, y, 0], { taper: [1.25, 1] });
  k.box(P.glow, [w * 0.18, w * 0.18, 0.02], [0, y + h * 0.05, d * 0.42], { glow: true, rot: [0, 0, Math.PI / 4] });
  const n = 4;
  for (let i = 0; i < n; i++) {
    const yy = y - h * 0.38 + (h * 0.8 * i) / (n - 1);
    const ww = w * (0.75 + 0.3 * (i / (n - 1)));
    for (const x of [-1, 1]) k.box(P.hull, [ww * 0.46, h * 0.09, d * 0.95], [x * ww * 0.27, yy, 0], { rot: [0, 0, x * -0.25] });
  }
  k.box(P.hull2, [w * 0.12, h * 1.05, d * 0.3], [0, y, d * 0.38]); // sternum
  k.box(P.trim, [w * 0.13, h * 0.08, d * 0.32], [0, y + h * 0.48, d * 0.38], { line: false });
}

const seer: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  t.box(P.trim, [0.22, 0.08, 0.16], [0, 0.0, 0]);
  t.box(P.dark, [0.08, 0.2, 0.08], [0, 0.12, 0]); // spine
  ribcage(t, P, 0.36, 0.3, 0.22, 0.37);
  t.box(P.hull, [0.4, 0.07, 0.24], [0, 0.55, 0], { taper: 0.8 });
  t.box(P.trim, [0.42, 0.03, 0.26], [0, 0.59, 0], { line: false });
  // Mantle and tall collar.
  t.box(P.hull, [0.3, 0.14, 0.12], [0, 0.6, -0.1], { taper: [0.8, 1] });
  robes(t, P, 0.28, 0.18, 0.78);
  // Back: a reliquary censer-rack with three small spires.
  t.box(P.dark, [0.2, 0.26, 0.08], [0, 0.4, -0.15]);
  for (const x of [-0.08, 0.08]) t.seg(P.trim, [x, 0.3, -0.2], [x * 1.4, 0.95, -0.24], 0.025, 0.025, { taper: 0.4 });
  // Floating relic shards around the head.
  for (let i = 0; i < 3; i++) {
    const a = (i / 3) * Math.PI * 2 + 0.4;
    c.float.box(P.trim, [0.05, 0.08, 0.05], [Math.cos(a) * 0.3, 0.9 + (i % 2) * 0.08, Math.sin(a) * 0.25 - 0.05], { rot: [0.3, a, 0.3], taper: [0.1, 0.1] });
    c.float.box(P.glow, [0.025, 0.025, 0.025], [Math.cos(a) * 0.3, 0.86 + (i % 2) * 0.08, Math.sin(a) * 0.25 - 0.05], { glow: true });
  }
  reliquaryHood(c.head, P, 1.0, 'gold');
  halo(c.halo, P, 0.28, 12, 0.16, 0.035);
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    k.box(P.hull, [0.12, 0.08, 0.14], [0.03, 0.04, 0], { rot: [0, 0, -0.4], taper: [0.6, 0.8] });
    k.seg(P.trim, [0.06, 0.06, 0], [0.12, 0.2, -0.02], 0.025, 0.025, { taper: 0 });
    k.pop();
  }
  return {
    hipY: 1.0, hipX: 0.1, neck: [0, 0.62, 0.0], shoulder: [0.22, 0.55, 0], halo: [0, 0.2, -0.1],
    leg: { style: 'relic', len: 1.0, w: 0.085 },
    arm: { style: 'bone', upper: 0.36, fore: 0.32, w: 0.07, heft: 0.95 },
    unarmed: 'staff', mount: [0.14, 0.64, -0.08], back: [0, 0.4, -0.2], height: 2.15,
  };
};

const wraith: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  t.box(P.trim, [0.2, 0.07, 0.14], [0, 0.0, 0]);
  t.box(P.dark, [0.07, 0.2, 0.07], [0, 0.12, 0]);
  ribcage(t, P, 0.3, 0.26, 0.18, 0.34);
  t.box(P.hull, [0.34, 0.06, 0.2], [0, 0.5, -0.01], { taper: 0.8 });
  // High hunched shoulders and a tattered cloak streaming back.
  t.box(P.clothDk, [0.42, 0.14, 0.18], [0, 0.52, -0.08], { taper: [0.7, 1] });
  for (const x of [-1, 1]) t.seg(P.hull, [x * 0.14, 0.52, -0.1], [x * 0.3, 0.78, -0.2], 0.05, 0.05, { taper: 0 }); // shoulder spines
  for (let i = 0; i < 5; i++) {
    const x = -0.16 + i * 0.08;
    cloth(t, i % 2 ? P.metal : P.clothDk, [x, 0.5, -0.12], 0.75 + (i % 3) * 0.15, 0.09, -0.35 - (i % 2) * 0.1, 0.25, 0.02);
  }
  for (const x of [-0.1, 0.1]) cloth(t, P.clothDk, [x, 0, 0.08], 0.45, 0.08, 0.05, 0.3, 0.02);
  reliquaryHood(c.head, P, 1.15, 'beak');
  halo(c.halo, P, 0.21, 10, 0.12, 0.032, 2);
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    k.seg(P.hull, [0.0, 0.0, 0.0], [0.08, 0.2, -0.1], 0.06, 0.06, { taper: 0 });
    k.seg(P.trim, [0.04, 0.02, 0.0], [0.16, 0.12, -0.12], 0.035, 0.035, { taper: 0 });
    k.pop();
  }
  return {
    hipY: 0.82, hipX: 0.09, neck: [0, 0.54, 0.06], shoulder: [0.2, 0.47, 0.0], halo: [0, 0.2, -0.11], lean: 0.38, scale: 1.12,
    leg: { style: 'bird', len: 0.82, w: 0.075 },
    arm: { style: 'bone', upper: 0.4, fore: 0.36, w: 0.06, heft: 1.0 },
    unarmed: 'talon', mount: [0.12, 0.55, -0.08], back: [0, 0.35, -0.16], height: 1.8,
  };
};

const goliath: ClassBuilder = (c) => {
  const { P, torso: t } = c;
  t.box(P.trim, [0.4, 0.14, 0.28], [0, 0.0, 0]);
  t.box(P.dark, [0.16, 0.2, 0.14], [0, 0.14, 0]);
  ribcage(t, P, 0.56, 0.36, 0.34, 0.42);
  t.box(P.hull, [0.4, 0.3, 0.06], [0, 0.44, 0.17], { taper: [1.3, 1] }); // breastplate over the cage
  t.box(P.glow, [0.08, 0.08, 0.02], [0, 0.46, 0.205], { glow: true, rot: [0, 0, Math.PI / 4] });
  t.box(P.trim, [0.12, 0.12, 0.02], [0, 0.46, 0.2], { rot: [0, 0, Math.PI / 4] });
  t.box(P.trim, [0.04, 0.3, 0.02], [0, 0.44, 0.206], { line: false });
  t.box(P.hull, [0.64, 0.1, 0.36], [0, 0.65, 0], { taper: 0.8 });
  t.box(P.trim, [0.66, 0.03, 0.38], [0, 0.7, 0], { line: false });
  robes(t, P, 0.44, 0.3, 0.92);
  // Wing-blades: tall flared bone vanes rising behind the shoulders.
  for (const x of [-1, 1]) {
    // Each vane is a flat blade in the XY plane: wide at the root, tapering to a point.
    t.seg(P.hull, [x * 0.18, 0.6, -0.22], [x * 0.6, 1.4, -0.3], 0.26, 0.04, { taper: [0.05, 1] });
    t.seg(P.trim, [x * 0.1, 0.62, -0.25], [x * 0.52, 1.42, -0.32], 0.04, 0.05, { taper: 0.3 });
    t.seg(P.hull2, [x * 0.22, 0.55, -0.24], [x * 0.78, 1.0, -0.3], 0.2, 0.035, { taper: [0.05, 1] });
    t.seg(P.trim, [x * 0.18, 0.5, -0.26], [x * 0.76, 0.95, -0.32], 0.03, 0.04, { taper: 0.3 });
    t.seg(P.hull2, [x * 0.24, 0.48, -0.24], [x * 0.7, 0.62, -0.28], 0.14, 0.03, { taper: [0.05, 1] });
    t.box(P.glow, [0.05, 0.05, 0.05], [x * 0.36, 0.98, -0.26], { glow: true, rot: [0, 0, Math.PI / 4] });
  }
  t.box(P.dark, [0.34, 0.32, 0.12], [0, 0.48, -0.22]);
  t.seg(P.trim, [0, 0.5, -0.28], [0, 1.55, -0.3], 0.04, 0.04);
  t.box(P.trim, [0.18, 0.03, 0.03], [0, 1.4, -0.3]);
  t.seg(P.trim, [0, 1.55, -0.3], [0, 1.68, -0.3], 0.07, 0.07, { taper: 0 });
  reliquaryHood(c.head, P, 1.2, 'bone');
  halo(c.halo, P, 0.3, 16, 0.18, 0.04);
  for (const [k, sgn] of [[c.armL, 1], [c.armR, -1]] as const) {
    k.push([0, 0, 0], [0, 0, 0], [sgn, 1, 1]);
    k.box(P.hull, [0.26, 0.14, 0.3], [0.05, 0.06, 0], { rot: [0, 0, -0.35], taper: [0.6, 0.8] });
    k.box(P.trim, [0.27, 0.03, 0.31], [0.06, 0.0, 0], { rot: [0, 0, -0.35], line: false });
    k.seg(P.hull2, [0.1, 0.0, 0], [0.26, -0.16, 0.0], 0.06, 0.26, { taper: [0.3, 1] });
    k.pop();
  }
  return {
    hipY: 1.02, hipX: 0.17, neck: [0, 0.72, 0.02], shoulder: [0.38, 0.62, 0], halo: [0, 0.2, -0.1],
    leg: { style: 'relic', len: 1.02, w: 0.13 },
    arm: { style: 'bone', upper: 0.4, fore: 0.36, w: 0.11, heft: 1.25 },
    unarmed: 'talon', mount: [0.24, 0.72, -0.1], back: [0, 0.5, -0.3], height: 2.7,
  };
};

const CLASSES: Record<string, ClassBuilder> = { lancer, sentinel, paladin, brute, artillery, scavenger, seer, wraith, goliath };

/** Core-mounted systems on the torso (shoulder weapons, lanterns, drones and the like). */
function coreSystems(c: Ctx, L: Layout) {
  const { P, torso: t } = c;
  const core = c.items.core ?? [];
  const [mx, my, mz] = L.mount;
  const [bx, by, bz] = L.back;
  const sc = L.height / 2;
  if (core.includes('carapace-gun')) {
    // Shoulder-mounted on the right, on a little turret.
    t.box(P.dark, [0.12 * sc, 0.08 * sc, 0.12 * sc], [-mx, my + 0.02, mz]);
    t.push([-mx, my + 0.12 * sc, mz + 0.02]);
    weapon(t, P, c.faction, 'carapace-gun', 0.9 * sc, 0.1);
    t.pop();
  }
  if (core.includes('soul-lantern')) {
    // Hung from a gold crook arching over the left shoulder.
    t.seg(P.trim, [mx, my - 0.05, mz - 0.05], [mx + 0.05, my + 0.55 * sc, mz - 0.1], 0.03, 0.03);
    t.seg(P.trim, [mx + 0.05, my + 0.55 * sc, mz - 0.1], [mx + 0.3 * sc, my + 0.6 * sc, mz - 0.02], 0.03, 0.03);
    t.seg(P.trim, [mx + 0.3 * sc, my + 0.6 * sc, mz - 0.02], [mx + 0.32 * sc, my + 0.52 * sc, mz], 0.02, 0.02);
    c.float.push([mx + 0.32 * sc, my + 0.38 * sc, mz]);
    soulLantern(c.float, P, 1.0 * sc);
    c.float.pop();
  }
  if (core.includes('spotter-drone')) {
    c.float.push([-mx - 0.15, my + 0.55 * sc, mz + 0.1]);
    c.float.box(P.hull2, [0.12, 0.06, 0.12], [0, 0, 0]);
    c.float.box(P.glow, [0.04, 0.03, 0.01], [0, 0, 0.065], { glow: true });
    c.float.box(P.dark, [0.3, 0.012, 0.03], [0, 0.05, 0], { line: false });
    c.float.box(P.dark, [0.03, 0.012, 0.3], [0, 0.05, 0], { line: false });
    c.float.box(P.trim, [0.02, 0.05, 0.02], [0, 0.04, 0], { line: false });
    c.float.pop();
  }
  if (core.includes('smoke-launcher')) {
    for (let i = 0; i < 3; i++) t.box(P.metal, [0.045, 0.045, 0.12], [mx + 0.02, my - 0.02 + i * 0.05, mz + 0.06], { rot: [-0.6, 0, 0] });
  }
  if (core.includes('targeting-array')) {
    t.seg(P.metal, [-mx * 0.6, my, mz - 0.05], [-mx * 0.7, my + 0.4 * sc, mz - 0.1], 0.025, 0.025);
    t.box(P.trim, [0.16 * sc, 0.1 * sc, 0.02], [-mx * 0.7, my + 0.42 * sc, mz - 0.1], { rot: [0.3, 0.3, 0] });
    t.box(P.glow, [0.03, 0.03, 0.03], [-mx * 0.7, my + 0.42 * sc, mz - 0.08], { glow: true });
  }
  if (core.includes('jump-jets')) {
    for (const x of [-1, 1]) {
      t.box(P.metal, [0.1 * sc, 0.24 * sc, 0.1 * sc], [x * 0.12 * sc, by - 0.05, bz - 0.06], { taper: 0.8 });
      t.box(P.glow, [0.08 * sc, 0.02, 0.08 * sc], [x * 0.12 * sc, by - 0.05 - 0.13 * sc, bz - 0.06], { glow: true });
    }
  }
  if (core.includes('coolant-loop')) {
    t.seg(P.accent, [bx - 0.12 * sc, by + 0.12, bz], [bx + 0.12 * sc, by + 0.12, bz], 0.04, 0.04);
    t.seg(P.accent, [bx - 0.12 * sc, by - 0.08, bz], [bx - 0.12 * sc, by + 0.12, bz], 0.04, 0.04);
    t.seg(P.accent, [bx + 0.12 * sc, by - 0.08, bz], [bx + 0.12 * sc, by + 0.12, bz], 0.04, 0.04);
  }
  if (core.includes('overcharged-boiler')) {
    t.box(P.metal, [0.2 * sc, 0.2 * sc, 0.12 * sc], [bx, by, bz - 0.04]);
    t.box(P.glow, [0.14 * sc, 0.05, 0.01], [bx, by, bz - 0.1 - 0.06 * sc], { glow: true });
    t.box(P.glow, [0.14 * sc, 0.05, 0.01], [bx, by - 0.07, bz - 0.1 - 0.06 * sc], { glow: true });
  }
  if (core.includes('field-repair-rig')) {
    t.seg(P.hazard, [bx + 0.08, by + 0.1, bz], [bx + 0.15, by + 0.45 * sc, bz - 0.15], 0.04, 0.04);
    t.seg(P.hazard, [bx + 0.15, by + 0.45 * sc, bz - 0.15], [bx + 0.3, by + 0.3 * sc, bz - 0.1], 0.03, 0.03);
    t.box(P.glow, [0.03, 0.03, 0.03], [bx + 0.3, by + 0.28 * sc, bz - 0.1], { glow: true });
  }
  if (core.includes('reactive-shell') || has(c, 'ablative-plating')) {
    // Extra layered plates bolted over the hull flanks.
    const col2 = core.includes('reactive-shell') ? P.trimDk : P.hull2;
    for (const x of [-1, 1]) t.box(col2, [0.04, 0.2 * sc, 0.2 * sc], [x * (mx + 0.05), my - 0.25 * sc, 0.02], { rot: [0, 0, x * 0.1] });
  }
}

function buildTemplate(w: WalkerInput, faction: string) {
  const P = FACTION[faction] ?? FACTION.covenant;
  const live = w.items.filter((it) => !it.destroyed);
  const items: Record<string, string[]> = {};
  for (const it of live) (items[it.location] ??= []).push(it.id);
  const c: Ctx = {
    P, faction, side: w.side, items,
    torso: new Kit(), head: new Kit(), halo: new Kit(), float: new Kit(), armL: new Kit(), armR: new Kit(), legL: new Kit(), legR: new Kit(),
  };
  const L = (CLASSES[w.chassis] ?? sentinel)(c);
  coreSystems(c, L);
  const side = SIDE_COLOUR[w.side] ?? SIDE_COLOUR[0];
  const legItems = items.legs ?? [];
  c.legL.push([0, 0, 0], [0, 0, 0], [1, 1, 1]);
  leg(c.legL, P, L.leg, side, legItems);
  c.legL.pop();
  c.legR.push([0, 0, 0], [0, 0, 0], [-1, 1, 1]);
  leg(c.legR, P, L.leg, side, legItems);
  c.legR.pop();
  c.armL.push([0, 0, 0], [0, 0, 0], [1, 1, 1]);
  const muzzleL = arm(c.armL, P, faction, L.arm, items.armLeft ?? [], L.unarmed);
  c.armL.pop();
  c.armR.push([0, 0, 0], [0, 0, 0], [-1, 1, 1]);
  const muzzleR = arm(c.armR, P, faction, L.arm, items.armRight ?? [], L.unarmed === 'staff' ? 'idle' : L.unarmed);
  c.armR.pop();

  const scale = L.scale ?? 1;
  const grow = OUTLINE / scale;
  const root = new THREE.Group();
  const body = new THREE.Group();
  body.name = 'body';
  body.scale.setScalar(scale);
  root.add(body);
  const group = (name: string, parent: THREE.Object3D, pos: V3, kit?: Kit) => {
    const g = new THREE.Group();
    g.name = name;
    g.position.set(...pos);
    parent.add(g);
    if (kit) bake(g, kit, grow);
    return g;
  };
  const legL = group('legL', body, [L.hipX, L.hipY, 0], c.legL);
  const legR = group('legR', body, [-L.hipX, L.hipY, 0], c.legR);
  const torso = group('torso', body, [0, L.hipY, 0], c.torso);
  torso.rotation.x = L.lean ?? 0;
  const head = group('head', torso, L.neck, c.head);
  if (c.halo.prims.length) group('halo', head, L.halo ?? [0, 0.15, -0.08], c.halo);
  if (c.float.prims.length) group('float', torso, [0, 0, 0], c.float);
  const armL = group('armL', torso, L.shoulder, c.armL);
  const armR = group('armR', torso, [-L.shoulder[0], L.shoulder[1], L.shoulder[2]], c.armR);
  // Arms hang plumb whatever the torso's lean.
  armL.rotation.x = armR.rotation.x = -(L.lean ?? 0) * 0.8;
  const mL = new THREE.Object3D();
  mL.name = 'muzzleL';
  mL.position.copy(muzzleL);
  armL.add(mL);
  const mR = new THREE.Object3D();
  mR.name = 'muzzleR';
  mR.position.copy(muzzleR);
  armR.add(mR);
  if (w.destroyedLocations.includes('armLeft')) armL.visible = false;
  if (w.destroyedLocations.includes('armRight')) armR.visible = false;
  if (w.destroyedLocations.includes('legs')) {
    legL.visible = legR.visible = false;
    body.position.y = -L.hipY * 0.75 * scale;
  }
  root.userData.height = L.height * scale;
  return root;
}

const CACHE = new Map<string, THREE.Group>();
const CACHE_LIMIT = 64;

function cacheKey(w: WalkerInput, faction: string) {
  const items = w.items
    .filter((i) => !i.destroyed)
    .map((i) => `${i.location}:${i.id}`)
    .sort()
    .join(',');
  return `${faction}|${w.chassis}|${w.side}|${items}|${[...w.destroyedLocations].sort().join(',')}`;
}

export function buildPixelWalker(w: WalkerInput, faction: string): THREE.Group {
  const key = cacheKey(w, faction);
  let template = CACHE.get(key);
  if (!template) {
    if (CACHE.size >= CACHE_LIMIT) CACHE.delete(CACHE.keys().next().value!);
    template = buildTemplate(w, faction);
    CACHE.set(key, template);
  }
  const root = template.clone(true);
  // Fresh materials per walker so the board can dim one walker without touching the others.
  const mats = { solid: SHARED_MATS.solid.clone(), glow: SHARED_MATS.glow.clone(), line: SHARED_MATS.line.clone() };
  root.traverse((o) => {
    if (o instanceof THREE.Mesh) o.material = mats[o.userData.kind as keyof typeof mats];
  });
  const get = (name: string) => root.getObjectByName(name)!;
  const parts: WalkerParts = {
    root,
    torso: get('torso') as THREE.Group,
    head: get('head') as THREE.Group,
    armL: get('armL') as THREE.Group,
    armR: get('armR') as THREE.Group,
    legL: get('legL') as THREE.Group,
    legR: get('legR') as THREE.Group,
    muzzleL: get('muzzleL'),
    muzzleR: get('muzzleR'),
  };
  const spinners: WalkerSpinner[] = [];
  const halo = root.getObjectByName('halo');
  if (halo) spinners.push({ object: halo, spin: 0.25, bob: 0, axis: 'z' });
  const float = root.getObjectByName('float');
  if (float) spinners.push({ object: float, spin: 0, bob: 0.03, axis: 'y' });
  root.userData.parts = parts;
  root.userData.materials = Object.values(mats);
  root.userData.spinners = spinners;
  root.userData.height = template.userData.height;
  return root;
}
