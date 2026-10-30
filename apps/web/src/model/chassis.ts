// Procedural chassis models. Each chassis has its own silhouette, built in
// millimetres at its real tabletop size, with named mount points
// (`mount_<location>_<slot>`) that equipment snaps to. Blender-made chassis
// use the same names, so they can replace these one at a time.
import * as THREE from 'three';
import type { Location } from '@brass-charter/rules';
import {
  at,
  bake,
  bar,
  boilerDrum,
  box,
  cyl,
  dome,
  gauge,
  group,
  lathe,
  piston,
  pipe,
  plate,
  rivetRing,
  rivetRow,
  smokestack,
  sphere,
  torus,
  type Palette,
} from './kit';

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

/** A tabletop base: a chamfered black rim, packed earth and a few flagstones. */
function base(diameter: number, p: Palette) {
  const r = diameter / 2;
  const g = group(
    lathe(
      [
        [r + 0.6, 0],
        [r + 0.6, 0.8],
        [r - 0.4, 3],
      ],
      p.iron,
      48,
    ),
    at(cyl(r - 0.5, r - 0.5, 0.4, p.ground, 48), 0, 3.05, 0),
  );
  const stones: Array<[number, number, number, number]> = [
    [-0.45, 0.35, 0.3, 0.2],
    [0.5, -0.4, 0.22, 0.9],
    [-0.2, -0.6, 0.18, 2.1],
    [0.15, 0.62, 0.16, 0.4],
  ];
  for (const [x, z, s, ry] of stones) g.add(at(plate(r * s * 1.4, 0.6, r * s, p.iron, 0.25), x * r, 3.3, z * r, 0, ry, 0));
  return g;
}

/**
 * Bulwark: a walking boiler. A wide banded drum for a body, a locomotive cab
 * on top, twin stacks, heavy armoured legs with pistons, big pauldrons and
 * clawed forearms that carry the weapons.
 */
function bulwark(slots: Record<Location, number>, p: Palette) {
  const root = new THREE.Group();
  root.add(base(BASE_MM.bulwark, p));

  // Legs, from the ground up: clawed foot, ankle, armoured shin, knee, thigh, hip.
  const stance = 6.8;
  for (const s of [-1, 1]) {
    const leg = new THREE.Group();
    leg.position.x = s * stance;
    leg.add(at(plate(7.4, 2.4, 9, p.iron), 0, 4.5, 1));
    for (const x of [-2.4, 0, 2.4]) leg.add(at(plate(2.2, 1.8, 3.6, p.iron, 0.5), x, 4.1, 6, 0.25));
    for (const x of [-2.4, 0, 2.4]) leg.add(at(dome(0.9, p.trim, 10), x, 4.6, 7.8, Math.PI / 2.4));
    leg.add(at(plate(3, 1.8, 3, p.iron), 0, 4.2, -4.2));
    leg.add(at(plate(6.2, 1.2, 6, p.hull), 0, 6, 1.4));
    leg.add(at(sphere(2.3, p.trim), 0, 7.4, 0.6));
    // Shin, leaning forward to a bent knee.
    const shin = group(plate(4.6, 8, 4.6, p.iron), at(plate(5.4, 7.6, 1.4, p.hull), 0, 0.2, 2.6), rivetRow([-2, 3.2, 3.35], [-2, -2.8, 3.35], 4, 0.35, p.trim), rivetRow([2, 3.2, 3.35], [2, -2.8, 3.35], 4, 0.35, p.trim));
    leg.add(at(shin, 0, 11, 1.6, 0.2));
    leg.add(at(bar(2.2, 6.4, p.iron, 'x'), 0, 14.8, 2.4));
    const knee = group(at(dome(3, p.hull), 0, 0, 0, Math.PI / 2), at(torus(3, 0.4, p.trim), 0, 0, 0.1), at(rivetRing(2.1, 8, 0.3, p.trim, true), 0, 0, 2.2));
    leg.add(at(knee, 0, 15, 3.4));
    leg.add(at(plate(4.4, 7.4, 5, p.iron), 0, 18.2, 0.8, -0.35));
    leg.add(at(plate(4.8, 4.6, 1.2, p.hull), s * 0.2, 18.6, 3.5, -0.35));
    leg.add(piston([s * 1.2, 6.4, -2.8], [s * 1.2, 19.4, -3.2], 0.8, p));
    root.add(leg);
  }
  root.add(at(bar(3.2, 18, p.iron, 'x'), 0, 21.6, 0));
  for (const s of [-1, 1]) root.add(at(bar(3.5, 0.8, p.trim, 'x'), s * 9, 21.6, 0));
  root.add(at(plate(10, 4.6, 7.4, p.iron), 0, 22.4, 0));
  root.add(at(plate(10.4, 1, 7.8, p.trim, 0.3), 0, 24.4, 0));
  for (let i = 0; i < slots.legs; i++) mount('legs', i, root, (i % 2 ? -1 : 1) * stance, 18, -3, Math.PI);

  // Body: the boiler drum.
  const torso = new THREE.Group();
  torso.position.set(0, 30.5, 0);
  torso.add(boilerDrum(6.6, 15.5, p, 3));
  // Chest armour with a gauge, and the firebox grille beneath it.
  const chest = group(plate(12.4, 8.6, 2, p.hull, 0.6), rivetRow([-5.4, 3.5, 1.05], [5.4, 3.5, 1.05], 8, 0.3, p.trim), rivetRow([-5.4, -3.5, 1.05], [5.4, -3.5, 1.05], 8, 0.3, p.trim));
  torso.add(at(chest, 0, 0.4, 6.5, -0.12));
  torso.add(at(gauge(1.25, p, 0.7), -3.8, 1.8, 7.6, -0.12));
  torso.add(at(gauge(0.9, p, 0.2), -1.4, 2.3, 7.5, -0.12));
  torso.add(at(plate(8.4, 3.4, 2.2, p.iron, 0.4), 0, -5.6, 5.4));
  for (const x of [-2.7, -0.9, 0.9, 2.7]) torso.add(at(box(1, 2, 0.4, p.fire), x, -5.6, 6.45));
  // Locomotive cab on top, with lit portholes.
  const cab = new THREE.Group();
  cab.add(plate(7.2, 5.4, 6.2, p.hull, 0.5));
  const roof = bar(4.4, 7.4, p.iron, 'z', 28);
  roof.scale.set(1, 0.2, 1);
  cab.add(at(roof, 0, 2.9, 0));
  cab.add(at(plate(7.6, 0.5, 6.6, p.trim, 0.2), 0, 2.7, 0));
  cab.add(at(cyl(0.7, 0.9, 1.6, p.iron, 12), -1.6, 3.9, -1.2));
  for (const x of [-1.8, 1.8]) {
    cab.add(at(cyl(1.05, 1.05, 0.3, p.fire, 16), x, 0.5, 3.15, Math.PI / 2));
    cab.add(at(torus(1.1, 0.3, p.trim, 16), x, 0.5, 3.2));
  }
  cab.add(at(box(0.5, 0.5, 2, p.trim), 3.2, 3.4, 0, 0, 0, 0));
  torso.add(at(cab, 0, 8, 1.6));
  // Twin stacks and a brass steam dome with a whistle.
  for (const s of [-1, 1]) torso.add(at(smokestack(1.3, s > 0 ? 9 : 7.5, p), s * 2.3, 5.2, -3.8));
  torso.add(at(lathe([[2.2, 0], [2.2, 0.6], [1.7, 1.8], [0.9, 2.6], [0, 2.8]], p.trim), 0, 6.1, -0.6 - 3.2));
  // Pipes down to the hips.
  for (const s of [-1, 1]) {
    torso.add(pipe([[s * 4.5, -5, -3.4], [s * 6.2, -7.6, -3.6], [s * 7.2, -11.5, -3.4]], 0.55, p.copper));
    torso.add(pipe([[s * 7.8, 0, -5], [s * 9.2, 1.5, -4.4], [s * 10.4, 2.6, -1.6]], 0.45, p.copper));
  }
  root.add(torso);

  const coreSpots: Array<[number, number, number, number]> = [
    [-6, 6.3, 0.6, 0],
    [6, 6.3, 0.6, 0],
    [0, 0.4, -7.6, Math.PI],
  ];
  for (let i = 0; i < slots.core; i++) {
    const [x, y, z, ry] = coreSpots[i] ?? coreSpots[coreSpots.length - 1];
    mount('core', i, torso, x, y, z, ry);
  }

  // Arms: pauldron, upper arm with a piston, elbow, armoured forearm and claw.
  for (const [loc, s] of [
    ['armLeft', 1],
    ['armRight', -1],
  ] as Array<[Location, number]>) {
    const arm = new THREE.Group();
    arm.position.set(s * 10.6, 2.6, 0);
    arm.add(sphere(3, p.iron));
    const pauldron = group(at(dome(4.8, p.hull, 24), 0, 0, 0), at(torus(4.8, 0.45, p.trim, 28), 0, 0, 0, Math.PI / 2), at(rivetRing(3.6, 10, 0.32, p.trim), 0, 1.9, 0, Math.PI / 2));
    pauldron.scale.set(1, 0.85, 1.15);
    arm.add(at(pauldron, s * 1.2, 1, 0, 0, 0, -s * 0.45));
    arm.add(at(cyl(1.9, 2.1, 7, p.iron), s * 1, -4.6, 0));
    arm.add(at(torus(2.15, 0.35, p.trim), s * 1, -2.4, 0, Math.PI / 2));
    arm.add(piston([s * 1, -2.2, 2], [s * 1, -7.6, 3], 0.55, p));
    arm.add(at(sphere(2.4, p.trim), s * 1, -8.4, 0.4));
    const fore = group(plate(4.8, 4.8, 10.4, p.hull, 0.7), at(plate(5.2, 1, 9, p.iron, 0.3), 0, 2.7, -0.2), rivetRow([0, 3.25, -3.6], [0, 3.25, 3.4], 5, 0.3, p.trim, [0, 1, 0]), at(torus(2.7, 0.4, p.trim), 0, 0, -4.4));
    for (const x of [-1.5, 0, 1.5]) fore.add(at(plate(1, 1.2, 3.4, p.iron, 0.3), x, -0.8, 6.2, 0.35));
    arm.add(at(fore, s * 1, -9.4, 4));
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, s * (1 + 2.4 + 0.6 + i * 4.2), -9.4, 4);
    torso.add(arm);
  }
  return root;
}

const BUILDERS: Record<string, (slots: Record<Location, number>, p: Palette) => THREE.Group> = { bulwark };

const LEGACY_SCALE: Record<string, number> = { scout: 1, striker: 1.2, bulwark: 1.4, titan: 1.7 };

/** The first placeholder: one blocky design scaled per chassis. Used until a chassis gets its own builder. */
function legacy(chassisId: string, slots: Record<Location, number>, p: Palette) {
  const k = LEGACY_SCALE[chassisId] ?? 1;
  const root = new THREE.Group();
  const baseR = BASE_MM[chassisId] / 2;
  root.add(at(cyl(baseR, baseR + 1, 3, p.iron, 32), 0, 1.5, 0));
  const legH = 11 * k;
  const hipY = 3 + legH;
  const stance = 4.5 * k;
  for (const side of [-1, 1]) {
    const leg = new THREE.Group();
    leg.add(at(box(5 * k, 2 * k, 7 * k, p.iron), 0, 1 * k, 1 * k));
    leg.add(at(box(3.2 * k, legH * 0.55, 3.2 * k, p.hull), 0, legH * 0.3, -0.5 * k, -0.15));
    leg.add(at(sphere(2 * k, p.trim), 0, legH * 0.58, 0));
    leg.add(at(box(3.6 * k, legH * 0.5, 3.6 * k, p.hull), 0, legH * 0.8, 0.4 * k, 0.15));
    leg.add(at(cyl(0.7 * k, 0.7 * k, legH * 0.5, p.trim), side * 2 * k, legH * 0.35, -1.6 * k));
    root.add(at(leg, side * stance, 3, 0));
  }
  root.add(at(box(11 * k, 3 * k, 6 * k, p.iron), 0, hipY, 0));
  for (let i = 0; i < slots.legs; i++) mount('legs', i, root, (i % 2 ? -1 : 1) * stance, 3 + legH * 0.75, -2.4 * k, Math.PI);
  const torso = new THREE.Group();
  torso.position.set(0, hipY + 6 * k, 0);
  torso.add(bar(5.5 * k, 13 * k, p.hull, 'x', 24));
  for (const x of [-5.5, 5.5]) torso.add(at(torus(5.5 * k, 0.5 * k, p.trim), x * k, 0, 0, 0, Math.PI / 2));
  torso.add(at(box(9 * k, 7 * k, 1.5 * k, p.hull), 0, -0.5 * k, 5 * k));
  torso.add(at(cyl(1.2 * k, 1.4 * k, 7 * k, p.iron), -3 * k, 7 * k, -3 * k));
  torso.add(at(cyl(1.2 * k, 1.4 * k, 5.5 * k, p.iron), -0.5 * k, 6 * k, -3.5 * k));
  torso.add(at(group(cyl(3 * k, 3.4 * k, 4 * k, p.hull), at(cyl(1.4 * k, 1.4 * k, 0.6 * k, p.glow), 0, 0.3 * k, 3.2 * k, Math.PI / 2)), 2.5 * k, 6 * k, 1.5 * k));
  root.add(torso);
  const spots = [
    [-4 * k, 5.5 * k, 0],
    [4 * k, 5.5 * k, -1 * k],
    [0, 1 * k, -6 * k],
  ];
  for (let i = 0; i < slots.core; i++) {
    const [x, y, z] = spots[i] ?? [0, 0, -6 * k];
    mount('core', i, torso, x, y, z, i === 2 ? Math.PI : 0);
  }
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
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, side * (0.8 + 2.6 + i * 2.8) * k, -8.5 * k, 3 * k);
    torso.add(arm);
  }
  return root;
}

export function buildChassis(chassisId: string, slots: Record<Location, number>, p: Palette): ChassisModel {
  const root = bake((BUILDERS[chassisId] ?? ((s, pal) => legacy(chassisId, s, pal)))(slots, p));
  root.name = `chassis_${chassisId}`;
  const mounts: Record<Location, THREE.Object3D[]> = { armLeft: [], armRight: [], core: [], legs: [] };
  for (const c of root.children) {
    const m = /^mount_(armLeft|armRight|core|legs)_(\d+)$/.exec(c.name);
    if (m) mounts[m[1] as Location][Number(m[2])] = c;
  }
  return { root, mounts };
}
