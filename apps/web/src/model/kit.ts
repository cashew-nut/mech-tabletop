// Building blocks for the procedural war-walker parts: materials with a little
// wear, bevelled plates, lathed boiler shapes, pipes, rivets, gauges and
// pistons. Units are millimetres, +Y up, +Z forward.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export interface Palette {
  /** Company livery: banners, tabards and painted panels. Recoloured with the walker's paint. */
  hull: THREE.Material;
  /** Blackened, oiled armour plate. */
  armour: THREE.Material;
  /** Gold filigree and fittings. */
  trim: THREE.Material;
  /** Dark gunmetal frame, joints and barrels. */
  iron: THREE.Material;
  /** Pale lamp-light of energy weapons. */
  glow: THREE.Material;
  /** Firebox and furnace light. */
  fire: THREE.Material;
  copper: THREE.Material;
  /** Gauge faces. */
  enamel: THREE.Material;
  /** The ground on top of the base. */
  ground: THREE.Material;
  /** Polished steel for blades. */
  steel: THREE.Material;
}

// ---------------------------------------------------------------- materials

/** Blotchy greyscale noise, used as a roughness map so metal looks handled and worn. */
function wearTexture(seed: number) {
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d')!;
  // Mostly near-white, so the material's own roughness holds, with darker
  // (shinier) worn patches where hands and weather have polished it.
  g.fillStyle = '#e6e6e6';
  g.fillRect(0, 0, 256, 256);
  let s = seed;
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 900; i++) {
    const v = Math.floor(150 + rand() * 105);
    g.fillStyle = `rgba(${v},${v},${v},${0.08 + rand() * 0.2})`;
    g.beginPath();
    g.arc(rand() * 256, rand() * 256, 2 + rand() * 18, 0, Math.PI * 2);
    g.fill();
  }
  // Fine scratches.
  g.strokeStyle = 'rgba(90,90,90,0.3)';
  for (let i = 0; i < 120; i++) {
    const x = rand() * 256;
    const y = rand() * 256;
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(x + (rand() - 0.5) * 30, y + (rand() - 0.5) * 6);
    g.stroke();
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  return tex;
}

let wear: { metal: THREE.Texture | null; paint: THREE.Texture | null } | null = null;
const shared = () => (wear ??= { metal: wearTexture(7), paint: wearTexture(31) });

export function makePalette(hullColour: string): Palette {
  const { metal, paint } = shared();
  return {
    hull: new THREE.MeshStandardMaterial({ name: 'hull', color: hullColour, roughness: 0.95, metalness: 0, side: THREE.DoubleSide }),
    armour: new THREE.MeshPhysicalMaterial({
      name: 'armour',
      color: '#242327',
      roughness: 0.4,
      roughnessMap: paint,
      metalness: 0.9,
      clearcoat: 0.25,
      clearcoatRoughness: 0.5,
    }),
    trim: new THREE.MeshStandardMaterial({ name: 'gold', color: '#c99a45', roughness: 0.36, roughnessMap: metal, metalness: 1 }),
    iron: new THREE.MeshStandardMaterial({ name: 'iron', color: '#35322f', roughness: 0.6, roughnessMap: metal, metalness: 0.85 }),
    glow: new THREE.MeshStandardMaterial({ name: 'glow', color: '#2a1c08', emissive: '#ffb347', emissiveIntensity: 1.3, roughness: 0.3 }),
    fire: new THREE.MeshStandardMaterial({ name: 'fire', color: '#2a0c02', emissive: '#ff6410', emissiveIntensity: 1.15, roughness: 0.4 }),
    copper: new THREE.MeshStandardMaterial({ name: 'bronze', color: '#7a5634', roughness: 0.45, roughnessMap: metal, metalness: 1 }),
    enamel: new THREE.MeshStandardMaterial({ name: 'enamel', color: '#efe4c6', roughness: 0.5, metalness: 0 }),
    steel: new THREE.MeshStandardMaterial({ name: 'steel', color: '#5c6066', roughness: 0.3, roughnessMap: metal, metalness: 1 }),
    ground: new THREE.MeshStandardMaterial({ name: 'ground', color: '#2b2824', roughness: 1, metalness: 0 }),
  };
}

// ---------------------------------------------------------------- placing

export type V3 = [number, number, number];

export function at<T extends THREE.Object3D>(obj: T, x: number, y: number, z: number, rx = 0, ry = 0, rz = 0): T {
  obj.position.set(x, y, z);
  obj.rotation.set(rx, ry, rz);
  return obj;
}

export function group(...children: THREE.Object3D[]) {
  const g = new THREE.Group();
  for (const c of children) g.add(c);
  return g;
}

// ---------------------------------------------------------------- shapes

const mesh = (g: THREE.BufferGeometry, m: THREE.Material) => new THREE.Mesh(g, m);

export const box = (w: number, h: number, d: number, m: THREE.Material) => mesh(new THREE.BoxGeometry(w, h, d), m);

/** A bevelled plate or block. */
export const plate = (w: number, h: number, d: number, m: THREE.Material, r = Math.min(w, h, d) * 0.18) =>
  mesh(new RoundedBoxGeometry(w, h, d, 2, Math.min(r, Math.min(w, h, d) / 2 - 0.01)), m);

export const cyl = (rTop: number, rBottom: number, h: number, m: THREE.Material, seg = 20) =>
  mesh(new THREE.CylinderGeometry(rTop, rBottom, h, seg), m);

export const sphere = (r: number, m: THREE.Material, seg = 18) => mesh(new THREE.SphereGeometry(r, seg, Math.ceil(seg * 0.7)), m);

/** A dome: the top half of a sphere, flat side down. */
export function dome(r: number, m: THREE.Material, seg = 20) {
  // Closed underneath, so it prints as a solid.
  const cap = new THREE.CircleGeometry(r, seg).rotateX(Math.PI / 2);
  const shell = new THREE.SphereGeometry(r, seg, Math.ceil(seg / 2), 0, Math.PI * 2, 0, Math.PI / 2);
  return mesh(mergeGeometries([shell.toNonIndexed(), cap.toNonIndexed()])!, m);
}

export const torus = (r: number, tube: number, m: THREE.Material, seg = 24) => mesh(new THREE.TorusGeometry(r, tube, 8, seg), m);

/** A shape turned around the Y axis from [radius, height] points, bottom to top. Closed at both ends. */
export function lathe(profile: Array<[number, number]>, m: THREE.Material, seg = 24) {
  const pts = profile.map(([r, y]) => new THREE.Vector2(Math.max(r, 0.001), y));
  const first = profile[0];
  const last = profile[profile.length - 1];
  if (first[0] > 0) pts.unshift(new THREE.Vector2(0.001, first[1]));
  if (last[0] > 0) pts.push(new THREE.Vector2(0.001, last[1]));
  return mesh(new THREE.LatheGeometry(pts, seg), m);
}

/** A cylinder lying along the given axis, centred on the origin. Wrapped in a group so `at` can still place and turn it. */
export function bar(r: number, len: number, m: THREE.Material, axis: 'x' | 'z' = 'z', seg = 16) {
  const c = cyl(r, r, len, m, seg);
  if (axis === 'z') c.rotation.x = Math.PI / 2;
  else c.rotation.z = Math.PI / 2;
  return group(c);
}

/** A barrel pointing forward along +Z from the origin. */
export function barrel(r: number, len: number, m: THREE.Material, seg = 16) {
  const b = bar(r, len, m, 'z', seg);
  b.position.z = len / 2;
  return group(b);
}

/** A pipe through the given points, with rounded bends. */
export function pipe(points: V3[], r: number, m: THREE.Material) {
  const curve = new THREE.CatmullRomCurve3(
    points.map((p) => new THREE.Vector3(...p)),
    false,
    'centripetal',
  );
  const tube = mesh(new THREE.TubeGeometry(curve, points.length * 10, r, 8, false), m);
  // Round off the open ends.
  return group(tube, at(sphere(r, m, 8), ...points[0]), at(sphere(r, m, 8), ...points[points.length - 1]));
}

const rivet = (r: number, m: THREE.Material) => dome(r, m, 8);

/** Rivets in a straight line from a to b, heads pointing along `normal`. */
export function rivetRow(a: V3, b: V3, count: number, r: number, m: THREE.Material, normal: V3 = [0, 0, 1]) {
  const g = new THREE.Group();
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...normal).normalize());
  for (let i = 0; i < count; i++) {
    const t = count === 1 ? 0.5 : i / (count - 1);
    const h = rivet(r, m);
    h.position.set(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
    h.quaternion.copy(q);
    g.add(h);
  }
  return g;
}

/**
 * Rivets round a ring of the given radius in the XY plane, heads pointing
 * outward from the centre, or along +Z when `axial`. Rotate the group to place it.
 */
export function rivetRing(radius: number, count: number, r: number, m: THREE.Material, axial = false) {
  const g = new THREE.Group();
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2;
    const h = rivet(r, m);
    h.position.set(Math.cos(a) * radius, Math.sin(a) * radius, 0);
    if (axial) h.rotation.x = Math.PI / 2;
    else h.rotation.z = a - Math.PI / 2;
    g.add(h);
  }
  return g;
}

/** A flared smokestack standing on the origin. */
export function smokestack(r: number, h: number, p: Palette) {
  const g = new THREE.Group();
  g.add(
    lathe(
      [
        [r * 1.5, 0],
        [r * 1.5, h * 0.06],
        [r, h * 0.12],
        [r, h * 0.78],
        [r * 1.25, h * 0.86],
        [r * 1.6, h],
        [r * 1.2, h],
        [r * 0.85, h * 0.9],
        [r * 0.85, h * 0.5],
      ],
      p.iron,
    ),
  );
  g.add(at(torus(r * 1.05, r * 0.14, p.trim), 0, h * 0.78, 0, Math.PI / 2));
  g.add(at(torus(r * 1.05, r * 0.1, p.trim), 0, h * 0.3, 0, Math.PI / 2));
  // A coal glow deep in the throat.
  g.add(at(cyl(r * 0.84, r * 0.84, 0.2, p.fire), 0, h * 0.86, 0));
  return g;
}

/** A pressure gauge facing +Z: brass bezel, enamel face and a needle. */
export function gauge(r: number, p: Palette, reading = 0.3) {
  const g = new THREE.Group();
  g.add(at(cyl(r, r, r * 0.5, p.trim, 20), 0, 0, 0, Math.PI / 2));
  g.add(at(cyl(r * 0.8, r * 0.8, r * 0.1, p.enamel, 20), 0, 0, r * 0.26, Math.PI / 2));
  g.add(at(torus(r * 0.9, r * 0.12, p.trim, 20), 0, 0, r * 0.28));
  const needle = box(r * 0.08, r * 0.7, r * 0.05, p.iron);
  needle.geometry.translate(0, r * 0.3, 0);
  g.add(at(needle, 0, 0, r * 0.33, 0, 0, reading * Math.PI));
  return g;
}

/** A brass gear wheel with its axle along Y. */
export function gear(r: number, thick: number, teeth: number, m: THREE.Material) {
  const g = group(cyl(r, r, thick, m, teeth * 2), cyl(r * 0.3, r * 0.3, thick * 1.6, m, 12));
  for (let i = 0; i < teeth; i++) {
    const a = (i / teeth) * Math.PI * 2;
    const t = box(r * 0.28, thick, r * 0.3, m);
    g.add(at(t, Math.cos(a) * r, 0, Math.sin(a) * r, 0, -a, 0));
  }
  return g;
}

/** A bevelled beam from a to b, `w` wide (along X) and `d` deep, for limbs and struts. */
export function link(a: V3, b: V3, w: number, d: number, m: THREE.Material) {
  const va = new THREE.Vector3(...a);
  const vb = new THREE.Vector3(...b);
  const beam = plate(w, va.distanceTo(vb), d, m);
  beam.position.copy(va).add(vb).multiplyScalar(0.5);
  beam.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), vb.sub(va).normalize());
  return beam;
}

/** A hydraulic piston from a to b: a fat iron sleeve and a thin brass rod. */
export function piston(a: V3, b: V3, r: number, p: Palette) {
  const va = new THREE.Vector3(...a);
  const vb = new THREE.Vector3(...b);
  const len = va.distanceTo(vb);
  const g = new THREE.Group();
  const sleeve = cyl(r, r, len * 0.55, p.iron, 12);
  sleeve.position.y = len * 0.275;
  const rod = cyl(r * 0.5, r * 0.5, len * 0.5, p.trim, 10);
  rod.position.y = len * 0.75;
  const collar = cyl(r * 1.25, r * 1.25, r * 0.6, p.trim, 12);
  collar.position.y = len * 0.55;
  g.add(sleeve, rod, collar, sphere(r * 1.1, p.iron, 10), at(sphere(r * 0.9, p.iron, 10), 0, len, 0));
  g.position.copy(va);
  g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), vb.clone().sub(va).normalize());
  return g;
}

// ---------------------------------------------------------------- gothic

/** The outline of a pointed (lancet) arch, `w` wide and `h` tall, standing on y = 0. */
function lancetShape(w: number, h: number) {
  const s = new THREE.Shape();
  const side = Math.max(0, h - w * 0.85);
  s.moveTo(-w / 2, 0);
  s.lineTo(-w / 2, side);
  s.quadraticCurveTo(-w / 2, side + (h - side) * 0.7, 0, h);
  s.quadraticCurveTo(w / 2, side + (h - side) * 0.7, w / 2, side);
  s.lineTo(w / 2, 0);
  s.lineTo(-w / 2, 0);
  return s;
}

/** A solid pointed arch facing +Z, `depth` thick. */
export function lancet(w: number, h: number, depth: number, m: THREE.Material) {
  const g = new THREE.ExtrudeGeometry(lancetShape(w, h), { depth, bevelEnabled: false, curveSegments: 6 });
  g.translate(0, -h / 2, -depth / 2);
  return mesh(g, m);
}

/** A lit cathedral window facing +Z: gold frame, glowing glass and a mullion. */
export function archWindow(w: number, h: number, p: Palette, light: THREE.Material = p.fire) {
  return group(
    lancet(w + 0.6, h + 0.5, 0.5, p.trim),
    at(lancet(w, h, 0.5, light), 0, -0.1, 0.12),
    at(box(0.22, h * 0.85, 0.3, p.trim), 0, -0.2, 0.4),
    at(box(w, 0.22, 0.3, p.trim), 0, -h * 0.12, 0.4),
  );
}

/** A gothic pinnacle standing on the origin: plinth, gold band, four-sided spire, corner pinnacles and a finial. */
export function spire(r: number, h: number, p: Palette) {
  const g = new THREE.Group();
  g.add(at(plate(r * 2, h * 0.32, r * 2, p.armour, r * 0.2), 0, h * 0.16, 0));
  g.add(at(plate(r * 2.2, h * 0.04, r * 2.2, p.trim, r * 0.08), 0, h * 0.33, 0));
  const point = cyl(r * 0.08, r * 1.05, h * 0.6, p.armour, 4);
  g.add(at(point, 0, h * 0.35 + h * 0.3, 0, 0, Math.PI / 4));
  for (const [x, z] of [
    [-1, -1],
    [1, -1],
    [-1, 1],
    [1, 1],
  ]) {
    g.add(at(cyl(r * 0.05, r * 0.32, h * 0.2, p.armour, 4), x * r * 0.78, h * 0.35 + h * 0.1, z * r * 0.78, 0, Math.PI / 4));
  }
  g.add(at(sphere(r * 0.22, p.trim, 10), 0, h * 0.97, 0));
  g.add(at(cyl(r * 0.07, r * 0.07, h * 0.12, p.trim, 6), 0, h * 1.03, 0));
  return g;
}

/** A gold sunburst emblem facing +Z. */
export function sunburst(r: number, p: Palette, rays = 12) {
  const g = group(at(cyl(r * 0.36, r * 0.36, r * 0.12, p.trim, 20), 0, 0, 0, Math.PI / 2), at(torus(r * 0.48, r * 0.05, p.trim, 24), 0, 0, 0.02));
  for (let i = 0; i < rays; i++) {
    const a = (i / rays) * Math.PI * 2;
    const len = i % 2 ? r * 0.55 : r * 0.75;
    const ray = cyl(0.02, r * 0.09, len, p.trim, 4);
    ray.position.set(Math.cos(a) * (r * 0.45 + len / 2), Math.sin(a) * (r * 0.45 + len / 2), 0);
    ray.rotation.z = a - Math.PI / 2;
    g.add(ray);
  }
  return g;
}

/**
 * A knight's helm facing +Z: a tall dome with a gold crest, a visor with
 * glowing slits, cheek guards and a gorget ring.
 */
export function helm(r: number, p: Palette) {
  const g = new THREE.Group();
  const skull = sphere(r, p.armour, 24);
  skull.scale.set(0.92, 1.12, 1);
  g.add(skull);
  g.add(at(lathe([[r * 0.5, 0], [r * 0.12, r * 0.6], [0, r * 0.75]], p.armour, 4), 0, r * 0.95, 0, 0, Math.PI / 4));
  g.add(at(plate(r * 0.16, r * 0.5, r * 1.9, p.trim, r * 0.06), 0, r * 0.92, -0.1));
  const visor = group(plate(r * 1.5, r * 0.95, r * 0.5, p.armour, r * 0.2));
  for (const y of [0.2, -0.08, -0.34]) visor.add(at(box(r * (y > 0 ? 1.1 : 0.8), r * 0.09, r * 0.2, p.glow), 0, y * r, r * 0.2));
  visor.add(at(box(r * 0.12, r * 0.9, r * 0.24, p.trim), 0, 0, r * 0.22));
  visor.add(at(box(r * 1.55, r * 0.08, r * 0.2, p.trim), 0, r * 0.46, r * 0.18));
  g.add(at(visor, 0, -r * 0.05, r * 0.72, -0.08));
  for (const s of [-1, 1]) g.add(at(plate(r * 0.4, r * 0.9, r * 0.9, p.armour, r * 0.12), s * r * 0.75, -r * 0.35, r * 0.25, 0, s * 0.35));
  g.add(at(torus(r * 0.78, r * 0.14, p.trim, 24), 0, -r * 0.95, 0, Math.PI / 2));
  return g;
}

/** Torn cloth hanging from the origin, `w` wide and `h` long, facing +Z, gently rippled. */
export function banner(w: number, h: number, m: THREE.Material, p: Palette, seed = 1, tails = 2) {
  let s = seed * 7919;
  const rand = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  const shape = new THREE.Shape();
  shape.moveTo(-w / 2, 0);
  shape.lineTo(-w / 2, -h * (0.82 + rand() * 0.1));
  // Ragged bottom edge, cut into swallow-tails.
  const steps = 7;
  for (let i = 1; i <= steps; i++) {
    const x = -w / 2 + (w * i) / steps;
    const notch = tails > 1 && Math.abs(x) < w * 0.12 ? 0.62 : 1;
    shape.lineTo(x - w / steps / 2, -h * (0.8 + rand() * 0.2) * notch);
    shape.lineTo(x, -h * (0.88 + rand() * 0.12) * (Math.abs(x) < w * 0.1 && tails > 1 ? 0.6 : 1));
  }
  shape.lineTo(w / 2, 0);
  shape.lineTo(-w / 2, 0);
  const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.35, bevelEnabled: false, curveSegments: 1 });
  const tess = geo.toNonIndexed();
  const pos = tess.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const t = -y / h;
    pos.setZ(i, pos.getZ(i) + Math.sin(x * 1.3 + t * 4) * 0.35 * t + t * t * 0.8);
  }
  tess.computeVertexNormals();
  return group(mesh(tess, m), at(bar(0.25, w + 1, p.trim, 'x', 8), 0, 0, 0.15), at(sphere(0.35, p.trim, 8), -(w + 1) / 2, 0, 0.15), at(sphere(0.35, p.trim, 8), (w + 1) / 2, 0, 0.15));
}

/** An armour plate with a raised gold border on its +Z face. */
export function trimmed(w: number, h: number, d: number, p: Palette, edge = Math.min(w, h) * 0.08) {
  const z = d / 2;
  return group(
    plate(w, h, d, p.armour, Math.min(w, h, d) * 0.25),
    at(box(w * 0.96, edge, edge, p.trim), 0, h / 2 - edge * 1.2, z),
    at(box(w * 0.96, edge, edge, p.trim), 0, -h / 2 + edge * 1.2, z),
    at(box(edge, h * 0.92, edge, p.trim), w / 2 - edge * 1.2, 0, z),
    at(box(edge, h * 0.92, edge, p.trim), -w / 2 + edge * 1.2, 0, z),
  );
}

/** A long tapering blade pointing +Z from the origin, with a gold spine. */
export function blade(len: number, w: number, p: Palette) {
  const s = new THREE.Shape();
  s.moveTo(0, -w * 0.35);
  s.lineTo(len * 0.8, -w * 0.25);
  s.lineTo(len, w * 0.15);
  s.lineTo(len * 0.7, w * 0.5);
  s.lineTo(0, w * 0.5);
  s.lineTo(0, -w * 0.35);
  const g = new THREE.ExtrudeGeometry(s, { depth: 0.3, bevelEnabled: true, bevelThickness: 0.15, bevelSize: 0.12, bevelSegments: 1 });
  g.translate(0, 0, -0.15);
  const b = mesh(g, p.steel);
  b.rotation.y = -Math.PI / 2;
  return group(b, at(box(0.32, 0.25, len * 0.72, p.trim), 0, w * 0.5, len * 0.36));
}

// ---------------------------------------------------------------- baking

/**
 * Merge every mesh under `root` into one mesh per material, so a walker with
 * hundreds of rivets is a dozen draw calls. Mount points are kept, moved
 * straight under the root with their placement unchanged.
 */
export function bake<T extends THREE.Object3D>(root: T): T {
  root.updateMatrixWorld(true);
  const inverse = root.matrixWorld.clone().invert();
  const byMaterial = new Map<THREE.Material, THREE.BufferGeometry[]>();
  const keep: THREE.Object3D[] = [];
  root.traverse((o) => {
    if (o === root) return;
    if (o.name.startsWith('mount_')) {
      keep.push(o);
      return;
    }
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    let g = m.geometry.index ? m.geometry.toNonIndexed() : m.geometry.clone();
    for (const name of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(name)) g.deleteAttribute(name);
    if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array((g.attributes.position.count * 2) | 0), 2));
    g = g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inverse, m.matrixWorld));
    const mat = m.material as THREE.Material;
    if (!byMaterial.has(mat)) byMaterial.set(mat, []);
    byMaterial.get(mat)!.push(g);
  });
  for (const m of keep) root.attach(m);
  for (const c of [...root.children]) if (!keep.includes(c)) root.remove(c);
  for (const [mat, geoms] of byMaterial) {
    const merged = mergeGeometries(geoms, false);
    if (!merged) continue;
    const out = new THREE.Mesh(merged, mat);
    out.name = mat.name || 'part';
    root.add(out);
  }
  return root;
}
