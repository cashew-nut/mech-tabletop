// Procedural parts for war-walker models. Units are millimetres, so an
// exported STL prints at tabletop scale (a 2-inch hex is 50.8 mm). +Y is up
// and +Z is forward. Chassis live in chassis.ts; this file holds the items,
// each built at Scout scale with its origin where it attaches.
import * as THREE from 'three';
import { at, barrel, blade, box, cyl, dome, group, lancet, lathe, piston, pipe, plate, rivetRow, sphere, spire, sunburst, torus, trimmed, type Palette } from './kit';

export { makePalette, type Palette } from './kit';
export { BASE_MM, baseMm, buildChassis, frameOf, type ChassisModel } from './chassis';
import { frameOf } from './chassis';

const SCALE: Record<string, number> = { scout: 1, striker: 1.2, bulwark: 1.4, titan: 1.7 };

// ---------------------------------------------------------------- equipment

type PartBuilder = (p: Palette) => THREE.Object3D;

/** Meshes for each item, built at Scout scale and pointing forward. */
export const PARTS: Record<string, PartBuilder> = {
  // ------------------------------------------------ weapons
  autocannon: (p) =>
    group(
      trimmed(3, 3.2, 5.2, p),
      at(barrel(0.6, 9, p.iron, 14), 0, 0.3, 2),
      at(barrel(0.95, 3.4, p.armour, 16), 0, 0.3, 2.2),
      ...[2.6, 4, 5.4].map((z) => at(torus(0.97, 0.14, p.trim, 14), 0, 0.3, z)),
      at(lathe([[0.7, 0], [1.1, 0.6], [1.1, 1.4], [0.8, 1.6]], p.trim, 14), 0, 0.3, 10.4, Math.PI / 2),
      at(barrel(1.2, 1.6, p.copper, 18), 2.2, -0.4, -1.4, 0, Math.PI / 2),
    ),
  'carapace-gun': (p) =>
    group(
      at(barrel(1.3, 4.4, p.iron, 18), 0, 0, -1.2),
      ...[0.4, 1.4, 2.4].map((z) => at(torus(1.4, 0.26, p.copper, 18), 0, 0, z)),
      at(lathe([[1.4, 0], [1.6, 0.6], [1.1, 1.6], [0.7, 1.8]], p.trim, 18), 0, 0, 3.2, Math.PI / 2),
      at(sphere(0.75, p.glow, 14), 0, 0, 5.1),
      at(cyl(0.6, 0.6, 2.6, p.copper, 10), 0, 1.6, 0.4, Math.PI / 2),
      at(torus(0.62, 0.12, p.trim, 10), 0, 1.6, 1.6),
    ),
  'missile-rack': (p) => {
    const rack = group(trimmed(4.8, 3.8, 5.6, p), at(plate(5.2, 0.5, 5, p.trim, 0.2), 0, 2.1, -0.2));
    for (const x of [-1.5, 0, 1.5])
      for (const y of [-0.9, 0.9]) {
        rack.add(at(lancet(1.1, 1.5, 0.4, p.iron), x, y, 2.9));
        rack.add(at(dome(0.38, p.trim, 10), x, y - 0.2, 2.95, Math.PI / 2));
      }
    rack.add(at(spire(0.5, 3, p), -1.8, 2.3, -2));
    rack.add(at(spire(0.5, 3, p), 1.8, 2.3, -2));
    return rack;
  },
  'rail-cannon': (p) =>
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
  'rocket-pod': (p) =>
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
  'arc-cannon': (p) =>
    group(
      plate(2.6, 2.6, 3, p.iron, 0.4),
      at(barrel(0.5, 9, p.trim, 12), 0, 0, 1),
      ...[3, 4.6, 6.2, 7.8].map((z) => at(cyl(0.95, 0.95, 0.35, p.enamel, 16), 0, 0, z, Math.PI / 2)),
      ...[3.8, 5.4, 7].map((z) => at(torus(0.75, 0.16, p.glow, 14), 0, 0, z)),
      at(sphere(0.5, p.glow, 12), 0, 0, 10.2),
      at(cyl(0.45, 0.45, 2.2, p.copper, 10), 0, 1.5, 0, Math.PI / 2),
    ),
  'industrial-claw': (p) =>
    group(
      at(barrel(0.9, 3.4, p.iron), 0, 0, 0),
      at(barrel(0.5, 2.6, p.trim), 0, 0, 3),
      at(cyl(1.25, 1.25, 0.6, p.trim, 14), 0, 0, 3.2, Math.PI / 2),
      at(plate(4.4, 3.4, 3.4, p.iron, 0.4), 0, 0, 7),
      ...[5.9, 8.1].map((z) => at(plate(4.7, 3.7, 0.5, p.trim, 0.15), 0, 0, z)),
      at(plate(3.6, 2.6, 0.8, p.armour, 0.25), 0, 0, 8.9),
      rivetRow([-1.8, 1.75, 6.4], [-1.8, 1.75, 7.6], 2, 0.22, p.trim, [0, 1, 0]),
      rivetRow([1.8, 1.75, 6.4], [1.8, 1.75, 7.6], 2, 0.22, p.trim, [0, 1, 0]),
      at(cyl(0.6, 0.6, 2.4, p.copper, 10), 0, 1.4, 1.8, Math.PI / 2),
    ),
  lance: (p) =>
    group(
      plate(2, 2.2, 2.4, p.iron, 0.4),
      at(cyl(1.6, 0.5, 2.6, p.trim, 16), 0, 0, 2.4, Math.PI / 2),
      at(cyl(0.5, 0.3, 9, p.iron, 10), 0, 0, 8, Math.PI / 2),
      at(spire(0.55, 3, p), 0, 0, 12.4, Math.PI / 2),
      at(plate(0.2, 2.4, 3, p.hull, 0.05), 0, -1.6, 4.4),
    ),
  'kinetic-claws': (p) =>
    group(
      plate(2, 2.2, 2.4, p.iron, 0.4),
      ...[-0.9, 0, 0.9].map((x) => at(blade(5.5, 0.9, p), x, -0.4, 1.6, 0, x * 0.25)),
      at(torus(0.9, 0.18, p.glow, 12), 0, 0, 1.2),
    ),
  // ------------------------------------------------ armour
  'kinetic-shield': (p) => {
    // A heater shield: flat top, curving to a point below.
    const s = new THREE.Shape();
    s.moveTo(-4, 3.6);
    s.lineTo(4, 3.6);
    s.lineTo(4, 0.6);
    s.quadraticCurveTo(3.6, -3.6, 0, -6);
    s.quadraticCurveTo(-3.6, -3.6, -4, 0.6);
    s.lineTo(-4, 3.6);
    const face = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: 0.8, bevelEnabled: true, bevelThickness: 0.3, bevelSize: 0.3, bevelSegments: 2 }), p.armour);
    const rim = new THREE.Mesh(new THREE.ExtrudeGeometry(s, { depth: 0.5, bevelEnabled: true, bevelThickness: 0.2, bevelSize: 0.55, bevelSegments: 1 }), p.trim);
    return group(
      at(rim, 0, 0, 0.6),
      at(face, 0, 0, 0.9),
      at(sunburst(2.4, p), 0, 0.4, 2.15),
      at(sphere(0.6, p.glow, 12), 0, 0.4, 2.2),
      at(box(0.4, 7.4, 0.3, p.trim), 0, -1.4, 2.05),
      at(plate(2, 2, 1.4, p.iron, 0.3), 0, 0, 0.3),
    );
  },
  // ------------------------------------------------ systems
  'soul-lantern': (p) => {
    // A belfry: four posts round a gold bell, under a spire.
    const g = group(at(plate(3.6, 0.8, 3.6, p.armour, 0.25), 0, 0.4, 0));
    for (const [x, z] of [
      [-1.4, -1.4],
      [1.4, -1.4],
      [-1.4, 1.4],
      [1.4, 1.4],
    ])
      g.add(at(box(0.5, 3.6, 0.5, p.armour), x, 2.6, z));
    g.add(at(lathe([[1.15, 0], [1.05, 0.3], [0.7, 1.4], [0.5, 2], [0, 2.1]], p.trim, 18), 0, 1.6, 0));
    g.add(at(sphere(0.25, p.glow, 8), 0, 1.5, 0));
    g.add(at(plate(3.8, 0.6, 3.8, p.trim, 0.2), 0, 4.6, 0));
    g.add(at(spire(1.3, 5, p), 0, 4.9, 0));
    return g;
  },
};

/** Scale for equipment on a chassis, so parts grow with the walker's frame. */
export const partScale = (chassisId: string) => SCALE[frameOf(chassisId)] ?? 1;
