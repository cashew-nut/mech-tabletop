// Part view for the builder's 3D model: pulls every part off its parent along the joint tree (Explode), draws a line at
// each joint, and lists the parts so they can be hidden. It works on the model the builder just built, so it always shows
// the walker as currently equipped. The maths is in explode.ts.
import * as THREE from 'three';
import { getEquipment } from '@brass-charter/rules';
import { explodeOffsets, kitParents, type Unit } from './explode';

export interface PartInfo extends Unit {
  node: THREE.Object3D;
  /** Where the node's origin (its joint) sits at rest, world space. */
  home: THREE.Vector3;
  /** Lowest point at rest, world y. */
  floor: number;
  item: boolean;
  label: string;
}

const prettyKit = (id: string) => {
  const m = /^kit_([a-z]+)(?:_([LR]))?$/.exec(id)!;
  return m[1] + (m[2] ? (m[2] === 'L' ? ' (left)' : ' (right)') : '');
};

function sideOf(o: THREE.Object3D) {
  for (let n: THREE.Object3D | null = o; n; n = n.parent) {
    const m = /^hp_.*_([LR])$/.exec(n.name);
    if (m) return m[1] === 'L' ? ' (left)' : ' (right)';
  }
  return '';
}

/** The equipment's name from the rules data, so the list matches the builder's. */
function itemName(id: string) {
  try {
    return getEquipment(id).name;
  } catch {
    return id.replace(/-/g, ' ');
  }
}

/** The nodes that make up the walker: kit parts first, then the equipment hung on it. */
function collectParts(root: THREE.Object3D, chassis: string): PartInfo[] {
  root.updateMatrixWorld(true);
  const out: PartInfo[] = [];
  const centreOf = (n: THREE.Object3D) => new THREE.Box3().setFromObject(n).getCenter(new THREE.Vector3());
  root.traverse((o) => {
    const isKit = /^kit_[a-z]+(_[LR])?$/.test(o.name);
    const isItem = o.name.startsWith('part_');
    if (!isKit && !isItem) return;
    out.push({
      id: isItem ? `${o.name}#${out.length}` : o.name, parent: null, node: o, item: isItem,
      centre: centreOf(o), home: o.getWorldPosition(new THREE.Vector3()), floor: new THREE.Box3().setFromObject(o).min.y,
      label: isItem ? itemName(o.name.slice(5)) + sideOf(o) : prettyKit(o.name),
    });
  });
  const kit = out.filter((p) => !p.item);
  const parents = kitParents(kit.map((p) => p.id), chassis);
  for (const p of kit) p.parent = parents.get(p.id) ?? null;
  // Equipment hangs off whichever body part is nearest to it.
  for (const it of out.filter((p) => p.item)) {
    let best = Infinity;
    for (const k of kit) {
      const d = k.centre.distanceToSquared(it.centre);
      if (d < best) { best = d; it.parent = k.id; }
    }
  }
  return [...kit, ...out.filter((p) => p.item)];
}

export class PartView {
  readonly parts: PartInfo[];
  private offsets: Map<string, THREE.Vector3>;
  private guides: THREE.LineSegments;
  private sockets: THREE.Points;
  /** 0 = together, 1 = pulled apart. */
  t = 0;
  showGuides = true;
  /** Fully open, the figure is about this much wider than closed (the camera backs off by it). */
  readonly spread: number;

  constructor(private model: THREE.Object3D, private scene: THREE.Scene, chassis: string) {
    this.parts = collectParts(model, chassis);
    const size = new THREE.Box3().setFromObject(model).getSize(new THREE.Vector3());
    this.offsets = explodeOffsets(this.parts, size.y * 0.14);
    // Lift by whatever the legs would sink below the floor, so nothing goes through the plinth.
    const lift = Math.max(0, ...this.parts.map((p) => 0.5 - (p.floor + (this.offsets.get(p.id)?.y ?? 0))));
    for (const o of this.offsets.values()) o.y += lift;
    this.guides = new THREE.LineSegments(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color: 0xe0b85a, depthTest: false, transparent: true, opacity: 0.9 }));
    this.sockets = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ color: 0xffe9a8, size: 6, sizeAttenuation: false, depthTest: false }));
    this.guides.renderOrder = this.sockets.renderOrder = 10;
    this.guides.frustumCulled = this.sockets.frustumCulled = false;
    scene.add(this.guides, this.sockets);
    this.t = 1;
    this.apply();
    const open = new THREE.Box3().setFromObject(model).getSize(new THREE.Vector3()).length();
    this.t = 0;
    this.apply();
    this.spread = Math.max(1, open / size.length());
  }

  apply() {
    for (const p of this.parts) {
      const off = this.offsets.get(p.id);
      const par = p.node.parent;
      if (!off || !par) continue;
      par.updateMatrixWorld(true);
      p.node.position.copy(par.worldToLocal(p.home.clone().addScaledVector(off, this.t)));
    }
    this.model.updateMatrixWorld(true);
    const pos: number[] = [];
    const dots: number[] = [];
    const byId = new Map(this.parts.map((p) => [p.id, p]));
    for (const p of this.parts) {
      const par = p.parent ? byId.get(p.parent) : undefined;
      if (!par || !p.node.visible) continue;
      const zero = new THREE.Vector3();
      const socket = p.home.clone().addScaledVector(this.offsets.get(par.id) ?? zero, this.t);
      const now = p.home.clone().addScaledVector(this.offsets.get(p.id) ?? zero, this.t);
      pos.push(socket.x, socket.y, socket.z, now.x, now.y, now.z);
      dots.push(socket.x, socket.y, socket.z);
    }
    this.guides.geometry.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    this.sockets.geometry.setAttribute('position', new THREE.Float32BufferAttribute(dots, 3));
    this.guides.visible = this.sockets.visible = this.showGuides && this.t > 0.01;
  }

  setVisible(p: PartInfo, on: boolean) {
    p.node.visible = on;
    this.apply();
  }

  dispose() {
    this.scene.remove(this.guides, this.sockets);
    this.guides.geometry.dispose();
    this.sockets.geometry.dispose();
    // Put everything back where the builder placed it, in case the model is kept.
    this.t = 0;
    this.apply();
    for (const p of this.parts) p.node.visible = true;
  }
}
