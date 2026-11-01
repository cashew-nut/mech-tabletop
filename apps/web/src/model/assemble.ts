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
import { FIT, fitClass, hardpoint, isCardOnly, nudgeOf, planLocation, pivotOf, poseOf, type Placement } from './fit';
import { itemPartName, kitCandidates, planKit } from './kitparts';
import { PARTS, buildChassis, makePalette, partScale, type ChassisModel, type Palette } from './parts';

/** Class items modelled on the right-hand side. */
const NATIVE_RIGHT = new Set(FIT.nativeRight);

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

/** Turn the hardpoint fit off to see the numbered mounts (before and after comparisons). */
let fitEnabled = true;
export const setFitEnabled = (on: boolean) => {
  fitEnabled = on;
};

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

/** A baked material whose crimson texels take the livery and everything else (black iron, gold, steel) stays as baked.
 * Models cut from a painted source (the Meshy Paladin) have one texture, so the paintable areas are found by hue in the
 * shader: texels that are mostly red keep their brightness (wear, filigree shading) and swap to the livery's hue. */
function liveryMaterial(mat: THREE.MeshStandardMaterial, livery: THREE.Color) {
  const painted = mat.clone();
  const lh = new THREE.Vector3(livery.r, livery.g, livery.b);
  lh.divideScalar(Math.max(lh.x, lh.y, lh.z, 1e-3));
  painted.onBeforeCompile = (shader) => {
    shader.uniforms.uLivery = { value: lh };
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\nuniform vec3 uLivery;')
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
        {
          vec3 c = diffuseColor.rgb;
          float red = smoothstep(0.55, 0.8, 1.0 - max(c.g, c.b) / (c.r + 1e-4)) * smoothstep(0.01, 0.05, c.r);
          float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
          float lumL = max(dot(uLivery, vec3(0.2126, 0.7152, 0.0722)), 0.02);
          diffuseColor.rgb = mix(c, uLivery * (lum / lumL), red);
        }`,
      );
  };
  painted.customProgramCacheKey = () => 'livery-hue-mask';
  return painted;
}

/** Recolour the hull materials of a Blender part, keeping their trim and glow.
 * Baked hull textures keep their wear: the livery is multiplied into them. */
function repaint(obj: THREE.Object3D, palette: Palette) {
  obj.traverse((o) => {
    const mesh = o as THREE.Mesh;
    if (!mesh.isMesh) return;
    const mat = mesh.material as THREE.MeshStandardMaterial;
    if (!mat?.name?.toLowerCase().startsWith('hull')) return;
    if (mat.map && mat.name.toLowerCase().includes('livery')) {
      mesh.material = liveryMaterial(mat, (palette.hull as THREE.MeshStandardMaterial).color);
    } else if (mat.map) {
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
function kitBody(chassisId: string, lib: PartLibrary | null, palette: Palette, mode: KitMode): (ChassisModel & { joints: Map<string, THREE.Object3D> }) | null {
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
  // A component the class never shows has no part to hide its stand-in, so it goes here; otherwise the frame's
  // placeholder cylinders hang where the class has none (the composite Brute's arm and forearm under its pauldrons).
  for (const s of standins) if (plan.omitted.includes(s.userData.standin)) s.visible = false;
  for (const s of standins) if (!s.visible) s.removeFromParent();
  return { root, mounts: collectMounts(root), joints };
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

/** Hang one item on a named hardpoint, or return false when the body has no such joint. */
function placeAtHardpoint(
  chassisId: string, joints: Map<string, THREE.Object3D>, mounts: Record<Location, THREE.Object3D[]>, loc: Location,
  id: string, libName: string | null, part: THREE.Object3D, place: Placement, scale: number, height: number,
) {
  const def = hardpoint(chassisId, place.hp);
  if (!def) return false;
  let anchor: THREE.Object3D;
  const rot = new THREE.Euler(...(def.rot ?? [0, 0, 0]).map((d) => (d * Math.PI) / 180) as [number, number, number]);
  if (def.mount) {
    const m = mounts[loc][Number(def.mount.replace(/\D/g, ''))];
    if (!m) return false;
    anchor = new THREE.Object3D();
    m.add(anchor);
  } else {
    const joint = joints.get(`joint_${def.joint}${place.side && ['shoulder', 'elbow', 'wrist', 'hip', 'knee', 'ankle'].includes(def.joint!) ? `_${place.side}` : ''}`) ?? joints.get(`joint_${def.joint}`);
    if (!joint || !def.offset) return false;
    anchor = new THREE.Object3D();
    const sign = place.side === 'R' ? -1 : 1;
    anchor.position.set(def.offset[0] * sign * height, def.offset[1] * height, def.offset[2] * height);
    joint.add(anchor);
  }
  anchor.name = `hp_${place.hp}`;
  // anchor (the hardpoint) > nudge (the placement table's hand adjustment, in the hardpoint's axes) > turn (the hardpoint's
  // own rotation, and the mirror across the walker on the right, so a pose written for the left works on both sides)
  // > the item.
  const mirror = !def.mount && place.side === 'R';
  const nudge = new THREE.Object3D();
  nudge.name = `nudge_${place.hp}`;
  const adjust = nudgeOf(chassisId, place.hp, id);
  if (adjust) {
    // Offsets are fractions of body height; a numbered mount may sit in a scaled parent, so convert to its units.
    const unit = new THREE.Vector3();
    anchor.parent!.getWorldScale(unit);
    nudge.position.set(...(adjust.offset.map((v, i) => (v * height) / (Math.abs(unit.getComponent(i)) || 1)) as [number, number, number]));
    nudge.rotation.set(...(adjust.rot.map((d) => (d * Math.PI) / 180) as [number, number, number]));
    // The right side is the mirror image of the left: out stays out, and turns about y and z reverse.
    if (mirror) {
      nudge.position.x *= -1;
      nudge.rotation.y *= -1;
      nudge.rotation.z *= -1;
    }
    nudge.scale.setScalar(adjust.scale);
  }
  const turn = new THREE.Object3D();
  turn.name = `turn_${place.hp}`;
  turn.rotation.copy(rot);
  if (mirror) turn.scale.x = -1;
  anchor.add(nudge);
  nudge.add(turn);
  const pose = poseOf(id, place.hp);
  scale *= pose.scale;
  // Class items are modelled for one hand; on the other side they are flipped (as the numbered mounts always did).
  const nativeRight = libName ? NATIVE_RIGHT.has(libName) : false;
  // A right-hand hardpoint on a joint is already mirrored, so only a numbered mount (not mirrored) needs the side in the decision.
  const flip = def.mount && place.side === 'R' ? !nativeRight : nativeRight;
  const pivot = new THREE.Vector3(...pivotOf(libName ?? id, pose.contact.length ? pose.contact : def.contact)).multiplyScalar(scale);
  if (flip) pivot.x *= -1;
  part.scale.set(flip ? -scale : scale, scale, scale);
  const itemRot = new THREE.Euler(...((pose.rot ?? [0, 0, 0]).map((d) => (d * Math.PI) / 180) as [number, number, number]));
  part.rotation.copy(itemRot);
  part.position.copy(pivot.applyEuler(itemRot).negate());
  // The sliders tool finds the item again by this.
  part.userData.fit = { item: id, hp: place.hp, side: place.side ?? null };
  turn.add(part);
  return true;
}

export function buildWalkerModel(walker: WalkerInput, hullColour: string, lib: PartLibrary | null = null, kit: KitMode = 'auto'): THREE.Group {
  const c = getChassis(walker.chassis);
  const palette = makePalette(hullColour);
  const body = kitBody(c.id, lib, palette, kit);
  const { root, mounts } = body ?? chassisFromLibrary(c.id, lib, c.slots, palette);
  const scale = partScale(c.id);
  const fit = fitEnabled ? fitClass(c.id) : null;
  let height = 0;
  if (fit) {
    root.updateMatrixWorld(true);
    const head = body?.joints.get('joint_head');
    height = head ? head.getWorldPosition(new THREE.Vector3()).y : 0;
  }

  for (const loc of LOCATIONS) {
    let slot = 0;
    // Card-only items (internal systems and effects) have no model: they take no mount and no hardpoint.
    const ids = (walker.loadout[loc] ?? []).filter((id) => !isCardOnly(id));
    // An arm holds one of the class's own items (the Brute's guns are whole forearms on its one elbow socket); a second
    // copy on the same arm is the faction's or shared model, placed like any other item.
    const arm = loc === 'armLeft' || loc === 'armRight';
    let ownUsed = false;
    const libNames = ids.map((id) => {
      if (!lib) return null;
      const own = itemPartName(lib.items, id, c.faction, c.id);
      if (!own?.endsWith(`@${c.id}`) || !arm) return own;
      if (!ownUsed) {
        ownUsed = true;
        return own;
      }
      return itemPartName(lib.items, id, c.faction);
    });
    const native = libNames.map((n) => !!n?.endsWith(`@${c.id}`));
    const plan = fit && height > 0 ? planLocation(c.id, loc, ids, native) : null;
    ids.forEach((id, index) => {
      const def = getEquipment(id);
      const libName = libNames[index];
      const fromLib = libName ? lib!.items.get(libName) : undefined;
      const make = () => {
        const part = fromLib ? fromLib.clone(true) : bake(PARTS[id]?.(palette) ?? new THREE.Group());
        if (fromLib) repaint(part, palette);
        part.name = `part_${id}`;
        return part;
      };
      const places = plan ? plan[index] : null;
      if (places && body && fit) {
        const placed = places.map((p) => placeAtHardpoint(c.id, body.joints, mounts, loc, id, libName, make(), p, scale * fit.scale, height));
        if (placed.every(Boolean)) {
          slot += def.slots;
          return;
        }
      }
      const anchor = mounts[loc][slot];
      slot += def.slots;
      if (!anchor) return; // over-full location: nothing left to attach to
      const part = make();
      part.scale.setScalar(scale);
      // A class's own item (lance@paladin) is modelled for the left; flip it for the right arm and the second core mount.
      // Items cut from a right-hand weapon (autocannon@brute) are the other way round.
      if (libName?.endsWith(`@${c.id}`)) {
        const right = loc === 'armRight' || (loc === 'core' && (slot - def.slots) % 2 === 1);
        if (right !== NATIVE_RIGHT.has(libName)) part.scale.x *= -1;
      }
      anchor.add(part);
    });
  }
  root.name = walker.name;
  return root;
}
