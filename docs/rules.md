# Brass Charter — Core Rules v0.5

> Draft for playtesting. Numbers will change. All class and equipment stats live in
> [`data/`](../data) and are the source of truth; tables here are for reading convenience.

## 1. The setting in one paragraph

The galaxy is carved up by three powers that hold its Charters. The **Iron Covenant** are noble
houses and sworn orders whose war engines are forged in cathedral foundries. The **Ashen
Foundries** are industrial warbands and mercenary legions, built to win, not to inspire. The
**Reliquary** are a forgotten order whose machines seem older than the wars themselves. They
settle disputes over worlds and trade lanes by **Charter Trial**: a legally binding battle
between small lances of war-walkers. Centuries ago the **Quieting** burned out
every advanced circuit in the galaxy, so starships, war-walkers and their weapons run on
aether-fired boilers, brass clockwork and valve-driven logic engines.

## 2. What you need

- A hex map, 16 x 12 hexes by default (2 inches per hex on a table).
- Six-sided dice (d6). A dozen is plenty.
- Tokens for Overpressure, Reserve, objectives, smoke and wrecks.
- One unit card per war-walker.

## 3. Glossary

| Term | Meaning |
| --- | --- |
| War-walker | A mech. Each one is built from a class (its chassis) plus equipment. |
| Faction | Who your lance is sworn to. It sets your classes, signature weapons and doctrine. |
| Driver | The pilot of a war-walker. Has a Command value and up to one trait. |
| Lance | Your force: 3 to 5 war-walkers, 100 points by default. |
| Pressure | The points a war-walker spends during its activation. |
| Boiler rating | How much Pressure a class builds each activation. |
| Overpressure | Stress tokens. Too many cause Faults. |
| Reserve | Pressure held back to use outside your activation. |
| Target number (TN) | The number each attack die must equal or beat to hit. |

## 4. Building a lance

1. Pick a faction (section 12). Its doctrine applies to your whole lance.
2. Pick 3 to 5 war-walkers. For each, pick one of your faction's classes (section 13) and fill
   its slots with equipment. Signature weapons (section 13.1) can only be fitted by their own
   faction. All defence, mobility and system gear is shared, except the Reliquary's Soul Lantern.
3. Give each war-walker a Driver: Command 0, 1 or 2 (0, 2 or 4 points) and optionally one trait.
4. The total of class, equipment and Driver costs must not exceed the Trial budget (100).

**Slots.** Each class has two arms, a core and legs, each with a number of slots. An item
uses as many slots as listed and must fit in one location: a 2-slot weapon needs an arm with
2 free slots. Items list which locations they may use (`arm`, `core`, `legs`, or `any`). The Carapace Gun is
a weapon that mounts on the core.

**Limits.** At most one Targeting Array per war-walker. Fitting two or more Ablative Plating on
one war-walker gives it -1 Stride.

## 5. Setting up

1. Pick a scenario (section 11) and place terrain and objectives as it says.
2. Each side rolls a d6; the higher roll picks a deployment edge. The other side deploys first.
3. Sides alternate placing one war-walker at a time anywhere within 3 hexes of their edge,
   facing any hexside. When one side has placed everything, the other places the rest.
   The Reliquary hold their last war-walker back until the enemy has finished (section 12).

## 6. The round

A Trial lasts **6 rounds**. Each round has three phases.

### 6.1 Initiative

Each side rolls a d6 and adds the highest Command among its war-walkers still in play.
Reroll ties. The winner activates first this round.

### 6.2 Activations

Sides take turns activating one war-walker that has not yet activated this round. When a side
has no war-walkers left to activate, the other side activates its remaining ones in a row.

**Passing.** A side with fewer war-walkers still in play than its opponent may pass instead
of activating, once per round.

### 6.3 End phase

1. Score objectives (section 10).
2. Every war-walker removes 1 Overpressure.
3. Unused Reserve is lost.

## 7. Activating a war-walker

### 7.1 Start of activation

1. If the war-walker has 3 or more Overpressure, roll on the Fault table (7.5).
2. It gains Pressure equal to its Boiler rating, adjusted by Faults, Ion hits and items.
3. It may **Open the Throttle**: gain up to 2 extra Pressure, taking 1 Overpressure per point.
   This is declared before the Fault roll; a Gauge failure cancels it.

### 7.2 Spending Pressure

Spend Pressure on these actions in any order and any number of times, as long as you can pay.

| Action | Cost | Effect |
| --- | --- | --- |
| Move | 1 | Move up to Stride hexes. Change facing freely while moving. |
| Turn | 1 | Change facing to any hexside without moving. |
| Fire | weapon's cost | Attack with one weapon (section 8). Each weapon fires at most once per activation. |
| Brace | 1 | +1 to the TN of attacks against this war-walker until its next activation. Once per activation. |
| Use a system | item's cost | As listed on the item. |
| Stand up | 1 | Stop being prone (section 9.4). |
| Ram | 2 | Melee attack, see 8.6. |
| Bank | 1 | Move 1 Pressure into Reserve. Reserve holds at most 2. |

Terrain:

| Terrain | Movement cost | Line of sight | Cover for a target in it |
| --- | --- | --- | --- |
| Open | 1 | Clear | None |
| Light cover (scrub, scaffolding) | 1 | Clear, but a target behind it gets light cover | +1 TN |
| Rough (rubble, slag) | 2 | Clear | None |
| Heavy cover (ruins, pipe stacks) | 2 | Blocked through it, not into it | +2 TN |
| Blocking (buildings, cliffs) | Impassable | Blocked | n/a |

A war-walker cannot enter a hex holding another war-walker, a wreck or blocking terrain.
Moving up one elevation level costs 1 extra hex of movement.

Unspent Pressure is lost at the end of the activation.

### 7.3 Reserve

Reserve Pressure can only be spent outside your own activation, on items that say "when hit"
or "reaction" (for example the Kinetic Shield). It is lost in the end phase.

### 7.4 Overpressure

Overpressure comes from Opening the Throttle, Hellfire Missile hits, some items and some
criticals. At 3 or more, you roll for Faults at the start of each activation. At **6 or more**
the safety valve blows: the war-walker removes all Overpressure and immediately ends its
activation (or skips its next one, if this happens outside its activation).

### 7.5 Fault table

Roll a d6. On 3 to 6 nothing happens. On 1 or 2, roll again on this table:

| d6 | Fault | Effect this activation |
| --- | --- | --- |
| 1 | Valve stick | -1 Pressure |
| 2 | Gear seize | -1 Stride |
| 3 | Breech jam | One random weapon cannot fire |
| 4 | Steam scald | +1 to the TN of all your attacks |
| 5 | Gauge failure | You cannot Open the Throttle |
| 6 | Boiler surge | +1 Overpressure |

## 8. Attacking

### 8.1 Arcs and line of sight

A war-walker's **front arc** is the hexside it faces plus the two hexsides either side of it
(half the circle). The **rear arc** is the single opposite hexside. The remaining two hexsides
are the **left and right side arcs**.

Weapons fire only at targets in the front arc. Draw a line from the centre of the attacker's
hex to the centre of the target's hex. Line of sight is blocked if the line passes through a
heavy cover or blocking hex, a wreck, smoke, or terrain higher than both attacker and target.
War-walkers do not block line of sight. A line that runs exactly along a hex edge is blocked
only if both hexes on that edge block it.

### 8.2 Range

| Band | Distance | TN modifier |
| --- | --- | --- |
| Short | 1-3 hexes | +0 |
| Medium | 4-7 hexes | +1 |
| Long | 8-12 hexes | +2 |

A weapon can fire up to its listed maximum band; beyond 12 hexes nothing can fire. Melee weapons need the target adjacent and in
the front arc.

### 8.3 Rolling to hit

The base TN is **4**. Apply every modifier that applies, then roll the weapon's Dice. Each die
that equals or beats the TN is a hit. A **6 always hits and is a critical**; a 1 always misses.
TN cannot go below 2.

| Situation | TN |
| --- | --- |
| Range band | +0 / +1 / +2 |
| Target in or behind light cover, or in smoke | +1 |
| Target in a heavy cover hex | +2 (does not stack with light cover) |
| Indirect fire | +1 |
| Target moved 4 or more hexes in its last activation | +1 |
| Target is Bracing | +1 |
| Attacker moved this activation (not melee) | +1 |
| Attacker is higher than the target | -1 |
| Target is prone | -1 |
| Targeting Array | -1 |
| Spotter Drone mark on target | -1 |

### 8.4 Hit location

Roll a d6 for each hit:

| d6 | Location |
| --- | --- |
| 1-2 | Legs |
| 3 | Left arm |
| 4 | Right arm |
| 5-6 | Core |

If the attacker is in the target's side arc, reroll a result for the arm on the far side once.
If the attacker is in the target's rear arc, Core hits use the rear core armour.

### 8.5 Damage

Each hit deals the weapon's Damage to the location. Damage removes Armour first, then
Structure. Pierce X ignores up to X points of Armour on each hit.

Roll on the **Critical table** once for each hit that reaches Structure, and once for each
critical (a natural 6), applied to the hit location. A hit that does both rolls twice.

| d6 | Critical | Effect |
| --- | --- | --- |
| 1-2 | Item destroyed | A random item in the location is destroyed. If none, 1 extra Structure damage. |
| 3 | Boiler breach | +2 Overpressure |
| 4 | Actuator damage | Arm: its weapons roll 1 fewer die. Legs: -1 Stride. Core: -1 Boiler rating. Lasts the whole Trial. |
| 5 | Knockdown | The war-walker is prone. |
| 6 | Clean through | 1 extra Structure damage to the Core. |

A location at 0 Structure is **destroyed**: its items stop working. Destroyed arm: nothing
more happens to it; further hits there go to the Core. Destroyed legs: Stride is halved
(round down, minimum 1) and further hits there go to the Core. **Destroyed Core: the
war-walker is out of the Trial.** Replace it with a wreck token.

### 8.6 Melee and Ram

A melee weapon attack works like shooting with no range, cover or attacker-moved modifiers.

**Ram** (2 Pressure): pick an adjacent enemy in your front arc and roll 2 dice at TN 4. Each
hit deals damage equal to your chassis Size. Both war-walkers then take 1 Overpressure. You
cannot Ram if you are prone.

## 9. Other rules

### 9.1 Wrecks

A wreck token blocks movement and line of sight.

### 9.2 Smoke

A smoke hex blocks line of sight through it. A war-walker in smoke counts as in light cover.
Smoke is removed in the end phase.

### 9.3 Indirect fire

A weapon with Indirect may fire at a target it cannot see if a friendly war-walker or Spotter
Drone mark can see it. Indirect attacks take an extra +1 TN.

### 9.4 Prone

A prone war-walker cannot Move, Fire, Ram or Brace until it spends 1 Pressure to stand up.
Attacks against it get -1 TN.

## 10. Objectives and victory

An objective is **held** by the side with the greater total chassis Size of war-walkers on or
adjacent to it (each class lists its Size in section 13). A tie, including nobody nearby, means
nobody holds it. Prone war-walkers still count.

Victory points (VP):

- In each end phase, score 1 VP per objective held (some scenarios change this).
- When an enemy war-walker is destroyed, score VP equal to its points cost divided by 4,
  rounded up.

After round 6 the side with more VP wins the Charter. A tie is a draw. If a lance is wiped out,
the Trial ends at once and the other side wins.

## 11. Scenarios

| Scenario | Setup | Special rules |
| --- | --- | --- |
| Hold the Field | 3 objectives in a line across the centre row, 4 hexes apart. | None. |
| Refinery Seizure | 5 objectives: one in the centre, four 3 hexes from it diagonally. | The centre objective is worth 2 VP. |
| Surveyor Escort | The attacker's surveyor token starts at the front of their deployment zone, in the centre column. It blocks movement like a war-walker. | A friendly war-walker next to the surveyor may spend 1 Pressure to move it up to 2 hexes. The attacker scores 6 VP when it reaches the far edge row. It can be shot like a war-walker (no armour, no hit location), at +1 TN while a friendly war-walker is next to it. 5 hits destroy it and give the defender 4 VP. No objectives. |

## 12. Factions

| Faction | Motto | Identity | Doctrine |
| --- | --- | --- | --- |
| Iron Covenant | Faith. Honour. Dominion. | Few, elite, armoured knights who win in melee. No Size 1 class. | **Sworn Knights:** each Driver trait costs 1 point less (minimum 1). |
| Ashen Foundries | Build. Fight. Repeat. | Cheap, tough gun walkers in numbers. | **Forge Plate:** Ablative Plating costs 1 point less. |
| Reliquary | Ancient. Watchful. Eternal. | Frail, fast or strange walkers around one towering Goliath. | **From the Veil:** deploy one war-walker after the enemy has finished deploying. If both sides are Reliquary, this cancels out. |

## 13. Reference: classes

| Faction | Class | Role | Size | Pts | Stride | Boiler | Slots (arm / arm / core / legs) | Armour (core front / rear / arm / legs) | Structure (core / other) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Covenant | Lancer | Assault | 2 | 16 | 3 | 5 | 2 / 2 / 1 / 1 | 6 / 3 / 3 / 3 | 4 / 3 |
| Covenant | Sentinel | Defence and support | 3 | 19 | 2 | 6 | 1 / 1 / 4 / 1 | 9 / 4 / 4 / 5 | 5 / 4 |
| Covenant | Paladin | Heavy melee | 4 | 22 | 2 | 6 | 2 / 2 / 2 / 1 | 10 / 5 / 5 / 6 | 6 / 5 |
| Foundries | Scavenger | Utility and recon | 1 | 6 | 3 | 4 | 1 / 1 / 2 / 1 | 4 / 2 / 2 / 3 | 3 / 2 |
| Foundries | Brute | Frontline | 3 | 15 | 2 | 6 | 2 / 2 / 2 / 1 | 9 / 4 / 5 / 5 | 5 / 4 |
| Foundries | Artillery | Long range | 3 | 12 | 1 | 7 | 3 / 3 / 2 / 1 | 7 / 3 / 3 / 5 | 5 / 4 |
| Reliquary | Wraith | Assassin | 1 | 5 | 4 | 5 | 1 / 1 / 1 / 1 | 3 / 2 / 2 / 2 | 3 / 2 |
| Reliquary | Seer | Artillery and psychic | 2 | 10 | 2 | 6 | 1 / 2 / 3 / 1 | 5 / 2 / 2 / 3 | 4 / 3 |
| Reliquary | Goliath | Heavy | 4 | 20 | 2 | 7 | 2 / 2 / 3 / 2 | 9 / 5 / 4 / 6 | 6 / 5 |

### 13.1 Signature weapons

| Faction | Weapon | Mount | Slots | Pressure | Pts | Range | Dice | Damage | Rules |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Covenant | Lance | Arm | 1 | 1 | 10 | Melee | 2 | 3 | **Charge:** +1 die if this war-walker has moved 2 or more hexes this activation. |
| Covenant | Melee Blade | Arm | 1 | 1 | 9 | Melee | 3 | 2 | Rolls of 5 or 6 are criticals. |
| Covenant | Carapace Gun | Core | 1 | 2 | 5 | Medium | 2 | 2 | Pierce 1. No ammo. |
| Covenant | Missile Rack | Arm | 2 | 1 | 6 | Long | 5 | 1 | Indirect. Ammo 4. |
| Foundries | Autocannon | Arm | 1 | 1 | 3 | Medium | 3 | 1 | Ammo 6. |
| Foundries | Rail Cannon | Arm | 2 | 2 | 7 | Long | 1 | 4 | Pierce 2. +2 TN instead of +1 after moving. |
| Foundries | Rocket Pod | Arm | 2 | 2 | 4 | Long | 2 | 2 | Blast. Minimum range 4. |
| Foundries | Industrial Claw | Arm | 1 | 1 | 5 | Melee | 2 | 3 | Push the target 1 hex away on a hit. |
| Reliquary | Arc Cannon | Arm | 1 | 1 | 6 | Medium | 3 | 1 | Each hit drains 1 Pressure from the target's next activation. No ammo. |
| Reliquary | Hellfire Missiles | Arm | 2 | 1 | 5 | Long | 3 | 1 | Indirect. Each hit adds 1 Overpressure. Ammo 3. |
| Reliquary | Kinetic Claws | Arm | 1 | 1 | 6 | Melee | 4 | 1 | **Backstab:** rolls of 5 or 6 are criticals from the target's rear arc. |
| Reliquary | Soul Lantern | Core (system) | 1 | 0 | 5 | | | | Enemy attacks on friendly war-walkers within 2 hexes get +1 TN. Does not stack. |

Shared equipment and Driver traits are listed in [`data/equipment.json`](../data/equipment.json) and
[`data/drivers.json`](../data/drivers.json).

## 14. Open questions for playtesting

- Does the Artillery's Stride 1 feel too slow to reach objectives?
- Do the factions feel different enough at the table, or do they need more exclusive systems?
- Smoke, Jump Jets and Field Repair test weakly, but the AI barely uses them. Do they feel weak
  in human play?
- Should Reserve be capped at 1 instead of 2?

## 15. Changes in v0.2

Balance pass driven by 600-game AI-vs-AI simulations (see [`balance.md`](balance.md)).

- Objectives are held by total chassis Size rather than by any presence. This stopped
  five-Scout swarms from winning on objectives alone.
- Bulwark Stride 1 to 2. Titan 32 to 33 points.
- Rail Lance can now fire after moving, taking +2 TN for moving instead of the usual +1 (Gyro
  Stabilisers remove both); 8 to 7 points.
- Missile Rack 4 to 5 dice and 3 to 4 ammo. Arc Mortar 7 to 6 points. Ion Lance 2 to 1 Pressure
  and 2 to 3 dice. Beam Cutter gains Pierce 1. Autocannon 4 to 3 points and 4 to 6 ammo.
- Scattergun 3 to 4, Impact Hammer 3 to 5, and Shear Blade 4 to 6 points.
- Targeting Array 5 to 4, Gyro Stabilisers 4 to 3, Kinetic Shield 4 to 3, and Overcharged Boiler
  4 to 2 points.
- Tactician 5 to 4 and Iron Nerve 3 to 2 points.

## 16. Changes in v0.3

- Alternating deployment and the Calloway & Vane late-deployment doctrine are now in the engine.
- Surveyor Escort is playable. Compared with the v0.2 draft, the surveyor starts at the front of
  the deployment zone instead of the back, takes 5 hits instead of 3, and is screened (+1 TN)
  while an escort stands next to it. In 120 AI-vs-AI games with alternating deployment the
  escorting side won 51%, lost 43% and drew 6%; the surveyor escaped in 74% of games.

## 17. Changes in v0.4

Balance pass, two 600-game simulator rounds (see [`balance.md`](balance.md)).

- Rail Lance costs 2 Pressure instead of 3 and 8 points instead of 7.
- Shear Blade costs 8 points instead of 6. Impact Hammer costs 6 instead of 5.
- Arc Mortar costs 5 points instead of 6.
- Gunner costs 2 points instead of 4.
- Titan costs 34 points instead of 33.
- The AI now uses Jump Jets and Smoke Launchers.

## 18. Changes in v0.5: the three factions

- The Iron Covenant, Ashen Foundries and Reliquary replace the Companies. Halvorsen's plating
  discount became the Foundries' doctrine and Calloway & Vane's late deployment became the
  Reliquary's. Meridian's free vent is retired, and the Covenant's trait discount is new.
- Nine faction classes replace the Scout, Striker, Bulwark and Titan.
- Each faction has four signature weapons only it can fit. Shear Blade became the Melee Blade,
  Beam Cutter the core-mounted Carapace Gun, Rail Lance the Rail Cannon (7 points), Arc Mortar the
  Rocket Pod (4 points), Impact Hammer the Industrial Claw (5 points), Ion Lance the Arc Cannon
  (now 1 damage, 6 points) and Static Choir the Soul Lantern (5 points). Lance, Hellfire Missiles
  and Kinetic Claws are new.
- Scattergun and Thermal Projector are retired.
- Tuned over 2,000 simulated Trials (see [`balance.md`](balance.md)).

## 19. Changes in v0.6: lighter frames, more room for equipment

Before this pass a class took a third to a half of a lance's budget before any equipment, so
heavy lances had to leave their walkers nearly bare (a 3-Paladin lance cost 102 points with no
weapons) and the Covenant could not field five walkers at all. Class costs fell by 35 to 55%
and the budget stayed at 100 (see [`balance.md`](balance.md)).

| Item | v0.5 | v0.6 |
| --- | --- | --- |
| Lancer / Sentinel / Paladin | 23 / 28 / 34 | 16 / 19 / 22 |
| Scavenger / Brute / Artillery | 12 / 25 / 22 | 6 / 15 / 12 |
| Wraith / Seer / Goliath | 11 / 16 / 33 | 5 / 10 / 20 |
| Lance / Melee Blade | 9 / 8 | 10 / 9 |
| Tactician | 4 | 3 |

- Example lances were rebuilt with fuller loadouts, and a wide and a heavy example were added
  per faction line-up (Vigil Host, Scrap Horde, Twin Colossi).
