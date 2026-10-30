# Brass Charter — Core Rules v0.1

> Draft for playtesting. Numbers will change. All chassis and equipment stats live in
> [`data/`](../data) and are the source of truth; tables here are for reading convenience.

## 1. The setting in one paragraph

The galaxy is carved up by the Chartered Companies, trading dynasties that own whole star
systems. They settle disputes over worlds and trade lanes by **Charter Trial**: a legally
binding battle between small lances of war-walkers. Centuries ago the **Quieting** burned out
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
| War-walker | A mech. Each one is built from a chassis plus equipment. |
| Driver | The pilot of a war-walker. Has a Command value and up to one trait. |
| Lance | Your force: 3 to 5 war-walkers, 100 points by default. |
| Pressure | The points a war-walker spends during its activation. |
| Boiler rating | How much Pressure a chassis builds each activation. |
| Overpressure | Stress tokens. Too many cause Faults. |
| Reserve | Pressure held back to use outside your activation. |
| Target number (TN) | The number each attack die must equal or beat to hit. |

## 4. Building a lance

1. Pick a Company (section 12). Its doctrine applies to your whole lance.
2. Pick 3 to 5 war-walkers. For each, pick a chassis and fill its slots with equipment.
3. Give each war-walker a Driver: Command 0, 1 or 2 (0, 2 or 4 points) and optionally one trait.
4. The total of chassis, equipment and Driver costs must not exceed the Trial budget (100).

**Slots.** Each chassis has two arms, a core and legs, each with a number of slots. An item
uses as many slots as listed and must fit in one location: a 2-slot weapon needs an arm with
2 free slots. Items list which locations they may use (`arm`, `core`, `legs`, or `any`).

**Limits.** At most one Targeting Array per war-walker. Fitting two or more Ablative Plating on
one war-walker gives it -1 Stride.

## 5. Setting up

1. Pick a scenario (section 11) and place terrain and objectives as it says.
2. Each side rolls a d6; the higher roll picks a deployment edge. The other side deploys first.
3. Sides alternate placing one war-walker at a time anywhere within 3 hexes of their edge,
   facing any hexside.

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

Overpressure comes from Opening the Throttle, Thermal Projector hits, some items and some
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

An objective is **held** by a side that has a war-walker on or adjacent to it while the other
side does not. Prone war-walkers still count.

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
| Surveyor Escort (not yet in the engine) | The attacker's surveyor token starts in their deployment zone. | The surveyor moves 2 hexes when a friendly war-walker adjacent to it spends 1 Pressure. The attacker scores 6 VP if it leaves the far edge. Destroying it (3 hits at TN 4, no armour) gives the defender 4 VP. No objectives. |

## 12. Companies

| Company | Specialty | Doctrine |
| --- | --- | --- |
| Halvorsen Ironworks | Heavy industry | Ablative Plating costs 1 point less. |
| Meridian Lantern Company | Aether refining | Once per round, one war-walker may remove 1 Overpressure for free at the start of its activation. |
| Calloway & Vane Surveyors | Scouting and mapping | Deploy one war-walker after the enemy has finished deploying (not yet in the engine). Spotter Drones cost 1 point less. |

## 13. Reference: chassis

| Chassis | Size | Pts | Stride | Boiler | Slots (arm / core / legs) | Armour (core front / rear / arm / legs) | Structure (core / other) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Scout | 1 | 12 | 3 | 4 | 1 / 1 / 1 | 4 / 2 / 2 / 3 | 3 / 2 |
| Striker | 2 | 18 | 2 | 5 | 2 / 2 / 1 | 6 / 3 / 3 / 4 | 4 / 3 |
| Bulwark | 3 | 25 | 1 | 6 | 2 / 3 / 1 | 8 / 4 / 4 / 5 | 5 / 4 |
| Titan | 4 | 32 | 1 | 7 | 3 / 3 / 2 | 10 / 5 / 5 / 6 | 6 / 5 |

Equipment and Driver traits are listed in [`data/equipment.json`](../data/equipment.json) and
[`data/drivers.json`](../data/drivers.json).

## 14. Open questions for playtesting

- Is Stride 1 too slow for Bulwark and Titan, or does their bigger boiler make up for it?
- Does passing once per round balance a 3-walker lance against a 5-walker lance?
- Is the Rail Lance's "cannot fire after moving" too punishing without Gyro Stabilisers?
- Should Reserve be capped at 1 instead of 2?
