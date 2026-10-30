// Procedural chassis models in the Iron Covenant style: blackened armour,
// gold filigree, spires, lit lancet windows and livery banners. Each chassis
// has its own silhouette, built in millimetres at its real tabletop size, with named mount points
// (`mount_<location>_<slot>`) that equipment snaps to. Blender-made chassis
// use the same names, so they can replace these one at a time.
import * as THREE from 'three';
import type { Location } from '@brass-charter/rules';
import {
  archWindow,
  at,
  bake,
  banner,
  bar,
  blade,
  box,
  cyl,
  dome,
  helm,
  group,
  lancet,
  lathe,
  link,
  piston,
  plate,
  smokestack,
  sphere,
  spire,
  sunburst,
  torus,
  trimmed,
  type Palette,
  type V3,
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

/** A tabletop base: a chamfered black rim, scorched ash, rubble and a broken flagstone or two. */
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
    [-0.2, -0.62, 0.18, 2.1],
    [0.15, 0.62, 0.16, 0.4],
  ];
  for (const [x, z, s, ry] of stones) g.add(at(plate(r * s * 1.4, 0.6, r * s, p.iron, 0.25), x * r, 3.3, z * r, 0.08, ry, -0.06));
  for (const [x, z, s] of [
    [0.62, 0.3, 0.09],
    [-0.6, -0.25, 0.07],
    [0.3, -0.72, 0.06],
  ]) {
    g.add(at(plate(r * s, r * s * 0.7, r * s * 0.8, p.ground, 0.2), x * r, 3.4, z * r, 0.4, x * 3, 0.3));
  }
  return g;
}

/** A pauldron for side `s`: a domed shoulder plate with a gold rim and a sunburst on its face. */
function pauldron(r: number, s: number, p: Palette, withSpire = true) {
  const g = group(at(dome(r, p.armour, 24), 0, 0, 0), at(torus(r, r * 0.08, p.trim, 28), 0, 0, 0, Math.PI / 2), at(torus(r * 0.72, r * 0.04, p.trim, 24), 0, r * 0.66, 0, Math.PI / 2));
  g.scale.set(1, 0.85, 1.15);
  const out = group(at(g, 0, 0, 0, 0, 0, -s * 0.5));
  out.add(at(sunburst(r * 0.42, p), s * r * 0.72, r * 0.42, 0, 0, s * (Math.PI / 2), 0));
  if (withSpire) out.add(at(spire(r * 0.22, r * 1.3, p), -s * r * 0.1, r * 0.7, -r * 0.35, 0, 0, -s * 0.1));
  return out;
}

interface LegShape {
  /** Size multiplier for plates and joints. */
  k: number;
  shin: number;
  thigh: number;
}

/**
 * A knightly leg, foot on the base and hip at the returned height: pointed
 * sabaton, greave with a gold spine, spiked knee, armoured thigh and a
 * piston behind.
 */
function knightLeg({ k, shin, thigh }: LegShape, p: Palette) {
  const g = new THREE.Group();
  const ankle: V3 = [0, 3.3 + 2 * k, 0];
  const knee: V3 = [0, ankle[1] + shin, 2 * k];
  const hip: V3 = [0, knee[1] + thigh, -0.2 * k];
  g.add(at(trimmed(4 * k, 5.6 * k, 1.6 * k, p), 0, 4.1 * k, 0.6 * k, -Math.PI / 2));
  g.add(at(cyl(0.05, 1.5 * k, 3 * k, p.armour, 4), 0, 4 * k, 4.6 * k, Math.PI / 2, Math.PI / 4));
  g.add(at(plate(2.6 * k, 1.4 * k, 2.4 * k, p.iron), 0, 4 * k, -2.6 * k));
  g.add(at(sphere(1.4 * k, p.iron), ...ankle));
  g.add(link(ankle, knee, 2.2 * k, 2.2 * k, p.iron));
  g.add(link([0, ankle[1] + 0.8 * k, 1.3 * k], [0, knee[1] - 0.6 * k, knee[2] + 1.2 * k], 3.2 * k, 1 * k, p.armour));
  g.add(link([0, ankle[1] + 1.2 * k, 1.9 * k], [0, knee[1] - 0.8 * k, knee[2] + 1.75 * k], 0.45 * k, 0.4 * k, p.trim));
  const poleyn = group(at(dome(2 * k, p.armour, 18), 0, 0, 0, Math.PI / 2), at(torus(2 * k, 0.22 * k, p.trim, 20), 0, 0, 0.1), at(cyl(0.05, 0.7 * k, 2.4 * k, p.trim, 8), 0, 0, 2.6 * k, Math.PI / 2));
  g.add(at(poleyn, 0, knee[1], knee[2] + 0.9 * k));
  g.add(at(bar(1.5 * k, 3.8 * k, p.iron, 'x'), ...knee));
  g.add(link(knee, hip, 2.8 * k, 3.2 * k, p.iron));
  g.add(link([0, knee[1] + 1.2 * k, knee[2] + 0.9 * k], [0, hip[1] - 0.6 * k, hip[2] + 1.8 * k], 3.4 * k, 1 * k, p.armour));
  g.add(link([0, knee[1] + 1.5 * k, knee[2] + 1.45 * k], [0, hip[1] - 0.9 * k, hip[2] + 2.35 * k], 0.5 * k, 0.3 * k, p.trim));
  g.add(piston([0, ankle[1] + 0.6 * k, -1.2 * k], [0, hip[1] - 1.2 * k, -1.8 * k], 0.45 * k, p));
  return { leg: g, hipY: hip[1] };
}

/** Faulds: overlapping skirt plates hanging from the waist, front and sides. */
function faulds(w: number, h: number, d: number, p: Palette) {
  const g = new THREE.Group();
  for (const [x, z, ry] of [
    [-w * 0.3, d / 2, 0],
    [w * 0.3, d / 2, 0],
    [-w / 2, 0, -Math.PI / 2],
    [w / 2, 0, Math.PI / 2],
  ]) {
    const pl = group(at(plate(w * 0.42, h, 0.6, p.armour, 0.2), 0, -h / 2, 0), at(box(w * 0.4, 0.25, 0.3, p.trim), 0, -h + 0.2, 0.3));
    g.add(at(pl, x, 0, z, 0.18, ry, 0));
  }
  return g;
}

/** Gauntlet fingers at the front of a forearm, curled slightly down. */
function gauntlet(w: number, p: Palette) {
  const g = new THREE.Group();
  for (const x of [-0.36, -0.12, 0.12, 0.36]) g.add(at(group(at(plate(w * 0.2, w * 0.2, w * 0.7, p.iron, w * 0.05), 0, 0, w * 0.35), at(cyl(0.02, w * 0.1, w * 0.3, p.trim, 6), 0, 0, w * 0.82, Math.PI / 2)), x * w, -w * 0.15, 0, 0.45));
  return g;
}

/**
 * Striker: the Covenant's cathedral knight. A visored helm with glowing
 * slits, a lantern furnace in the chest, sunburst pauldrons crowned with
 * pinnacles, spires on the back, and a livery tabard and torn cape.
 */
function striker(slots: Record<Location, number>, p: Palette) {
  const root = new THREE.Group();
  root.add(base(BASE_MM.striker, p));

  const stance = 4.4;
  let hipY = 0;
  for (const s of [-1, 1]) {
    const { leg, hipY: y } = knightLeg({ k: 1, shin: 8.6, thigh: 7.2 }, p);
    hipY = y;
    root.add(at(leg, s * stance, 0, 0, 0, 0, s * 0.03));
  }
  root.add(at(bar(1.8, 11.4, p.iron, 'x'), 0, hipY, -0.2));
  root.add(at(trimmed(7.4, 3.4, 5, p), 0, hipY + 0.6, 0));
  root.add(at(plate(8, 0.7, 5.6, p.trim, 0.25), 0, hipY + 2.2, 0));
  root.add(at(faulds(8, 3.6, 5.6, p), 0, hipY + 1.8, 0));
  // Livery tabard front and back.
  root.add(at(banner(3.6, hipY - 7, p.hull, p, 3), 0, hipY + 1.8, 3.2, 0.06));
  root.add(at(banner(3.2, hipY - 9, p.hull, p, 5), 0, hipY + 1.8, -3.3, -0.06, Math.PI));
  for (let i = 0; i < slots.legs; i++) mount('legs', i, root, 0, hipY - 1, -3.6 - i, Math.PI);

  // Torso: a narrow-waisted cuirass, broad at the chest.
  const torso = new THREE.Group();
  torso.position.set(0, hipY + 2.4, 0);
  const cuirass = lathe(
    [
      [3.6, 0],
      [4.6, 2],
      [5.8, 5.6],
      [5.9, 8],
      [4.8, 9.6],
      [3, 10.2],
    ],
    p.armour,
    32,
  );
  cuirass.scale.set(1, 1, 0.78);
  torso.add(cuirass);
  for (const [y, r] of [
    [2, 4.6],
    [8, 5.9],
  ]) {
    const band = torus(r, 0.24, p.trim, 36);
    band.scale.set(1, 0.78, 1);
    torso.add(at(band, 0, y, 0, Math.PI / 2));
  }
  // Gold ribs framing the chest.
  for (const s of [-1, 1]) torso.add(link([s * 1.4, 2.2, 3.6], [s * 3.4, 8, 4.4], 0.4, 0.4, p.trim));
  // The lantern furnace.
  torso.add(at(archWindow(2.6, 4.2, p), 0, 4.9, 4.45, -0.1));
  torso.add(at(sunburst(1.1, p), 0, 8.3, 4.5, -0.15));
  // Gorget and helm.
  torso.add(at(cyl(2.6, 3.2, 1.6, p.iron, 20), 0, 10.6, 0));
  torso.add(at(helm(2.5, p), 0, 13.8, 0.9));
  // Back: twin spires, a pair of thin stacks and a torn cape.
  for (const s of [-1, 1]) {
    torso.add(at(spire(1.3, 12, p), s * 2.6, 6.2, -3.6, -0.06, 0, s * 0.04));
    torso.add(at(smokestack(0.55, 6, p), s * 1.1, 7.4, -4.1, -0.2));
  }
  torso.add(at(banner(7.4, 17, p.hull, p, 9), 0, 8.6, -4.6, -0.2, Math.PI));
  root.add(torso);
  const coreSpots: Array<[number, number, number]> = [
    [-4.6, 8.8, -2.6],
    [4.6, 8.8, -2.6],
  ];
  for (let i = 0; i < slots.core; i++) mount('core', i, torso, ...(coreSpots[i] ?? [0, 7, -5]));

  for (const [loc, s] of [
    ['armLeft', 1],
    ['armRight', -1],
  ] as Array<[Location, number]>) {
    const arm = new THREE.Group();
    arm.position.set(s * 6.6, 8.2, 0);
    arm.add(sphere(2, p.iron));
    arm.add(at(pauldron(3.8, s, p), s * 1, 0.6, 0));
    arm.add(at(banner(2.2, 7, p.hull, p, 13 + s, 1), s * 3.2, -0.6, 1.2, 0.1, s * 0.5, 0));
    arm.add(link([s * 0.6, -1, 0], [s * 0.9, -5.8, 0.3], 1.9, 1.9, p.iron));
    arm.add(at(trimmed(2.4, 3.6, 1, p), s * 1.7, -3.6, 0.3, 0, s * (Math.PI / 2)));
    const couter = group(at(dome(1.4, p.armour, 14), 0, 0, 0, 0, 0, -s * (Math.PI / 2)), at(cyl(0.04, 0.4, 1.6, p.trim, 6), s * 1.8, 0, 0, 0, 0, -s * (Math.PI / 2)));
    arm.add(at(couter, s * 1.1, -6.2, -0.4));
    arm.add(at(sphere(1.4, p.iron), s * 0.9, -6.2, 0.3));
    const fore = group(at(trimmed(3.6, 8, 3.4, p), 0, 0, 0, -Math.PI / 2, 0, 0), at(torus(1.9, 0.25, p.trim, 18), 0, 0, -3.6));
    fore.add(at(gauntlet(3, p), 0, -0.4, 4));
    arm.add(at(fore, s * 0.9, -6.8, 3.2));
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, s * (0.9 + 1.8 + 2.2 + i * 4), -6.8, 3.2);
    torso.add(arm);
  }
  return root;
}

/**
 * Scout: the light recon walker. Long spindly reverse-jointed legs, a slim
 * cuirass and small helm, swept blade-wings on the shoulders, forearm blades
 * and a ragged pennant.
 */
function scout(slots: Record<Location, number>, p: Palette) {
  const root = new THREE.Group();
  root.add(base(BASE_MM.scout, p));

  const stance = 3;
  const hipY = 17.2;
  for (const s of [-1, 1]) {
    const leg = new THREE.Group();
    leg.position.x = s * stance;
    for (const ry of [-0.4, 0, 0.4]) {
      const toe = group(at(plate(0.9, 0.8, 3.2, p.iron, 0.25), 0, 0, 1.6), at(cyl(0.02, 0.4, 1.4, p.trim, 6), 0, -0.1, 3.7, Math.PI / 2 + 0.3));
      leg.add(at(toe, 0, 3.7, 0.2, 0, ry));
    }
    leg.add(at(cyl(0.02, 0.45, 2.4, p.iron, 6), 0, 3.8, -1.6, -Math.PI / 2 - 0.4));
    leg.add(at(sphere(0.95, p.iron), 0, 4.3, 0));
    const ankle: V3 = [0, 4.3, 0];
    const knee: V3 = [0, 11.2, -2.8];
    const hip: V3 = [0, hipY, 0.3];
    leg.add(link(ankle, knee, 1.2, 1.3, p.iron));
    leg.add(link([0, 5.4, 0.1], [0, 10.4, -1.9], 1.6, 0.6, p.armour));
    leg.add(link([0, 5.8, 0.35], [0, 10, -1.55], 0.3, 0.25, p.trim));
    leg.add(at(sphere(1.1, p.armour), ...knee));
    leg.add(at(cyl(0.03, 0.5, 2.6, p.trim, 6), 0, knee[1] + 0.2, knee[2] - 1.6, -Math.PI / 2 + 0.25));
    leg.add(link(knee, hip, 1.9, 2.2, p.armour));
    leg.add(link([s * 1, knee[1] + 0.8, knee[2] + 0.6], [s * 1, hip[1] - 0.8, hip[2] - 0.2], 0.3, 1.4, p.trim));
    leg.add(piston([0, 5, -0.8], [0, 15, 1.2], 0.35, p));
    root.add(leg);
  }
  root.add(at(bar(1.2, 7.8, p.iron, 'x'), 0, hipY, 0.3));
  root.add(at(trimmed(4.6, 2.2, 3.4, p), 0, hipY + 0.5, 0.2));
  root.add(at(faulds(5, 2.4, 3.6, p), 0, hipY + 1.4, 0.2));
  root.add(at(banner(2.2, 8, p.hull, p, 21), 0, hipY + 1.4, 2.2, 0.08));
  for (let i = 0; i < slots.legs; i++) mount('legs', i, root, (i % 2 ? -1 : 1) * (stance + 1.4), 14, -0.6, Math.PI);

  const torso = new THREE.Group();
  torso.position.set(0, hipY + 1.6, 0);
  const cuirass = lathe(
    [
      [2.2, 0],
      [3, 1.6],
      [3.9, 4.4],
      [3.9, 6],
      [3, 7.2],
      [1.8, 7.6],
    ],
    p.armour,
    28,
  );
  cuirass.scale.set(1, 1, 0.75);
  torso.add(cuirass);
  const band = torus(3.9, 0.18, p.trim, 28);
  band.scale.set(1, 0.75, 1);
  torso.add(at(band, 0, 5.6, 0, Math.PI / 2));
  torso.add(at(archWindow(1.6, 2.6, p), 0, 3.4, 3, -0.12));
  torso.add(at(cyl(1.5, 1.9, 1.2, p.iron, 16), 0, 7.8, 0));
  torso.add(at(helm(1.75, p), 0, 9.9, 0.5));
  torso.add(at(spire(0.75, 7, p), 0, 5, -2.6, -0.15));
  torso.add(at(banner(3.4, 10, p.hull, p, 23), 0, 6.4, -3.1, -0.25, Math.PI));
  root.add(torso);
  for (let i = 0; i < slots.core; i++) mount('core', i, torso, 2.2 - i * 4.4, 6.6, -2);

  for (const [loc, s] of [
    ['armLeft', 1],
    ['armRight', -1],
  ] as Array<[Location, number]>) {
    const arm = new THREE.Group();
    arm.position.set(s * 4.4, 5.6, 0);
    arm.add(sphere(1.3, p.iron));
    arm.add(at(pauldron(2.5, s, p, false), s * 0.6, 0.4, 0));
    // Swept blade-wings rising off the back of the shoulder.
    arm.add(at(blade(10, 1.8, p), s * 1.2, 1, -1, -2.25, s * 0.25, 0));
    arm.add(at(blade(7, 1.4, p), s * 1.8, 0.4, -1, -2.6, s * 0.45, 0));
    arm.add(link([s * 0.5, -0.6, 0], [s * 0.8, -4, 0.3], 1.2, 1.2, p.iron));
    arm.add(at(sphere(1, p.armour), s * 0.8, -4.3, 0.3));
    const fore = group(at(trimmed(2.2, 5, 2.2, p), 0, 0, 0, -Math.PI / 2), at(torus(1.2, 0.16, p.trim, 14), 0, 0, -2.2));
    fore.add(at(gauntlet(2, p), 0, -0.3, 2.6));
    fore.add(at(blade(8, 1.3, p), 0, -1.4, -1.2, 0.2));
    arm.add(at(fore, s * 0.8, -4.8, 2));
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, s * (0.8 + 1.1 + 1.6 + i * 3.2), -4.8, 2);
    torso.add(arm);
  }
  return root;
}

/**
 * Bulwark: the heavy assault walker. A hunched armoured nave on long legs,
 * its helm sunk low under a gothic arch, lit windows in the chest, spires
 * at every corner and smokestacks behind, with massive sunburst pauldrons.
 */
function bulwark(slots: Record<Location, number>, p: Palette) {
  const root = new THREE.Group();
  root.add(base(BASE_MM.bulwark, p));

  const stance = 6.4;
  let hipY = 0;
  for (const s of [-1, 1]) {
    const { leg, hipY: y } = knightLeg({ k: 1.3, shin: 9, thigh: 7.4 }, p);
    hipY = y;
    root.add(at(leg, s * stance, 0, 0, 0, 0, s * 0.04));
  }
  root.add(at(bar(2.4, 16.4, p.iron, 'x'), 0, hipY, -0.3));
  root.add(at(trimmed(10, 4.4, 7, p), 0, hipY + 0.8, 0));
  root.add(at(faulds(10.4, 4.2, 7.4, p), 0, hipY + 2.6, 0));
  root.add(at(banner(4.4, hipY - 9, p.hull, p, 31), 0, hipY + 2.6, 4, 0.08));
  for (let i = 0; i < slots.legs; i++) mount('legs', i, root, (i % 2 ? -1 : 1) * stance, hipY - 4, -3.6, Math.PI);

  const torso = new THREE.Group();
  torso.position.set(0, hipY + 7.8, 0);
  torso.rotation.x = 0.1;
  torso.add(plate(14.4, 10, 12, p.armour, 1.6));
  torso.add(at(plate(15, 0.8, 12.6, p.trim, 0.3), 0, -4.4, 0));
  torso.add(at(plate(15, 0.6, 12.6, p.trim, 0.25), 0, 4.6, 0));
  const front = group(trimmed(12, 7.4, 1.2, p));
  for (const x of [-3.2, 3.2]) front.add(at(archWindow(2.2, 4.4, p), x, -0.6, 0.7));
  front.add(at(sunburst(1.5, p), 0, 1.6, 0.7));
  torso.add(at(front, 0, -0.6, 6.2));
  for (const s of [-1, 1]) torso.add(at(group(trimmed(9, 7, 1, p), at(archWindow(1.6, 3.4, p), 0, 0, 0.6)), s * 7.4, -0.4, 0, 0, s * (Math.PI / 2)));
  // The helm sits low at the front, framed by a gold-edged gothic arch.
  torso.add(at(lancet(8.2, 8.4, 1.4, p.trim), 0, 7.4, 2.2));
  torso.add(at(lancet(7.4, 7.8, 1.8, p.armour), 0, 7.3, 2.1));
  torso.add(at(spire(1.1, 8, p), 0, 11.2, 2.1));
  torso.add(at(helm(2.8, p), 0, 6.6, 4.4));
  // Corner spires and twin stacks.
  for (const [x, z] of [
    [-6, -4.6],
    [6, -4.6],
  ])
    torso.add(at(spire(1.4, 11, p), x, 5, z));
  for (const s of [-1, 1]) torso.add(at(smokestack(1.1, 9, p), s * 2.6, 5, -4.2));
  torso.add(at(banner(10, 16, p.hull, p, 37), 0, 3.6, -6.2, -0.15, Math.PI));
  root.add(torso);

  const coreSpots: Array<[number, number, number, number]> = [
    [-4.6, 5, 1.6, 0],
    [4.6, 5, 1.6, 0],
    [0, -0.6, -6.4, Math.PI],
  ];
  for (let i = 0; i < slots.core; i++) {
    const [x, y, z, ry] = coreSpots[i] ?? coreSpots[coreSpots.length - 1];
    mount('core', i, torso, x, y, z, ry);
  }

  for (const [loc, s] of [
    ['armLeft', 1],
    ['armRight', -1],
  ] as Array<[Location, number]>) {
    const arm = new THREE.Group();
    arm.position.set(s * 9.8, 2.4, 0);
    arm.add(sphere(2.8, p.iron));
    arm.add(at(pauldron(5.2, s, p), s * 1.2, 0.8, 0));
    arm.add(at(banner(3, 10, p.hull, p, 41 + s, 1), s * 4.6, -1, 1.2, 0.1, s * 0.55, 0));
    arm.add(link([s * 0.8, -1.6, 0], [s * 1.1, -8, 0.4], 2.8, 2.8, p.iron));
    arm.add(at(trimmed(3.2, 4.8, 1.2, p), s * 2.6, -4.6, 0.3, 0, s * (Math.PI / 2)));
    arm.add(at(sphere(2, p.iron), s * 1.1, -8.4, 0.4));
    arm.add(at(group(at(dome(1.9, p.armour, 16), 0, 0, 0, 0, 0, -s * (Math.PI / 2)), at(cyl(0.05, 0.55, 2.2, p.trim, 6), s * 2.4, 0, 0, 0, 0, -s * (Math.PI / 2))), s * 1.4, -8.4, -0.6));
    const fore = group(at(trimmed(5, 11, 5, p), 0, 0, 0, -Math.PI / 2), at(torus(2.7, 0.35, p.trim, 20), 0, 0, -4.8), at(torus(2.7, 0.28, p.trim, 20), 0, 0, 3.4));
    fore.add(at(gauntlet(4, p), 0, -0.6, 5.2));
    arm.add(at(fore, s * 1.1, -9.2, 4));
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, s * (1.1 + 2.5 + 2.8 + i * 4.4), -9.2, 4);
    torso.add(arm);
  }
  return root;
}

/** A pitched roof `w` wide with its ridge `h` above y = 0, running `len` along Z. */
function gable(w: number, h: number, len: number, m: THREE.Material) {
  const a = 4;
  const ridge = group(at(box(a, a, len, m), 0, 0, 0, 0, 0, Math.PI / 4));
  ridge.scale.set(w / (a * Math.SQRT2), h / ((a * Math.SQRT2) / 2), 1);
  return ridge;
}

/**
 * Titan: the mobile fortress. A cathedral nave carried on four splayed legs,
 * with corner towers, a steeple over a rose window, rows of lit lancets,
 * smokestacks at the back and gun casemates on its flanks.
 */
function titan(slots: Record<Location, number>, p: Palette) {
  const root = new THREE.Group();
  root.add(base(BASE_MM.titan, p));

  let hipY = 0;
  for (const [x, z, ry] of [
    [-9.6, 7, -0.55],
    [9.6, 7, 0.55],
    [-9.6, -7.4, Math.PI + 0.55],
    [9.6, -7.4, Math.PI - 0.55],
  ]) {
    const { leg, hipY: y } = knightLeg({ k: 1.45, shin: 10.4, thigh: 8 }, p);
    hipY = y;
    root.add(at(leg, x, 0, z, 0, ry, 0));
  }
  for (const z of [7, -7.4]) root.add(at(bar(2.6, 22, p.iron, 'x'), 0, hipY, z));
  root.add(at(plate(16, 4, 18, p.iron, 0.8), 0, hipY + 1, 0));
  for (let i = 0; i < slots.legs; i++) mount('legs', i, root, (i % 2 ? -1 : 1) * 8.6, hipY - 1.6, 0, Math.PI);

  const torso = new THREE.Group();
  const bodyY = hipY + 8;
  torso.position.set(0, bodyY, 0);
  // The nave.
  torso.add(plate(19, 10, 25, p.armour, 1.2));
  torso.add(at(plate(19.8, 1, 25.8, p.trim, 0.35), 0, -4.8, 0));
  torso.add(at(plate(19.6, 0.7, 25.6, p.trim, 0.3), 0, 5, 0));
  torso.add(at(gable(17, 6.4, 22, p.armour), 0, 5.2, -0.6));
  torso.add(at(box(0.5, 0.5, 22, p.trim), 0, 11.6, -0.6));
  for (const s of [-1, 1]) {
    for (const z of [-7, -1.4, 4.2]) torso.add(at(archWindow(2, 4.6, p), s * 9.6, 0.2, z, 0, s * (Math.PI / 2)));
    torso.add(at(banner(3.4, 9, p.hull, p, 51 + s), s * 9.9, 4.4, 8.6, 0, s * (Math.PI / 2)));
  }
  // West front: rose window, great lancet and a steeple.
  const facade = group(trimmed(15, 13, 1.4, p));
  facade.add(at(lancet(14, 6, 1.4, p.armour), 0, 9.4, 0));
  facade.add(at(archWindow(4.4, 6.8, p), 0, -2.4, 0.8));
  const rose = group(at(cyl(2.8, 2.8, 0.4, p.fire, 24), 0, 0, 0, Math.PI / 2), at(torus(3, 0.4, p.trim, 28), 0, 0, 0.3));
  for (let i = 0; i < 8; i++) rose.add(at(box(0.25, 5.4, 0.3, p.trim), 0, 0, 0.35, 0, 0, (i * Math.PI) / 8));
  rose.add(at(sphere(0.7, p.trim, 10), 0, 0, 0.4));
  facade.add(at(rose, 0, 4.4, 0.8));
  for (const x of [-5.4, 5.4]) facade.add(at(archWindow(1.6, 4, p, p.glow), x, -3.4, 0.8));
  torso.add(at(facade, 0, 1.6, 12.8));
  torso.add(at(spire(2.2, 15, p), 0, 11.5, 12.2));
  // Corner towers.
  for (const [x, z] of [
    [-9.2, 12.2],
    [9.2, 12.2],
    [-9.2, -12.2],
    [9.2, -12.2],
  ]) {
    const tower = group(at(cyl(2.6, 2.8, 14, p.armour, 8), 0, 7, 0), at(cyl(3, 3, 0.7, p.trim, 8), 0, 14, 0), at(cyl(2.9, 2.9, 0.6, p.trim, 8), 0, 5, 0));
    tower.add(at(archWindow(1.2, 2.8, p), 0, 10.4, 2.75));
    tower.add(at(spire(2.1, 11, p), 0, 14.3, 0));
    torso.add(at(tower, x, -5, z));
  }
  for (const s of [-1, 1]) torso.add(at(smokestack(1.5, 11, p), s * 3.4, 8, -9));
  torso.add(at(banner(11, 18, p.hull, p, 57), 0, 4, -13, -0.12, Math.PI));
  root.add(torso);
  const coreSpots: Array<[number, number, number, number]> = [
    [-5.4, 7.6, 4, 0],
    [5.4, 7.6, 4, 0],
    [0, 0, -13.6, Math.PI],
  ];
  for (let i = 0; i < slots.core; i++) {
    const [x, y, z, ry] = coreSpots[i] ?? coreSpots[coreSpots.length - 1];
    mount('core', i, torso, x, y, z, ry);
  }

  // Gun casemates on the flanks carry the arm weapons.
  for (const [loc, s] of [
    ['armLeft', 1],
    ['armRight', -1],
  ] as Array<[Location, number]>) {
    const arm = new THREE.Group();
    arm.position.set(s * 10.4, -1.4, 6.2);
    arm.add(at(bar(3.4, 4, p.iron, 'x', 20), s * 1, 0, 0));
    arm.add(at(group(trimmed(6.4, 6.4, 7, p), at(sunburst(2, p), 0, 0, 3.6)), s * 3.4, 0, 0.6, 0, s * (Math.PI / 2)));
    arm.add(at(spire(1, 6, p), s * 3.4, 3.2, 0.6));
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, s * (7.6 + i * 4.8), -0.6, 1.6);
    torso.add(arm);
  }
  return root;
}

const BUILDERS: Record<string, (slots: Record<Location, number>, p: Palette) => THREE.Group> = { scout, striker, bulwark, titan };

export function buildChassis(chassisId: string, slots: Record<Location, number>, p: Palette): ChassisModel {
  const build = BUILDERS[chassisId];
  if (!build) throw new Error(`No model for chassis ${chassisId}`);
  const root = bake(build(slots, p));
  root.name = `chassis_${chassisId}`;
  const mounts: Record<Location, THREE.Object3D[]> = { armLeft: [], armRight: [], core: [], legs: [] };
  for (const c of root.children) {
    const m = /^mount_(armLeft|armRight|core|legs)_(\d+)$/.exec(c.name);
    if (m) mounts[m[1] as Location][Number(m[2])] = c;
  }
  return { root, mounts };
}
