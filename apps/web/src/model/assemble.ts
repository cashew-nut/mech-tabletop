// Assemble a war-walker model from its build: chassis first, then each item
// snapped to the chassis mount for its location and slot. Parts listed in
// public/parts/manifest.json (exported from Blender) replace the placeholders.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { LOCATIONS, getChassis, getEquipment, type Location, type WalkerInput } from '@brass-charter/rules';
import { PARTS, buildChassis, makePalette, partScale, type ChassisModel, type Palette } from './parts';

export interface PartLibrary {
  chassis: Map<string, THREE.Object3D>;
  items: Map<string, THREE.Object3D>;
}

interface Manifest {
  chassis?: Record<string, string>;
  items?: Record<string, string>;
}

let libraryPromise: Promise<PartLibrary> | null = null;

/** Load any Blender-exported parts once. Missing or broken files fall back to placeholders. */
export function loadPartLibrary(): Promise<PartLibrary> {
  libraryPromise ??= (async () => {
    const lib: PartLibrary = { chassis: new Map(), items: new Map() };
    let manifest: Manifest = {};
    try {
      const res = await fetch('parts/manifest.json');
      if (res.ok) manifest = await res.json();
    } catch {
      return lib;
    }
    const loader = new GLTFLoader();
    const load = async (file: string) => (await loader.loadAsync(`parts/${file}`)).scene;
    for (const [kind, entries] of [
      ['chassis', manifest.chassis ?? {}],
      ['items', manifest.items ?? {}],
    ] as const) {
      for (const [id, file] of Object.entries(entries)) {
        try {
          lib[kind].set(id, await load(file));
        } catch (e) {
          console.warn(`Could not load part ${file}, using the placeholder`, e);
        }
      }
    }
    return lib;
  })();
  return libraryPromise;
}

/** Recolour the hull material of a Blender part, keeping its trim and glow. */
function repaint(obj: THREE.Object3D, palette: Palette) {
  obj.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    const mat = mesh.material as THREE.MeshStandardMaterial;
    if (mat?.name?.toLowerCase().startsWith('hull')) mesh.material = palette.hull;
  });
}

function chassisFromLibrary(id: string, lib: PartLibrary | null, slots: Record<Location, number>, palette: Palette): ChassisModel {
  const source = lib?.chassis.get(id);
  if (!source) return buildChassis(id, slots, palette);
  const root = source.clone(true) as THREE.Group;
  repaint(root, palette);
  const mounts: Record<Location, THREE.Object3D[]> = { armLeft: [], armRight: [], core: [], legs: [] };
  // Blender suffixes repeated names (mount_core_0.001), so export_parts.py
  // also stores the true name in the node's extras, which land in userData.
  root.traverse((o) => {
    const m = /^mount_(armLeft|armRight|core|legs)_(\d+)$/.exec(o.userData.mount ?? o.name);
    if (m) mounts[m[1] as Location][Number(m[2])] = o;
  });
  return { root, mounts };
}

export const COMPANY_COLOURS: Record<string, string> = {
  halvorsen: '#7a2e22',
  meridian: '#1f5c63',
  'calloway-vane': '#2f3e66',
};

export function buildWalkerModel(walker: WalkerInput, hullColour: string, lib: PartLibrary | null = null): THREE.Group {
  const c = getChassis(walker.chassis);
  const palette = makePalette(hullColour);
  const { root, mounts } = chassisFromLibrary(c.id, lib, c.slots, palette);
  const scale = partScale(c.id);

  for (const loc of LOCATIONS) {
    let slot = 0;
    for (const id of walker.loadout[loc] ?? []) {
      const def = getEquipment(id);
      const anchor = mounts[loc][slot];
      slot += def.slots;
      if (!anchor) continue; // over-full location: nothing left to attach to
      const fromLib = lib?.items.get(id);
      const part = fromLib ? fromLib.clone(true) : (PARTS[id]?.(palette) ?? new THREE.Group());
      if (fromLib) repaint(part, palette);
      part.name = `part_${id}`;
      part.scale.setScalar(scale);
      anchor.add(part);
    }
  }
  root.name = walker.name;
  return root;
}
