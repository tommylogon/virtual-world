# Long-Horizon Simulation — Design & Progress

**Last updated:** 2026-09-19
**Goal:** run the Kraktooth Goblin Camp (and any scenario) for weeks of in-game
time with **every** character a real agent — not 7 minds and 16 mannequins —
while keeping LLM cost proportional to *novelty and attention*, not to time or
population. Then let the user watch it, follow a character, and drop in to
interact.

Related: [[reversibility-contract]], [[trace-format]], tasks 397 (scopes),
399 (background simulation), 403 (unified memory).

---

## 1. The constraint that drives everything

The goblin scenario pins `time_per_tick_minutes = 1`. A week is 10,080 ticks.
With ~23 characters, LLM-per-character-per-tick is ~80,000 calls/week — dead on
arrival. So the design decouples three things that the current engine fuses:

1. **World time** — a cheap 1-minute tick that advances regardless of the player.
2. **Cognition** — LLM calls anchored to events/sequence-boundaries, not ticks.
3. **Fidelity** — only the attended set (anchors + graph-hop radius) runs full
   cognition; everything else runs deterministic background rules.

Non-negotiable decisions:

- **One state model, two decision policies.** Same `Player`, same graph, same
  clock; only the decision source changes. See the reversibility contract.
- **Trace with reasons.** Background actions write an objective fact + why-tag;
  the LLM summarizes the trace into memory (never the reverse).
- **Shared state, not two models.** Promotion is "start asking the character
  instead of their rulebook."

Attention model (borrowed from Star Citizen Quantum's virtualize/physicalize,
with Dwarf Fortress / RimWorld identity continuity): anchors (observed
character, human player, pinned location/item) + a graph-hop radius + a global
cap with deterministic eviction + hysteresis, promoting on approach.

## 2. Phase 0 — Survival (done)

The world could not survive a day: session-scaled drains killed everyone in ~2h.

- **`vital_rates.py`** — single source of truth for per-minute rates (1 tick =
  1 in-game minute). From a full meter: Hunger ~3 weeks, Thirst ~3 days, Energy
  ~16h; Social/Hygiene/Entertainment ~1–2 days; Sanity slow (~14 days).
  `change(player, stat, per_minute)` is the fractional accumulator so sub-1
  rates actually accrue.
- **`engine/tick_manager.py`** — baseline loop + all environmental, temperature,
  social, sanity, bladder, sleep and HP-regen effects routed through
  `vital_rates`. Hunger/Thirst grace+drain retuned so time-to-death lands near
  the 3-week / 3-day targets.
- **`engine/activities.py`** — activity regen rescaled to per-minute.
- **Scenario migration** — `tools/migrate_decay_rates.py` re-bakes per-player
  `decay_rates` (baked rates *override* engine defaults, so calibration was
  invisible without this). Applied to `world_template.json` + the goblin
  scenario.
- **Goblin weather fixed** — the scenario shipped a perpetual blizzard
  (`temperature_mod` to -15) on a green, temperate map, inherited as authored
  content. Replaced with a clear → overcast → rain day cycle.
- **`data/library/traits/high_metabolism.json`** — goblin fast metabolism
  (Hunger ×2, Thirst ×1.5, Energy ×1.3).

### Findings (with evidence)

- Environmental drains (stale air 1/tick, humid Hygiene 1/tick, dark Sanity
  1/tick, cold Energy/HP per tick) dominated and killed in ~2h.
- **The mystery HP drain was temperature, not sanity.** Sanity breakdown
  conditions never drain HP by design; cold does (`core_temp < 33 →
  HP -0.15/min`). Root cause: an authored **snowy gale forecast re-applies every
  tick**, driving effective temperature below 5°C and core temp down. Proved by
  isolating weather (zero HP drops with weather cleared).
- The soak's "neutral environment" was initially invalid because weather
  re-writes area env each tick; the tool now clears forecast too.

### Tooling — `tools/soak_sim.py`

Headless fast-forward with **live progress** (bar, %, game time, ticks/s,
elapsed, ETA, alive/dead, new deaths + causes), projected wall-clock for
day/week/month, survival + cause breakdown, death times, growth
(log/turn_events/graph/memories/trace), survivor vitals, `--debug-hp`
(HP drops with conditions/temp/area/env), `--neutral-environment`,
`--engine-decay`, `--override`, `--set`, `--apply-trait`, `--report`.

**Throughput:** ~6–9 ticks/s with 23 characters → **1 game week ≈ 18–29 min,
1 month ≈ 1.5–2h.**

## 3. Phase 1 — Time engine (partially exists)

Run-N-turns already works, and with no human in the roster nothing blocks the
round. Remaining: a server-side batch `advance` and a non-blocking human
(no-human roster, or a turn timeout). See the recap for the verified mechanics
(2s/step hardcoded, one `tick_turn` per queue wrap).

## 4. Phase 2 — Background tier (in progress)

### Done: the objective trace

- **`engine/trace.py`** — `record / recent / since / summarize_window / rollup /
  load / to_list`. Bounded at 200 entries, salient-first retention, run
  collapsing. No LLM.
- **Integrated** — `Player.trace_log`, `Player.to_dict`, and
  `engine/serialization._deserialize_player` round-trip it.
- **Wired** — need tier crossings (`why="needs:<vital>"`), deaths (`salient`),
  and resolved actions in `apply_action`.
- **Tests** — `tests/test_trace.py` (7). Soak reports trace volume.

This is task-399's "append-only facts log."

### Done (v1): background survival runner

`engine/background_simulation.py` (`BackgroundSimulation.process_due`), wired
into `tick_turn()` after `process_simple_npcs`. Characters with
`simulation_mode == "background"` are considered only when due
(`next_due_tick`, deterministic jittered interval), and make one coarse
decision against shared state:

- **drink** when Thirst ≥ 55 — either from a water-tagged **area** (natural
  water is an area tag, not an item) or a drink item, else travel toward one;
- **eat** when Hunger ≥ 55 from a reachable food item;
- **sleep** when Energy ≤ 30, or ≤ 15 regardless (critical exhaustion wins);
- **travel** one hop toward the nearest reachable resource area.

Every decision writes a trace entry with a reason tag. `simulation_mode` and
`next_due_tick` are serialized. A 2-day, 23-character soak went from **3/23
alive → 22/23** after the priority fix. Tests: `tests/test_background_simulation.py`.

### Next: schedules, promotion/demotion, and a data repair

1. **Scenario graph repair** (blocker) — see Open issues: 6 areas can't reach
   any resource, and way edges reference sanitized area ids.
2. Promotion/demotion — `trace.summarize_window` builds the LLM catch-up
   summary on promotion; demotion rolls the foreground span into the trace
   (reversibility contract).
3. Schedules/work so background characters do more than survive.

## 5. Files touched this pass

| File | Change |
|---|---|
| `vital_rates.py` | **new** — canonical per-minute rates + `change()` |
| `player.py` | decay defaults from `vital_rates`; `trace_log` + serialization |
| `virtual_world_engine.py` | `baseline_decay` from `vital_rates` |
| `engine/tick_manager.py` | all drains → per-minute; trace on needs/death/act |
| `engine/activities.py` | per-minute activity regen |
| `engine/trace.py` | **new** — trace store |
| `engine/serialization.py` | restore `trace` |
| `data/library/traits/high_metabolism.json` | **new** goblin metabolism trait |
| `data/scenarios/kraktooth_goblin_camp.json` | temperate forecast; decay_rates |
| `world_template.json` | decay_rates migrated |
| `tools/soak_sim.py` | **new/expanded** — reporting, debug, isolation |
| `tools/migrate_decay_rates.py` | **new** — rate migration |
| `tests/test_trace.py` | **new**; `test_activities.py`, `test_social_company.py` updated to per-minute |
| `docs/design/reversibility-contract.md`, `docs/design/trace-format.md` | **new** contracts |

## 6. Test status

Full suite excluding `test_mcp_*` (pre-existing `'function' object has no
attribute` failures, unrelated): **2835 passing, 0 failures**. (The combat
suite has a pre-existing flaky RNG test that fails intermittently.)

## 7. Open issues

- **Scenario graph is fragmented and mis-id'd.** Way edges reference sanitized
  area ids (`area_chiefs_pit`) while area node ids keep the punctuation
  (`area_chief's_pit`), so strict-id pathfinding returns None from most areas.
  A normalized-name navigator now compensates inside the background runner, but
  **6 of 30 areas still cannot reach any water source**: Abandoned Farm, Animal
  Pens, Blackmarsh, Mine Access, Side Tunnels, Storage Caves. Characters there
  will die of thirst regardless of behavior. This is a scenario data repair
  (fix way endpoints and/or link/tag the stranded areas), not engine logic.
- Background characters currently only **survive** (eat/drink/sleep); they have
  no schedules, work, or social behavior yet.
- **Social/Entertainment** can still bottom out for isolated characters within
  ~12h; expected to be fed by Phase 2 behaviors rather than tuned further.
- **Cross-zone roaming** remains the hardest seam (see reversibility contract).
- **MCP test failures** are pre-existing and unrelated to this work.
