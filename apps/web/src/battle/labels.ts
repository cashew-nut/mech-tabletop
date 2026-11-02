// Display names shared by the Trial's panels.
import type { Zone } from '@brass-charter/rules';

/** Armour zones, in the order the cards list them. */
export const ZONE_NAMES: Record<Zone, string> = {
  coreFront: 'Core',
  coreRear: 'Core (rear)',
  armLeft: 'Left arm',
  armRight: 'Right arm',
  legs: 'Legs',
};
