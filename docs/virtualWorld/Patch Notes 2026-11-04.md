---
type: doc
tags: [surface/docs]
---

# Calls, Currents & Cradles - 4 November 2026

A batch of seven backlog cards moved to review. Two add new ways to move and talk (swimming, long-distance calls), two make characters more aware of their own lives (editable schedules in the prompt, followable pursuits), one adds pregnancy and birth to the lifecycle clock, and two are tooling and verification.

---

## Long-distance communication

Carried devices can now relay speech across the map.

- `call <contact>`, `answer` and `hangup` drive phone calls. Walkie-talkies and radios are tuned with `use`.
- A device must be powered: a `uses` counter, or a battery child part.
- Speakerphone calls are audible to people standing nearby.
- An active call applies the new `on_a_call` condition.
- New library items: `walkie_talkie`, `radio_battery`; `phone` gained the `use` action.

## Swimming and diving

- `swim <direction>` and `dive <direction>` cross ways that `require` them, rolling Athletics against `swim_dc` / `dive_dc`.
- New `Air` vital (default 100). Submerged characters lose 20 per tick; at 0 the existing `suffocating` condition applies. At the surface Air refills 50 per tick.
- Background and soak characters can use both verbs.

## Characters see and edit their own day

- The agent turn prompt now shows the complete schedule, marks the current step, and teaches `schedule`, `schedule add HH:MM <activity> [at <area>]` and `schedule remove HH:MM`. `schedule` is listed in available actions.
- A character with an assigned pursuit now gets it as its followable plan: the plan tracker is seeded from the server plan, the undertaking reason appears under `=== YOUR PLAN ===`, and a pursuit plan no longer ages out after 10 turns.

## Pregnancy, gestation and birth

- Conception requires an adult life stage, compatible biological sexes, and willingness (no unwilling flag, no pregnancy-related boundary, no negative consent).
- Gestation is one bounded record per character that advances with the sim clock through three trimesters.
- Birth creates a real child character at the mother's location with a `birth_tick` and parent relationships. Pregnancy survives save and reload.
- Conception is reachable via trigger effects (`attempt_conception`) and autonomous intimate flirt interactions in mature-enabled worlds.

## Reproductive cycles, periods and going into heat

- Species table (`SPECIES_CYCLES`) declares the reproductive pattern: `cycle` (human, elf, dwarf), `heat` (goblin, wolf, frog, beasts), or `none` (undead, constructs, plants).
- Cycle state (`Player.reproductive_cycle`) advances on clock ticks in `lifecycle.on_clock`.
- Phases apply and clear conditions via the standard condition catalog (`menstruating`, `ovulating`, `in_heat`) with zero custom prompt or status bloat.
- Fertile window gates `pregnancy.is_fertile`: cycling species can only conceive when ovulating or in heat; species with `pattern: "none"` preserve baseline stage rules.
- Pregnancy suspends active cycles; birth resumes from day 1.
- In-heat drive raises flirt action weights in background social interactions without ever bypassing consent, willingness, or boundaries.
- Character Inspector Mind, Persona, and Bio views display cycle phase, day, and fertility badges.

## Plan executor runtime (Task-702)

- Unified typed plan runner in `engine/plan_executor.py` handles execution of grounded step sequences (`travel`, `take`, `drop`, `activity`, `wait`).
- Grounded preconditions checked before each step; failures abort execution cleanly with descriptive reason rather than desyncing or hanging.
- Preempted by critical physiological needs (Hunger >= 80, Thirst >= 80, Exhaustion >= 90) before next action is committed.
- Interrupted activities trigger cleanup; completed plans clear active pursuit and plan state on the player.

## Recipe station bindings and craft feedback (Task-703)

- Crafting and cooking actions now emit full missing ingredients lists on failure (e.g. "You are missing: raw_egg, butter.") rather than failing silently or with partial info.
- Spatial station binding adds transient `(player, station, "at")` edge in the world graph during execution, allowing station-bound activities to be perceived in-place.
- Transient spatial relations are cleaned up automatically in `end_activity` on completion or interruption.
- Area node name collision prevention: station fixture lookups explicitly exclude area nodes sharing fixture names.

## MOSIAC pursuit selector (Task-704)

- Grounded choice step in `engine/mosiac_selector.py` evaluates candidate pursuits against active goals.
- Goals prioritized with 1-is-highest priority semantics and opened tick ordering.
- Goal alignment scores candidate steps against active goal achievement references (items, presence, area, tag, synonyms).
- Parameters grounded against library schemas (`meal`, `rally`, `gather`, `haul`, `sleep-at-venue`, `fish-and-bring-home`, `scout-and-report`).
- Rejection is an explicit choice: characters can decline pursuits without penalty; declines reset on schedule cycle boundary.

## Daily reflection and goal mutation (Task-409)

- `engine/daily_reflection.py` runs once per in-game day per character to summarize recent memories, active goals, vitals, and relationships.
- Deepens memories with reflection records (`reflection_depth: 1`, `type: "reflection"`).
- Mutates and reprioritizes GIMP active goals via `engine.goals.set_status` and priority shifts.
- Bounded and gated: leaves simulation unchanged if no local provider is configured; persists `last_reflection_day` across saves.

## Terrain hazards compiler (Task-747)

- `engine/hazards.py` and `engine/world_compile.py` compile painted layer hazards into authoritative simulation triggers.
- Water crossings without bridges emit `river` hazards with water current strength and bearing.
- Water crossings requiring jump emit `on_fail_jump` river hazards into the water.
- Steep storey drops emit `cliff` and `fall` hazards scaling with storey delta.
- Painted bramble, briar, and thorn vegetation emit `thorns` enter hazards.

## Large-world projection & indexing benchmark (Task-402)

- `tools/benchmark_scale.py` benchmarks hierarchical world scopes from 11k to 107,541 nodes across world, settlement, building, room, and item layers.
- Scoped payload bounds verified: child scopes transfer < 0.2% of full-world payloads (146 nodes vs 2,364 in Kraktooth).
- Index lookup vs full-world scan verified: 0.023ms index lookup vs 20.68ms linear scan.

## Chunk persistence & gateway ways (Task-401)

- Four sub-tasks (581, 582, 583, 584) and task-402 verified end-to-end for chunk lifecycle, stable area IDs, and gateway ways.
- `tests/test_chunk_lifecycle.py` passes all 5 tests verifying boundary traversals, scoped eviction, dirty persistence, and gateway ways.

## Child-scope procedural generators & corner doors (Task-884)

- Pluggable generators in `engine/scope_generators/` for settlement (central square, arterial avenues, zoned lots), ruin/dungeon (MST corridor routing, dwarven chambers, catastrophe filters), and wilderness (sinuous river carving, elevation gradients).
- Markov transition matrix in `data/worldpainter/adjacency.json` and `engine/world_adjacencies.py` with `suggest_buffer` and `feather_seam`.
- 19 dwarven subterranean library biomes added in `data/library/biomes/`.
- 45-degree chamfered corner doors supported in `engine/world_compile.py` guarded by solid wall flanking checks.

## Area naming pass & bridge disambiguation (Task-638)

- `engine/world_compile.py` emits human-readable `display_name` on compiled area properties.
- Way `pass_message` strips internal grid coordinate suffixes (`_GRID_SUFFIX`) so coordinates never leak into player-facing prose.
- Authoring pass on `data/scenarios/kraktooth_goblin_camp.json`: 10 repeated bridge locations carry distinct contextual `display_name` properties, preventing ambiguous lookups.

## Server-side batch time advance (Task-414)

- `POST /api/world/advance` advances simulated world time in batch accepting either `ticks: N` or `minutes: N`.
- Runs via `timeskip.advance_world` with day-sized chunking and live tick streaming (`_publish_tick`) to prevent request timeouts.
- Guarded with `_timeskip_busy` 409 conflict checks.

## Turn order source of truth and modes (Task-437)

- `engine/turn_order.py`: Created `TurnOrderResolver` supporting four engine-authoritative modes: `sequential` (canonical character ID order), `random` (deterministic seeded shuffle per round), `initiative` (d20 + DEX modifier), and `simultaneous` (order-invariant commit).
- `VirtualWorld` owns the resolver and exposes `get_turn_order()`, `get_turn_order_ids()`, and `get_turn_order_info()`.
- Synchronized with `BackgroundSimulation.process_due()` and `NpcBehaviors.process_simple_npcs()`.
- Registered `GET /api/turn/order` and `POST /api/turn/order` routes.
- `turn-queue.ts`: Updated client queue to adopt server-authoritative turn order on initialization and advance.

## Timeskip follow-ups: leisure vendors & explore frontier (Task-482)

- Long spans up to `timeskip.MAX_MINUTES` (10,080 minutes / 1 week) run in day-sized chunks with merged results.
- Vendor leisure buying: characters with leisure intent at a merchant or shop buy valid portable items, transferring coin if carried, moving the item to the buyer's inventory, and recording the purchase in lived log and turn events.
- Added `"buy"` venue definition in `engine/venues.py`.
- Explore frontier preference: `_explore_step` detects and prioritizes exits leading to newly materialized areas, unmade scopes, or generated scope frontiers, recording destination and frontier progress in lived log and turn events.

## Area grids, movement costs & A* pathfinding (Task-99)

- `engine/pathfinding.py`: Created A* pathfinding over intra-area grids supporting per-tile costs (`floor: 1`, `water: 2`, `rubble: 3`, `wall: 99`), impassable blocking, 4-neighborhood with optional diagonals, path cost calculation, and adjacent cell navigation.
- `area.py`: Extended `Area` class with `grid=None` field.
- `engine/movement.py`: Added `get_area_grid()`, `set_area_grid()`, `move_to_coord()` and `move_to_item()` handlers deducting Energy costs and updating character/item cell coordinates.
- `virtual_world_engine.py`: Exposed `move_to_coord()`, `move_to_item()`, `get_area_grid()`, and `set_area_grid()`.
- `engine/npc_behaviors.py`: Wired `execute_go_action()` for intra-area navigation.
- `routes/action_handlers.py`: Added `move_to [x] [y]` and `move_to [item]` CLI command handling.
- `static/js/inspector/area-view.ts`: Added `_renderAreaGridSection()` for interactive micro-positioning visualization.

## Tooling

- `tools/drive_sim.py` is a checked-in HTTP driver for stepped integration runs: tick stepping, state sampling, vital freezing, stop-on-arrival, JSONL telemetry. It replaces the ad-hoc PowerShell scripts. Usage is documented in the Background Simulation note.
- Simultaneous mode v2 (async per-character cooldown timers, startup talkativeness, mention fast-tracking, burst governor) was already implemented; its card was verified against 24 passing Commons agent tests and moved to review.

## Verification status

Unit and engine tests: `test_long_distance_comms` (10), `test_swimming_and_diving` (5), `test_schedule` (43), `test_pregnancy` (7), `test_reproductive_cycle` (8), `test_background_social` (29), `test_drive_sim` (4), `test_plan_executor` (5), `test_recipe_activity` (5), `test_crafting` (28), `test_mosiac_selector` (5), `test_daily_reflection` (4), `test_compiled_hazards` (7), `test_world_projection_benchmark` (3), `test_chunk_lifecycle` (5), `test_world_adjacencies` (5), `test_scope_generators` (4), `test_area_names` (3), `test_world_compile` (119), plus targeted node suites for the prompt changes and TypeScript compilation (`npm run build:ts`). No live LLM turn was run for the schedule or pursuit prompts, and none of these were exercised in the browser.
