import { describe, expect, it } from 'vitest';
import equipmentData from '../../../data/equipment.json';
import chassisData from '../../../data/chassis.json';
import { FIT, compactPlacements, fitClass, hardpoint, isCardOnly, nudgeOf, planLocation, pivotOf, poseOf } from '../src/model/fit';

const names = (plan: ReturnType<typeof planLocation>) => plan.map((p) => p?.map((x) => (x.side ? `${x.hp}:${x.side}` : x.hp)).join('+') ?? null);

describe('equipment fit', () => {
  it('only the built classes use hardpoints', () => {
    for (const id of ['paladin', 'brute', 'seer', 'sentinel']) expect(fitClass(id), id).not.toBeNull();
    for (const id of ['lancer', 'scavenger', 'artillery', 'wraith', 'goliath']) expect(fitClass(id), id).toBeNull();
  });

  it('puts a second weapon after a two-slot weapon on the forearm, not the shoulder', () => {
    expect(names(planLocation('paladin', 'armRight', ['rail-cannon', 'autocannon']))).toEqual(['grip:R', 'forearm-top:R']);
    expect(names(planLocation('brute', 'armLeft', ['rocket-pod', 'kinetic-shield']))).toEqual(['grip:L', 'bracer:L']);
  });

  it('gives the Brute one forearm per elbow socket: a gun forearm or a held item, and the next weapon on the pauldron', () => {
    // Its guns are whole forearms (grip-native) and a claw or rail cannon takes the same socket (grip), so neither
    // doubles up there, and the forearm-top beside a forearm the Brute does not have is skipped too.
    expect(names(planLocation('brute', 'armLeft', ['autocannon', 'autocannon'], [true, false]))).toEqual(['grip-native:L', 'shoulder-top:L']);
    expect(names(planLocation('brute', 'armRight', ['industrial-claw', 'autocannon'], [false, true]))).toEqual(['grip:R', 'shoulder-top:R']);
    expect(names(planLocation('brute', 'armRight', ['rail-cannon', 'autocannon']))).toEqual(['grip:R', 'shoulder-top:R']);
    const socket = hardpoint('brute', 'grip')!;
    expect([socket.joint, socket.contact]).toEqual(['elbow', ['back']]);
  });

  it("hangs the Carapace Gun on the arm: a forearm on the Sentinel's elbow, a shoulder pod on the Paladin", () => {
    // An arm item in the rules. The Sentinel's own copy (item_carapace-gun@sentinel) is a whole forearm, so it takes the elbow of
    // whichever arm holds it and hides the forearm and hand there.
    expect(names(planLocation('sentinel', 'armLeft', ['carapace-gun'], [true]))).toEqual(['forearm-gun:L']);
    expect(names(planLocation('sentinel', 'armRight', ['carapace-gun'], [true]))).toEqual(['forearm-gun:R']);
    expect(hardpoint('sentinel', 'forearm-gun')).toMatchObject({ joint: 'elbow', side: 'loc', hides: ['forearm', 'hand'] });
    expect(poseOf('carapace-gun', 'forearm-gun', 'sentinel').contact).toEqual([]);
    // the Paladin's pod sits on the shoulder of the arm that holds it
    expect(names(planLocation('paladin', 'armLeft', ['carapace-gun'], [true]))).toEqual(['shoulder-top:L']);
    expect(names(planLocation('paladin', 'armRight', ['carapace-gun'], [false]))).toEqual(['shoulder-top:R']);
    expect(poseOf('carapace-gun', 'shoulder-top', 'paladin').contact).toEqual(['bottom']);
  });

  it("hangs the Brute's own claw and rail cannon on the elbow socket like its gun forearms", () => {
    // item_industrial-claw@brute and item_rail-cannon@brute are whole forearms on the same peg as the cannon arm and the gatling.
    expect(names(planLocation('brute', 'armLeft', ['industrial-claw'], [true]))).toEqual(['grip-native:L']);
    expect(names(planLocation('brute', 'armRight', ['rail-cannon'], [true]))).toEqual(['grip-native:R']);
    expect(FIT.nativeRight).not.toContain('industrial-claw@brute');
    expect(FIT.nativeRight).not.toContain('rail-cannon@brute');
  });

  it("seats the Seer's Hellfire launchers on both shoulder sockets from the core, leaving the arms free", () => {
    expect(names(planLocation('seer', 'core', ['hellfire-missiles'], [true]))).toEqual(['shoulder-sockets:L+shoulder-sockets:R']);
    expect(planLocation('seer', 'armLeft', ['hellfire-missiles'], [true])).toEqual([null]);
    expect(hardpoint('seer', 'shoulder-sockets')!.joint).toBe('shoulder');
    expect(pivotOf('hellfire-missiles@seer')).toEqual([0, 0, 0]);
  });

  it("plugs the Seer's own spear and claws into the wrist socket in place of the hand", () => {
    // arc-cannon@seer and kinetic-claws@seer carry the hand's half knuckle and peg: they take the wrist, the hand is hidden,
    // and a second weapon on that arm goes past the grip they block (the shared model, not the Seer's own).
    expect(names(planLocation('seer', 'armRight', ['kinetic-claws', 'arc-cannon'], [true, false]))).toEqual(['wrist-socket:R', 'forearm-top:R']);
    expect(names(planLocation('seer', 'armLeft', ['arc-cannon'], [true]))).toEqual(['wrist-socket:L']);
    const socket = hardpoint('seer', 'wrist-socket')!;
    expect([socket.joint, socket.offset, socket.hides]).toEqual(['wrist', [0, 0, 0], ['hand']]);
    // other classes keep the tuned numbered grip for their own items, and shared items stay in the grip
    expect(names(planLocation('paladin', 'armLeft', ['lance'], [true]))).toEqual(['grip-native:L']);
    expect(names(planLocation('seer', 'armLeft', ['kinetic-claws'], [false]))).toEqual(['grip:L']);
  });

  it('fills the arm ladder in order and uses the right side', () => {
    expect(names(planLocation('paladin', 'armRight', ['lance', 'lance', 'lance']))).toEqual(['grip:R', 'forearm-top:R', 'shoulder-top:R']);
    expect(names(planLocation('paladin', 'armRight', ['lance', 'lance', 'lance', 'lance']))[3]).toBeNull();
  });

  it('spreads core items over different hardpoints, away from the neck', () => {
    const plan = names(planLocation('seer', 'core', ['soul-lantern', 'soul-lantern', 'soul-lantern']));
    expect(plan).toEqual(['waist-L', 'waist-R', null]);
    expect(new Set(plan).size).toBe(plan.length);
  });

  it('lets the Paladin\'s own shield plug into its numbered mount, and sits its rack and gun pods on the shoulder of their arm', () => {
    expect(FIT.items['kinetic-shield'].nativeMount).toBe(true);
    // arm weapons: the Paladin's and the Sentinel's own pods go through the shoulder hardpoint, not a numbered mount
    for (const cls of ['paladin', 'sentinel'])
      expect(names(planLocation(cls, 'armRight', ['missile-rack'], [true])), cls).toEqual(['shoulder-top:R']);
    expect(planLocation('paladin', 'armLeft', ['kinetic-shield'], [true])).toEqual([null]);
    // the faction's shared copy still goes through the hardpoints
    expect(names(planLocation('paladin', 'armLeft', ['kinetic-shield'], [false]))).toEqual(['bracer:L']);
  });

  it('gives card-only items no hardpoint and no fit entry', () => {
    expect(FIT.cardOnly.length).toBeGreaterThan(0);
    for (const id of FIT.cardOnly) {
      expect(isCardOnly(id), id).toBe(true);
      expect(FIT.items[id], id).toBeUndefined();
      expect(equipmentData.equipment.some((e) => e.id === id), `${id} is still an item`).toBe(true);
    }
    expect(isCardOnly('lance')).toBe(false);
    expect(planLocation('paladin', 'legs', ['sprint-servos'])).toEqual([null]);
  });

  it('gives an unknown item no placement, so it falls back to the numbered mounts', () => {
    expect(planLocation('brute', 'core', ['not-an-item'])).toEqual([null]);
  });

  it('describes every item for every location it can mount in', () => {
    const kinds: Record<string, 'arm' | 'core' | 'legs'> = { arm: 'arm', core: 'core', legs: 'legs' };
    for (const e of equipmentData.equipment) {
      if (isCardOnly(e.id)) continue;
      const mounts = e.mount.includes('any') ? ['arm', 'core', 'legs'] : e.mount;
      for (const m of mounts) {
        const prefs = FIT.items[e.id]?.[kinds[m]];
        expect(prefs?.length, `${e.id} ${m}`).toBeGreaterThan(0);
      }
    }
  });

  it('only names hardpoints that exist, and every class has its overrides section', () => {
    for (const [id, item] of Object.entries(FIT.items)) {
      for (const k of ['arm', 'core', 'legs'] as const) for (const hp of item[k] ?? []) expect(FIT.hardpoints[hp], `${id} ${hp}`).toBeDefined();
    }
    for (const id of Object.keys(FIT.classes)) {
      expect(FIT.overrides[id], id).toBeDefined();
      expect(chassisData.chassis.some((c) => c.id === id), id).toBe(true);
    }
    expect(hardpoint("paladin", "grip-native")?.mount).toBeDefined();
  });

  it('measures a contact face from the item bounds', () => {
    // A plate's back face is its smallest z, a hung item's top face is its largest y.
    const back = pivotOf('kinetic-shield', ['back']);
    expect(back[2]).toBeCloseTo(-0.42, 1);
    expect(pivotOf('soul-lantern', ['top'])[1]).toBeGreaterThan(5);
    expect(poseOf('soul-lantern', 'waist-L').contact).toEqual(['top']);
  });

  describe('placement table', () => {
    const table = FIT.placements!;
    const restore = JSON.stringify(table);
    const reset = () => {
      for (const k of Object.keys(table)) delete table[k];
      Object.assign(table, JSON.parse(restore));
    };

    it('has a section for every class with a fit, and changes nothing until a row is added', () => {
      for (const id of Object.keys(FIT.classes)) expect(table[id], id).toBeDefined();
      expect(nudgeOf('paladin', 'grip', 'lance')).toBeNull();
    });

    it('lets an item row win over the hardpoint row, field by field', () => {
      table.paladin = { grip: { '*': { offset: [0, 0.01, 0], scale: 1.2 }, lance: { scale: 0.8 } } };
      expect(nudgeOf('paladin', 'grip', 'kinetic-claws')).toEqual({ offset: [0, 0.01, 0], rot: [0, 0, 0], scale: 1.2 });
      expect(nudgeOf('paladin', 'grip', 'lance')).toEqual({ offset: [0, 0.01, 0], rot: [0, 0, 0], scale: 0.8 });
      expect(nudgeOf('seer', 'grip', 'lance')).toBeNull();
      reset();
    });

    it('drops rows that change nothing, unless they undo the hardpoint row', () => {
      expect(
        compactPlacements({
          grip: { '*': { scale: 1 }, lance: { offset: [0, 0, 0], rot: [0, 0, 0], scale: 1 } },
          bracer: { '*': { scale: 1.2 }, 'kinetic-shield': { offset: [0, 0, 0], rot: [0, 0, 0], scale: 1 }, 'soul-lantern': { rot: [0, 10, 0] } },
        }),
      ).toEqual({ bracer: { '*': { scale: 1.2 }, 'kinetic-shield': { offset: [0, 0, 0], rot: [0, 0, 0], scale: 1 }, 'soul-lantern': { rot: [0, 10, 0] } } });
    });
  });
});
