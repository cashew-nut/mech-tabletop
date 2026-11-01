// Which Blender kit parts make up a walker. Each class (data/chassis.json)
// names its faction and frame. Its body is the faction's skeleton,
// `<faction>_frame_<frame>` (or the class's own `<faction>_frame_<class>`, built on
// the joints its parts were cut on), with one part per component joint, looked up
// class first and then frame:
//   covenant_helm_paladin  ->  covenant_helm_titan  ->  the frame's stand-in
// Sided components (arms, legs, pauldrons) are modelled for the left (+X) and
// mirrored for the right, unless a `<faction>_<component>-right_<variant>`
// part exists. The components and their joints live in data/model-kit.json,
// which the Blender kit (assets/blender/kit) reads too.
import kitData from '../../../../data/model-kit.json';

export interface KitComponent {
  id: string;
  joint: string;
  sided?: boolean;
  required: boolean;
}

export type Side = 'L' | 'R';

export const COMPONENTS = kitData.components as KitComponent[];
export const KIT_FACTIONS = Object.keys(kitData.factions);
export const SPARE_MOUNTS = kitData.spareMounts as Record<string, number>;
/** Components a class never shows, so the frame's part does not fill in for them (the composite Paladin's torso has its own collar). */
const OMIT = kitData.omit as unknown as Record<string, string[] | string>;

const SIDED_JOINTS = new Set(['shoulder', 'elbow', 'wrist', 'hip', 'knee', 'ankle']);

export const frameName = (faction: string, frame: string) => `${faction}_frame_${frame}`;

export const jointName = (joint: string, side?: Side) => (SIDED_JOINTS.has(joint) && side ? `joint_${joint}_${side}` : `joint_${joint}`);

export interface PlannedPart {
  component: string;
  side?: Side;
  /** The joint the part hangs on, such as joint_elbow_R. */
  joint: string;
  /** Kit part name, such as covenant_forearm_titan. */
  name: string;
  /** A left-hand part reused on the right: flip it across X. */
  mirror: boolean;
}

export interface KitPlan {
  frame: string;
  parts: PlannedPart[];
  /** Required components with no part yet: the stand-ins show instead. */
  missing: string[];
  /** Components the class never shows: their stand-ins go too (the composite Brute's arms are its guns). */
  omitted: string[];
}

interface Names {
  has(name: string): boolean;
}

/** The part for one component, class first, then frame. */
export function resolvePart(names: Names, faction: string, component: string, cls: string, frame: string, side?: Side) {
  const comps = side === 'R' ? [`${component}-right`, component] : [component];
  for (const comp of comps) {
    for (const variant of [cls, frame]) {
      const name = `${faction}_${comp}_${variant}`;
      if (names.has(name)) return { name, ownRight: comp.endsWith('-right') };
    }
  }
  return null;
}

/** The class's own frame (foundries_frame_brute, on the joints its parts were cut on) if there is one, else the frame's. */
export const classFrame = (names: Names, faction: string, cls: string, frame: string) =>
  names.has(frameName(faction, cls)) ? frameName(faction, cls) : names.has(frameName(faction, frame)) ? frameName(faction, frame) : null;

/** Plan a class's kit body from the names available, or null without a frame. */
export function planKit(names: Names, faction: string, cls: string, frame: string): KitPlan | null {
  const skeleton = classFrame(names, faction, cls, frame);
  if (!skeleton) return null;
  const parts: PlannedPart[] = [];
  const missing = new Set<string>();
  const omitted: string[] = [];
  for (const c of COMPONENTS) {
    if (OMIT[cls]?.includes(c.id)) {
      omitted.push(c.id);
      continue;
    }
    for (const side of c.sided ? (['L', 'R'] as Side[]) : [undefined]) {
      const found = resolvePart(names, faction, c.id, cls, frame, side);
      if (!found) {
        if (c.required) missing.add(c.id);
        continue;
      }
      parts.push({ component: c.id, side, joint: jointName(c.joint, side), name: found.name, mirror: side === 'R' && !found.ownRight });
    }
  }
  return { frame: skeleton, parts, missing: [...missing], omitted };
}

/** Every kit name a class could use, for loading only what it needs. */
export function kitCandidates(faction: string, cls: string, frame: string): string[] {
  const out = [frameName(faction, cls), frameName(faction, frame)];
  for (const c of COMPONENTS) {
    if (OMIT[cls]?.includes(c.id)) continue;
    for (const comp of c.sided ? [c.id, `${c.id}-right`] : [c.id]) {
      for (const variant of [cls, frame]) out.push(`${faction}_${comp}_${variant}`);
    }
  }
  return out;
}

/** An item's Blender part: the class's own variant (lance@paladin) first, then the faction's, then the shared one. */
export const itemPartName = (names: Names, id: string, faction?: string, cls?: string) =>
  cls && names.has(`${id}@${cls}`)
    ? `${id}@${cls}`
    : faction && names.has(`${id}@${faction}`)
      ? `${id}@${faction}`
      : names.has(id)
        ? id
        : null;
