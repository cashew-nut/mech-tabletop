// Procedural parts for war-walker models. Units are millimetres, so an
// exported STL prints at tabletop scale (a 2-inch hex is 50.8 mm). +Y is up
// and +Z is forward. Chassis live in chassis.ts; this file holds the items,
// each built at Scout scale with its origin where it attaches.
import * as THREE from 'three';
import { at, barrel, box, cyl, dome, gauge, group, lathe, pipe, plate, rivetRing, rivetRow, sphere, torus, type Palette } from './kit';

export { makePalette, type Palette } from './kit';
export { BASE_MM, buildChassis, type ChassisModel } from './chassis';

const SCALE: Record<string, number> = { scout: 1, striker: 1.2, bulwark: 1.4, titan: 1.7 };

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
      plate(3.4, 3.2, 5.2, p.iron, 0.5),
      at(plate(3.8, 0.6, 4.4, p.trim, 0.2), 0, 1.7, 0),
      ...[-1, 1].map((s) => at(cyl(0.7, 0.7, 4, p.copper, 12), s * 2, 0, -0.2, Math.PI / 2)),
      ...[-1, 1].map((s) => at(plate(0.7, 1.1, 14, p.iron, 0.2), s * 0.95, 0, 8.5)),
      ...[-1, 1].map((s) => at(box(0.25, 0.5, 13, p.glow), s * 0.55, 0, 8.6)),
      ...[4.5, 8, 11.5].flatMap((z) => [at(torus(1.55, 0.22, p.glow, 20), 0, 0, z), at(torus(1.75, 0.18, p.trim, 20), 0, 0, z + 0.45)]),
      at(plate(3, 1.7, 0.8, p.trim, 0.2), 0, 0, 15.2),
      pipe([[1.9, -0.6, -2], [2.1, -1.4, 0], [1.4, -1.2, 3]], 0.3, p.copper),
    ),
  'arc-mortar': (p) => group(at(box(4, 2, 4, p.iron), 0, -1, 0), at(cyl(1.8, 2.2, 5, p.hull), 0, 1.5, 0.5, 0.5), at(torus(1.9, 0.4, p.trim), 0, 3.3, 1.7, 0.5 + Math.PI / 2)),
  'ion-lance': (p) => group(at(barrel(0.6, 8, p.trim), 0, 0, 0), ...[2, 4, 6].map((z) => at(torus(1.1, 0.3, p.glow), 0, 0, z)), box(2.4, 2.4, 2.4, p.iron)),
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
    shape.moveTo(0, -1.2);
    shape.lineTo(9, 0);
    shape.lineTo(0, 1.5);
    shape.lineTo(0, -1.2);
    const blade = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: 0.5, bevelEnabled: false }), p.trim);
    blade.rotation.y = -Math.PI / 2;
    return group(box(2, 2, 2, p.iron), at(blade, 0.25, 0, 0.5, 0, -Math.PI / 2));
  },
  'ablative-plating': (p) =>
    group(
      at(plate(5.2, 4.2, 1.2, p.iron, 0.3), 0, 0, 0.6),
      at(plate(4.8, 2.1, 0.9, p.hull, 0.3), 0, 1.05, 1.5, -0.12),
      at(plate(4.8, 2.1, 0.9, p.hull, 0.3), 0, -1, 1.5, -0.12),
      rivetRow([-2, 1.6, 2], [2, 1.6, 2], 4, 0.22, p.trim),
      rivetRow([-2, -0.45, 2], [2, -0.45, 2], 4, 0.22, p.trim),
    ),
  'reactive-shell': (p) => group(...[-1.5, 0, 1.5].flatMap((x) => [-1, 1].map((y) => at(box(1.3, 1.6, 1.2, p.iron), x, y, 1)))),
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
  'jump-jets': (p) =>
    group(
      ...[-1.4, 1.4].map((x) => at(cyl(1.2, 1.2, 4, p.iron), x, 0, 0)),
      ...[-1.4, 1.4].map((x) => at(cyl(1.4, 0.8, 1.5, p.glow), x, -2.6, 0)),
    ),
  'sprint-servos': (p) => group(at(cyl(0.8, 0.8, 5, p.trim), 0, 0, 0), at(cyl(1.2, 1.2, 1.5, p.iron), 0, 2.2, 0)),
  'gyro-stabilisers': (p) => group(sphere(1.6, p.iron), at(torus(2.2, 0.35, p.trim), 0, 0, 0, Math.PI / 2), at(torus(2.2, 0.35, p.trim), 0, 0, 0, 0, Math.PI / 2)),
  'anchor-spikes': (p) =>
    group(
      at(plate(4, 1.2, 2, p.iron, 0.3), 0, -0.4, 0),
      ...[-1.2, 1.2].flatMap((x) => [
        at(cyl(0.95, 0.95, 0.8, p.trim, 12), x, -1.2, 0),
        at(lathe([[0.8, 0], [0.8, 0.6], [0.05, 4]], p.iron, 12), x, -1.4, 0, Math.PI),
      ]),
    ),
  'targeting-array': (p) => {
    const dish = new THREE.Mesh(new THREE.SphereGeometry(2.4, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2.5), p.trim);
    dish.rotation.x = Math.PI / 2;
    return group(at(cyl(0.4, 0.4, 3, p.iron), 0, 1.5, 0), at(dish, 0, 3.5, 0.3), at(sphere(0.5, p.glow), 0, 3.5, 1.4));
  },
  'coolant-loop': (p) => group(at(torus(2, 0.6, p.trim), 0, 1.5, 0), at(cyl(1, 1, 2.5, p.iron), 0, 0.5, 0)),
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
  'static-choir': (p) => group(at(cyl(0.3, 0.3, 7, p.iron), 0, 3.5, 0), ...[2.5, 4.5, 6.5].map((y) => at(cyl(1.6 - y / 8, 1.6 - y / 8, 0.3, p.trim), 0, y, 0))),
  'spotter-drone': (p) => group(at(cyl(0.3, 0.3, 3, p.iron), 0, 1.5, 0), at(cyl(2.2, 1.2, 0.8, p.hull), 0, 3.4, 0), at(sphere(0.6, p.glow), 0, 3.4, 1.6)),
  'field-repair-rig': (p) =>
    group(at(cyl(0.5, 0.5, 4, p.iron), 0, 2, 0), at(box(0.8, 0.8, 5, p.trim), 0, 4, 2), at(box(1.6, 1.2, 1.2, p.iron), 0, 3.4, 4.5), at(torus(0.8, 0.25, p.trim), 0, 2.6, 4.5)),
};

/** Scale for equipment on a chassis, so parts grow with the walker. */
export const partScale = (chassisId: string) => SCALE[chassisId] ?? 1;
