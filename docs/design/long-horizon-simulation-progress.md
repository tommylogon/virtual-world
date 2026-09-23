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

### Next: schedules, promotion/demotion, and scenario hygiene

These are filed as tasks — see §9 for the current map.

1. **Background schedules / work / coarse social** (task-409) so background
   characters do more than survive.
2. **Promotion/demotion** (task-412) — `trace.summarize_window` builds the LLM
   catch-up summary on promotion; demotion rolls the foreground span into the
   trace (reversibility contract).
3. **Scenario hygiene** (task-408) — reachability is now fixed (30/30, see §7);
   what remains is de-duplicating the 46→23 character nodes, canonical
   way/area ids at authoring time, and giving the scenario a `name`.
4. **Food renewal** (task-410) so a month does not starve the camp.

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
attribute` failures, unrelated): **2879 passing, 0 failures**. The combat suite
has a pre-existing flaky RNG test that can fail intermittently.

The exact total moves with `tests/test_data_no_mojibake.py`, which is
parametrized over every JSON under `data/` — adding or deleting a scenario,
template, or tag file shifts it by one. Compare failures, not the total.

## 7. Open issues

- **Scenario graph ids are still inconsistent.** `tools/repair_way_links.py`
  symmetrized way links and connected Side Tunnels ↔ Water Source, so all **30/30
  areas are reachable** (verified via `include_hidden=True`); the earlier "6
  stranded areas" is resolved. Remaining: way/area endpoints should be canonical
  at authoring time so strict-id pathfinding needs no normalized-name
  compensator.
- **Duplicate character nodes.** The canonical goblin scenario has **46 character
  nodes for 23 players**. 22 are bare-named orphans (0 edges, referenced
  nowhere); the extra is a `player_human_explorer` / `player_player_human_explorer`
  artifact. Raw JSON node **keys do not match their `id` fields**, so dedupe must
  go through `WorldGraph` with an orphan proof, not raw JSON surgery (task-408).
- **The camp's 11 authored triggers are dead data.** They are
  `logic_trigger → area` edges with `event` on the node; the runtime matches
  `trigger_type` on the edge with the owner as source, and nothing flips them at
  load. Folder-authoring must emit the modern shape (task-408).
- **Food is at the edge.** One-week soak survivors average Hunger **84.7**
  (max 100 — starvation end of the drive scale). The camp cannot feed itself
  over a month (task-410).
- Background characters currently only **survive** (eat/drink/sleep); they have
  no schedules, work, or social behavior yet. Soak shows Social 0.1, Sanity 0,
  Hygiene 0, Entertainment 0 (task-409).
- **Cross-zone roaming** remains the hardest seam (see reversibility contract).
- **MCP test failures** are pre-existing and unrelated to this work.

## 8. Performance pass (2026-09-19) — tasks 406, 407

The blocker found by profiling was **not** the LLM: it was trigger/exit
plumbing. Per tick the engine swept all ~106 nodes calling `_execute_triggers`,
which built a full template context *before* checking for a match, and that
context read the legacy `current_area` property — rebuilding an `Area` and its
exits on every access, by scanning all edges and lowercasing every endpoint
(~876 exit rebuilds and ~1M `str.lower()` per tick). The camp has **zero**
tick/time triggers, so all of it was waste.

**Task 406 — trigger dispatch**
- `graph.get_trigger_sources(type)`: event index over `triggers` edges that
  carry a `trigger_type`. `_fire_turn_triggers` / `_fire_time_triggers` now
  iterate only trigger owners, of any node type.
- Standing items (not carried, not lit) now get `on_tick`, once, without
  double-firing the carried/lit paths — the prerequisite for growth triggers.
- `_execute_triggers` fetches edges and type-filters before building context,
  and reads the area by id instead of the `current_area` property.

**Task 407 — graph lookups**
- Edges indexed by lowercased source/target; lookups are O(degree) with no
  per-edge `.lower()`. `_revision` drives cache invalidation; a length check
  lazily rebuilds if external code mutates `edges` directly.
- `build_exits_for_area(include_hidden=True)` cached by revision (authoring path
  only — the game view depends on player discovery state).
- Lighting scan collapsed from two passes to one.

**Measured**
- One-week (10,080-tick) background soak: **9m49s → 17.1 ticks/s, 23/23 alive,
  0 deaths** (was ~6–9 t/s; a week used to be unreachable interactively at
  ~128h of browser-driven wall clock). Trace 4,459; memories 17.
- Full suite: **2831 passing**, 0 failures (the 4-file delta is the mojibake
  parametrization, not coverage).
- Post-fix profile hot spots: `lighting.get_ambient_light` (~33%, now trimmed),
  the call volume of `get_edges_for_target`, background `move_to_area`, and
  `Player.state`. The old trigger/exit cost is gone from the hot path.

**What this does and does not change for playing**
- *Simulating/observing* the world: materially better — weeks are now minutes
  headless, triggers cost nothing when unused, and objects can act over time.
- *Interactive play*: essentially unchanged. The browser still drives one
  character at a time with a hardcoded ~2s step and one `tick_turn` per full
  roster wrap. The 2s sleep is UI pacing, not a rate limit (that is
  `RateLimiter`); it should be configurable and skipped when a step already took
  longer. Making the world playable at speed is **task-414**.

**Second pass (same day) — lighting and edge moves.**
- `get_ambient_light` now uses `max(base, best_item)` instead of
  `min(base + sum_items, max(base, best_item))`. The sum was dead arithmetic the
  ceiling discarded: four torches never out-shone one. Effective light is the
  brightest source, full stop.
- Every area's light is computed **once per tick** (`recompute_area_lights`) and
  read from a stamp, instead of rescanning the room plus neighbours on every
  access. The stamp is keyed to graph revision, and `toggleable_items` /
  burn-out still compute fresh on their own paths.
- `graph.remove_edge` / `remove_edges_for_node` now unindex just the removed
  edges instead of rebuilding every index (trigger edges still rebuild, since
  the trigger index is a set of sources).
- `graph.retarget_edge` added: unequip moves its edge in place (`equipped` →
  `carrying`) instead of remove + add. Take/drop still remove + add, but its
  direct `graph.edges.remove(...)` bypasses were replaced with graph calls.
  **Follow-up:** retarget take/drop placement edges too (task-407 note).

Measured after the second pass: one-week soak **56s → 181 ticks/s** (was 9m49s /
17.1 t/s after the first pass), 23/23 alive, and **identical survivor vitals and
trace count** — behaviour unchanged. Test suite runtime fell 78s → ~25s.

**Third pass — the accumulating cost was the turn-event buffer.**
Profiling early vs late ticks (200 vs 9,500) showed `get_edges_for_target`,
`condition_has_condition`, `get_state`, lighting and temperature all flat, but
`GameLogger.record_turn_event` went 0.086s → 0.987s for the *same* call count.
Cause: it rebuilt the whole `turn_events` list on every append, and a headless
run never calls `clear_turn_events`, so the buffer grew to ~17,000 — O(n²) across
the run. It now prunes only when the turn changes and caps the buffer at 2,000.
After the fix, call counts are flat early vs late (~2% drift) and
`record_turn_event` is out of the hot list. The residual is periodic hourly work
plus host-load variance.

Also in this pass: take/drop capture their placement edge and retarget it
(player on take, room on drop) instead of remove + add, and the capacity/hand
checks now run **before** any mutation, so a failed take can no longer orphan
the item.

## 9. What's left (task map)

| # | Area | What | Status |
|---|---|---|---|
| 406 | triggers | event index, standing-item ticks, lazy context | review |
| 407 | graph | edge indexes, exits cache, lighting pass | review |
| 408 | world | consolidate scenario, dedupe nodes, canonical ids, folders→JSON | todo |
| 409 | characters | background schedules + daily reflection + coarse social | todo |
| 410 | gameplay | plant growth → food renewal, week supply | todo |
| 411 | world | attention budget / fidelity tiers | todo |
| 412 | characters | promotion/demotion + trace→memory consolidation | todo |
| 413 | testing | tick-perf baseline + regression guard | review (`tests/test_perf_guards.py`) |
| 414 | gameplay | server-side `advance(N)` + non-blocking human | todo |
| 415 | ui | long-horizon observer mode | cancelled (deferred) |
