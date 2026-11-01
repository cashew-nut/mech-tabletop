// Exploded view of a kit walker: every part slides off its parent, and the move adds up down the joint tree, so a hand
// ends up one step past its forearm, which is one step past its arm. Pure maths (no three.js scene), used by viewer.ts.
import * as THREE from 'three';

/** Which kit component each one plugs into (the composite pipeline's TREE, assets/blender/parts/composite). */
export const PARENT: Record<string, string> = {
  torso: 'pelvis', thigh: 'pelvis', shin: 'thigh', foot: 'shin',
  helm: 'torso', crown: 'helm', back: 'torso', cloth: 'torso', collar: 'torso',
  pauldron: 'torso', arm: 'pauldron', forearm: 'arm', hand: 'forearm',
};

/** Classes whose tree differs: the Seer's arm plugs straight into the torso, with the pauldron on a knuckle beside it. */
const TREE_OVERRIDE: Record<string, Record<string, string>> = { seer: { arm: 'torso' } };

const SIDED = new Set(['pauldron', 'arm', 'forearm', 'hand', 'thigh', 'shin', 'foot']);

export interface Unit {
  /** Node name, such as kit_forearm_L. */
  id: string;
  /** The id of the unit it plugs into, or null for the root (the pelvis). */
  parent: string | null;
  /** Where its middle sits at rest, world space. */
  centre: THREE.Vector3;
}

/** The parent unit of each kit part present, climbing to the nearest ancestor that exists (the Brute has no arm). */
export function kitParents(ids: string[], chassis: string): Map<string, string | null> {
  const have = new Set(ids);
  const out = new Map<string, string | null>();
  for (const id of ids) {
    const m = /^kit_([a-z]+)(?:_([LR]))?$/.exec(id);
    if (!m) continue;
    const side = m[2];
    let comp: string | undefined = m[1];
    let parent: string | null = null;
    for (let guard = 0; comp && guard < 8; guard++) {
      comp = TREE_OVERRIDE[chassis]?.[comp] ?? PARENT[comp];
      if (!comp) break;
      const cand = SIDED.has(comp) && side ? `kit_${comp}_${side}` : `kit_${comp}`;
      if (have.has(cand)) {
        parent = cand;
        break;
      }
    }
    out.set(id, parent);
  }
  return out;
}

/**
 * How far each unit moves at full explosion (world space). A unit goes along the line from its parent's middle to its
 * own, and carries its parent's move with it. `reach` is the distance of one step.
 */
export function explodeOffsets(units: Unit[], reach: number): Map<string, THREE.Vector3> {
  const byId = new Map(units.map((u) => [u.id, u]));
  const out = new Map<string, THREE.Vector3>();
  const solve = (u: Unit, depth = 0): THREE.Vector3 => {
    const done = out.get(u.id);
    if (done) return done;
    const parent = u.parent && depth < 12 ? byId.get(u.parent) : undefined;
    if (!parent) {
      out.set(u.id, new THREE.Vector3());
      return out.get(u.id)!;
    }
    const dir = u.centre.clone().sub(parent.centre);
    if (dir.lengthSq() < 1e-6) dir.set(0, 1, 0);
    dir.normalize();
    const off = solve(parent, depth + 1).clone().addScaledVector(dir, reach);
    out.set(u.id, off);
    return off;
  };
  for (const u of units) solve(u);
  return out;
}
