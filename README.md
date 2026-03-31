# HUNTR/X

Hey there! We are **HUNTR/X**, a team of 3, and the **Champions** of the Terminal 2026 hosted by Correlation One in collaboration with Citadel and CitSec!

This repository contains all the algorithms, strategies, and core logic we developed during the course of the tournament.

## Members
* Gurnoor ([@G-Sohal](https://github.com/G-Sohal))
* Swara ([@Swara-IITB](https://github.com/Swara-IITB))
* Archita ([@architabanka](https://github.com/architabanka))

## Takedown
"[Takedown](https://youtu.be/l8Dr7vzMSVE?si=pwWNyydeuIVwy7gm)" is the final algo we submitted (and won the championship with - yahoo!)
### Breaking it down:

**Initial Defences**
We start every game by establishing a highly centralised, upgraded "core" of Supports and Turrets right in the middle of our territory (around rows 11-13). This acts as the anchor for our entire board, keeping our main turrets shielded early on.

**Reactive Defences**
We actively parse the game's action frames to track exactly where the enemy manages to breach our edges. If an opponent scores on a specific x-coordinate, we instantly add that lane to our `breached_lanes` blacklist. On the next turn, Takedown forcefully plugs the hole by deploying a front turret, and eventually a back turret, directly in that lane. You may break through once, but you don't break through twice.

**Greedy Turrets**
Once the core is safe and breaches are plugged, we get greedy. The algorithm blankets the remaining map with turrets in a perfectly spaced grid (every 3 tiles) across the front and back lines. This maximises our damage coverage and starves the enemy of safe paths it can travel on our side

**Offensive Scouting**
We don't blindly spam units. When we have the resources, Takedown randomly samples valid spawn locations and simulates the exact path our units will take to the enemy edge. It calculates the precise turret damage our units will take on every single tile of that path and  picks the spawn location that guarantees the least amount of damage.
If the algorithm detects that the best path is completely walled off by the enemy (landlocked), it automatically pivots to deploying **Demolishers** to bust the door down. Otherwise, we swarm the safest path with **Scouts** only!

---
