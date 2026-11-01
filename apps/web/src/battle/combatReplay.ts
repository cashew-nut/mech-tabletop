// Turns the events the rules engine already logged into "exchanges" the UI can replay:
// the dice that were rolled and what they did to the target. Nothing here rolls or decides
// anything; it only reads state.log (and the walkers before/after) so the rules stay untouched.
import { SURVEYOR_ID, type GameEvent, type GameState, type WalkerState } from '@brass-charter/rules';

export interface Die {
  value: number;
  hit: boolean;
  /** A natural 6 (the engine lets some weapons crit lower; the UI only gilds sixes). */
  crit: boolean;
}

export interface Impact {
  zone: string;
  damage: number;
  structure: number;
}

export interface Note {
  type: string;
  text: string;
}

export interface Exchange {
  id: string;
  kind: 'fire' | 'ram' | 'blast';
  attackerId: string | null;
  targetId: string;
  itemId?: string;
  tn: number;
  dice: Die[];
  rerolled: boolean;
  impacts: Impact[];
  /** Shields, criticals, destroyed locations, knock-back, valve blows, in the order they happened. */
  notes: Note[];
  headline: string;
  attackerBefore: WalkerState | null;
  attackerAfter: WalkerState | null;
  targetBefore: WalkerState | null;
  targetAfter: WalkerState | null;
  surveyorHp?: { before: number; after: number; max: number };
}

/** The engine's hit rule, used only to colour dice the roll event already reported. */
export const isHit = (roll: number, tn: number) => roll === 6 || (roll !== 1 && roll >= tn);

const NOTE_TYPES = new Set(['shield', 'reactive', 'critical', 'location', 'destroyed', 'push', 'valve', 'hit']);

function find(state: GameState, id: string | null | undefined): WalkerState | null {
  return id ? (state.walkers.find((w) => w.id === id) ?? null) : null;
}

/**
 * Group the events added between two states into dice exchanges.
 * `before` is the state the action was applied to, `after` the state it returned.
 */
export function buildExchanges(before: GameState, after: GameState): Exchange[] {
  const events: GameEvent[] = after.log.slice(before.log.length);
  const out: Exchange[] = [];
  let cur = null as Exchange | null;
  let rolled = false;
  let pendingSplash = null as Exchange | null;
  const stamp = before.log.length;

  const start = (e: GameEvent, kind: 'fire' | 'ram'): Exchange => {
    const targetId = e.targetId as string;
    const ex: Exchange = {
      id: `${stamp}-${out.length}`,
      kind,
      attackerId: (e.walkerId as string) ?? null,
      targetId,
      itemId: e.itemId as string | undefined,
      tn: 0,
      dice: [],
      rerolled: false,
      impacts: [],
      notes: [],
      headline: e.text,
      attackerBefore: find(before, e.walkerId as string),
      attackerAfter: find(after, e.walkerId as string),
      targetBefore: find(before, targetId),
      targetAfter: find(after, targetId),
    };
    if (targetId === SURVEYOR_ID && before.surveyor && after.surveyor) {
      ex.surveyorHp = { before: before.surveyor.hp, after: after.surveyor.hp, max: Math.max(before.surveyor.hp, 5) };
    }
    return ex;
  };

  for (const e of events) {
    switch (e.type) {
      case 'fire':
      case 'ram':
        cur = start(e, e.type);
        out.push(cur);
        rolled = false;
        pendingSplash = null;
        break;
      case 'reroll':
        if (cur && !rolled) cur.rerolled = true;
        break;
      case 'roll': {
        const rolls = (e.rolls as number[]) ?? [];
        const tn = (e.tn as number) ?? 4;
        const dice = rolls.map((value) => ({ value, hit: isHit(value, tn), crit: isHit(value, tn) && value === 6 }));
        if (cur && !rolled) {
          cur.dice = dice;
          cur.tn = tn;
          rolled = true;
        } else if (cur) {
          // A later roll in the same action is a blast splash on a neighbour; its target arrives with the blast event.
          pendingSplash = {
            ...cur,
            id: `${stamp}-${out.length}`,
            kind: 'blast',
            attackerId: cur.attackerId,
            targetId: '',
            dice,
            tn,
            rerolled: false,
            impacts: [],
            notes: [],
            headline: 'Blast splash',
            targetBefore: null,
            targetAfter: null,
            surveyorHp: undefined,
          };
        }
        break;
      }
      case 'blast': {
        if (!pendingSplash) break;
        const targetId = e.targetId as string;
        pendingSplash.targetId = targetId;
        pendingSplash.targetBefore = find(before, targetId);
        pendingSplash.targetAfter = find(after, targetId);
        pendingSplash.headline = `Blast catches ${pendingSplash.targetAfter?.name ?? 'a neighbour'}.`;
        out.push(pendingSplash);
        cur = pendingSplash;
        pendingSplash = null;
        break;
      }
      default:
        if (cur && NOTE_TYPES.has(e.type)) {
          if (e.type === 'hit' && typeof e.zone === 'string') {
            cur.impacts.push({ zone: e.zone, damage: (e.damage as number) ?? 0, structure: (e.structure as number) ?? 0 });
          } else if (e.type !== 'hit') cur.notes.push({ type: e.type, text: e.text });
          else cur.notes.push({ type: 'hit', text: e.text }); // surveyor hits
        } else if (e.type === 'end' || e.type === 'activate' || e.type === 'move') {
          cur = null;
        }
    }
  }
  return out.filter((x) => x.dice.length > 0 && x.targetId);
}
