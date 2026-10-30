// Building blocks for the procedural war-walker parts: materials with a little
// wear, bevelled plates, lathed boiler shapes, pipes, rivets, gauges and
// pistons. Units are millimetres, +Y up, +Z forward.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

export interface Palette {
  /** Painted armour; recoloured with the Company livery. */
  hull: THREE.Material;
  /** Polished brass fittings. */
  trim: THREE.Material;
  /** Dark gunmetal frame, joints and barrels. */
  iron: THREE.Material;
  /** Aether glow of energy weapons. */
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
    hull: new THREE.MeshPhysicalMaterial({
      name: 'hull',
      color: hullColour,
      roughness: 0.55,
      roughnessMap: paint,
      metalness: 0.2,
      clearcoat: 0.2,
      clearcoatRoughness: 0.45,
    }),
    trim: new THREE.MeshStandardMaterial({ name: 'brass', color: '#d9a94e', roughness: 0.42, roughnessMap: metal, metalness: 1 }),
    iron: new THREE.MeshStandardMaterial({ name: 'iron', color: '#4a443e', roughness: 0.62, roughnessMap: metal, metalness: 0.8 }),
    glow: new THREE.MeshStandardMaterial({ name: 'glow', color: '#0d3b36', emissive: '#19d6bf', emissiveIntensity: 1.25, roughness: 0.3 }),
    fire: new THREE.MeshStandardMaterial({ name: 'fire', color: '#3a1606', emissive: '#ff5a0a', emissiveIntensity: 1.5, roughness: 0.4 }),
    copper: new THREE.MeshStandardMaterial({ name: 'copper', color: '#c46a3c', roughness: 0.38, roughnessMap: metal, metalness: 1 }),
    enamel: new THREE.MeshStandardMaterial({ name: 'enamel', color: '#efe4c6', roughness: 0.5, metalness: 0 }),
    steel: new THREE.MeshStandardMaterial({ name: 'steel', color: '#c9ccd0', roughness: 0.28, roughnessMap: metal, metalness: 1 }),
    ground: new THREE.MeshStandardMaterial({ name: 'ground', color: '#3d362e', roughness: 1, metalness: 0 }),
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

/** A banded boiler drum lying along X: iron end caps, brass bands and rivet rings. */
export function boilerDrum(r: number, len: number, p: Palette, bands = 3) {
  const g = new THREE.Group();
  g.add(bar(r, len, p.hull, 'x', 32));
  for (const side of [-1, 1]) {
    const cap = lathe(
      [
        [r * 1.04, 0],
        [r * 1.04, r * 0.12],
        [r * 0.9, r * 0.3],
        [r * 0.55, r * 0.45],
        [0, r * 0.5],
      ],
      p.iron,
      32,
    );
    cap.rotation.z = -side * (Math.PI / 2);
    cap.position.x = (side * len) / 2;
    g.add(cap);
    const ring = rivetRing(r * 0.8, 10, r * 0.06, p.trim, true);
    ring.rotation.y = side * (Math.PI / 2);
    ring.position.x = side * (len / 2 + r * 0.3);
    g.add(ring);
  }
  for (let i = 0; i < bands; i++) {
    const x = bands === 1 ? 0 : -len / 2 + r * 0.25 + ((len - r * 0.5) * i) / (bands - 1);
    const band = torus(r * 1.01, r * 0.07, p.trim, 32);
    band.rotation.y = Math.PI / 2;
    band.position.x = x;
    g.add(band);
    const ring = rivetRing(r * 1.06, 14, r * 0.045, p.iron);
    ring.rotation.y = Math.PI / 2;
    ring.position.x = x + r * 0.15;
    g.add(ring);
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
