// Procedural placeholder parts for war-walker models. Units are millimetres,
// so an exported STL prints at tabletop scale (a 2-inch hex is 50.8 mm).
// +Y is up and +Z is forward. Every chassis exposes named mount points
// (`mount_<location>_<slot>`) that equipment snaps to; Blender-made parts use
// the same names, so they can replace these placeholders one at a time.
import * as THREE from 'three';
import type { Location } from '@brass-charter/rules';

export interface Palette {
  hull: THREE.Material;
  trim: THREE.Material;
  iron: THREE.Material;
  glow: THREE.Material;
}

export function makePalette(hullColour: string): Palette {
  return {
    hull: new THREE.MeshStandardMaterial({ color: hullColour, roughness: 0.6, metalness: 0.3 }),
    trim: new THREE.MeshStandardMaterial({ color: '#c19a4b', roughness: 0.35, metalness: 0.85 }),
    iron: new THREE.MeshStandardMaterial({ color: '#3a332c', roughness: 0.8, metalness: 0.5 }),
    glow: new THREE.MeshStandardMaterial({ color: '#3fd0bd', emissive: '#2fb3a3', emissiveIntensity: 0.8, roughness: 0.4 }),
  };
}

const box = (w: number, h: number, d: number, m: THREE.Material) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
const cyl = (rTop: number, rBottom: number, h: number, m: THREE.Material, seg = 16) =>
  new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBottom, h, seg), m);
const sphere = (r: number, m: THREE.Material) => new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12), m);
const torus = (r: number, tube: number, m: THREE.Material) => new THREE.Mesh(new THREE.TorusGeometry(r, tube, 8, 20), m);

function at<T extends THREE.Object3D>(obj: T, x: number, y: number, z: number, rx = 0, ry = 0, rz = 0): T {
  obj.position.set(x, y, z);
  obj.rotation.set(rx, ry, rz);
  return obj;
}

/** A barrel pointing forward along +Z. */
const barrel = (r: number, len: number, m: THREE.Material) => {
  const b = cyl(r, r, len, m);
  b.rotation.x = Math.PI / 2;
  b.position.z = len / 2;
  return b;
};

function group(...children: THREE.Object3D[]) {
  const g = new THREE.Group();
  for (const c of children) g.add(c);
  return g;
}

// ---------------------------------------------------------------- chassis

const SCALE: Record<string, number> = { scout: 1, striker: 1.2, bulwark: 1.4, titan: 1.7 };
export const BASE_MM: Record<string, number> = { scout: 25, striker: 32, bulwark: 40, titan: 50 };

export interface ChassisModel {
  root: THREE.Group;
  mounts: Record<Location, THREE.Object3D[]>;
}

function mount(location: Location, index: number, parent: THREE.Object3D, x: number, y: number, z: number, ry = 0) {
  const m = new THREE.Object3D();
  m.name = `mount_${location}_${index}`;
  at(m, x, y, z, 0, ry, 0);
  parent.add(m);
  return m;
}

/** Placeholder chassis: base, two legs, hips, boiler torso with smokestacks, cab and two arms. */
export function buildChassis(chassisId: string, slots: Record<Location, number>, p: Palette): ChassisModel {
  const k = SCALE[chassisId] ?? 1;
  const root = new THREE.Group();
  root.name = `chassis_${chassisId}`;
  const mounts: Record<Location, THREE.Object3D[]> = { armLeft: [], armRight: [], core: [], legs: [] };

  // Base, like a tabletop miniature's.
  const baseR = BASE_MM[chassisId] / 2;
  root.add(at(cyl(baseR, baseR + 1, 3, p.iron, 32), 0, 1.5, 0));

  const legH = 11 * k;
  const hipY = 3 + legH;
  const stance = 4.5 * k;
  for (const side of [-1, 1]) {
    const leg = new THREE.Group();
    leg.add(at(box(5 * k, 2 * k, 7 * k, p.iron), 0, 1 * k, 1 * k)); // foot
    leg.add(at(box(3.2 * k, legH * 0.55, 3.2 * k, p.hull), 0, legH * 0.3, -0.5 * k, -0.15)); // shin
    leg.add(at(sphere(2 * k, p.trim), 0, legH * 0.58, 0)); // knee
    leg.add(at(box(3.6 * k, legH * 0.5, 3.6 * k, p.hull), 0, legH * 0.8, 0.4 * k, 0.15)); // thigh
    leg.add(at(cyl(0.7 * k, 0.7 * k, legH * 0.5, p.trim), side * 2 * k, legH * 0.35, -1.6 * k)); // piston
    root.add(at(leg, side * stance, 3, 0));
  }
  root.add(at(box(11 * k, 3 * k, 6 * k, p.iron), 0, hipY, 0)); // hips

  for (let i = 0; i < slots.legs; i++) {
    mount('legs', i, root, (i % 2 ? -1 : 1) * stance, 3 + legH * 0.75, -2.4 * k, Math.PI);
  }

  // Torso: a riveted boiler drum lying side to side, with a front plate and stacks.
  const torso = new THREE.Group();
  torso.position.set(0, hipY + 6 * k, 0);
  const drum = cyl(5.5 * k, 5.5 * k, 13 * k, p.hull, 24);
  drum.rotation.z = Math.PI / 2;
  torso.add(drum);
  for (const x of [-5.5, 5.5]) {
    const band = torus(5.5 * k, 0.5 * k, p.trim);
    band.rotation.y = Math.PI / 2;
    torso.add(at(band, x * k, 0, 0));
  }
  torso.add(at(box(9 * k, 7 * k, 1.5 * k, p.hull), 0, -0.5 * k, 5 * k)); // front plate
  torso.add(at(cyl(1.2 * k, 1.4 * k, 7 * k, p.iron), -3 * k, 7 * k, -3 * k)); // stacks
  torso.add(at(cyl(1.2 * k, 1.4 * k, 5.5 * k, p.iron), -0.5 * k, 6 * k, -3.5 * k));
  // Cab with a glowing porthole.
  const cab = group(cyl(3 * k, 3.4 * k, 4 * k, p.hull), at(cyl(1.4 * k, 1.4 * k, 0.6 * k, p.glow), 0, 0.3 * k, 3.2 * k, Math.PI / 2));
  torso.add(at(cab, 2.5 * k, 6 * k, 1.5 * k));
  root.add(torso);

  for (let i = 0; i < slots.core; i++) {
    // Core slots: on the shoulders, then the back.
    const spots = [
      [-4 * k, 5.5 * k, 0],
      [4 * k, 5.5 * k, -1 * k],
      [0, 1 * k, -6 * k],
    ];
    const [x, y, z] = spots[i] ?? [0, 0, -6 * k];
    mount('core', i, torso, x, y, z, i === 2 ? Math.PI : 0);
  }

  // Arms hang from shoulder joints; weapons mount along the forearm, pointing forward.
  for (const [loc, side] of [
    ['armLeft', 1],
    ['armRight', -1],
  ] as Array<[Location, number]>) {
    const arm = new THREE.Group();
    arm.position.set(side * 8.5 * k, 2 * k, 0);
    arm.add(sphere(2.8 * k, p.trim));
    arm.add(at(box(3 * k, 6 * k, 3 * k, p.hull), side * 0.8 * k, -4 * k, 0));
    arm.add(at(sphere(1.6 * k, p.iron), side * 0.8 * k, -7.5 * k, 0));
    arm.add(at(box(3.4 * k, 3.4 * k, 8 * k, p.hull), side * 0.8 * k, -8.5 * k, 3 * k));
    for (let i = 0; i < slots[loc]; i++) {
      mount(loc, i, arm, side * (0.8 + 2.6 + i * 2.8) * k, -8.5 * k, 3 * k);
    }
    torso.add(arm);
    for (const m of arm.children.filter((c) => c.name.startsWith('mount_'))) mounts[loc].push(m);
  }
  for (const c of torso.children) if (c.name.startsWith('mount_core')) mounts.core.push(c);
  for (const c of root.children) if (c.name.startsWith('mount_legs')) mounts.legs.push(c);
  return { root, mounts };
}

// ---------------------------------------------------------------- equipment

type PartBuilder = (p: Palette) => THREE.Object3D;

/** Placeholder meshes for each item, built at Scout scale and pointing forward. */
export const PARTS: Record<string, PartBuilder> = {
  scattergun: (p) => group(at(box(3, 3, 4, p.iron), 0, 0, 0), ...[-0.8, 0.8].flatMap((x) => [-0.8, 0.8].map((y) => at(barrel(0.6, 4, p.trim), x, y, 1.5)))),
  autocannon: (p) => group(box(3, 3, 5, p.iron), at(barrel(0.7, 7, p.trim), 0, 0.3, 2), at(box(1, 2, 2, p.trim), 1.8, 0, 0)),
  'beam-cutter': (p) => group(at(barrel(1.3, 5, p.iron), 0, 0, -1), at(torus(1.4, 0.4, p.trim), 0, 0, 3.5), at(barrel(0.8, 1.5, p.glow), 0, 0, 4)),
  'thermal-projector': (p) => {
    const nozzle = cyl(0.6, 1.6, 3, p.trim);
    nozzle.rotation.x = Math.PI / 2;
    nozzle.position.z = 4.5;
    return group(at(cyl(1.6, 1.6, 4, p.hull), 0, 1.5, -1, Math.PI / 2), at(barrel(0.9, 3, p.iron), 0, 0, 0), nozzle);
  },
  'missile-rack': (p) =>
    group(
      box(5, 4, 6, p.hull),
      ...[-1.3, 0, 1.3].flatMap((x) => [-0.8, 0.8].map((y) => at(barrel(0.5, 0.6, p.iron), x, y, 3))),
      at(box(5.4, 0.6, 6.4, p.trim), 0, 2.2, 0),
    ),
  'rail-lance': (p) =>
    group(
      box(3, 3, 5, p.iron),
      at(box(0.8, 0.8, 14, p.trim), 0.9, 0, 7),
      at(box(0.8, 0.8, 14, p.trim), -0.9, 0, 7),
      ...[3, 6, 9].map((z) => at(torus(1.6, 0.35, p.glow), 0, 0, z)),
    ),
  'arc-mortar': (p) => group(at(box(4, 2, 4, p.iron), 0, -1, 0), at(cyl(1.8, 2.2, 5, p.hull), 0, 1.5, 0.5, 0.5), at(torus(1.9, 0.4, p.trim), 0, 3.3, 1.7, 0.5 + Math.PI / 2)),
  'ion-lance': (p) => group(at(barrel(0.6, 8, p.trim), 0, 0, 0), ...[2, 4, 6].map((z) => at(torus(1.1, 0.3, p.glow), 0, 0, z)), box(2.4, 2.4, 2.4, p.iron)),
  'impact-hammer': (p) => group(at(barrel(0.6, 5, p.iron), 0, 0, 0), at(box(4, 3, 3, p.hull), 0, 0, 6), at(box(4.4, 1, 3.4, p.trim), 0, 1.8, 6)),
  'shear-blade': (p) => {
    const shape = new THREE.Shape();
    shape.moveTo(0, -1.2);
    shape.lineTo(9, 0);
    shape.lineTo(0, 1.5);
    shape.lineTo(0, -1.2);
    const blade = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: 0.5, bevelEnabled: false }), p.trim);
    blade.rotation.y = -Math.PI / 2;
    return group(box(2, 2, 2, p.iron), at(blade, 0.25, 0, 0.5, 0, -Math.PI / 2));
  },
  'ablative-plating': (p) => group(at(box(5, 4, 1.4, p.hull), 0, 0, 1), ...[-1.6, 1.6].map((x) => at(sphere(0.4, p.trim), x, 1.4, 1.8))),
  'reactive-shell': (p) => group(...[-1.5, 0, 1.5].flatMap((x) => [-1, 1].map((y) => at(box(1.3, 1.6, 1.2, p.iron), x, y, 1)))),
  'kinetic-shield': (p) => group(at(cyl(4.5, 4.5, 0.8, p.hull, 24), 0, 0, 2, Math.PI / 2), at(torus(4.5, 0.4, p.trim), 0, 0, 2.3), at(sphere(1, p.glow), 0, 0, 2.6)),
  'smoke-launcher': (p) => group(box(3, 1.5, 2, p.iron), ...[-0.9, 0, 0.9].map((x) => at(cyl(0.5, 0.5, 2.5, p.trim), x, 1.5, 0.5, -0.4))),
  'jump-jets': (p) =>
    group(
      ...[-1.4, 1.4].map((x) => at(cyl(1.2, 1.2, 4, p.iron), x, 0, 0)),
      ...[-1.4, 1.4].map((x) => at(cyl(1.4, 0.8, 1.5, p.glow), x, -2.6, 0)),
    ),
  'sprint-servos': (p) => group(at(cyl(0.8, 0.8, 5, p.trim), 0, 0, 0), at(cyl(1.2, 1.2, 1.5, p.iron), 0, 2.2, 0)),
  'gyro-stabilisers': (p) => group(sphere(1.6, p.iron), at(torus(2.2, 0.35, p.trim), 0, 0, 0, Math.PI / 2), at(torus(2.2, 0.35, p.trim), 0, 0, 0, 0, Math.PI / 2)),
  'anchor-spikes': (p) => group(...[-1.2, 1.2].map((x) => at(new THREE.Mesh(new THREE.ConeGeometry(0.8, 4, 10), p.trim), x, -3, 0, Math.PI))),
  'targeting-array': (p) => {
    const dish = new THREE.Mesh(new THREE.SphereGeometry(2.4, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2.5), p.trim);
    dish.rotation.x = Math.PI / 2;
    return group(at(cyl(0.4, 0.4, 3, p.iron), 0, 1.5, 0), at(dish, 0, 3.5, 0.3), at(sphere(0.5, p.glow), 0, 3.5, 1.4));
  },
  'coolant-loop': (p) => group(at(torus(2, 0.6, p.trim), 0, 1.5, 0), at(cyl(1, 1, 2.5, p.iron), 0, 0.5, 0)),
  'overcharged-boiler': (p) => group(at(cyl(1.4, 1.8, 6, p.iron), 0, 3, 0), at(torus(1.6, 0.4, p.glow), 0, 5.5, 0, Math.PI / 2)),
  'static-choir': (p) => group(at(cyl(0.3, 0.3, 7, p.iron), 0, 3.5, 0), ...[2.5, 4.5, 6.5].map((y) => at(cyl(1.6 - y / 8, 1.6 - y / 8, 0.3, p.trim), 0, y, 0))),
  'spotter-drone': (p) => group(at(cyl(0.3, 0.3, 3, p.iron), 0, 1.5, 0), at(cyl(2.2, 1.2, 0.8, p.hull), 0, 3.4, 0), at(sphere(0.6, p.glow), 0, 3.4, 1.6)),
  'field-repair-rig': (p) =>
    group(at(cyl(0.5, 0.5, 4, p.iron), 0, 2, 0), at(box(0.8, 0.8, 5, p.trim), 0, 4, 2), at(box(1.6, 1.2, 1.2, p.iron), 0, 3.4, 4.5), at(torus(0.8, 0.25, p.trim), 0, 2.6, 4.5)),
};

/** Scale for equipment on a chassis, so parts grow with the walker. */
export const partScale = (chassisId: string) => SCALE[chassisId] ?? 1;
