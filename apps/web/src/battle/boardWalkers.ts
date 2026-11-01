// War-walkers on the 3D board: the real kit models from the Lance Ledger, scaled to the board and given a hex-sized base.
// Models are authored in millimetres (Paladin 50 tall, Brute 35); the board works in hex-radius units.
import * as THREE from 'three';
import { getChassis, type WalkerInput, type WalkerState } from '@brass-charter/rules';
import { FACTION_COLOURS, buildWalkerModel, ensureKitParts, loadPartLibrary, type PartLibrary } from '../model/assemble';
import { frameOf } from '../model/chassis';

/** Board units per millimetre of model. 0.07 puts a Paladin about 2 hex-widths tall, like the north star. */
export const BOARD_UNITS_PER_MM = Number(new URLSearchParams(location.search).get('scale') ?? 0.07);

/** Round base radius in board units, by frame (a hex is 0.87 across from centre to flat). */
export const BASE_RADIUS: Record<string, number> = { scout: 0.52, striker: 0.64, bulwark: 0.76, titan: 0.84 };
const BASE_LIFT = 0.07;
const DIM = 0.55;

export interface BoardWalker {
  group: THREE.Group;
  /** The figure alone, so it can be laid down while the base stays flat. */
  pose: THREE.Group;
  setProne: (prone: boolean) => void;
  /** Height of the figure above its base, board units. */
  height: number;
  radius: number;
  /** How far the figure's back sits behind its base centre, for laying it down when prone. */
  back: number;
  /** Invisible hit target: ray-casting the 120k-triangle model would stall the click. */
  proxy: THREE.Mesh;
  setDim: (dim: boolean) => void;
  key: string;
}

export class WalkerLibrary {
  private lib: PartLibrary | null = null;
  private requested = new Set<string>();
  private cache = new Map<string, BoardWalker>();

  constructor(private renderer: THREE.WebGLRenderer, private onChange: () => void) {
    loadPartLibrary(renderer).then((lib) => {
      this.lib = lib;
      onChange();
    });
  }

  /** Walkers need their class's kit parts; fetch them once and ask for a rebuild when they arrive. */
  private need(chassis: string) {
    if (!this.lib || this.requested.has(chassis)) return;
    this.requested.add(chassis);
    ensureKitParts(this.lib, chassis).then((added) => {
      if (added) {
        for (const [id, w] of this.cache) if (w.key.startsWith(`${chassis}|`)) this.cache.delete(id);
        this.onChange();
      }
    });
  }

  /** The walker's model, built once per walker and loadout. Null until the part library has loaded. */
  get(w: WalkerState): BoardWalker | null {
    if (!this.lib) return null;
    this.need(w.chassis);
    const key = `${w.chassis}|${w.items.map((i) => `${i.location}:${i.id}:${i.destroyed ? 'x' : ''}`).join(',')}|${this.lib.kit.size}`;
    const hit = this.cache.get(w.id);
    if (hit && hit.key === key) return hit;
    const built = this.build(w, key);
    this.cache.set(w.id, built);
    return built;
  }

  private build(w: WalkerState, key: string): BoardWalker {
    const c = getChassis(w.chassis);
    const loadout: WalkerInput['loadout'] = {};
    for (const it of w.items) (loadout[it.location] ??= []).push(it.id);
    const input: WalkerInput = { name: w.name, chassis: w.chassis, driver: { command: w.command, trait: w.trait }, loadout };
    const model = buildWalkerModel(input, FACTION_COLOURS[c.faction ?? ''] ?? '#7a2e22', this.lib);
    model.traverse((o) => {
      if (o.userData.standin === 'base' || o.userData.boardBase) o.visible = false;
      const mesh = o as THREE.Mesh;
      if (mesh.isMesh) mesh.raycast = () => {};
    });
    // Per-walker materials so spent walkers can dim without touching the shared ones.
    const mats: Array<{ mat: THREE.MeshStandardMaterial; base: THREE.Color }> = [];
    model.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      const clone = (m: THREE.Material) => {
        const cm = m.clone() as THREE.MeshStandardMaterial;
        if (cm.color) mats.push({ mat: cm, base: cm.color.clone() });
        return cm;
      };
      mesh.material = Array.isArray(mesh.material) ? mesh.material.map(clone) : clone(mesh.material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
    });
    model.scale.setScalar(BOARD_UNITS_PER_MM);
    const frame = frameOf(w.chassis);
    const radius = BASE_RADIUS[frame] ?? 0.7;
    const box = new THREE.Box3().setFromObject(model);
    const height = Math.max(0.8, box.max.y);
    const pose = new THREE.Group();
    pose.position.y = BASE_LIFT;
    pose.add(model);

    const group = new THREE.Group();
    group.rotation.order = 'YXZ';
    const sideColour = w.side === 0 ? 0x2d6e9c : 0x9c3a26;
    const plinth = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius + 0.05, BASE_LIFT, 40), new THREE.MeshStandardMaterial({ color: 0x2a2724, roughness: 0.8, metalness: 0.1 }));
    plinth.position.y = BASE_LIFT / 2;
    plinth.castShadow = plinth.receiveShadow = true;
    const ring = new THREE.Mesh(new THREE.RingGeometry(radius - 0.1, radius - 0.03, 48), new THREE.MeshBasicMaterial({ color: sideColour, side: THREE.DoubleSide }));
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = BASE_LIFT + 0.004;
    group.add(plinth, ring, pose);

    const proxy = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height + BASE_LIFT, 12), new THREE.MeshBasicMaterial({ visible: false }));
    proxy.position.y = (height + BASE_LIFT) / 2;
    proxy.userData.walkerId = w.id;
    group.add(proxy);
    group.userData.walkerId = w.id;

    const setDim = (dim: boolean) => {
      for (const { mat, base } of mats) mat.color.copy(base).multiplyScalar(dim ? DIM : 1);
      (plinth.material as THREE.MeshStandardMaterial).color.setHex(dim ? 0x161412 : 0x2a2724);
    };
    const back = Math.max(0.2, -box.min.z);
    const setProne = (prone: boolean) => {
      pose.rotation.x = prone ? -Math.PI / 2 : 0; // laid on its back
      pose.position.y = BASE_LIFT + (prone ? back * 1.05 : 0);
    };
    return { group, pose, setProne, height, radius, back, proxy, setDim, key };
  }
}
