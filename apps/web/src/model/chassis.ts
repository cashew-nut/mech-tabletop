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
  boilerDrum,
  box,
  cyl,
  dome,
  gauge,
  helm,
  group,
  lathe,
  link,
  piston,
  pipe,
  plate,
  rivetRing,
  rivetRow,
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
 * Scout: a quick bird-legged runner. An egg-shaped boiler pod with one big
 * lit eye, a single stack, stubby arms and reverse-jointed legs with claws.
 */
function scout(slots: Record<Location, number>, p: Palette) {
  const root = new THREE.Group();
  root.add(base(BASE_MM.scout, p));

  const stance = 3.4;
  for (const s of [-1, 1]) {
    const leg = new THREE.Group();
    leg.position.x = s * stance;
    // Three splayed toes forward and a spur behind.
    for (const ry of [-0.45, 0, 0.45]) {
      const toe = group(at(plate(1.1, 0.9, 3.6, p.iron, 0.3), 0, 0, 1.8), at(dome(0.45, p.trim, 8), 0, 0, 3.6, Math.PI / 2));
      leg.add(at(toe, 0, 3.7, 0.2, 0, ry));
    }
    leg.add(at(plate(1, 0.9, 2.4, p.iron, 0.3), 0, 3.7, -1.2, -0.3));
    leg.add(at(sphere(1.1, p.trim), 0, 4.4, 0));
    // Shank up and back to the reverse knee, thigh forward to the hip.
    leg.add(link([0, 4.4, 0], [0, 10.4, -2.8], 1.6, 1.8, p.iron));
    leg.add(link([0, 6.2, 0.2], [0, 9.8, -1.6], 1.9, 0.8, p.armour));
    leg.add(at(sphere(1.35, p.iron), 0, 10.4, -2.8));
    leg.add(at(torus(1.35, 0.22, p.trim, 14), 0, 10.4, -2.8, 0, Math.PI / 2));
    leg.add(link([0, 10.4, -2.8], [0, 14.4, 0.2], 2.4, 2.8, p.armour));
    leg.add(rivetRow([s * 1.25, 11.4, -1.9], [s * 1.25, 13.6, -0.4], 3, 0.22, p.trim, [s, 0, 0]));
    leg.add(piston([0, 5, -0.9], [0, 12.6, 0.6], 0.45, p));
    root.add(leg);
  }
  root.add(at(bar(1.6, 9.4, p.iron, 'x'), 0, 14.4, 0.2));
  for (const s of [-1, 1]) root.add(at(bar(1.8, 0.5, p.trim, 'x'), s * 4.9, 14.4, 0.2));
  for (let i = 0; i < slots.legs; i++) mount('legs', i, root, (i % 2 ? -1 : 1) * (stance + 1.4), 11.2, -1.6, Math.PI);

  // The pod: an egg-shaped boiler with a brass belt and a cyclops porthole.
  const torso = new THREE.Group();
  torso.position.set(0, 14.6, 0);
  torso.add(
    lathe(
      [
        [2.6, 0],
        [4.4, 1.2],
        [5.3, 3.2],
        [5.4, 4.8],
        [4.9, 6.8],
        [3.6, 8.6],
        [1.6, 9.6],
        [0, 9.9],
      ],
      p.armour,
      32,
    ),
  );
  torso.add(at(torus(5.42, 0.36, p.trim, 36), 0, 4.2, 0, Math.PI / 2));
  torso.add(at(rivetRing(5.2, 18, 0.22, p.iron), 0, 5.3, 0, Math.PI / 2));
  torso.add(at(lathe([[2.7, 0], [2.7, 0.8], [2.3, 1.4]], p.iron, 20), 0, -0.2, 0));
  const eye = group(
    at(cyl(2.1, 2.3, 1.2, p.trim, 24), 0, 0, 0, Math.PI / 2),
    at(cyl(1.75, 1.75, 0.3, p.fire, 24), 0, 0, 0.55, Math.PI / 2),
    at(torus(1.9, 0.25, p.trim, 24), 0, 0, 0.6),
    at(rivetRing(2.05, 8, 0.18, p.iron, true), 0, 0, 0.6),
  );
  torso.add(at(eye, 0, 5.6, 4.6, -0.12));
  torso.add(at(gauge(0.8, p, 0.6), 2.9, 2.4, 3.9, -0.3, 0.55));
  torso.add(at(plate(3.6, 1.6, 1.2, p.iron, 0.3), 0, 2.2, 4.6, -0.4));
  for (const x of [-1, 0, 1]) torso.add(at(box(0.6, 0.9, 0.3, p.fire), x * 1.05, 2.2, 5.25, -0.4));
  torso.add(at(smokestack(0.95, 5.6, p), -1.6, 7.6, -2.4));
  torso.add(pipe([[-4.6, 3, -2], [-5.2, 0.6, -1.6], [-3.6, -0.6, -0.4]], 0.35, p.copper));
  root.add(torso);
  for (let i = 0; i < slots.core; i++) mount('core', i, torso, 2.2, 8.4, -0.6 - i * 2.4);

  for (const [loc, s] of [
    ['armLeft', 1],
    ['armRight', -1],
  ] as Array<[Location, number]>) {
    const arm = new THREE.Group();
    arm.position.set(s * 5.4, 5, 0);
    arm.add(sphere(1.6, p.iron));
    arm.add(at(dome(2.2, p.armour, 16), s * 0.5, 0.6, 0, 0, 0, -s * 0.6));
    arm.add(at(torus(2.2, 0.22, p.trim, 18), s * 0.5, 0.6, 0, Math.PI / 2, 0, -s * 0.6));
    arm.add(link([s * 0.6, -0.8, 0], [s * 0.9, -3.8, 0.4], 1.5, 1.5, p.iron));
    arm.add(at(sphere(1.15, p.trim), s * 0.9, -4, 0.4));
    arm.add(at(group(plate(2.6, 2.6, 5.4, p.armour, 0.45), rivetRow([0, 1.35, -1.8], [0, 1.35, 1.8], 3, 0.2, p.trim, [0, 1, 0]), at(torus(1.45, 0.2, p.trim, 16), 0, 0, -2.3)), s * 0.9, -4.6, 2.4));
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, s * (0.9 + 1.3 + 1.6 + i * 3.2), -4.6, 2.4);
    torso.add(arm);
  }
  return root;
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
    leg.add(at(plate(6.2, 1.2, 6, p.armour), 0, 6, 1.4));
    leg.add(at(sphere(2.3, p.trim), 0, 7.4, 0.6));
    // Shin, leaning forward to a bent knee.
    const shin = group(plate(4.6, 8, 4.6, p.iron), at(plate(5.4, 7.6, 1.4, p.armour), 0, 0.2, 2.6), rivetRow([-2, 3.2, 3.35], [-2, -2.8, 3.35], 4, 0.35, p.trim), rivetRow([2, 3.2, 3.35], [2, -2.8, 3.35], 4, 0.35, p.trim));
    leg.add(at(shin, 0, 11, 1.6, 0.2));
    leg.add(at(bar(2.2, 6.4, p.iron, 'x'), 0, 14.8, 2.4));
    const knee = group(at(dome(3, p.armour), 0, 0, 0, Math.PI / 2), at(torus(3, 0.4, p.trim), 0, 0, 0.1), at(rivetRing(2.1, 8, 0.3, p.trim, true), 0, 0, 2.2));
    leg.add(at(knee, 0, 15, 3.4));
    leg.add(at(plate(4.4, 7.4, 5, p.iron), 0, 18.2, 0.8, -0.35));
    leg.add(at(plate(4.8, 4.6, 1.2, p.armour), s * 0.2, 18.6, 3.5, -0.35));
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
  const chest = group(plate(12.4, 8.6, 2, p.armour, 0.6), rivetRow([-5.4, 3.5, 1.05], [5.4, 3.5, 1.05], 8, 0.3, p.trim), rivetRow([-5.4, -3.5, 1.05], [5.4, -3.5, 1.05], 8, 0.3, p.trim));
  torso.add(at(chest, 0, 0.4, 6.5, -0.12));
  torso.add(at(gauge(1.25, p, 0.7), -3.8, 1.8, 7.6, -0.12));
  torso.add(at(gauge(0.9, p, 0.2), -1.4, 2.3, 7.5, -0.12));
  torso.add(at(plate(8.4, 3.4, 2.2, p.iron, 0.4), 0, -5.6, 5.4));
  for (const x of [-2.7, -0.9, 0.9, 2.7]) torso.add(at(box(1, 2, 0.4, p.fire), x, -5.6, 6.45));
  // Locomotive cab on top, with lit portholes.
  const cab = new THREE.Group();
  cab.add(plate(7.2, 5.4, 6.2, p.armour, 0.5));
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
    const pauldron = group(at(dome(4.8, p.armour, 24), 0, 0, 0), at(torus(4.8, 0.45, p.trim, 28), 0, 0, 0, Math.PI / 2), at(rivetRing(3.6, 10, 0.32, p.trim), 0, 1.9, 0, Math.PI / 2));
    pauldron.scale.set(1, 0.85, 1.15);
    arm.add(at(pauldron, s * 1.2, 1, 0, 0, 0, -s * 0.45));
    arm.add(at(cyl(1.9, 2.1, 7, p.iron), s * 1, -4.6, 0));
    arm.add(at(torus(2.15, 0.35, p.trim), s * 1, -2.4, 0, Math.PI / 2));
    arm.add(piston([s * 1, -2.2, 2], [s * 1, -7.6, 3], 0.55, p));
    arm.add(at(sphere(2.4, p.trim), s * 1, -8.4, 0.4));
    const fore = group(plate(4.8, 4.8, 10.4, p.armour, 0.7), at(plate(5.2, 1, 9, p.iron, 0.3), 0, 2.7, -0.2), rivetRow([0, 3.25, -3.6], [0, 3.25, 3.4], 5, 0.3, p.trim, [0, 1, 0]), at(torus(2.7, 0.4, p.trim), 0, 0, -4.4));
    for (const x of [-1.5, 0, 1.5]) fore.add(at(plate(1, 1.2, 3.4, p.iron, 0.3), x, -0.8, 6.2, 0.35));
    arm.add(at(fore, s * 1, -9.4, 4));
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, s * (1 + 2.4 + 0.6 + i * 4.2), -9.4, 4);
    torso.add(arm);
  }
  return root;
}
/**
 * Titan: a locomotive that learned to walk. A long boiler pointing forward
 * with a riveted smokebox door for a face, headlamp and chimney on top, the
 * driver's cab behind, drive cylinders below, and colossal piston legs.
 */
function titan(slots: Record<Location, number>, p: Palette) {
  const root = new THREE.Group();
  root.add(base(BASE_MM.titan, p));

  const stance = 9.6;
  for (const s of [-1, 1]) {
    const leg = new THREE.Group();
    leg.position.x = s * stance;
    leg.add(at(plate(10, 3, 13, p.iron), 0, 4.8, 1));
    for (const x of [-3.4, 0, 3.4]) {
      leg.add(at(plate(2.8, 2.4, 4.6, p.iron, 0.6), x, 4.4, 8.4, 0.25));
      leg.add(at(dome(1.2, p.trim, 10), x, 5, 10.6, Math.PI / 2.4));
    }
    for (const x of [-2.6, 2.6]) leg.add(at(plate(2.6, 2.2, 3.6, p.iron, 0.5), x, 4.4, -6.4, -0.25));
    leg.add(at(plate(8.8, 1.6, 8.6, p.armour), 0, 7, 1.4));
    leg.add(rivetRow([-3.8, 7.85, -2.2], [3.8, 7.85, -2.2], 6, 0.32, p.trim, [0, 1, 0]));
    leg.add(at(sphere(3.2, p.trim), 0, 8.8, 0.6));
    leg.add(link([0, 8.8, 0.6], [0, 18.6, 3], 6.4, 6.4, p.iron));
    leg.add(link([0, 9.8, 4], [0, 18, 6.2], 7.4, 1.8, p.armour));
    leg.add(rivetRow([-3, 10.8, 5.2], [-3, 16.8, 6.8], 5, 0.34, p.trim, [0, 0.25, 1]));
    leg.add(rivetRow([3, 10.8, 5.2], [3, 16.8, 6.8], 5, 0.34, p.trim, [0, 0.25, 1]));
    leg.add(at(bar(3.4, 9, p.iron, 'x'), 0, 19, 3));
    for (const x of [-4.6, 4.6]) leg.add(at(bar(3.7, 0.8, p.trim, 'x'), x, 19, 3));
    leg.add(at(group(at(dome(4.4, p.armour, 24), 0, 0, 0, Math.PI / 2), at(torus(4.4, 0.55, p.trim, 28), 0, 0, 0.1), at(rivetRing(3.2, 10, 0.4, p.trim, true), 0, 0, 3)), 0, 19.2, 5.6));
    leg.add(link([0, 19, 3], [0, 27.6, -0.4], 6.8, 7.6, p.armour));
    leg.add(at(plate(7.4, 5, 1.2, p.trim, 0.3), 0, 23.4, 3.3, -0.38));
    leg.add(piston([s * 2, 9.6, -3.2], [s * 2, 26, -4.6], 1.1, p));
    leg.add(piston([-s * 2.4, 9.6, -3], [-s * 2.4, 25, -4.2], 0.8, p));
    root.add(leg);
  }
  root.add(at(bar(4.4, 26, p.iron, 'x'), 0, 27.8, -0.4));
  root.add(at(plate(15, 6.6, 11, p.iron), 0, 29, -0.4));
  root.add(at(plate(15.6, 1.2, 11.6, p.trim, 0.4), 0, 32, -0.4));
  for (let i = 0; i < slots.legs; i++) mount('legs', i, root, (i % 2 ? -1 : 1) * (stance + 4.4), 22, -1.2, Math.PI);

  const torso = new THREE.Group();
  torso.position.set(0, 41.6, 0);
  // The boiler barrel runs front to back, banded and riveted.
  torso.add(at(bar(8, 20, p.armour, 'z', 36), 0, 0, -1));
  for (const z of [-8, -2, 4]) {
    torso.add(at(torus(8.04, 0.45, p.trim, 40), 0, 0, z));
    torso.add(at(rivetRing(8.15, 22, 0.32, p.iron), 0, 0, z + 0.9));
  }
  // Smokebox and its door: the Titan's face.
  torso.add(at(bar(8.4, 5, p.iron, 'z', 36), 0, 0, 11));
  torso.add(at(torus(8.4, 0.5, p.trim, 40), 0, 0, 13.4));
  const door = group(
    at(lathe([[7.4, 0], [7.4, 0.5], [6.4, 1.2], [3, 2], [0, 2.2]], p.iron, 36), 0, 0, 0, Math.PI / 2),
    at(rivetRing(6.6, 18, 0.36, p.trim, true), 0, 0, 0.9),
    at(cyl(1.2, 1.2, 0.8, p.trim, 16), 0, 0, 2.4, Math.PI / 2),
    at(box(5.6, 0.6, 0.5, p.trim), 0, 0, 2.6),
    at(box(0.6, 5.6, 0.5, p.trim), 0, 0, 2.6),
  );
  for (const y of [-3.8, 3.8]) door.add(at(plate(9, 1, 0.6, p.trim, 0.25), -2.6, y, 1.3, 0, 0, 0));
  torso.add(at(door, 0, 0, 13.6));
  // Headlamp, chimney, steam and sand domes.
  const lamp = group(plate(3.8, 3.4, 3.4, p.iron, 0.5), at(cyl(1.4, 1.4, 0.4, p.fire, 20), 0, 0, 1.75, Math.PI / 2), at(torus(1.5, 0.3, p.trim, 20), 0, 0, 1.9), at(cyl(0.5, 0.8, 1.6, p.iron, 10), 0, 2.4, 0));
  torso.add(at(lamp, 0, 9.4, 12));
  torso.add(at(smokestack(2, 11, p), 0, 7.2, 7.4));
  torso.add(at(lathe([[2.8, 0], [2.8, 0.8], [2.2, 2.6], [1.2, 3.6], [0, 3.9]], p.trim, 28), 0, 7.6, 0.2));
  torso.add(at(lathe([[2.4, 0], [2.4, 0.6], [1.9, 2], [0, 2.6]], p.armour, 24), 0, 7.7, -4.6));
  torso.add(at(cyl(0.35, 0.35, 2.4, p.trim, 10), 1.4, 11.6, 0.2));
  // Drive cylinders below the barrel, as on a locomotive.
  for (const s of [-1, 1]) {
    torso.add(at(bar(2.6, 8.6, p.iron, 'z', 20), s * 6.6, -7, 6.4));
    for (const z of [2.3, 10.5]) torso.add(at(bar(2.9, 0.7, p.trim, 'z', 20), s * 6.6, -7, z));
    torso.add(pipe([[s * 5, -3, 9], [s * 6.6, -4.4, 8.6]], 0.7, p.copper));
  }
  // Driver's cab at the back, lit windows looking over the boiler.
  const cab = new THREE.Group();
  cab.add(plate(17, 11, 9, p.armour, 0.8));
  const roof = bar(10, 10.6, p.iron, 'z', 40);
  roof.scale.set(1, 0.22, 1);
  cab.add(at(roof, 0, 5.6, 0));
  cab.add(at(plate(17.6, 0.8, 9.6, p.trim, 0.3), 0, 5.3, 0));
  for (const x of [-5.2, 5.2]) {
    cab.add(at(plate(4.4, 3.4, 0.4, p.fire, 0.3), x, 2.3, 4.45));
    cab.add(at(plate(5, 4, 0.5, p.trim, 0.3), x, 2.3, 4.35));
  }
  for (const s of [-1, 1]) {
    cab.add(at(cyl(1.5, 1.5, 0.4, p.fire, 20), s * 8.45, 1.6, 0, 0, 0, Math.PI / 2));
    cab.add(at(torus(1.55, 0.35, p.trim, 20), s * 8.6, 1.6, 0, 0, Math.PI / 2));
    cab.add(rivetRow([s * 8.55, -3.8, -3.6], [s * 8.55, -3.8, 3.6], 6, 0.32, p.trim, [s, 0, 0]));
  }
  cab.add(at(gauge(1.4, p, 0.75), 0, -1, 4.7));
  torso.add(at(cab, 0, 5, -13.4));
  // Firebox glowing beneath the cab.
  torso.add(at(plate(11, 5, 6, p.iron, 0.6), 0, -7.6, -10.6));
  for (const x of [-3.6, -1.2, 1.2, 3.6]) torso.add(at(box(1.2, 2.6, 0.4, p.fire), x, -7.6, -7.5));
  for (const s of [-1, 1]) torso.add(pipe([[s * 7.6, 2, -6], [s * 10.4, 0.4, -5], [s * 12.6, 0.4, -1.4]], 0.7, p.copper));
  root.add(torso);
  const coreSpots: Array<[number, number, number, number]> = [
    [-5.8, 8.2, 2.4, 0],
    [5.8, 8.2, 2.4, 0],
    [0, 5, -18.4, Math.PI],
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
    arm.position.set(s * 13.4, 0.4, 0);
    arm.add(at(bar(4.4, 5.6, p.iron, 'x', 24), 0, 0, 0));
    arm.add(at(bar(4.7, 0.8, p.trim, 'x', 24), s * 2.8, 0, 0));
    const pauldron = group(
      at(dome(6.6, p.armour, 28), 0, 0, 0),
      at(torus(6.6, 0.6, p.trim, 32), 0, 0, 0, Math.PI / 2),
      at(rivetRing(5, 14, 0.4, p.trim), 0, 2.8, 0, Math.PI / 2),
      at(dome(3.2, p.trim, 20), 0, 4.4, 0),
    );
    pauldron.scale.set(1, 0.8, 1.15);
    arm.add(at(pauldron, s * 1.8, 2, 0, 0, 0, -s * 0.42));
    arm.add(link([s * 1.4, -2, 0], [s * 1.6, -10.4, 0.6], 4.4, 4.4, p.iron));
    arm.add(at(torus(2.8, 0.45, p.trim, 20), s * 1.5, -4.4, 0.2, Math.PI / 2));
    arm.add(piston([s * 1.5, -2.6, 3], [s * 1.6, -10, 3.8], 0.9, p));
    arm.add(at(sphere(3.4, p.trim), s * 1.6, -11.4, 0.6));
    const fore = group(
      plate(6.8, 6.8, 14, p.armour, 1),
      at(plate(7.2, 1.2, 12, p.iron, 0.4), 0, 3.8, -0.4),
      rivetRow([0, 4.45, -5], [0, 4.45, 4.4], 6, 0.36, p.trim, [0, 1, 0]),
      at(torus(3.8, 0.55, p.trim, 24), 0, 0, -6),
      at(torus(3.8, 0.4, p.trim, 24), 0, 0, 4),
    );
    for (const x of [-2.2, 0, 2.2]) fore.add(at(plate(1.4, 1.8, 5, p.iron, 0.4), x, -1.2, 8.4, 0.35));
    arm.add(at(fore, s * 1.6, -12.6, 5.6));
    for (let i = 0; i < slots[loc]; i++) mount(loc, i, arm, s * (1.6 + 3.4 + 3 + i * 5.8), -12.6, 5.6);
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
