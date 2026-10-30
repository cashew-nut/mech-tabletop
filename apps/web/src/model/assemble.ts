// Assemble a war-walker model from its build: a body first, then each item
// snapped to the body's mount for its location and slot. Parts listed in
// public/parts/manifest.json (exported from Blender) replace the procedural
// placeholders. The body comes from, in order:
//   1. the faction kit: the class's frame skeleton with a Blender part on
//      every joint, class parts before frame parts (see kitparts.ts). Used
//      once every required component has a part, or always with kit: 'force';
//   2. a whole-body `chassis_<class>` GLB;
//   3. the procedural chassis in chassis.ts.
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/examples/jsm/loaders/KTX2Loader.js';
import { LOCATIONS, getChassis, getEquipment, type Location, type WalkerInput } from '@brass-charter/rules';
import { bake } from './kit';
import { itemPartName, kitCandidates, planKit } from './kitparts';
import { PARTS, buildChassis, makePalette, partScale, type ChassisModel, type Palette } from './parts';

export interface PartLibrary {
  chassis: Map<string, THREE.Object3D>;
  items: Map<string, THREE.Object3D>;
  /** Kit frames and parts loaded so far (see ensureKitParts). */
  kit: Map<string, THREE.Object3D>;
  /** Kit names the manifest lists, loaded or not, mapped to their files. */
  kitFiles: Map<string, string>;
  load?: (file: string) => Promise<THREE.Object3D>;
}

interface Manifest {
  chassis?: Record<string, string>;
  items?: Record<string, string>;
  kit?: Record<string, string>;
}

export type KitMode = 'auto' | 'force' | 'off';

export const emptyLibrary = (): PartLibrary => ({ chassis: new Map(), items: new Map(), kit: new Map(), kitFiles: new Map() });

let libraryPromise: Promise<PartLibrary> | null = null;

/** Load the manifest and any Blender-exported chassis and items once. Missing
 * or broken files fall back to placeholders. Pass the renderer so KTX2
 * textures can be transcoded for its GPU. Kit parts load per class, on demand. */
export function loadPartLibrary(renderer?: THREE.WebGLRenderer): Promise<PartLibrary> {
  libraryPromise ??= (async () => {
    const lib = emptyLibrary();
    let manifest: Manifest = {};
    try {
      const res = await fetch('parts/manifest.json');
      if (res.ok) manifest = await res.json();
    } catch {
      return lib;
    }
    const loader = new GLTFLoader();
    if (renderer) loader.setKTX2Loader(new KTX2Loader().setTranscoderPath('basis/').detectSupport(renderer));
    lib.load = async (file: string) => (await loader.loadAsync(`parts/${file}`)).scene;
    for (const [kind, entries] of [
      ['chassis', manifest.chassis ?? {}],
      ['items', manifest.items ?? {}],
    ] as const) {
      for (const [id, file] of Object.entries(entries)) {
        try {
          lib[kind].set(id, await lib.load(file));
        } catch (e) {
          console.warn(`Could not load part ${file}, using the placeholder`, e);
        }
      }
    }
    for (const [name, file] of Object.entries(manifest.kit ?? {})) lib.kitFiles.set(name, file);
    return lib;
  })();
  return libraryPromise;
}

/** Load the kit frame and parts a class could use. Resolves true if anything new arrived. */
export async function ensureKitParts(lib: PartLibrary, chassisId: string): Promise<boolean> {
  const c = getChassis(chassisId);
  if (!c.faction || !lib.load) return false;
  let added = false;
  for (const name of kitCandidates(c.faction, c.id, c.frame)) {
    const file = lib.kitFiles.get(name);
    if (!file || lib.kit.has(name)) continue;
    try {
      lib.kit.set(name, await lib.load(file));
      added = true;
    } catch (e) {
      console.warn(`Could not load kit part ${file}`, e);
      lib.kitFiles.delete(name);
    }
  }
  return added;
}

/** Recolour the hull materials of a Blender part, keeping their trim and glow.
 * Baked hull textures keep their wear: the livery is multiplied into them. */
function repaint(obj: THREE.Object3D, palette: Palette) {
  obj.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    const mat = mesh.material as THREE.MeshStandardMaterial;
    if (!mat?.name?.toLowerCase().startsWith('hull')) return;
    if (mat.map) {
      const painted = mat.clone();
      painted.color.copy((palette.hull as THREE.MeshStandardMaterial).color);
      mesh.material = painted;
    } else {
      mesh.material = palette.hull;
    }
  });
}

function collectMounts(root: THREE.Object3D) {
  const mounts: Record<Location, THREE.Object3D[]> = { armLeft: [], armRight: [], core: [], legs: [] };
  // Blender suffixes repeated names (mount_core_0.001), so the exporter also
  // stores the true name in the node's extras, which land in userData.
  root.traverse((o) => {
    const m = /^mount_(armLeft|armRight|core|legs)_(\d+)$/.exec(o.userData.mount ?? o.name);
    if (m) mounts[m[1] as Location][Number(m[2])] = o;
  });
  return mounts;
}

/** The class's frame with kit parts hung on its joints, or null to fall back. */
function kitBody(chassisId: string, lib: PartLibrary | null, palette: Palette, mode: KitMode): ChassisModel | null {
  const c = getChassis(chassisId);
  if (mode === 'off' || !lib || !c.faction) return null;
  const plan = planKit(lib.kit, c.faction, c.id, c.frame);
  if (!plan || (plan.missing.length && mode !== 'force')) return null;
  const root = lib.kit.get(plan.frame)!.clone(true) as THREE.Group;
  repaint(root, palette);
  const joints = new Map<string, THREE.Object3D>();
  const standins: THREE.Object3D[] = [];
  root.traverse((o) => {
    const j = o.userData.joint ?? (o.name.startsWith('joint_') ? o.name : undefined);
    if (j) joints.set(j, o);
    if (o.userData.standin) standins.push(o);
  });
  for (const p of plan.parts) {
    const joint = joints.get(p.joint);
    if (!joint) continue;
    const part = lib.kit.get(p.name)!.clone(true);
    repaint(part, palette);
    part.name = `kit_${p.component}${p.side ? `_${p.side}` : ''}`;
    if (p.mirror) part.scale.x = -1;
    joint.add(part);
    for (const s of standins) if (s.userData.standin === p.component && (s.userData.side ?? undefined) === p.side) s.visible = false;
  }
  for (const s of standins) if (!s.visible) s.removeFromParent();
  return { root, mounts: collectMounts(root) };
}

function chassisFromLibrary(id: string, lib: PartLibrary | null, slots: Record<Location, number>, palette: Palette): ChassisModel {
  const source = lib?.chassis.get(id);
  if (!source) return buildChassis(id, slots, palette);
  const root = source.clone(true) as THREE.Group;
  repaint(root, palette);
  return { root, mounts: collectMounts(root) };
}

/** Default livery per faction, from the concept board. */
export const FACTION_COLOURS: Record<string, string> = {
  covenant: '#7a1c1c',
  foundries: '#9a4a1c',
  reliquary: '#2f5a5a',
};

export function buildWalkerModel(walker: WalkerInput, hullColour: string, lib: PartLibrary | null = null, kit: KitMode = 'auto'): THREE.Group {
  const c = getChassis(walker.chassis);
  const palette = makePalette(hullColour);
  const { root, mounts } = kitBody(c.id, lib, palette, kit) ?? chassisFromLibrary(c.id, lib, c.slots, palette);
  const scale = partScale(c.id);

  for (const loc of LOCATIONS) {
    let slot = 0;
    for (const id of walker.loadout[loc] ?? []) {
      const def = getEquipment(id);
      const anchor = mounts[loc][slot];
      slot += def.slots;
      if (!anchor) continue; // over-full location: nothing left to attach to
      const libName = lib ? itemPartName(lib.items, id, c.faction) : null;
      const fromLib = libName ? lib!.items.get(libName) : undefined;
      const part = fromLib ? fromLib.clone(true) : bake(PARTS[id]?.(palette) ?? new THREE.Group());
      if (fromLib) repaint(part, palette);
      part.name = `part_${id}`;
      part.scale.setScalar(scale);
      anchor.add(part);
    }
  }
  root.name = walker.name;
  return root;
}
