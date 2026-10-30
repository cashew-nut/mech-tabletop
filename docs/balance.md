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
use the same greedy AI, so these numbers measure the rules as that AI plays them. The AI rarely
jumps, never lays smoke, and only repairs itself, so those items will read low.

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
