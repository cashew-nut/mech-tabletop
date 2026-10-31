// Stylised pixel war-walkers for the 3D board: boxy figures built in code, one silhouette per class and one palette per
// faction. They face +Z. Limbs hang from pivot groups listed in userData.parts so the animation stage can swing them.
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

interface Palette {
  hull: number;
  trim: number;
  dark: number;
  glow: number;
  cloth?: number;
}

const FACTION: Record<string, Palette> = {
  covenant: { hull: 0x23212a, trim: 0xd4a956, dark: 0x111016, glow: 0xff5a3c, cloth: 0x8e1b2c },
  foundries: { hull: 0x8a4a2c, trim: 0xb8321f, dark: 0x2a211c, glow: 0xff9a2e },
  reliquary: { hull: 0xe3dcc6, trim: 0xd4a956, dark: 0x6d6a5c, glow: 0x35e0cf },
};
export const SIDE_COLOUR = [0x2d6e9c, 0x9c3a26];

interface Profile {
  scale: number;
  legH: number;
  legW: number;
  torso: [number, number, number];
  armW: number;
  armLen: number;
  head: number;
}

const PROFILE: Record<string, Profile> = {
  lancer: { scale: 0.95, legH: 0.55, legW: 0.16, torso: [0.45, 0.5, 0.3], armW: 0.12, armLen: 0.5, head: 0.2 },
  sentinel: { scale: 1.0, legH: 0.5, legW: 0.22, torso: [0.7, 0.6, 0.45], armW: 0.17, armLen: 0.5, head: 0.24 },
  paladin: { scale: 1.15, legH: 0.7, legW: 0.26, torso: [0.85, 0.75, 0.5], armW: 0.2, armLen: 0.65, head: 0.28 },
  scavenger: { scale: 0.8, legH: 0.35, legW: 0.14, torso: [0.4, 0.35, 0.3], armW: 0.1, armLen: 0.35, head: 0.2 },
  brute: { scale: 1.0, legH: 0.45, legW: 0.22, torso: [0.8, 0.55, 0.5], armW: 0.2, armLen: 0.5, head: 0.22 },
  artillery: { scale: 1.0, legH: 0.5, legW: 0.2, torso: [0.65, 0.55, 0.45], armW: 0.15, armLen: 0.45, head: 0.2 },
  wraith: { scale: 0.9, legH: 0.65, legW: 0.1, torso: [0.3, 0.4, 0.2], armW: 0.08, armLen: 0.55, head: 0.18 },
  seer: { scale: 0.95, legH: 0.5, legW: 0.13, torso: [0.4, 0.5, 0.3], armW: 0.1, armLen: 0.45, head: 0.2 },
  goliath: { scale: 1.2, legH: 0.7, legW: 0.28, torso: [0.95, 0.8, 0.55], armW: 0.24, armLen: 0.7, head: 0.3 },
};

const MELEE = new Set(['lance', 'melee-blade']);
const CLAWS = new Set(['industrial-claw', 'kinetic-claws']);

const box = new THREE.BoxGeometry(1, 1, 1);

function cube(parent: THREE.Object3D, material: THREE.Material, w: number, h: number, d: number, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(box, material);
  m.scale.set(w, h, d);
  m.position.set(x, y, z);
  parent.add(m);
  return m;
}

const pivot = (parent: THREE.Object3D, x: number, y: number, z = 0) => {
  const g = new THREE.Group();
  g.position.set(x, y, z);
  parent.add(g);
  return g;
};

function armProp(arm: THREE.Group, itemId: string | undefined, len: number, w: number, m: { hull: THREE.Material; trim: THREE.Material; dark: THREE.Material }, muzzle: THREE.Object3D) {
  const tip = -len;
  if (!itemId) {
    muzzle.position.set(0, tip, 0.1);
    return;
  }
  if (itemId === 'lance') {
    cube(arm, m.dark, 0.06, 0.06, 1.5, 0, tip + 0.05, 0.6);
    cube(arm, m.trim, 0.14, 0.14, 0.3, 0, tip + 0.05, 1.4);
    muzzle.position.set(0, tip + 0.05, 1.55);
  } else if (itemId === 'melee-blade') {
    cube(arm, m.trim, 0.08, 0.9, 0.04, 0, tip - 0.3, 0.2);
    cube(arm, m.dark, 0.3, 0.06, 0.1, 0, tip, 0.2);
    muzzle.position.set(0, tip - 0.7, 0.2);
  } else if (CLAWS.has(itemId)) {
    for (const x of [-0.07, 0, 0.07]) cube(arm, m.trim, 0.04, 0.04, 0.4, x, tip, 0.25);
    cube(arm, m.dark, w * 1.2, w, w * 1.2, 0, tip, 0);
    muzzle.position.set(0, tip, 0.5);
  } else if (itemId === 'kinetic-shield') {
    cube(arm, m.hull, 0.08, 0.7, 0.55, 0.12 * Math.sign(arm.position.x), tip + 0.2, 0.15);
    cube(arm, m.trim, 0.1, 0.5, 0.06, 0.12 * Math.sign(arm.position.x), tip + 0.2, 0.43);
    muzzle.position.set(0, tip, 0.2);
  } else {
    // A gun barrel; heavier for cannons and launchers.
    const heavy = /cannon|pod|rack|missile/.test(itemId);
    const b = heavy ? 0.17 : 0.11;
    cube(arm, m.dark, b, b, 0.75, 0, tip + 0.08, 0.4);
    if (heavy) cube(arm, m.trim, b * 1.4, b * 1.4, 0.12, 0, tip + 0.08, 0.55);
    muzzle.position.set(0, tip + 0.08, 0.8);
  }
}

export function buildPixelWalker(w: Pick<WalkerState, 'chassis' | 'size' | 'side' | 'items' | 'destroyedLocations' | 'prone'>, faction: string): THREE.Group {
  const pal = FACTION[faction] ?? FACTION.covenant;
  const p = PROFILE[w.chassis] ?? PROFILE.sentinel;
  const mats = {
    hull: new THREE.MeshLambertMaterial({ color: pal.hull, flatShading: true }),
    trim: new THREE.MeshLambertMaterial({ color: pal.trim, flatShading: true }),
    dark: new THREE.MeshLambertMaterial({ color: pal.dark, flatShading: true }),
    cloth: new THREE.MeshLambertMaterial({ color: pal.cloth ?? pal.trim, flatShading: true }),
    side: new THREE.MeshLambertMaterial({ color: SIDE_COLOUR[w.side], flatShading: true }),
    glow: new THREE.MeshBasicMaterial({ color: pal.glow }),
  };

  const root = new THREE.Group();
  const body = pivot(root, 0, 0);
  body.scale.setScalar(p.scale * 1.6); // big enough to read at the default camera
  const [tw, th, td] = p.torso;
  const hipY = p.legH;

  // Legs, with a side-coloured foot band so ownership reads at a glance.
  const leg = (x: number) => {
    const g = pivot(body, x, hipY);
    cube(g, mats.hull, p.legW, p.legH * 0.55, p.legW, 0, -p.legH * 0.28);
    cube(g, mats.dark, p.legW * 0.8, p.legH * 0.45, p.legW * 0.8, 0, -p.legH * 0.72);
    cube(g, mats.hull, p.legW * 1.5, 0.09, p.legW * 2, 0, -p.legH + 0.045, 0.06);
    cube(g, mats.side, p.legW * 1.55, 0.04, p.legW * 2.05, 0, -p.legH + 0.02, 0.06);
    return g;
  };
  const gap = tw * 0.28;
  const legL = leg(gap);
  const legR = leg(-gap);
  if (w.destroyedLocations.includes('legs')) {
    legL.visible = legR.visible = false;
    body.position.y = -p.legH * 0.7;
  }

  const torso = pivot(body, 0, hipY);
  cube(torso, mats.hull, tw, th, td, 0, th / 2);
  cube(torso, mats.trim, tw * 0.5, 0.08, td * 1.05, 0, th * 0.55);
  const topY = th;

  // Head.
  const head = pivot(torso, 0, topY);
  cube(head, mats.hull, p.head, p.head, p.head, 0, p.head / 2 + 0.03);
  cube(head, mats.glow, p.head * 0.7, p.head * 0.14, 0.04, 0, p.head * 0.62, p.head / 2 + 0.03);

  // Arms and their weapons.
  const arm = (side: 'armLeft' | 'armRight', x: number) => {
    const g = pivot(torso, x, th * 0.88);
    const muzzle = new THREE.Object3D();
    g.add(muzzle);
    cube(g, mats.hull, p.armW, p.armLen, p.armW, 0, -p.armLen / 2);
    cube(g, mats.trim, p.armW * 1.6, p.armW * 1.1, p.armW * 1.6, 0, 0.02); // pauldron
    const item = w.items.find((it) => it.location === side && !it.destroyed)?.id;
    armProp(g, item, p.armLen, p.armW, mats, muzzle);
    g.rotation.x = -0.3; // rest pose: arms ready, weapons a little forward
    if (w.destroyedLocations.includes(side)) g.visible = false;
    return { g, muzzle };
  };
  const aL = arm('armLeft', tw / 2 + p.armW * 0.7);
  const aR = arm('armRight', -(tw / 2 + p.armW * 0.7));

  // Faction dressing.
  if (faction === 'covenant') {
    cube(head, mats.trim, 0.04, p.head * 0.9, 0.06, 0, p.head + 0.14, -0.02); // crest
    cube(torso, mats.cloth, tw * 0.5, th * 0.7, 0.04, 0, th * 0.3, td / 2 + 0.03); // tabard
    cube(torso, mats.trim, tw * 1.1, 0.07, td * 0.3, 0, th * 0.95, td * 0.2); // gorget
  } else if (faction === 'foundries') {
    for (const x of [-0.18, 0.18]) {
      cube(torso, mats.dark, 0.12, 0.45, 0.12, x * (tw / 0.5), th + 0.1, -td * 0.35); // smokestacks
      cube(torso, mats.glow, 0.09, 0.05, 0.09, x * (tw / 0.5), th + 0.34, -td * 0.35);
    }
    cube(torso, mats.glow, tw * 0.3, th * 0.22, 0.04, 0, th * 0.45, td / 2 + 0.02); // furnace core
    cube(torso, mats.trim, tw * 0.25, th * 0.18, 0.03, -tw * 0.25, th * 0.82, td / 2 + 0.02); // hull plate number
  } else {
    const r = p.head * 0.85;
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      cube(head, mats.glow, 0.06, 0.06, 0.06, Math.cos(a) * r, p.head + 0.28 + Math.sin(a) * 0.04, Math.sin(a) * r); // halo
    }
    cube(torso, mats.trim, tw * 0.15, th * 0.6, 0.04, 0, th * 0.4, td / 2 + 0.02);
    cube(torso, mats.hull, tw * 0.9, th * 0.5, td * 0.5, 0, th * 0.5, -td * 0.5); // hood-like mantle
  }

  // Class flourishes.
  if (w.chassis === 'sentinel') cube(torso, mats.trim, tw * 1.25, 0.1, td * 1.2, 0, th * 0.98);
  if (w.chassis === 'paladin' || w.chassis === 'goliath') for (const s of [-1, 1]) cube(torso, mats.trim, 0.12, 0.3, 0.12, s * tw * 0.3, th + 0.15, 0); // shoulder spires
  if (w.chassis === 'brute' || w.chassis === 'goliath') cube(torso, mats.dark, tw * 1.1, th * 0.25, td * 0.3, 0, th * 0.1, td * 0.3);
  if (w.chassis === 'artillery') cube(torso, mats.dark, 0.2, 0.2, 0.9, tw * 0.3, th + 0.1, -0.1); // back-mounted tube
  if (w.chassis === 'scavenger') torso.rotation.x = 0.35; // hunched
  if (w.chassis === 'seer') cube(torso, mats.glow, 0.16, 0.16, 0.16, 0, th + p.head + 0.55, 0.0); // floating lantern
  if (w.chassis === 'wraith') cube(torso, mats.dark, tw * 1.6, th * 0.8, 0.05, 0, th * 0.4, -td * 0.7); // tattered cloak

  root.userData.parts = { root, torso, head, armL: aL.g, armR: aR.g, legL, legR, muzzleL: aL.muzzle, muzzleR: aR.muzzle } satisfies WalkerParts;
  root.userData.materials = Object.values(mats);
  return root;
}
