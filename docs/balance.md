# Balance report — rules v0.2

Three tuning passes took the example lances from 81% / 23% / 45% to 38% / 63% / 50%. Every
chassis and Company now wins 49–53% of its games.

## How it was measured

`npm run sim -- <games> <seed>` plays AI-vs-AI Trials. The scenarios (Hold the Field, Refinery
Seizure) and maps (Open Field, Foundry Flats) rotate with each game. It runs two things:

- **Example lances:** every ordered pairing of the three example lances, 8 seeds each way.
- **Random lances:** 600 Trials between random legal lances of 3 to 5 war-walkers, each costing
  94 to 100 points. Each chassis, item, trait and Company is credited with the win rate of the
  lances that include it.

With 100 to 600 games behind each figure, differences under about 5 points are noise. Both sides
use the same greedy AI, so these numbers measure the rules as that AI plays them. The AI never
jumps or lays smoke and only repairs itself, so those items will read low.

## Results

| Measure | Baseline (v0.1) | Pass 1 | Pass 2 | v0.2 (pass 3, new seed) |
| --- | --- | --- | --- | --- |
| Calloway Swarm (5 Scouts) | 81% | 72% | 70% | 38% |
| Halvorsen Gun Line | 23% | 17% | 14% | 63% |
| Meridian Lanterns | 45% | 61% | 66% | 50% |
| 3 / 4 / 5 walker lances | 42 / 57 / 49% | 50 / 52 / 48% | 54 / 49 / 49% | 52 / 55 / 43% |
| Chassis range | 50–52% | 49–55% | 49–57% | 49–53% |
| Company range | 46–53% | 50–51% | 49–51% | 50% each |
| Item range | 36–55% | 38–56% | 36–56% | 38–58% |

The Gun Line example was rebuilt in pass 2 (Gyro Stabilisers on both Bulwarks, a Missile Rack
Striker). The other examples only changed to stay within 100 points.

## What changed and why

| Change | Why |
| --- | --- |
| Objectives are held by total chassis Size nearby, not by any presence | Five Scouts could out-hold any heavier lance. This one change evened out lance sizes. |
| Bulwark Stride 1 to 2 | At Stride 1, Bulwark lances could not reach objectives in time, and the Gun Line lost 86% of its games. |
| Titan 32 to 33 pts | The Titan sat at 55–57% across passes. |
| Rail Lance fires after moving at +2 TN, 8 to 7 pts; Gyro removes the penalty, 4 to 3 pts | "Cannot fire after moving" made it 42%. |
| Missile Rack 5 dice, 4 ammo; Arc Mortar 6 pts; Ion Lance 1 Pressure, 3 dice; Beam Cutter Pierce 1; Autocannon 3 pts, 6 ammo | Ranged weapons sat at 39–45% while close-range ones sat at 55%. |
| Scattergun 4, Impact Hammer 5, Shear Blade 6 pts | Close and melee weapons over-performed. |
| Targeting Array 4, Kinetic Shield 3, Overcharged Boiler 2 pts | Each of these sat at 36–43%. |
| Tactician 4, Iron Nerve 2 pts | Weakest traits. |

## Watch list for the next pass

- **Shear Blade (58%) and Brawler (58%):** melee is still strong. The next step is probably 2 dice
  instead of 3, rather than another price rise.
- **5-walker lances (43%):** after the objective change, these may now be slightly too weak.
  Watch for that before touching Scout costs.
- **Arc Mortar (38%) and Spotter Drone (39%):** partly the AI, which doesn't set up indirect
  fire well. Check in human play first.
- **Iron Nerve and Tactician (40%):** the AI rarely benefits from either one.

## v0.3 check (phase 7)

The simulator now uses alternating deployment, plays all four scenarios (including Surveyor
Escort and Twin Wells) and pairs every scenario with every map, Canal Docks included. Earlier
runs always put each scenario on the same map. One 600-game run with `npm run sim -- 600 1`
and no rule changes:

| Measure | v0.2 | v0.3 |
| --- | --- | --- |
| Example lances (Swarm / Gun Line / Lanterns) | 38% / 63% / 50% | 56% / 53% / 41% |
| Chassis range | 49–53% | 49–54% |
| Companies | 50% each | 48–52% |
| Side that deployed first | n/a | 51% |
| 3 / 4 / 5-walker lances | n/a / n/a / 43% | 56% / 50% / 46% |

Surveyor Escort was tuned on its own over 120 games of the example lances (see rules section 16).

New on the watch list: Rail Lance (39%) and Gunner (38%) dropped once the broken-up maps came in.
Shear Blade (56%) and Impact Hammer (55%) are still the strongest items. Melee is still slightly
too good.

## v0.4 pass

Two 600-game rounds with `npm run sim -- 600 1`, using alternating deployment, every scenario
and every map, after the AI learned to use Jump Jets and Smoke.

| Measure | v0.3 | Round 1 | Round 2 (v0.4) |
| --- | --- | --- | --- |
| Rail Lance | 39% | 52% | 47% |
| Gunner | 38% | 52% | 49% |
| Shear Blade | 56% | 56% | 55% |
| Impact Hammer | 55% | 52% | 55% |
| Arc Mortar | 43% | 45% | 44% |
| Titan | 54% | 56% | 49% |
| Chassis range | 49–54% | 48–56% | 49–51% |
| Driver traits range | 38–49% | 44–55% | 47–51% |
| Example lances (Swarm / Gun Line / Lanterns) | 56 / 53 / 41% | 44 / 72 / 34% | 44 / 64 / 42% |

Round 1 changed Rail Lance from 3 to 2 Pressure, Gunner from 4 to 2 points, Shear Blade from 6 to
7, Impact Hammer from 5 to 6 and Arc Mortar from 6 to 5. That fixed Rail Lance and Gunner, but the
Gun Line example, which fields two Rail Lances, jumped to 72%. Round 2 raised Rail Lance to 8 points,
Shear Blade to 8 and the Titan to 34. To stay inside 100 points, the Gun Line's Rivet now carries
an Autocannon in place of the Missile Rack.

Each example lance plays 48 games, so its rate moves by about ±7 points from noise. Items fitted
in fewer than 120 games move by more than ±9.

Watch list for v0.5:
- Kinetic Shield (37%, 112 games) looks weak. The AI rarely banks Pressure for it.
- Melee is still a little strong: Shear Blade and Impact Hammer at 55%.
- The Gun Line example (64%) is still the strongest example lance.
- 5-walker lances are at 46%.
