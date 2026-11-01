import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import type { WalkerInput } from '@brass-charter/rules';
import { buildWalkerModel, emptyLibrary, type PartLibrary } from '../src/model/assemble';
import { stlBytes } from '../src/model/exporters';
import { COMPONENTS, SPARE_MOUNTS, jointName, kitCandidates, planKit, resolvePart } from '../src/model/kitparts';

const JOINTS = ['root', 'pelvis', 'spine', 'chest', 'neck', 'head', 'shoulder', 'elbow', 'wrist', 'hip', 'knee', 'ankle'];

/** A stand-in for an exported frame GLB: joints, stand-ins and spare mounts, named as export_parts.py writes them. */
function fakeFrame() {
  const root = new THREE.Group();
  const joints = new Map<string, THREE.Object3D>();
  for (const j of JOINTS) {
    for (const side of ['L', 'R'] as const) {
      const name = jointName(j, side);
      if (joints.has(name)) continue;
      const o = new THREE.Object3D();
      o.name = name.replace('.', '_');
      o.userData.joint = name;
      joints.set(name, o);
      root.add(o);
    }
  }
  for (const c of COMPONENTS) {
    for (const side of c.sided ? (['L', 'R'] as const) : [undefined]) {
      const s = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial());
      s.userData.standin = c.id;
      if (side) s.userData.side = side;
      joints.get(jointName(c.joint, side))!.add(s);
    }
  }
  for (const [loc, n] of Object.entries(SPARE_MOUNTS)) {
    for (let i = 0; i < n; i++) {
      const m = new THREE.Object3D();
      m.name = `mount_${loc}_${i}_001`; // as GLTFLoader sanitises Blender's .001 suffix
      m.userData.mount = `mount_${loc}_${i}`;
      joints.get('joint_chest')!.add(m);
    }
  }
  return root;
}

function fakePart(name: string, hull = false) {
  const g = new THREE.Group();
  const mat = new THREE.MeshStandardMaterial({ name: hull ? `hull_${name}` : `${name}_kit`, map: new THREE.Texture() });
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), mat);
  mesh.name = name;
  g.add(mesh);
  return g;
}

function kitLibrary(faction: string, variant: (component: string) => string, skip: string[] = []): PartLibrary {
  const lib = emptyLibrary();
  lib.kit.set(`${faction}_frame_titan`, fakeFrame());
  for (const c of COMPONENTS) if (c.required && !skip.includes(c.id)) lib.kit.set(`${faction}_${c.id}_${variant(c.id)}`, fakePart(`${faction}_${c.id}`, c.id === 'torso'));
  return lib;
}

const paladin = (loadout: WalkerInput['loadout'] = {}) => ({ name: 'Test', chassis: 'paladin', driver: { command: 0, trait: null }, loadout }) as WalkerInput;

describe('kit part resolution', () => {
  it('prefers the class part, then the frame part', () => {
    const names = new Set(['covenant_helm_titan', 'covenant_helm_paladin', 'covenant_arm_titan']);
    expect(resolvePart(names, 'covenant', 'helm', 'paladin', 'titan')?.name).toBe('covenant_helm_paladin');
    expect(resolvePart(names, 'covenant', 'arm', 'paladin', 'titan')?.name).toBe('covenant_arm_titan');
    expect(resolvePart(names, 'covenant', 'shin', 'paladin', 'titan')).toBeNull();
  });

  it('mirrors left parts onto the right unless a right-hand part exists', () => {
    const names = new Set(['covenant_frame_titan', 'covenant_arm_titan', 'covenant_pauldron_titan', 'covenant_pauldron-right_paladin']);
    const plan = planKit(names, 'covenant', 'paladin', 'titan')!;
    const arm = plan.parts.filter((p) => p.component === 'arm');
    expect(arm.map((p) => [p.joint, p.mirror])).toEqual([
      ['joint_shoulder_L', false],
      ['joint_shoulder_R', true],
    ]);
    const right = plan.parts.find((p) => p.component === 'pauldron' && p.side === 'R')!;
    expect([right.name, right.mirror]).toEqual(['covenant_pauldron-right_paladin', false]);
    expect(plan.missing).toContain('helm');
  });

  it('leaves out components a class omits, rather than falling back to the frame part', () => {
    const names = new Set(['covenant_frame_titan', 'covenant_collar_titan', 'covenant_cloth_titan', 'covenant_torso_paladin']);
    const parts = planKit(names, 'covenant', 'paladin', 'titan')!.parts.map((p) => p.component);
    expect(parts).toEqual(['torso']);
    expect(planKit(names, 'covenant', 'sentinel', 'titan')!.parts.map((p) => p.component)).toContain('collar');
    expect(kitCandidates('covenant', 'paladin', 'titan')).not.toContain('covenant_collar_titan');
  });

  it('needs the frame skeleton', () => {
    expect(planKit(new Set(['covenant_helm_titan']), 'covenant', 'paladin', 'titan')).toBeNull();
  });

  it('lists every candidate name for loading', () => {
    const names = kitCandidates('reliquary', 'goliath', 'titan');
    expect(names).toContain('reliquary_frame_titan');
    expect(names).toContain('reliquary_hand-right_goliath');
    expect(names).toContain('reliquary_hand_titan');
  });
});

describe('kit walker assembly', () => {
  it('builds a complete kit body, mirroring the right side and dropping covered stand-ins', () => {
    const lib = kitLibrary('covenant', () => 'titan');
    const model = buildWalkerModel(paladin({ armRight: ['lance'] }), '#123456', lib);
    const right = model.getObjectByName('kit_forearm_R')!;
    expect(right.parent!.userData.joint).toBe('joint_elbow_R');
    expect(right.scale.x).toBe(-1);
    expect(model.getObjectByName('kit_forearm_L')!.scale.x).toBe(1);
    const standins: string[] = [];
    model.traverse((o) => o.userData.standin && standins.push(o.userData.standin));
    // Optional components with no part keep their stand-ins; covered ones go.
    expect(standins).not.toContain('helm');
    expect(standins).toContain('pauldron');
    // Equipment still snaps to the frame's mounts.
    expect(model.getObjectByName('part_lance')!.parent!.userData.mount).toBe('mount_armRight_0');
    // Livery is multiplied into the baked hull texture.
    const torso = model.getObjectByName('covenant_torso') as THREE.Mesh;
    const mat = torso.material as THREE.MeshStandardMaterial;
    expect(mat.map).toBeTruthy();
    expect(mat.color.getHexString()).toBe(new THREE.Color('#123456').getHexString());
  });

  it('uses class parts over frame parts', () => {
    const lib = kitLibrary('covenant', () => 'titan');
    lib.kit.set('covenant_helm_paladin', fakePart('paladin_helm'));
    const model = buildWalkerModel(paladin(), '#123456', lib);
    expect(model.getObjectByName('paladin_helm')).toBeTruthy();
    expect(model.getObjectByName('covenant_helm')).toBeUndefined();
  });

  it('falls back to the procedural body while a required part is missing', () => {
    const lib = kitLibrary('covenant', () => 'titan', ['foot']);
    const model = buildWalkerModel(paladin(), '#123456', lib);
    expect(model.getObjectByName('kit_helm')).toBeUndefined();
    const forced = buildWalkerModel(paladin(), '#123456', lib, 'force');
    expect(forced.getObjectByName('kit_helm')).toBeTruthy();
    const feet: THREE.Object3D[] = [];
    forced.traverse((o) => o.userData.standin === 'foot' && feet.push(o));
    expect(feet).toHaveLength(2);
  });

  it('prefers a faction variant of an item', () => {
    const lib = kitLibrary('covenant', () => 'titan');
    lib.items.set('jump-jets', fakePart('shared_jets'));
    lib.items.set('jump-jets@covenant', fakePart('covenant_jets'));
    const model = buildWalkerModel(paladin({ legs: ['jump-jets'] }), '#123456', lib);
    expect(model.getObjectByName('covenant_jets')).toBeTruthy();
  });

  it('exports mirrored parts right side out', () => {
    const g = new THREE.Group();
    const box = new THREE.Mesh(new THREE.BoxGeometry(2, 3, 4), new THREE.MeshStandardMaterial());
    box.scale.x = -1;
    g.add(box);
    const view = stlBytes(g);
    // A closed mesh with outward faces has a positive signed volume.
    let volume = 0;
    for (let i = 0; i < view.getUint32(80, true); i++) {
      const v = [0, 1, 2].map((k) => new THREE.Vector3(...[0, 1, 2].map((a) => view.getFloat32(84 + i * 50 + 12 + k * 12 + a * 4, true))));
      volume += v[0].dot(v[1].clone().cross(v[2])) / 6;
    }
    expect(volume).toBeCloseTo(24, 3);
  });
});
