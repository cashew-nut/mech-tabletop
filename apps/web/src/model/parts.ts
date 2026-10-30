// Procedural parts for war-walker models. Units are millimetres, so an
// exported STL prints at tabletop scale (a 2-inch hex is 50.8 mm). +Y is up
// and +Z is forward. Chassis live in chassis.ts; this file holds the items,
// each built at Scout scale with its origin where it attaches.
import * as THREE from 'three';
import { at, barrel, box, cyl, dome, gauge, gear, group, lathe, piston, pipe, plate, rivetRing, rivetRow, sphere, torus, type Palette } from './kit';

export { makePalette, type Palette } from './kit';
export { BASE_MM, buildChassis, type ChassisModel } from './chassis';

const SCALE: Record<string, number> = { scout: 1, striker: 1.2, bulwark: 1.4, titan: 1.7 };

// ---------------------------------------------------------------- equipment

type PartBuilder = (p: Palette) => THREE.Object3D;

/** Meshes for each item, built at Scout scale and pointing forward. */
export const PARTS: Record<string, PartBuilder> = {
  // ------------------------------------------------ weapons
  scattergun: (p) =>
    group(
      plate(3, 3, 3.8, p.iron, 0.4),
      ...[-0.75, 0.75].flatMap((x) => [-0.75, 0.75].map((y) => at(barrel(0.55, 4.4, p.iron, 12), x, y, 1.4))),
      at(plate(3.3, 3.3, 0.8, p.trim, 0.3), 0, 0, 3.2),
      at(plate(3.3, 3.3, 0.7, p.trim, 0.3), 0, 0, 5.5),
      at(cyl(1.4, 1.4, 1.4, p.copper, 18), 0, -2.2, -0.4),
      at(torus(1.4, 0.18, p.trim, 18), 0, -2.2, -0.4, Math.PI / 2),
      rivetRow([-1.2, 1.55, -1.2], [1.2, 1.55, -1.2], 3, 0.2, p.trim, [0, 1, 0]),
    ),
  autocannon: (p) =>
    group(
      plate(3, 3.2, 5.2, p.iron, 0.45),
      at(plate(3.3, 0.6, 4.4, p.hull, 0.2), 0, 1.75, -0.2),
      at(barrel(0.6, 9, p.iron, 14), 0, 0.3, 2),
      at(barrel(0.95, 3.4, p.trim, 16), 0, 0.3, 2.2),
      ...[2.8, 3.8, 4.8].map((z) => at(torus(0.97, 0.12, p.iron, 14), 0, 0.3, z)),
      at(plate(1.7, 1.7, 1.1, p.iron, 0.3), 0, 0.3, 10.6),
      at(barrel(1.2, 1.6, p.copper, 18), 2.2, -0.4, -1.4, 0, Math.PI / 2),
      pipe([[1.6, -0.9, -0.2], [2.4, -1.6, 1.2], [1.4, -1.4, 2]], 0.3, p.trim),
    ),
  'beam-cutter': (p) =>
    group(
      at(barrel(1.3, 4.4, p.iron, 18), 0, 0, -1.2),
      ...[0.4, 1.4, 2.4].map((z) => at(torus(1.4, 0.26, p.copper, 18), 0, 0, z)),
      at(lathe([[1.4, 0], [1.6, 0.6], [1.1, 1.6], [0.7, 1.8]], p.trim, 18), 0, 0, 3.2, Math.PI / 2),
      at(sphere(0.75, p.glow, 14), 0, 0, 5.1),
      at(cyl(0.6, 0.6, 2.6, p.copper, 10), 0, 1.6, 0.4, Math.PI / 2),
      at(torus(0.62, 0.12, p.trim, 10), 0, 1.6, 1.6),
    ),
  'thermal-projector': (p) =>
    group(
      at(barrel(1.5, 4.2, p.copper, 18), 0, 1.6, -1.6),
      ...[-1.2, 2].map((z) => at(torus(1.52, 0.18, p.trim, 18), 0, 1.6, z + 0.4)),
      at(dome(1.5, p.copper, 16), 0, 1.6, 2.6, Math.PI / 2),
      at(barrel(0.8, 3.6, p.iron, 14), 0, 0, 0),
      at(lathe([[0.8, 0], [0.9, 0.4], [1.6, 2.4], [1.7, 2.6], [1.2, 2.6]], p.trim, 18), 0, 0, 3.4, Math.PI / 2),
      at(sphere(0.55, p.fire, 10), 0, 0, 5.5),
      pipe([[0, 1, 1.6], [0, 0.7, 2.6]], 0.3, p.trim),
      at(gauge(0.6, p, 0.6), 1.55, 1.6, 0, 0, Math.PI / 2),
    ),
  'missile-rack': (p) => {
    const rack = group(plate(4.8, 3.8, 5.6, p.hull, 0.5), at(plate(5, 4, 0.6, p.iron, 0.2), 0, 0, 2.7), at(plate(5.2, 0.5, 5, p.iron, 0.2), 0, 2.1, -0.2));
    for (const x of [-1.5, 0, 1.5])
      for (const y of [-0.85, 0.85]) {
        rack.add(at(cyl(0.6, 0.6, 0.5, p.iron, 14), x, y, 3, Math.PI / 2));
        rack.add(at(dome(0.45, p.trim, 10), x, y, 2.9, Math.PI / 2));
      }
    rack.add(rivetRow([-2.45, 1.2, -2], [-2.45, 1.2, 2], 4, 0.2, p.trim, [-1, 0, 0]));
    rack.add(rivetRow([2.45, 1.2, -2], [2.45, 1.2, 2], 4, 0.2, p.trim, [1, 0, 0]));
    return rack;
  },
  'rail-lance': (p) =>
    group(
      plate(3.4, 3.2, 5.2, p.iron, 0.5),
      at(plate(3.8, 0.6, 4.4, p.trim, 0.2), 0, 1.7, 0),
      ...[-1, 1].map((s) => at(cyl(0.7, 0.7, 4, p.copper, 12), s * 2, 0, -0.2, Math.PI / 2)),
      ...[-1, 1].map((s) => at(plate(0.7, 1.1, 14, p.iron, 0.2), s * 0.95, 0, 8.5)),
      ...[-1, 1].map((s) => at(box(0.25, 0.5, 13, p.glow), s * 0.55, 0, 8.6)),
      ...[4.5, 8, 11.5].flatMap((z) => [at(torus(1.55, 0.22, p.glow, 20), 0, 0, z), at(torus(1.75, 0.18, p.trim, 20), 0, 0, z + 0.45)]),
      at(plate(3, 1.7, 0.8, p.trim, 0.2), 0, 0, 15.2),
      pipe([[1.9, -0.6, -2], [2.1, -1.4, 0], [1.4, -1.2, 3]], 0.3, p.copper),
    ),
  'arc-mortar': (p) =>
    group(
      at(plate(4.2, 1.6, 4.2, p.iron, 0.4), 0, -1, 0),
      at(cyl(1.4, 1.4, 1, p.trim, 16), 0, 0, 0),
      at(
        group(
          lathe([[1.9, 0], [1.9, 3.6], [2.2, 4.2], [2.2, 5], [1.6, 5]], p.iron, 22),
          ...[1, 2.4].map((y) => at(torus(1.95, 0.22, p.trim, 22), 0, y, 0, Math.PI / 2)),
          at(torus(1.75, 0.3, p.glow, 22), 0, 4.9, 0, Math.PI / 2),
        ),
        0,
        0.2,
        0.2,
        0.55,
      ),
      piston([0, -0.6, -1.6], [0, 2.2, -0.4], 0.4, p),
    ),
  'ion-lance': (p) =>
    group(
      plate(2.6, 2.6, 3, p.iron, 0.4),
      at(barrel(0.5, 9, p.trim, 12), 0, 0, 1),
      ...[3, 4.6, 6.2, 7.8].map((z) => at(cyl(0.95, 0.95, 0.35, p.enamel, 16), 0, 0, z, Math.PI / 2)),
      ...[3.8, 5.4, 7].map((z) => at(torus(0.75, 0.16, p.glow, 14), 0, 0, z)),
      at(sphere(0.5, p.glow, 12), 0, 0, 10.2),
      at(cyl(0.45, 0.45, 2.2, p.copper, 10), 0, 1.5, 0, Math.PI / 2),
    ),
  'impact-hammer': (p) =>
    group(
      at(barrel(0.9, 3.4, p.iron), 0, 0, 0),
      at(barrel(0.5, 2.6, p.trim), 0, 0, 3),
      at(cyl(1.25, 1.25, 0.6, p.trim, 14), 0, 0, 3.2, Math.PI / 2),
      at(plate(4.4, 3.4, 3.4, p.iron, 0.4), 0, 0, 7),
      ...[5.9, 8.1].map((z) => at(plate(4.7, 3.7, 0.5, p.trim, 0.15), 0, 0, z)),
      at(plate(3.6, 2.6, 0.8, p.hull, 0.25), 0, 0, 8.9),
      rivetRow([-1.8, 1.75, 6.4], [-1.8, 1.75, 7.6], 2, 0.22, p.trim, [0, 1, 0]),
      rivetRow([1.8, 1.75, 6.4], [1.8, 1.75, 7.6], 2, 0.22, p.trim, [0, 1, 0]),
      at(cyl(0.6, 0.6, 2.4, p.copper, 10), 0, 1.4, 1.8, Math.PI / 2),
    ),
  'shear-blade': (p) => {
    const shape = new THREE.Shape();
    shape.moveTo(0, -1);
    shape.lineTo(7, -0.6);
    shape.quadraticCurveTo(9.6, 0.2, 9.2, 1.4);
    shape.lineTo(0, 1.3);
    shape.lineTo(0, -1);
    const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.4, bevelEnabled: true, bevelThickness: 0.2, bevelSize: 0.2, bevelSegments: 1 });
    geo.translate(0, 0, -0.2);
    const blade = new THREE.Mesh(geo, p.steel);
    return group(
      plate(2, 2.2, 2.4, p.iron, 0.4),
      at(plate(3, 3, 0.6, p.trim, 0.25), 0, 0, 1.4),
      at(blade, 0, 0, 1.6, 0, -Math.PI / 2),
      at(box(0.3, 0.25, 7.6, p.fire), 0, -0.98, 5.2),
      rivetRow([0.5, 0, 2.4], [0.5, 0, 5.6], 3, 0.2, p.trim, [1, 0, 0]),
    );
  },
  // ------------------------------------------------ armour
  'ablative-plating': (p) =>
    group(
      at(plate(5.2, 4.2, 1.2, p.iron, 0.3), 0, 0, 0.6),
      at(plate(4.8, 2.1, 0.9, p.hull, 0.3), 0, 1.05, 1.5, -0.12),
      at(plate(4.8, 2.1, 0.9, p.hull, 0.3), 0, -1, 1.5, -0.12),
      rivetRow([-2, 1.6, 2], [2, 1.6, 2], 4, 0.22, p.trim),
      rivetRow([-2, -0.45, 2], [2, -0.45, 2], 4, 0.22, p.trim),
    ),
  'reactive-shell': (p) =>
    group(
      at(plate(5, 3.8, 0.8, p.iron, 0.2), 0, 0, 0.4),
      ...[-1.6, 0, 1.6].flatMap((x) =>
        [-0.9, 0.9].flatMap((y) => [at(plate(1.4, 1.6, 1.2, p.hull, 0.25), x, y, 1.3), at(dome(0.25, p.trim, 8), x, y, 1.9, Math.PI / 2)]),
      ),
    ),
  'kinetic-shield': (p) => {
    const face = lathe([[4.6, 0], [4.6, 0.5], [3.2, 1.1], [1.2, 1.4]], p.hull, 32);
    return group(
      at(face, 0, 0, 1.2, Math.PI / 2),
      at(torus(4.6, 0.38, p.trim, 36), 0, 0, 1.45),
      at(rivetRing(3.9, 12, 0.22, p.trim, true), 0, 0, 1.55),
      at(cyl(1.3, 1.3, 0.6, p.trim, 20), 0, 0, 2.6, Math.PI / 2),
      at(sphere(0.9, p.glow, 16), 0, 0, 2.95),
      ...[0, 1, 2, 3].map((i) => at(box(0.35, 2.2, 0.2, p.glow), Math.cos((i * Math.PI) / 2 + 0.785) * 2.4, Math.sin((i * Math.PI) / 2 + 0.785) * 2.4, 2.05, 0, 0, (i * Math.PI) / 2 + 0.785 + Math.PI / 2)),
      at(plate(2, 2, 1.4, p.iron, 0.3), 0, 0, 0.5),
    );
  },
  'smoke-launcher': (p) =>
    group(
      plate(3.4, 1.6, 2.4, p.iron, 0.3),
      at(plate(3.6, 0.4, 2.6, p.trim, 0.15), 0, 0.8, 0),
      ...[-1, 0, 1].flatMap((i) => [
        at(cyl(0.55, 0.55, 2.6, p.iron, 12), i * 1.1, 1.8, 0.4, -0.45),
        at(cyl(0.65, 0.65, 0.4, p.trim, 12), i * 1.1, 3, 0.95, -0.45),
      ]),
    ),
  // ------------------------------------------------ mobility
  'jump-jets': (p) =>
    group(
      at(plate(4.6, 2.4, 2.2, p.iron, 0.4), 0, 0.6, 0),
      at(cyl(0.9, 0.9, 3.4, p.copper, 14), 0, 2.4, 0),
      at(dome(0.9, p.copper, 12), 0, 4.1, 0),
      ...[-1.4, 1.4].flatMap((x) => [
        at(lathe([[1.5, -2.4], [1.1, -0.4], [0.9, 0]], p.iron, 16), x, 0, 0),
        at(torus(1.45, 0.16, p.trim, 16), x, -2.3, 0, Math.PI / 2),
        at(cyl(1.3, 1.3, 0.2, p.fire, 16), x, -2.45, 0),
      ]),
    ),
  'sprint-servos': (p) =>
    group(
      at(gear(1.6, 0.6, 12, p.trim), 0, 1.2, 0, 0, 0, Math.PI / 2),
      at(gear(1, 0.5, 9, p.copper), 0.1, -0.6, 1.4, 0, 0, Math.PI / 2),
      at(cyl(0.6, 0.6, 1.6, p.iron, 12), 0, 1.2, 0, 0, 0, Math.PI / 2),
      piston([0, -2.8, -0.4], [0, 0.6, -0.8], 0.45, p),
    ),
  'gyro-stabilisers': (p) =>
    group(
      sphere(1.2, p.iron, 16),
      at(sphere(0.6, p.glow, 12), 0, 0, 1.05),
      at(torus(2.2, 0.28, p.trim, 24), 0, 0, 0, Math.PI / 2),
      at(torus(1.8, 0.24, p.copper, 24), 0, 0, 0, 0, Math.PI / 2),
      at(torus(2.2, 0.16, p.trim, 24), 0, 0, 0),
      at(cyl(0.4, 0.4, 5, p.iron, 10), 0, 0, 0),
    ),
  'anchor-spikes': (p) =>
    group(
      at(plate(4, 1.2, 2, p.iron, 0.3), 0, -0.4, 0),
      ...[-1.2, 1.2].flatMap((x) => [
        at(cyl(0.95, 0.95, 0.8, p.trim, 12), x, -1.2, 0),
        at(lathe([[0.8, 0], [0.8, 0.6], [0.05, 4]], p.iron, 12), x, -1.4, 0, Math.PI),
      ]),
    ),
  // ------------------------------------------------ systems
  'targeting-array': (p) => {
    const dish = new THREE.Mesh(new THREE.SphereGeometry(1.8, 18, 6, 0, Math.PI * 2, 0, Math.PI / 3), p.trim);
    return group(
      at(cyl(0.9, 1.1, 0.8, p.iron, 14), 0, 0.4, 0),
      at(cyl(0.3, 0.3, 2.6, p.iron, 10), 0, 2, 0),
      at(lathe([[0.7, 0], [0.7, 3.4], [0.9, 3.6], [0.9, 4.4], [0.6, 4.4]], p.trim, 16), 0, 3.4, -2, Math.PI / 2),
      at(cyl(0.6, 0.6, 0.2, p.glow, 14), 0, 3.4, 2.45, Math.PI / 2),
      ...[-0.6, 1.2].map((z) => at(torus(0.75, 0.14, p.iron, 14), 0, 3.4, z)),
      at(dish, 0, 2.2, -1.2, -Math.PI / 2.2),
      at(sphere(0.25, p.glow, 8), 0, 2.4, -0.5),
    );
  },
  'coolant-loop': (p) => {
    const coil: Array<[number, number, number]> = [];
    for (let i = 0; i <= 28; i++) {
      const a = (i / 28) * Math.PI * 6;
      coil.push([Math.cos(a) * 1.7, 0.6 + (i / 28) * 3.4, Math.sin(a) * 1.7]);
    }
    return group(
      at(cyl(1.1, 1.1, 4.4, p.iron, 16), 0, 2.4, 0),
      at(dome(1.1, p.trim, 14), 0, 4.6, 0),
      at(plate(3.8, 0.6, 3.8, p.iron, 0.25), 0, 0.3, 0),
      pipe(coil, 0.26, p.copper),
      at(gauge(0.5, p, 0.2), 0, 3.2, 1.15),
    );
  },
  'overcharged-boiler': (p) =>
    group(
      lathe([[2, 0], [2, 0.4], [1.7, 0.7], [1.7, 4.6], [1.2, 5.6], [0.5, 6]], p.copper),
      ...[1.2, 2.6, 4].map((y) => at(torus(1.75, 0.2, p.trim, 20), 0, y, 0, Math.PI / 2)),
      at(cyl(0.65, 0.65, 0.3, p.fire, 14), 0, 1.9, 1.65, Math.PI / 2),
      at(torus(0.7, 0.18, p.trim, 14), 0, 1.9, 1.75),
      at(gauge(0.55, p, 0.85), 0, 3.4, 1.75),
      at(cyl(0.35, 0.35, 1.6, p.trim, 10), 0, 6.4, 0),
      at(sphere(0.5, p.trim, 10), 0, 7.2, 0),
      pipe([[1.7, 4.2, 0], [2.5, 4.4, 0], [2.6, 0.5, 0]], 0.25, p.trim),
    ),
  'static-choir': (p) =>
    group(
      at(cyl(1.3, 1.5, 1, p.iron, 16), 0, 0.5, 0),
      at(cyl(0.3, 0.4, 7.4, p.iron, 10), 0, 4.4, 0),
      ...[2.4, 3.9, 5.4].map((y, i) => at(cyl(1.5 - i * 0.35, 1.5 - i * 0.35, 0.3, p.enamel, 18), 0, y, 0)),
      ...[3.15, 4.65].map((y) => at(torus(0.9, 0.12, p.copper, 14), 0, y, 0, Math.PI / 2)),
      at(torus(0.9, 0.22, p.glow, 18), 0, 7.6, 0, Math.PI / 2),
      at(sphere(0.45, p.glow, 12), 0, 8.4, 0),
    ),
  'spotter-drone': (p) =>
    group(
      at(cyl(1, 1.2, 0.8, p.iron, 14), 0, 0.4, 0),
      at(cyl(0.25, 0.25, 2.2, p.iron, 8), 0, 1.8, 0),
      at(lathe([[0.5, 0], [1.6, 0.4], [1.8, 0.9], [1.3, 1.4], [0, 1.6]], p.hull, 20), 0, 2.8, 0),
      at(torus(1.8, 0.16, p.trim, 20), 0, 3.7, 0, Math.PI / 2),
      at(sphere(0.45, p.glow, 12), 0, 3.6, 1.5),
      at(torus(0.5, 0.12, p.trim, 12), 0, 3.6, 1.7),
      at(cyl(0.15, 0.15, 0.8, p.trim, 6), 0, 4.7, 0),
      ...[0, Math.PI / 2].map((ry) => at(box(4.4, 0.1, 0.5, p.trim), 0, 5.1, 0, 0, ry + 0.4, 0.08)),
    ),
  'field-repair-rig': (p) =>
    group(
      at(cyl(1, 1.2, 0.8, p.iron, 14), 0, 0.4, 0),
      at(gear(1.1, 0.4, 10, p.trim), 0, 1.1, 0),
      at(cyl(0.45, 0.45, 3.6, p.iron, 10), 0, 2.8, 0),
      at(sphere(0.6, p.trim, 10), 0, 4.6, 0),
      at(group(at(plate(0.8, 0.8, 5, p.trim, 0.2), 0, 0, 2.4), piston([0, -1.6, -0.2], [0, -0.3, 2.2], 0.3, p)), 0, 4.6, 0, -0.3),
      at(cyl(0.08, 0.08, 1.8, p.iron, 6), 0, 5.2, 4.8),
      at(torus(0.4, 0.12, p.trim, 10), 0, 4.1, 4.8, 0, Math.PI / 2),
      at(plate(1.8, 1.2, 1.4, p.copper, 0.25), -1.4, 0.9, -0.6),
    ),
};

/** Scale for equipment on a chassis, so parts grow with the walker. */
export const partScale = (chassisId: string) => SCALE[chassisId] ?? 1;
