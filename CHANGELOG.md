# Changelog

All notable changes to VirtualWorld. See `docs/virtualWorld/Scenario Workflows & UI Audit.md` for the long-term plan this release follows.

---

## Unreleased — "One Copy of Every Truth" (2026-09-20 → 09-21)

A saved world was carrying the same facts three times over, the natural-language
editor was quietly discarding failed edits while burning its entire context, and
a locked door was treated as more soundproof than a closed one. This pass makes
the graph the single source of truth, gives the NL editor an honest ledger, and
fixes the two bugs that stopped a saved background map from ever coming back.

### 🗃 Scenario files are graph-only — 28% smaller
A saved scenario held `areas`, `rooms` **and** `graph.nodes`, all describing the
same world. `rooms` was a byte-identical duplicate of `areas` (the same dict
assigned to two keys), and every `areas` entry carried a verbatim copy of its
node's `properties`, plus `ambient_light`/`light_description` recomputed each tick
and an `items` list that was always empty. Every remaining field was audited:
**nothing in `areas` was unique** — `name` is `node.name`, and
`description`/`environment`/`floor` are `node.properties`.

- **`to_scenario_dict()` no longer writes** `areas`, `rooms`, `ways` or
  `item_registry`. The goblin camp drops **455,567 → 322,407 bytes (−28%, ~131 KB)**
  with identical reload behaviour (31 areas, 23 players, descriptions intact).
- **…but the live payload keeps them.** ~20 frontend call sites read
  `worldState.areas` (agent-engine, agent-lens, inspector, item-library/placement,
  graph/layout-engine), so the projection stays in `/api/state` and only the *file*
  is stripped. `tests/test_scenario_graph_only.py` locks both directions so a
  future tidy-up cannot collapse the wrong one.
- **The Changes panel now reads areas from the graph**, exactly as it already did
  for items and ways — areas had simply never been migrated. Its fingerprint also
  drops `exits`, which every written payload strips: that made it a constant on
  the live side and a false "changed" for any older file still carrying a copy.
- **`_scenario_name` round-trips again.** Every save dropped it, so a restored file
  was "unnamed" — and because the name is what keys the local background-map cache,
  that single omission made a saved map unloadable. An empty name is now omitted
  rather than written as `""`, which `data.get(...) or ...` reads as "unnamed" and
  would let it outrank a real name.

### 🧠 The NL editor needed an honest ledger
- **A partially-failed Apply threw away the failures.** `/api/graph/batch` answers
  `207 partial` with `applied[]`/`errors[]`; the editor showed the errors and then
  cleared *every* op it had sent, so edits that never applied vanished with no way
  to retry. Only ops the server reports as applied are cleared now, and the toast
  says how many are still staged. A regression harness drives the real
  `StagingBuffer` through success / partial / total-failure / selective-apply and
  both replay paths (23 checks).
- **Context pruning had disabled itself.** `prune()` reset the counters it then
  guarded on, so the next call handed back the *entire* transcript: at iteration 90
  the model received **179 messages** while the tracker claimed ~1,004 tokens, and
  `overLimit` read false forever. Metadata is now keyed by message identity instead
  of array position, the window is measured from the array actually being sent, and
  critical retention is bounded newest-first. The same loop now sends **29**.
- **The `[Summary: N earlier turns omitted]` marker never fired** — it was gated on
  index 0 being dropped, but index 0 is the system prompt and always kept, so
  dropped turns disappeared with no signal to the model.
- **Errors were invisible.** `turn:end` fires from `finally` and reset the badge to
  "Ready" immediately after the error handler set "Error", and the message was
  never rendered in the chat. Both fixed, plus the hardcoded `round x/10` label
  that the 100-round cap had made a lie.
- **The ghost preview never panned for spawns** — the spotlight looked up
  `nlghost_<parent_id>` while the ghost was created as `nlghost_spawn_<op_id>`.
- **`get_background_map`** tool added, so the agent knows a reference map exists
  (path, transform, opacity, lock) without pretending it can see the pixels. The
  catalog is **24 tools**; the header claimed 20 and was already wrong at 23.

### 🔊 A lock is not soundproofing
`get_way_barrier`'s own contract treats closed/blocked/locked as one "solid state"
for a per-door `sound_barrier` override, but the defaults disagreed: a locked door
blocked **2** where a closed one blocked **1**. A lock is a latch on a door that is
already closed, so `sound.way_locked` and `sound.way_blocked` are now **1**
(`hidden` stays 2). Behaviour change: a shout carries through a locked door, and a
scream carries through an open+closed+locked chain — the loudest channel is no
longer stopped by a latch. The value was duplicated in four places, including a JS
mirror in `turn-feed.js` that would otherwise have disagreed with the engine.

### 🗺 …and why the background map would not come back
Two defects, both upstream of the image itself:
- **The scenario name never reached the client.** `_serialize_world()` omitted
  `_scenario_name`, so `/api/state` never carried it and the client only knew the
  name if it had set it that session. `graph-background.js:_scenarioIdentity()`
  returns `null` without a name, and the local cache is consulted only for a named
  scenario — so a locally-held map was **never** restored.
- **The two "which scenario am I" functions disagreed.** `_scenarioKey()` accepted
  the `body.dataset.scenarioName` fallback that Save/Export Scenario writes;
  `_scenarioIdentity()` did not. The key is now derived from the identity, so they
  cannot diverge.

### ⏱ Vital decay now scales with the tick's game time
Every rate in `vital_rates` is *per in-game minute*, but `time_per_tick_minutes`
is settable per scenario and live from Engine Config — and nothing multiplied by
it. A tick applied one minute's worth of decay no matter how many minutes it
covered, so the clock and the meters disagreed silently the moment the tick
stopped being a minute.

- **`vital_rates.change()` takes `minutes`**, and `tick_minutes(world)` is the one
  place that reads `time_per_tick_minutes` (tolerating junk: `0`, `None` and
  `"nonsense"` all fall back to 1, and a negative sign is treated as a typo).
  `TickManager._decay()` routes every per-minute effect through it.
- **The baseline loop uses the same accumulator as everything else.** It had its
  own `_decay_accum` separate from `change()`'s `_rate_accum` — two parallel
  implementations of the same idea, and a second source of truth per meter.
- **The starvation grace is counted in minutes, not ticks.** It is a wall-clock
  reprieve (360 min of hunger, 60 min of thirst); counted in ticks, a 15-minute
  world would have stretched the 1-hour thirst grace into 15 hours. Damage past
  the grace scales with the tick too (0.5 HP/min × 15 = 7.5 HP).
- **`soak_sim.py`'s `TICKS_PER_DAY` was hardcoded to 1440** "at
  time_per_tick_minutes == 1", so the day/week/month projections lied by exactly
  the tick-length factor while `fmt_span` printed the real spans.

Consequences worth knowing: the **boot `world_template.json` runs at 5
min/tick**, so decay in the default world was running **5× too slow** (the
kraktooth campaign pins 1, so its soak numbers are unaffected). The pleasure
meters (`Arousal`/`Stimulation`/`Pleasure`) are in `baseline_decay` and were
marked *"still per-tick; not yet folded into the per-minute scale"* — they are
now folded in, so they drain 5× per tick in a 5-minute world and may want
re-tuning. `tests/test_tick_time_scaling.py` covers the invariant (equal game
time, equal decay, at 1/5/15-minute ticks); the pleasure and Social-company
suites pin a one-minute tick because they assert per-minute calibration.

### 🎟 Background decisions are paced in game minutes, not ticks
Decay was only half the story. `engine/background_simulation.py` gated
decisions on `DECISION_INTERVAL = 10` **ticks**, so at 15 min/tick a character
decided every 150 minutes instead of every 10 and got a fifteenth as many
decisions per game hour. A week soak at 15 min/tick killed everyone of
exhaustion inside a day at first, then 3/23 once decay was scaled — with food
in reach.

- **Action credit replaces the tick interval.** Credit accrues at
  `time_per_tick_minutes / DECISION_MINUTES` (10) and is spent one decision at
  a time, capped at `MAX_ACTIONS_PER_TICK` (4). A busy or unconscious character
  neither decides nor banks credit, so a long sleep cannot leave a backlog to
  dump on waking. First sighting acts at once, and an explicit future
  `next_due_tick` from a save or tool still defers.
- **Measured invariant:** over the same 1,440 game minutes, 1 min/tick gives
  78.2 decisions/hour and 15 min/tick gives 78.0 — identical within noise,
  where it used to be 15x apart.
- **Body-temperature drift is scaled too.** `drift`/`converge_rate` were
  per-tick while the cold/heat damage they feed was per-minute, so a 15-minute
  tick spent 15 minutes taking band damage per 1 minute of *leaving* the band.
  That was killing poorly-sheltered and cold-blooded characters (Croak-Mother
  in Blackmarsh at 8h15m). Fixed, and the death is gone.
- **`soak_sim.py` gains `--minutes-per-tick`** (it previously only read the
  value from the scenario, so the one thing worth tuning was the one thing you
  could not vary) **and `--mature`**. Both the camp scenario and
  `world_template.json` ship `mature_content: false`, and with it off
  `sync_pleasure_vitals` *strips* Arousal/Stimulation/Pleasure and their decay
  rates — so every soak so far ran a world missing that whole subsystem. With
  `--mature` the sweep is unchanged (those meters start at 0 and do not feed
  survival, and background characters never trip the cascade), but the run is
  now the real world. Worth deciding whether the camp *should* ship it off: the
  players carry `body_state`/`region_exposed` data that implies otherwise.

Week soak, `--background-all`, same game week: **1 min/tick 23/23 alive**;
**15 min/tick 21/23** in 9s instead of 70s, the two deaths being starvation at
6d14h+ — the known finite-food issue (task-410), not the tick length. The
1-minute result is unchanged, which is the point: `×1` scaling is a no-op.

A tick-length sweep over the same game week is flat until the step gets
coarse — **23/23 alive at 1, 2 and 5 min/tick**, then 21–22/23 at 15/30/60. The
death is the *same character* (Silver-Talon) at every coarse step and the whole
camp's food is consumed either way, so the tail is the finite-food problem
(task-410), not the time scaling: at 1 min/tick the hungriest three end the
week at Hunger 100 *alive*. Use ≤5 min/tick when tuning rates.

### ⏳ Condition durations are game minutes
`player.py` documented `duration = ticks remaining` and
`engine/conditions.py` counted one down per tick, so a 5-minute `unconscious`
lasted **75 game minutes** in a 15-minute world, `satisfied` 5 hours and
`sensitized` 150 minutes.

- **Durations and condition `periodic` drains are per game minute.**
  `process_tick` counts down by the tick's minutes and routes periodics through
  `vital_rates.change(..., minutes=…)`, so sub-1 periodics also stop truncating
  to nothing (they were written straight into `vitals` before).
- **`get_active_conditions` reports `minutes_remaining`** rather than
  `ticks_remaining` — nothing consumed the old key.
- **Save compatibility:** instances store a bare number, so a save written at
  1 min/tick is byte-identical in meaning; at a longer tick an old value now
  reads as minutes, which is the correct interpretation.
- Verified: a 10-minute condition expires after 10 / 2 / 1 ticks at 1 / 5 / 10
  minutes per tick (`tests/test_tick_time_scaling.py`).

Re-running the sweep after this changed nothing (same deaths, same identities),
which is the expected negative result: it confirms the remaining soak deaths are
food-limited rather than a residue of tick-quantised time.

Still tick-quantised and not yet converted: `npc_behaviors.npc_action_interval`
(a second, older action scheduler).

### 🧾 Character memories are no longer capped at 200
`player.add_memory` silently dropped the **oldest** memory once a character
passed 200 — a cap nobody chose, and FIFO, so a busy week of generated events
would have pushed the hand-written backstory out first.

- The cap is now `memory.max_per_character` (Engine Config → memory, default
  **0 = unlimited**), read at call time like every other engine setting.
- When a limit *is* set, eviction skips `source: "manual"` memories, so authored
  backstory is the last thing to go rather than the first.
- Verified: 600 generated memories all retained by default; with a cap of 50 the
  total trims to 50 and **all 10 authored memories survive**.

This matters for the background social work (task-423): at the measured decision
rate a character accrues ~2–4 memories per game hour, which would have started
evicting the authored past after roughly three game days.

### 🔗 Relationships fade when nobody maintains them
Closeness only ever moved on an event: `last_interaction_tick` was written in
five places and **read in none**, so a pair that never met again kept its value
forever and a week of simulation could only ratchet.

- **`Player.decay_relationships()`** eases closeness toward 0 by elapsed game
  days, driven from the tick loop **once per game day** — so a 1-minute world and
  a 15-minute one drift identically, and the cost is daily rather than 23
  characters × N relationships every tick.
- **Safe on authored data, deliberately.** The step can never cross zero, shared
  history damps the rate through `interaction_count` (the same counter that feeds
  `derive.familiarity`, so six prior interactions roughly halve the drift), and an
  authored `label` ("my brother") is a *declaration* rather than a measurement, so
  it is never touched — only the computed closeness moves.
- Sub-1 daily steps accumulate per relationship the way vitals do; a 0.5/day rate
  would otherwise round to nothing every day.
- Tunable at `relationship.decay_per_day` (Engine Config → relationship, default
  0.5). Verified tick-length independent: 3 days at 1 min/tick and at 15 min/tick
  land on the same closeness.

### 🏷 Scenarios name themselves from the filename
A blank `_scenario_name` is the failure mode that made saves land as "unnamed"
and left the frontend's local background-map cache unreachable, since
`_scenarioIdentity()` keys off the name. `world.set_scenario_source(path)` is now
the one place that keeps source and name consistent: it derives the name from the
filename stem when the world has none, never overwrites an existing name, and
`None` clears the source only. All seven path-bearing assignments route through it.
`_scenario_name` is also initialised in `VirtualWorld.__init__` instead of only
appearing once something set it.

### 📋 Filed for next
`task-416` area-major tick iteration · `task-417` co-presence gate for coarse
meetings (amends `task-409 §4`, which would otherwise pair characters on opposite
sides of the map) · `task-418` awareness channels replacing `radius_hops` ·
`task-419` one `at` per character + anchor budget · `task-420` a single
relationship write path · `task-421` light barrier parity with sound · `task-422`
NL editor budget controls; `bug-36` `moveNode` called for absent nodes.

---

## Unreleased — "Long-horizon simulation: Phase 0 + trace" (2026-09-19 → 09-20)

Groundwork for running a scenario for weeks of in-game time with every
character a real agent. Two things made that impossible: vitals were still on
session timescales outside the drives (environment/regen/comfort vitals killed
everyone in ~2 hours), and there was no objective record of what a background
character did. See `docs/design/long-horizon-simulation-progress.md`.

### ⏳ Vitals on a true per-minute scale
- **`vital_rates.py`** — new single source of truth for per-minute rates (1 tick
  = 1 in-game minute). From a full meter: Hunger ~3 weeks, Thirst ~3 days, Energy
  ~16h; Social/Hygiene/Entertainment ~1–2 days; Sanity ~14 days. `change()` is a
  fractional accumulator so sub-1 rates actually accrue.
- **All environmental/temperature/social/sanity/bladder/sleep/HP-regen effects**
  in `engine/tick_manager.py` routed through it and rescaled; `engine/activities.py`
  activity regen rescaled too. Cold/heat now measured per minute, heat correctly
  *raises* Thirst (drive), and HP regen no longer outpaces starvation.
- **`tools/migrate_decay_rates.py`** — new: re-bakes per-player `decay_rates`
  (baked rates override engine defaults, so the calibration was otherwise
  invisible). Applied to `world_template.json` and the goblin scenario.
- **`data/library/traits/high_metabolism.json`** — new goblin trait (Hunger ×2,
  Thirst ×1.5, Energy ×1.3).

### 🧾 Objective character trace (task-399 foundation)
- **`engine/trace.py`** — new append-only, code-written history per character:
  `record / recent / since / summarize_window / rollup / load / to_list`, capped
  at 200 entries with salient-first retention. Wired into need tier crossings
  (`why="needs:*"`), deaths (salient), and resolved actions. Round-trips through
  `Player.to_dict` / `_deserialize_player`.
- **Design contracts** — `docs/design/reversibility-contract.md` (one state
  model, two decision policies; what must stay live while backgrounded) and
  `docs/design/trace-format.md` (entry schema, kinds, reason tags, trace→memory).

### 🌦 Scenario fixes
- **Kraktooth forecast** rewritten from a perpetual blizzard (`temperature_mod`
  -15, light -12) to a clear → overcast → rain day cycle. The frozen baseline was
  killing every exterior character with hypothermia within ~11 game-hours.

### 🧪 Tooling & tests
- **`tools/soak_sim.py`** — headless long-run harness with live progress
  (bar/ETA/ticks-per-second/deaths), day/week/month wall-clock projections,
  survival breakdown, `--debug-hp`, `--neutral-environment` (now clears weather
  too), `--engine-decay`, `--override`, `--set`, `--apply-trait`, `--report`.
  Measured ~6–9 ticks/s with 23 characters → a game week ≈ 18–29 min.
- `tests/test_trace.py` (new); `test_activities.py` / `test_social_company.py`
  updated to the per-minute model. **2828 passing** (excluding pre-existing,
  unrelated `test_mcp_*` failures).

### ⚡ Trigger/edge indexing and background scale (tasks 406/407)
- **`graph.py`** — a trigger-event index (`get_trigger_sources`) plus edge
  indexes keyed on lowercased source/target. Turn/time trigger sweeps now visit
  **only** nodes that own that trigger (any node type) instead of every node,
  and edge lookups no longer scan the whole edge list or call `.lower()` per
  edge. A `_revision` counter drives cache invalidation; a length check lazily
  rebuilds if code mutates `edges` directly.
- **Standing items can tick** — `engine/tick_manager.py` now fires `on_tick` for
  items that are neither carried/equipped nor lit/on (a bush, nest, shrine),
  exactly once, without disturbing the existing carried/lit paths.
- **Cheaper trigger execution** — `_execute_triggers` fetches trigger edges and
  type-filters them before building its template context, and resolves the
  current area by id instead of reading the legacy `current_area` property
  (which rebuilt an `Area` plus its exits on every access).
- **Authoring exits cached** — `build_exits_for_area(include_hidden=True)` is
  memoised by graph revision. The game-facing view depends on per-player
  discovery state and is deliberately **not** cached.
- **Lighting** — effective light is now explicitly the **brightest single
  source** (`max`), not a sum: the old `own + items` was computed and then
  discarded by the brightness ceiling anyway (four dim torches never out-shone
  one torch). Every area's light is recomputed **once per tick** into a stamp
  the render/tick paths read, instead of rescanning the room and its neighbours
  on every access; `_item_light_stats` also collapsed from two content passes
  to one. `graph.retarget_edge` was added, and unequip now moves its edge in
  place instead of remove + add.
- **Scenario cleanup** — deleted four generated goblin byproduct scenarios
  (`*_assembled`, `*_populated`, `*_generated`, `*_generated_connected`); one
  goblin scenario remains.
- **The turn-event buffer was O(n²).** `GameLogger.record_turn_event`
  (`engine/logging_events.py`) rebuilt the whole buffer on *every* append. The
  browser clears it each turn, but a headless run never calls
  `clear_turn_events`, so it grew to ~17,000 and each append scanned all of it —
  the real cause of a 265 → 135 ticks/s decline across a week. It now prunes only
  when the turn changes and hard-caps the buffer at 2,000.
- **Take/drop move edges instead of remove + add.** Placement edges are
  captured, then retargeted onto the player (take) or back into the room (drop),
  the way unequip already was. A failed take no longer orphans the item, because
  the capacity/hand checks now run before any graph mutation.
- **Regression guard** — `tests/test_perf_guards.py` asserts the *shape* of the
  hot paths (buffer bounds, index usage, trigger-sweep scope, brightest-source
  lighting, stamp invalidation) instead of wall-clock time. Verified to fail
  when a fix is reverted.
- **Measured** — a one-week (10,080-tick) background soak runs in **~56s
  (181 ticks/s), 23/23 alive** (roughly 56–71s depending on host load) — down
  from ~6–9 ticks/s and from 9m49s after the first pass. Survivor vitals and
  trace are identical to the slower run, so this is pure speed. After the
  logging fix, function-call counts are flat early vs late in a run. Full suite
  **2831 passing** — four fewer than before only because
  `tests/test_data_no_mojibake.py` is parametrized over every scenario JSON and
  four files were deleted.
- **Not yet playable at speed** — the browser is still the metronome (~2s/step,
  one `tick_turn` per roster wrap). Server-side batch advance is task-414.

### 🧰 Gotchas (this pass)
- The interactive ~2s step delay is **UI pacing, not a rate limit**. Rate
  limiting is `RateLimiter` (`agent-engine.js:412–425`, driven by
  `config.rpmLimit`); the sleep predates it. Keep it for readability, make it
  configurable, and use 0 in headless/batch paths.
- The camp's 11 authored triggers are **dead data**: written as
  `logic_trigger → area` edges with `event` on the node, but the runtime matches
  `trigger_type` on the edge with the owner as source. None of them fire.

### 🔬 LLM Inspector — raw request/response capture (task-405)
- `shared/dataset-collector.js` gains `captureRaw` / `getAllRaw` / `clearRaw` /
  `countRaw` over a new IndexedDB store `llm_raw_exchanges` (DB version 4). It
  stores the full request body, response status/headers/raw body, duration, and
  usage. **Authorization/API-key headers are redacted** before storage, and the
  store is capped at 200 entries.
- `llm-client.js` captures after `resp.json()` (non-streaming), after
  `_handleStream` (streaming), and on error responses (400/429/500) so provider
  error shapes are visible.
- New `ui/llm-inspector.js`: a floating **🔬 LLM inspector** panel with
  per-entry expand, a usage line (including `reasoning_tokens`), **Copy
  request / Copy response**, filters by label and status, body search, and
  Clear. Entries survive reload.
- New Settings toggle **🔬 Show Raw LLM** (`config.showRawLLM`, default off) —
  capture is opt-in.

### 🐛 Fixes (settings + active character + DeepSeek)
- **Settings silently reset four toggles.** `populateForm()` never restored
  `agent-mature-content`, `agent-auto-retry-invalid`, `agent-simultaneous-mode`,
  or `agent-structured-output`, so they rendered unchecked and the next Save
  wrote them back as `false`. All four are now restored on form load (and a new
  guard audits that every settings checkbox is covered).
- **"No agent selected" after refresh.** `config.controllingPlayer` is
  client-only and not persisted, while the header's `Active:` comes from the
  server's `active_player`. `step()` and `startRun()` now fall back to the
  server's active player instead of refusing to run.
- **DeepSeek model names.** Profile + model dropdown updated to
  `deepseek-flash` and `deepseek-v4-pro`; `deepseek-v4-flash`, `deepseek-chat`,
  and `deepseek-reasoner` are retired aliases. Thinking is enabled by default at
  `high`, so the disable path is explicit, and effort `none` now means "thinking
  off" rather than being sent as an invalid `reasoning_effort`.

### 🗺️ Scenario authoring fixes + two engine effects
The camp's trigger validator reported **78 issues across 45 nodes**; it now
reports **0**, and the 11 previously-dead triggers fire.

- **Triggers (11).** Authored as `logic_trigger -> owner` with the event on the
  node — a shape the runtime never matches, so none fired. They now use
  `owner -> logic_trigger` with `trigger_type` on the edge, and their legacy
  flat fields migrate into `effects[]` (`message`, `spawn_items`,
  `grant_memory`).
- **`grant_memory` effect (new).** Adds a memory entry to the target player via
  `Player.add_memory`. Registered in `EFFECT_TYPES` with an editor template
  (`data/library/items/template_grant_memory.json`).
- **`once` triggers (new).** A trigger node with `once: true` fires exactly
  once (`fired` persists on the node). Without it the camp's discovery triggers
  repeated their message and duplicated their spawned items.
- **Effect aliases.** `decrement_uses` → `adjust_uses {delta:-1}` and
  `roll_condition` → `save` (with `on_success`/`on_fail` wrapped as lists) —
  both were unknown effect types that silently did nothing.
- **Ways.** Every bidirectional way had only one authored side, so the reverse
  exit fell back to the way name and read backwards (*"passage to scouting
  rooms"* from inside the rooms). Reverse sides now carry the opposite cardinal,
  a direction label, and a view of the far area.
- **Weapons.** Club / Knife / Rusty Hatchet / Spear had `damage_dice` but no
  `damage`, so combat silently used a flat 5; `damage` now mirrors the dice.
- **Tooling.** `tools/fix_scenario_authoring.py` (dry-run by default) applies
  all of the above; `tests/test_camp_trigger_wiring.py` locks the wiring, the
  once gate, and `grant_memory`.

### 👁️ Human panel perception + stranger targeting
- **"Since your turn" no longer leaks the world.** `agent/turn-feed.js`
  subscribed to the global `events` log, and `digest()` returned *everything*
  logged since the last turn — so the human saw other characters acting in other
  areas, written in second person as if it were their own action. `event-stream.js`
  now carries the acting character on the `log` bus payload (explicit actor,
  else the open turn card's actor; system rows stay unattributed), and both the
  digest and the "What happened" feed filter to what the viewer could perceive:
  their own rows plus rows acted by characters in the same room.
- **Audio propagation through ways.** Speech in *other* areas is now included
  when it carries. The panel mirrors `engine/sound.py` exactly — BFS from the
  speaker's area accumulating per-way barriers (`sound.speech_*` 0/1/1/2/3 for
  whisper/normal/sing/shout/scream; `sound.way_open` 0.5, see-through 0.75,
  closed 1, locked/blocked/hidden 2; ambient noise dampening at the origin) and
  a room hears the line when `penetration - accumulated > 0`. So a shout through
  a closed door carries, normal speech carries through an open passage, and a
  whisper stays private. Uses the model's default values — a customised Engine
  Config override is not read by the panel yet.
- **Unmet characters can be targeted by the label the scene shows.**
  `matching.py _match_character_name` gained an appearance-label tier, so a
  stranger resolves by their `unknown_display_name()` ("the woman") — exact,
  partial, or significant-word match, with ambiguity still returning candidates.
  Previously `approach the woman` failed with *"There's no 'woman' here to
  approach."* while the scene listed her. Once met, the real name is what matches.
- Tests: `tests/test_stranger_targeting.py`.

### 🗺️ Graph map background — right-click + on-canvas handles
- **Right-click empty canvas** → 🗺 menu: **Add background image…**, then
  **Edit image**, **✂ Crop**, **⤢ Fit to nodes**, **🎚 Opacity…**, **🗑 Remove
  image**, plus **🔒 Lock nodes** and **💾 Save node layout**. No permanent
  toolbar — the map is opt-in per right-click.
- **Manipulate on the canvas**: drag the image to move, corner handles scale it
  about its centre, the top dot rotates it, and in crop mode the amber inner
  edges crop it (crop is a normalised source window, so cropping enlarges the
  kept region to fill the frame). A small hint chip appears while editing, with
  opacity and Done.
- Rendering: an `<img>` layer is inserted as the **first child** of
  `#graph-container`, so it paints beneath the (transparent) vis canvas — nodes
  draw over the map and the map never covers the legend. It is kept glued to the
  view transform on every `afterDrawing` (`translate(centre) scale(s)
  translate(-viewPos)`), so it pans and zooms with the graph. A second,
  above-canvas handle layer is `pointer-events: none` except on the handles, so
  normal graph interaction is untouched when not editing.
- Persisted per scenario in IndexedDB (`graph_assets`, DB version 5): image data
  URL, rect, rotation, crop, opacity, lock flag, and node positions. Locking
  freezes physics and applies the saved positions.
- Caveat: the storage key is the scenario `_scenario_name` (falling back to
  `default`), so until the camp scenario carries a `name` (task-408) its layout
  is filed under the boot name.

### 📚 Front-end module documentation sweep
- Every non-vendor module under `static/js` (**133**) now opens with a
  `@module` / `@contributes` / `@powers` / `@relates` / `@docs` contract, so
  "what does this file contribute and what feature does it power?" is answerable
  without reading the file.
- `tools/js_module_index.py` generates `docs/design/js-module-index.md`
  (module · purpose · file · contributes · powers · docs), and `--check` **fails
  on any new module missing the contract**. The legacy baseline was retired as
  files were documented and is now empty.
- Bugs found by the sweep (all fixed): an **unreachable `Social` tier** in
  `prompt-builder/character-state.js` (the `[social_need: moderate]` cue never
  fired — two identical `if (v < WARNING)` branches), and `agent/vital-thresholds.js`
  not exporting its own `DRIVE_*` constants. Also: the duplicated lore/brevity
  block in `system-prompt.js` extracted to shared helpers, stale counts in the
  `prompt-builder/index.js` manifest, and missing headers on `event-bus.js`,
  `graph/layout-engine.js`, and `graph/edge-inspector.js`.
- Docs health: `tools/fix_docs_mojibake.py` repaired **233** cp1252 sequences
  across 34 files, and `tests/test_docs_no_mojibake.py` now guards **all** of
  `docs/` (previously only `data/` was checked). `_Index.md`'s stale hardcoded
  repo path was corrected.
- Open decisions raised by the sweep are collected in
  `docs/design/pending-confirmations.md`.

### 🧼 Readable locals + TypeScript toolchain
- **163 cryptic single-letter locals renamed** across 11 files (`v` / `T` / `n` →
  `value` / `thresholds` / `vitals` …). Worst offender:
  `prompt-builder/character-state.js: describeVital`, where `v < T.WARNING`
  became `value < thresholds.WARNING`. Loop indices and coordinates (`i`, `x`)
  are still fine; the convention is documented.
- **TypeScript adopted, incrementally** (`.js` and `.ts` coexist; the app works
  at every step):
  - `tsconfig.json` (`npm run build:ts`) compiles `static/js/**/*.ts` → `.js`
    beside the source — `strict`, `noEmitOnError`, comments preserved.
  - `tsconfig.check.json` (`npm run typecheck`) parses **every** JS + TS with
    `noEmit`; JS opts into checking per file via `// @ts-check`.
  - Converted files stay **classic scripts** (no `import`/`export`) and use
    ambient globals in `static/js/types/globals.d.ts`, so the `<script>` load
    order is unchanged.
  - First module converted: `agent/rate-limiter.ts` → generated
    `rate-limiter.js` (doc header + module contract preserved, `window.RateLimiter`
    intact). `npm run typecheck` is clean across all 133 modules.
  - TS 7 notes: `module: "none"` and `alwaysStrict` were removed (using
    `esnext`), and emitted files begin with `"use strict";`, which the module
    contract guard now steps over.
  - Convention and conversion recipe: `docs/design/typescript-migration.md`.

### 🗺️ Graph layout durability + adaptive edges
- **Node positions persist to the WORLD.** 🗺 → **Save layout to world** (and
  locking) writes each node's `properties.x`/`y` through a single atomic
  `POST /api/graph/batch` — so a layout survives reloads, travels with the
  scenario file, and is one undo step. `buildNodeConfig()` seeds `x`/`y` from
  those properties on load. **`x`/`y` never reach library templates** —
  `handle_library_create_or_update` strips presentation-only properties, and the
  template-refresh paths already build explicit key lists, so a refresh cannot
  clear a node's saved position either. `tests/test_library_presentation_keys.py`
  locks both the helper and the route.
- **Background map stored as a FILE, not base64.** New
  `POST /api/graph/background/image` saves to `static/images/backgrounds/…`, and
  the path plus transform (rect/rotation/crop/opacity/locked) lives in a new
  scenario-level `graph_background` block, serialized like `world_lore`.
  Embedding the map as base64 would have added ~2.7 MB to the scenario per
  commit for a 2 MB image; IndexedDB remains a local fallback for maps never
  uploaded.
- **Search no longer wrecks hand-made layouts.** `graph/focus.js` called
  `network.moveNode()` on *every* match regardless of `physics: false`, and
  `_kickClusterPhysics()` switched global physics on and ran `stabilize(60)`
  even when physics was off — re-settling the whole layout. Frozen nodes are now
  excluded from the cluster grid, and the kick is skipped entirely when physics
  is disabled.
- **Adaptive connection edges.** Area↔way edges size to the label actually
  drawn: `clamp(45…130, 35 + 3.2 × labelLength)`, so unlabelled edges stay tight
  and long names get room without stretching the map. A per-way `edge_length`
  property still overrides.

### 🌍 Scenario naming + per-scenario isolation
- **The top-bar name is now real.** The click-to-rename chip only ever wrote
  `document.body.dataset.scenarioName` — never the server — so the name was
  cosmetic, vanished on reload, and even keyed the graph-background cache. New
  **`POST /api/scenario/name`** sets `world._scenario_name` and, when the source
  file has a different basename, **repoints the commit target** to
  `data/scenarios/<name>.json` — so a world booted from the boot template stops
  committing into `world_template.json`. Existing files are never clobbered.
  The chip updates immediately and reverts if the server rejects the name.
- **Graph backgrounds are per-scenario.** Loading a different world left the
  previous world's map on screen, and the IndexedDB fallback keyed unnamed
  scenarios to one shared `default` slot. The **world is now authoritative**:
  every state refresh re-derives the background (clearing it when the world has
  none), the local cache is consulted only for a *named* scenario, and a
  previous world's physics freeze is undone rather than inherited.

---

## Unreleased — "Survival balance & Sanity breakdown" (2026-09-08)

The mansion survival fix: teenagers were dying of starvation in ~45–63 in-universe minutes despite carrying granola bars and water bottles, because the drive decay was 1/tick, vitals were invisible to the agent, and the moodlets never told anyone *what to do*. Low Sanity was also still draining HP and being listed as a cause of death — going insane doesn't kill you, it makes you more dangerous.

### 🍞 Survival rates → real-world scale
- **Decay rates are now per-minute, not per-tick.** 1 tick = 1 in-game minute, so a healthy adult can now go ~3 weeks without food and ~3 days without water instead of ~15 minutes. Hunger 1→**0.06/min**, Thirst 1→**0.18/min** — applied in `virtual_world_engine.py`, `player.py`, and all 9 players in `data/scenarios/mansion.json` (the scenario was shipping lowercase `hunger`/`thirst` keys the tick loop silently ignored, so the values were never used).
- **Fractional accumulator** in `engine/tick_manager.py`: sub-1/tick rates were vanishing under `int()` truncation, so the drives barely moved. The leftover now carries over tick-to-tick and the real rate actually accrues.
- **Death slope softened.** Hunger/Thirst now drain HP only after a grace period at max (60m / 30m), then at 0.5/1.0 HP/tick instead of 1/2 — a real recovery window. HP stays an integer.

### 🧠 Maslow-prioritized moodlets & plans
- Hunger/Thirst tiers in `describeVitals` rewritten as **imperatives that name the exact carried item**: *"EAT your granola_bar or FIND SOMETHING TO EAT NOW"*, *"DRINK your water_bottle"*, falling back to *"FIND SOMETHING TO EAT NOW"* when nothing is carried. Threat-qualified so they don't contradict the existing `ThreatDetector` alert. Generic — driven by item tags and carried-item graph edges, no scenario-specific strings.
- The plan prompt's critical-needs note now cites **Maslow's hierarchy** and requires the first plan step to satisfy the most urgent physiological need before exploration, investigation, or social goals.

### 👻 Sanity makes you dangerous, not dead
- **Removed the Sanity → HP drain** (`engine/tick_manager.py`) and dropped "madness" from the death-cause list. Sanity ≤ 0 has no physical consequence. Going psychotic, seeing friends as enemies, getting anxious or suicidal is bad for your health in the way that matters here: it makes you a worse fighter and a worse ally, not a corpse.
- **Two new Sanity-triggered conditions** (`engine/player_conditions.py`), mutually exclusive, wired in the tick loop alongside `social_breakdown`:

| Condition | Trigger | attack | defense | periodic | ends on |
|---|---|---|---|---|---|
| `paranoid` | Sanity < 50 | **+1** | −2 | Sanity −1 | comfort, rest, socialize |
| `hallucinating` | Sanity < 25 | **+2** | −3 | Sanity −2 | comfort, rest, meditate |

- **`buildInsanityContext` tiers rewritten as behavioral directives** — *"You are HALLUCINATING... Trust your instincts over your senses. Attack first, ask questions never"* / *"You are PARANOID... assume it's an attack"* — so the LLM steers toward the dangerous behavior instead of just narrating mood.
- **`Involuntary` flavor** for both: paranoid → stutter speech + glance-around/white-knuckles emotes; hallucinating → ramble speech + stare-at-nothing/mutter-to-empty-corner emotes.

### 🧪 Verification
- `npm run lint` clean over all of `static/js/`.
- All edited Python parses and imports; conditions load (38 total).
- **233 condition/vital/tick/sanity tests pass.** 2,672 tests pass overall; the only failures are 56 pre-existing `tests/test_mcp_*.py` harness breakages (`'function' object has no attribute 'fn'`), which touch none of these files and were already broken before this change.

### 🧰 Gotchas
- The scenario's `decay_rates` keys were lowercase (`hunger`/`thirst`) while `Player.decay_rates` and the tick loop use capitalized `Hunger`/`Thirst` — so the scenario values were silently ignored and fell back to the engine default. Normalized to the canonical casing. If you hand-author `decay_rates` in a scenario, match the Player convention or they won't take effect.
- `mansion.json` is the only scenario patched; other scenarios still ship the old 1/tick rates. Patch them when you re-run them.

---

## 1.7.1 — "Self-healing JSON & dataset capture" (2026-09-07)

The parse-failure follow-up: when heuristic JSON repair gives up, the LLM now fixes its own broken output (the sports-bra response had 5 stray closing braces — `19 {` vs `24 }` — unrecoverable by regex); and every request/response pair is now captured to IndexedDB so it can be exported as a chat-format JSONL fine-tuning dataset.

### ⚡ LLM-backed JSON repair (last-resort fallback)

- `parseJSONFromResponse` now also returns the **parser error message** alongside `{json, raw}`.
- `AIGenerator.generate`: when `extractTopLevelJSON` + `repairJSON` both fail, the broken JSON **and the error** are sent back to the LLM ("This JSON is invalid. Identify and fix the issue based on the error message, and return ONLY the corrected JSON object."), re-parsed, and used as if the original parse had succeeded. Falls through to the existing failure path if the repair also fails. Verified end-to-end: broken bra-JSON → parse null + `"…at position 354"` → one repair call → success.

### 🧪 Dataset collector (fine-tuning pipeline, step 1)

- `shared/dataset-collector.js`: captures every completed `llmClient.chat` call — `{messages, response, label, model, parsed_ok, repaired}` — into a new IndexedDB store (`llm_dataset`, storage v3). Streaming and non-streaming both covered.
- Floating **🧪 dataset** button (bottom-right): live count (captured / parsed-OK / failed), **Export all / parsed-OK only / failures only** as chat-format JSONL (system→user→assistant + meta), and clear.
- The negative examples (failed parses, like the bra) are exactly what a tiny fine-tune needs to learn "emit valid JSON in the app's exact shapes" — pair them with the AI-repaired output as the target.

### 🛠 Fixes

- **`graphManager is not defined`** on load (`static/js/graph/focus.js`): `init()` dereferenced `graphManager` at parse time; it now defers until the global exists (`DOMContentLoaded` / `state:updated` self-guard).
- **ESLint guard**: flat config (`eslint.config.js`) with `no-undef` over `static/js` + the full cross-file global set (excludes 3rd-party `vendor/`). `npm run lint` clean. Would have caught the `graphManager` bug statically.

### 🧰 Gotchas

- Restart your server — storage version bumped to 3 (IndexedDB upgrades on next load; existing data preserved).
- Dataset export is manual (the 🧪 button); nothing leaves the browser until you click export.

---

## 1.7.0 — "Trigger Smith & Triage" (2026-09-07)

The authoring-and-triggers day: an AI trigger suggester that finally writes *correct* triggers (full catalog + worked-example prompt, `{triggers:[...]}` object output, fixed local-model response parsing), a plan-driven heuristic floor that can't invent "eat the spyglass", a review-the-diff modal instead of blind overwrites, a batched apply that doesn't lag the graph, a validator that became a triage panel (group by node/code, dismiss-until-touched, derived progress), graph search that freezes hidden nodes and clusters matches, and a fixed dead `on_light` trigger. **Full suite at 2636 passing** (81 MCP/emote tests deselected — pre-existing harness breakage, see Gotchas).

### 🤖 Trigger AI generator — works now

- **Prompt is a real catalog, not a schema dump** (task-396): every trigger type, condition, and effect with a plain-language description AND a worked example; three complete style-anchor objects (food, tainted-drink, haunted-take). Hard rules the model used to miss: `effects[]` is mandatory (≥1 per trigger), prose lives in `effects[].params.message` / `adjust_vital.success_message` (top-level strings stay `""`), consume uses exactly ONE of `on_eat`/`on_drink`/`on_use`, finite-uses get a `uses_above:0` guard, heat sources are item **properties** (`target_temperature`/`heating_rate`), not triggers.
- **Model output is now `{"triggers":[...]}`** (object wrapper) — local models handle that far better than a bare array; the parser also still accepts a bare array defensively. `extractTopLevelJSON` correctly handles top-level arrays (brace-only extraction was destroying them).
- **Local-model streaming fixed**: the whole answer rides inside the `response.completed` envelope for Responses-API providers (ornith-1.5-9b etc.); `_handleStream` now pulls content out of it AND logs the raw response to the event stream like every other generator — no more opening the network tab to see what the model made.
- **`on_light` is no longer dead**: it was registered but never fired. `toggle_item_status` now fires it as a companion to `on_toggle_on` when a toggleable turns on, so authors can bind "this got lit" flavor without the toggle_on/off dichotomy. Never author both `on_light` + `on_toggle_on` (they fire together). 4 new tests (`tests/test_toggleable_items.py`).

### 🎯 Trigger suggester — heuristic + AI + diff review

- **Plan-driven**: the item's own actions decide WHICH triggers exist (`examine/use/take/drop/equip/unequip/eat/drink/read` → their `on_*`), tags/category decide WHAT they contain. Category detection is tags + explicit actions only — no free-text word matching, so "lea**ther**" can never turn a spyglass into food (validated across all 472 library items: zero eat-without-eat-action, zero duplicates). Augments: lights → `on_light` + `on_toggle_off`, books → `on_read`, consumables with only a `use` action carry the vital on `on_use`.
- **Heuristic floor is provably solid**: empty-guards, CON-save poison on tainted/cursed, Arcana/Survival examine reveals, haunted take-whispers — and it beats the hand-authored `water_bottle`/`energy_drink`/`tainted_wine` (which lacked the guard/poison entirely).
- **AI authors the prose** on the same plan (`TriggerSuggestAI` → shared `AIGenerator`), with heuristic backfill for plan types the model skips.
- **Diff modal, not overwrite** (`trigger-suggest-diff.js`): per-trigger cards with Keep existing / Use suggested / Skip both pills, live "Apply N changes" footer, and `covered()` dedupe so a food item that already has `on_eat` Hunger is left alone. Applies in both the item-library form and the item/way/area inspectors, via one atomic `/api/graph/batch` (single undo) instead of N sequential createNode+createEdge round-trips — the apply no longer lags the graph.
- **Architectural cleanup**: `ItemLibraryAI` never was a separate AI (it always wrapped the shared `AIGenerator`); the trigger-AI moved to `shared/trigger-suggest-ai.js` so the inspector doesn't reach through the item-library namespace.

### 🛠 Validator → triage panel (task-393)

- **Group by node / by code**: one row per way/item/area (a way's 6 side-warnings collapse to one expandable row; candy_jar's 4 empty stubs collapse to one) or one row per issue class ("way_missing_cardinal ×58"). De-duplicates the flat 254-row wall.
- **Dismiss-until-touched**: 🚫/🔓 writes `ignored_issues` into the node itself (survives reloads — your whole "can't remember what's fixed" pain); a dismissal expires if the node is edited after (`_ignored_at` vs `node.updated`).
- **🧹 remove all empty stubs**, **⚡ quick-fix** for mechanical info nudges, **⚡ Fix all** (one batch), and a derived progress bar (clean/total item+way+area nodes with no undismissed issues — computed, can't drift).
- **Scrollable list + sticky count**, sticky filter toggle, `POST /api/triggers/ignore` backend.

### 🧭 Graph search freezes + clusters (task-394)

- Hidden (non-match) nodes are **excluded from physics** during a search — they were invisible but still repelling, which is why "food" results stayed wedged in place. Matches settle freely now.
- On settle, the match cluster gets **gathered into a compact grid at the viewport center** (positions + viewport saved); clearing the search **restores the exact prior layout**.
- **KEEP checkbox** next to the search box: freezes hidden nodes but leaves matches geographically in place — for "where does food live in this house?" reasoning.
- **Tag filtering** landed in both the graph search and Ctrl+K palette (write what you *think* exists in tags, fuzzy-match reveals those nodes too).

### 🚪 Way-orientation honesty (task-395 rework)

- The earlier blind bulk-fill (churching "north" cardinals, templated pass/visible messages) was **removed** — it would have written false facts into ways. `way_missing_pass_message` / `cardinal` / `view_direction` downgraded from `warning` to `info` (they have engine defaults), a `clear_way_fix_fields` op undoes any legacy mints exactly, and the panel's button now routes to the existing per-way ✨ Improve AI instead of templating prose. Remove-`fix_way_orientation` no-op deleted.

### 🧰 Gotchas in this release

- **Restart your server** — engine changed (`toggleable_items.py`, `trigger_validator.py`, `routes/triggers.py`, `routes/graph_ops.py`); static JS is reload-only.
- **Mansion scenario file churned** by live testing saves — inspect before mixing with other templates.
- **81 tests deselected** (`-k "not mcp and not emote"`): the pre-existing MCP harness breakage (`'function' object has no attribute 'fn'`) plus the emote suite; unchanged by this release.
- The AI trigger suggester needs a configured API key/model; the heuristic `⚡ Suggest` works fully offline. Diff modal defaults: conflicts → keep existing, adds → add.
- `on_light` now fires with `on_toggle_on`; existing items that had BOTH will double-fire (remove one).

### 🧪 Behind the scenes

- New modules: `static/js/shared/trigger-suggest-ai.js`, `static/js/shared/trigger-suggest-diff.js`, `static/js/item-library/consumable-triggers.js`, `tests/test_toggleable_items.py` (4).
- Updated: `engine/toggleable_items.py`, `engine/trigger_validator.py`, `routes/triggers.py`, `routes/graph_ops.py`, `static/js/{llm-client,api,validator-panel}.js`, `static/js/shared/{json-utils,trigger-editor}.js`, `static/js/inspector/trigger-helpers.js`, `static/js/graph/{focus,projector,tooltips}.js`, `static/js/ui/command-palette.js`, `static/js/item-library.js` + `item-library/ai-generation.js`, `static/js/agent/prompt-builder/{contextual-actions,system-prompt,turn-prompts}.js`, `templates/index.html`.
- Tasks: task-393 (validator triage), task-394 (graph search cluster), task-395 (way-orientation rework), task-396 (AI trigger prompt examples — reference + embedding).
- Full suite at **2636 passing** (81 deselected).

---

## 1.6.0 — "Cold Open" (2026-09-04)

The believability day, run against a live tick-by-tick event log: the planner was found **disconnected from the decide prompt since the PlanTracker migration** and re-wired end-to-end, the human turn panel became an honest observer (no whispers, no other minds), the react phase got its own minimal prompt (~6.2–8.1k → ~2.5–3.5k tokens, internal contradiction deleted), stranger descriptions stopped leaking names through their "appearance handle", and the taco_bell_date scenario was rebuilt to open **cold** — two strangers, one crash, zero shared history. **Full suite at 2653 passing** (pre-existing MCP harness failures unchanged; see Gotchas).

### 🗺 Planner — visible, honest, unit-tested

- **The plan was never shown to the decider.** `buildPlanContext` / `hasPlan` / the inspector read `window.VW.agent._plans` — a store `PlanTracker` had replaced. Fixed: all three read `PlanTracker`, so `=== YOUR PLAN ===` (with `(done)` / `(CURRENT)` markers and the blocked-step warning) now renders in the decide prompt for the first time since the migration. Fresh plans are visible **the same turn** (the decide snapshot refreshes after `setPlan`).
- **`trackStep` matching fixed twice**: stop-words are filtered for real (the old `length > 2` filter passed "the", so *any* action containing "the" completed *any* step), and an action **with a target must match a non-verb step word** — `approach the order counter` no longer completes `approach the round the corner to oak lane` on the shared verb alone. Bare verbs (`look`, `wait`, `rest`…) still advance on the verb.
- **`shouldReplan` returns a reason string** consumed by the task-340 crisis log: `no plan` / `plan aged out` / `current step failed repeatedly` / `threat detected` / the critical need itself — replacing the fallback label that logged every no-crisis replan as a fake `plan stalled`.
- **`setPlan` records the turn clock** (was `time_ticks`, compared against `turnNumber` — a mixed-units bug that broke plan-age checks across engine re-inits).
- `getFailures` exported; the PREVIOUS PLAN prompt section reads PlanTracker directly.
- Tests: 6 new tracker tests (stop-words, verb-vs-target, reason strings, block-and-advance semantics).

### 👁 Observer feed (human turn panel)

- **`turn-feed.js` rewritten** around structured entries: raw event lines parse into speech / whisper / action / emote / result / system / NPC / recall, grouped and styled with icons, colored actor labels, quoted speech, italic emotes.
- **Observer Concise view is the default**: whispers collapse to *"X whispered"* (never the words), inner monologues, memory-recall dumps, plan stalls, and meta noise are filtered out; a short narrative summary ("Since your turn: …") opens the feed. **Detailed** toggle restores the full styled log.
- Stranger names are masked in the feed via the same `anonymousName` logic as the scene.

### ⚡ React phase — own mind, own prompt

- **Dedicated minimal react system prompt** (`buildReactSystemPrompt`): lore + emote rules + speech/volume + JSON rules + length. The action-law blocks (ACTIONS / ACTION STRUCTURE / ITEMS vs FLAVOR / INTIMACY) are gone — they were ~1.2k of weight that also directly contradicted the react instruction *"MUST NOT include action or item fields."*
- **Fresh 2-message conversation** for the react call: the decide-phase replay (~2–3k of persona/room/plan/available-actions duplication) and chain-follow-up bloat no longer ride along. React calls drop from **~6.2–8.1k to ~2.5–3.5k tokens**; the exchange is still mirrored into the character history for next-turn continuity, and the persona rides in the react user message.
- **Movement-aware react context**: a `go` now says *"You just moved — you are now in X. The full description of your new surroundings is in === WHAT HAPPENED === below."* instead of the lying *"surroundings are unchanged — see your observation above"* pointing at the room you left.
- Inline truncated-JSON retry re-asks in the same conversation with a completion nudge, and the final (retried) response is what lands in history.

### 🙈 Stranger descriptions stop leaking names (task-339 companion)

- **New `engine/name_masking.py`** + scrubbing applied in **both** people renderers: `scene_snapshot.py` (decide-prompt People lines, incl. the JS dim-light `"A vague shape in the gloom — …"` prefix) and `area_description.py` (the backend `look` People line). A stranger's first sentence is an *appearance* handle — descriptions that open with the character's own name no longer leak it; the name is learned by hearing it, as designed.
- Previously this leak let an observer-LLM "learn" a name nobody had spoken.

### 🎭 Scenario: `taco_bell_date.json` rebuilt as a cold open

- **Premise**: Miki's date (Bradley — patreon discovery, ended on a sidewalk an hour ago) went bad; Jake is simply out for food. They crash into each other at the blind corner — **that is turn 0**. Both start on Elm Street, seconds after the collision, as strangers.
- **Jake's 5 first-date memories replaced** with stranger-state seeds: the fridge inventory that sent him out, the pegging shout (now a *past* visit), a neon-sign photography hyperfixation aimed at the flickering `'bell'` panel, and the crash itself. His personality no longer pre-decides "you noticed miki tonight… intentional date."
- **Miki**: keeps the Bradley anchor; the earring contradiction resolved as story — it went missing during the date and *she* found it crumpled in her hoodie pocket (clasp bent), so prose and live equipped-state finally agree. Relationships wiped both ways: the anonymizer ("the man" / "a man's voice") is now correct, and names get learned in-run.
- **World fixes**: ` Streetlight (copy)` (an Elm Street lamppost — spray-painted arrow and all — sitting in the wrong alley) is now **String of Bare Bulbs** matching oak lane's prose; both streetlight names lost their phantom leading spaces; the impossible old meet-cute spill trigger (4 copies, spilling from a crushed empty can) is neutralized.

### 🛠 Fixes

- **Witnessed dedupe** — a character's decide emote and identical react emote no longer render as two WITNESSED lines; repeated heard sounds dedupe too.
- **Comprehensive AVAILABLE ACTIONS** — the block now lists every actionable verb per turn with concrete targets (per-way go/dash/examine/open/close, per-item take/use/read/toggle, self verbs with need hints) instead of a curated sparse subset; the scene view's way menu respects already-standing-at-the-way state (no duplicate `approach`).
- **System prompt trimmed** post-AVAILABLE-ACTIONS: rules that duplicate what the per-turn block demonstrates (go/approach semantics, action structure examples) cut ~40%.
- Plan-stall label honesty, memory-recall label cleanup, and NPC idle lines parse as typed entries in the feed.

### 🧰 Gotchas in this release

- **Restart your server** — engine changed (`name_masking.py`, `scene_snapshot.py`, `area_description.py`); static JS is reload-only.
- **Scenario edits apply on reset to initial state** — existing saves keep the old state. The rebuilt taco_bell_date opens cold; older runs in your saves/ folder are from the previous premise.
- The observer feed defaults to **Concise**; the Detailed toggle shows whispers' existence, system rows, and typed raw entries — it is a debug view, not the intended read.
- React calls are ~2.5–3.5k tokens now, but keep LM Studio context ≥ 9k anyway: the context window, not `max_tokens`, was silently truncating completions mid-JSON (diagnosed via two identical ~196-token cuts on ~6k prompts).
- Plan steps still match by word overlap on prose steps — structured `goal/step/then` plans are the designed follow-up (see session analysis).

### 🧪 Behind the scenes

- New: `engine/name_masking.py`, `tests/test_name_masking.py` (5).
- Updated: `tests/test_plan_tracker.js` (+6), `engine/scene_snapshot.py`, `engine/area_description.py`, `static/js/agent/{plan-tracker,agent-engine,turn-feed}.js`, `static/js/agent/prompt-builder/{character-state,helpers,room-context,system-prompt,turn-prompts}.js`, `static/js/inspector/agent-view.js`, `data/scenarios/taco_bell_date.json`.
- JS unit suite **52 passing**; engine name/masking/snapshot/area tests **34 passing**; full Python suite **2653 passing** — the pre-existing `tests/test_mcp_*.py` harness breakage (54–55 failures, `'function' object has no attribute 'fn'`) predates this release and is unchanged by it.

---

## 1.5.0 — "Tender Magic & Graph Forge" (2026-09-02)

A sweeping working-tree day: environment/time/weather engine plumbing, trigger-graph viewport and compile-honesty overhaul, broadened NPC behavior vocabulary, character/schema cleanup, and a 15-spell Lyrie spellbook design task. **Suite at 2507 passing**; no regressions in the core scenario/turn flow.

### 🌦 Environment & Time (engine)

- **Area status engine** (`engine/area_statuses.py`): data-driven area status definitions, persistence, and save/load round-trip.
- **Environment propagation** (`engine/environment_propagation.py`): temperature/light decay and adjacency propagation wired into the tick loop.
- **Effect handlers** (`engine/effect_handlers/environment.py`): `set_environment`, `adjust_environment`, `set_weather`, `set_time`, `set_date`, `forecast_override`, `adjust_forecast`, `apply_area_status`, `clear_area_status`, `set_wet` implemented as item/trigger effects.
- **Tick integration** (`engine/tick_manager.py`): area status + environment updates execute each tick.
- **Trigger validator** (`engine/trigger_validator.py`): new catalog entries for the expanded environment/time effect set.

### 🧠 NPC Behaviors

- **`engine/triggers/behaviors.py`** (+899 lines): new action types `add_memory`, `set_emotion`, `set_flag`, `hide_in`, `hide_behind`, `hide_under`. NPCs can now leave memories, change mood, set runtime flags, and take cover.

### 🎨 Trigger Graph Editor

- **Viewport**: pan, zoom-to-cursor, Fit, dot-grid background, per-graph viewport persistence.
- **Wires**: left-in/right-out socket layout, YES/NO branch coloring, arrowheads, wire selection + delete, cycle/duplicate guards.
- **Compile honesty**: badges/warnings for fan-out drop, behavior NO-branch drop, and Y-position priority override.
- **Catalog parity**: trigger node now supports multi-select trigger types from the shared registry; condition node grouped dropdown covers all 27 conditions; effect node covers the full 42-effect catalog plus save-gate branches, `llm_respond`, `scry`, memory effects, and environment presets.
- **Interaction fixes**: field commits on `input`, selection class-toggle instead of rebuild, Escape/close guard, draft autosave.
- **Tests**: `tools/test_trigger_graph_viewport.cjs` (19/19), `tools/test_behavior_action_cards.cjs` (119 action types).

### 🧍 Characters

- **Lyrie** (`data/library/characters/Lyrie.json`): equipment slots normalized from string refs to full item objects; memory schema unified (`salience_override`, tick normalization, text formatting cleanup); vitals corrected (`Hunger 94→6`, `Thirst 94→6`); stray markdown artifact removed from `personality`.
- **Whiskers** (`data/library/characters/whiskers.json`): character data update.

### 🗺 Scenario & World Template

- **`data/scenarios/mansion.json`**: migrated to the current scenario schema (`players` map, `current_area`, `area_presence`, equipment objects).
- **`world_template.json`**: refreshed to match the new schema.
- **`virtual_world_engine.py`**: small schema/plumbing updates to keep live state aligned with the migrated format.

### 📚 Library Items & Triggers

- **New templates**: `template_adjust_forecast`, `template_apply_area_status`, `template_clear_area_status`, `template_forecast_override`, `template_set_date`, `template_set_time`, `template_set_weather`, `template_set_wet`.
- **New scratch trigger**: `data/library/triggers/untitled.json`.
- **New reference**: `docs/Trigger-Condition-Effect-Cheat-Sheet.md`.

### 🛠 Fixes

- **Behavior form editor crash**: `weighItem`/`inventoryItem` undeclared consts fixed; all 119 behavior action cards now build without throwing.
- **Graph field persistence**: inline handlers now reference `TriggerGraph` correctly; id substitution no longer mangles quoted ids.
- **Behavior graph layout**: re-layout from single tall column to priority-ordered row-major grid; fit zoom improved on dense behavior sets.
- **Wire rendering after reopen**: wires now redraw after viewport settle, preventing offset/scattered wires on open.

### 🧰 Gotchas in this release

- **Restart your server** — engine, routes, and frontend all changed.
- The mansion scenario file is large and structurally different from older scenarios; inspect via the Scenario Manager before mixing with older templates.
- `llm_respond` remains blocked in trigger contexts without a host-side LLM provider decision.
- Some new effect types (`polymorph_target`, `create_illusory_companion`, `broadcast_emotion`, `repair_item`, `ward_area`, etc.) are proposed in `task-391` but not yet implemented in the engine.

### 🧪 Behind the scenes

- New modules: `engine/area_statuses.py`, `engine/environment_propagation.py`, `engine/effect_handlers/environment.py`, `static/js/shared/env-presets.js`.
- New tests: `tests/test_area_statuses.py`, `tools/test_trigger_graph_viewport.cjs`, `tools/test_behavior_action_cards.cjs`, `tools/_probe_parity.cjs`.
- New tasks: `task-388` (trigger-graph overhaul), `task-389`/`task-390` (NPC behavior phases), `task-391` (Lyrie spell items + engine effect proposals).
- Task vault reorganized: 10 environment tasks moved to `done/environment/` or `cancelled/`; sequence doc bumped to 392.
- Full suite at **2507 passing**.

---

## 1.4.0 — "Body Language" (2026-09-01)

The mature-content pleasure system (vitals, intimacy verbs, arousal conditions, release loop,
mature traits), a company-aware Social overhaul, vitals-driven emotions, involuntary actions,
invisible undead-ghost NPCs, and the identity foundation for id-backed characters. Everything
adult is opt-in behind a single 🔞 toggle and leaves the base game untouched. **2589 passing**
(69 MCP tests deselected — pre-existing harness breakage, see Gotchas).

### 🔞 Mature content toggle (task-206)

- **World flag** `mature_content` mirroring ghost_mode end-to-end: `GET/POST /api/settings/mature_content`,
  world attribute, save/load round-trip, settings-modal toggle (🔞 Content group), IndexedDB persistence.
- Everything below is gated on it: toggle off → no pleasure vitals exist, intimacy verbs reject with a
  flavor message, adult traits vanish from library pickers, arousal conditions strip themselves.

### 💗 Pleasure vitals & release loop (tasks 207/208)

- **Three new vitals** — Arousal (slow ebb), Stimulation (medium drain), Pleasure (fast fade) — appear
  only in mature worlds, self-healing via `Player.sync_pleasure_vitals()`, with baseline decay rates.
- **Clothing friction** (task-208): equipped items' `friction` property trickles Arousal (0–3/tick).
- **Edging**: Stimulation 50–64 stacks the `sensitized` condition and feeds Arousal.
- **Release**: Stimulation ≥ 65 ∧ Arousal ≥ 40 fires the cascade — Energy −20, Entertainment +30,
  Hygiene −10, Sanity +15, meters reset, `satisfied` + `overstimulated` applied, log line for the
  active player.

### 💘 Intimacy verbs (tasks 211/212)

- **New module** `engine/pleasure_actions.py`: 8 verbs (kiss, caress, lick, suck, bite, pinch, blow,
  tickle) with a `VERB_BASE` pressure/pleasure/pain table.
- **Body-part targeting**: `kiss lydia on neck`, `pinch her on the left nipple` — same region resolver
  as task-253 combat. Omitted `where` defaults per verb (kiss → lips). Covered regions land
  *through clothing* (damped ×0.4).
- **Multiplier pipeline** (task-212): intensity (light/normal/firm — leading "firmly kiss…" and
  trailing "…gently" both parse) × region sensitivity (paperdoll `body_state`) × trait
  `body_part_multipliers` (e.g. `wired_differently`: nipples ×3.0, genitals ×0.1) × closeness bonus.
- **Pain flips**: `pain_potential` verbs (bite, pinch) can drive Pleasure negative → `overstimulated`.
- **Interact-type**: never damages, recorded as `interact` turn events, no weapon/roll path — a clean
  `interact` vs `attack` split in the dispatch.
- **Frontend** (`action-normalizer.js`): mature worlds accept/emits
  `{action:"kiss", target, where, intensity}`; the system prompt gains an intimacy schema section.
  Non-mature worlds never accept or advertise the verbs.

### 🧬 Arousal conditions & mature traits (tasks 209/213)

- **13 new conditions**: `warming_up` / `aroused` / `highly_aroused` / `frantic` (threshold-driven
  from the Arousal vital, applied/removed automatically each tick), `overstimulated`, `nipple_hard`,
  `blushing`, `wetness`, `sensitized` (edging stacks), `satisfied` (afterglow), plus base-game
  `itch`, `goosebumps`, and `social_breakdown`.
- **Guard**: condition periodic effects can no longer CREATE vitals — an arousal condition on a
  non-mature world can't leak an Arousal key into `player.vitals`.
- **7 mature traits** (`wired_differently`, `quick_recovery`, `sensory_memory`, `sex_addict`,
  `attention_seeker`, `exhibitionist`, `single_track`) — marked `mature: True` and hidden from
  library listings unless the toggle is on. Wired hooks: `quick_recovery` halves the
  overstimulated bout, `sensory_memory` leaves lingering sensitivity after release, `sex_addict`
  doubles Entertainment decay at low Arousal.

### 🪞 Body-state descriptions (task-210)

- **Equipment description enrichment**: the appearance prompt now carries per-item detail properties
  (opacity / coverage / current_state / friction) plus a visible-physical-state section (flush, hard
  nipples, trembling, desperation…) — woven into the prose in both the LLM and fallback paths.
- **Agent prompts** gain first-person body-state lines derived from the arousal conditions.

### 👻 Undead ghost NPCs (task-309 MVP)

- Tag a character `ghost`/`undead`: invisible to room listings and social presence, skips ALL vital
  processing (no hunger/cold/fatigue), untargetable ("the blow passes straight through"), and
  **phases through locked/blocked/one-way/item-gated ways** — perfect for atmospheric stalkers.

### 🗼 Emotion from vitals (task-142)

- `engine/emotion.derive_from_vitals()`: when no explicit emotion has been set (or the affect map
  decayed back to neutral), mood is derived from actual physical state — starving → craving/anxious,
  frozen → uneasy, exhausted → irritated/melancholic, injured → afraid, dying → deep calm (ghosts),
  asleep → silent. Explicit emotions always win; vitals only fill the silence.

### 👥 Company-aware Social overhaul (task-353)

- **Isolation timer**: after 5 consecutive alone-ticks, Social decay accelerates (extra −1/tick);
  introverts exempt, **loners reverse it** (+1/tick in solitude).
- **Physical ≠ social** (task-353 §2): humid air and `humidity: humid` now sap **Hygiene** (not
  Social); perfume boosts **Entertainment** (not Social). A lone character in a perfumed room is
  still alone.
- **GROUP_ENERGY_DRAIN** is now consumed: crowds of 3+ sap Energy per the trait value.
- **Self-talk**: speaking with no living listeners in the room gives +1 Social instead of +5.
- **chatty trait**: +2 per exchange (speaker +7, chatty listeners +5).
- **Behavioral gates** (§5): prompt flags (`social_need: moderate/desperate`) at Social < 50/25 and a
  `social_breakdown` condition below 10 (Sanity drain, removed once Social recovers ≥ 15).
- New traits: `loner`, `chatty` (conflict-correct, library-seeded).
- **Fixed 5 pre-existing `test_social_company.py` failures** (the humid-area Social double-drain).

### 💬 Involuntary actions (task-166)

- **`static/js/agent/involuntary.js`**: condition-driven speech/emote interruptions — frightened →
  stutter ("W-what did you say?"), freezing → chattering stutter, sick/poisoned → coughs,
  social_breakdown → hollow muttering, itch/goosebumps → scratch/shiver emotes, plus a low random
  baseline (hiccup/burp/yelp). Pronoun-aware, never blocks the intended action, injected before the
  text is sent so the room and event stream both see it.

### 🛠 Fixes

- **Mana vital leak** — non-magic characters showed a Mana bar because saves/scenarios hardcode
  `"Mana": 0` and every hydration path overwrote vitals after the tag sync. All five hydration
  paths (save load, library spawn, template load, library import, player import + graph copy) now
  re-run `sync_vitals_with_tags()`.
- **Latent `AttributeError`** in the NPC hunter facade (`_get_nearest_player_to` /
  `_get_path_to_area` called non-existent undecorated names on `npc_behaviors`).
- **TickManager ghost check** — `TickManager.player_manager` is actually the engine; the undead-ghost
  decay skip went through a facade that resolved to `None` (found by the new tests).
- **Release cascade** — `satisfied`/`overstimulated` no longer exclude each other (refractory
  overload + afterglow coexist).

### 🧪 Behind the scenes

- New test file: `tests/test_pleasure_system.py` (21 tests) covering the toggle gating, multiplier
  pipeline, dispatch (incl. the leading-adverb form), friction/edging/release, quick_recovery,
  ghost NPC behavior, phasing through locked ways, and id round-trips.
- **task-316 foundation** (safe subset): stable opaque `Player.id` (uuid8, serialized/restored) and
  `graph.add_node` no longer silently overwrites duplicate **character** nodes. The full
  registry/relationship re-key remains a dedicated follow-up.
- Task vault: 142/166/206/207/208/209/210/211/212/213-lite/309-MVP/316-foundation/353 — implemented
  in this session.
- Full suite at **2589 passing** (+21 new; 69 MCP tests deselected).

### 🧰 Gotchas in this release

- **Restart your server** — the engine, routes, and frontend all changed.
- **Mature content is opt-in and off by default.** Toggle it in settings (🔞 Content group) or
  `POST /api/settings/mature_content`. Toggling mid-session strips/creates the three vitals and
  their conditions automatically — nothing leaks into clean scenarios.
- **Item `friction` / `opacity` / `coverage` properties** drive the new description + arousal
  behavior but no library items have them yet — set them in the inspector/library and they work.
- **Ghost NPCs** need the `ghost` or `undead` **tag** on the character. They're fully invisible:
  no room listing, no social presence, no tick processing. Include them in queries with
  `include_ghosts=True`.
- **MCP test modules** (`tests/test_mcp_*.py`) are broken by a pre-existing harness issue
  (`'function' object has no attribute 'fn'`) that predates this release — 69 tests deselected
  until that harness is fixed.
- The 4 remaining mature traits (attention_seeker, exhibitionist, single_track, sex_addict's
  perception side) are defined but await the NPC-perception framework (task-214) for their hooks.

---

## 1.3.0 — "Weather Eye & Wild Words" (2026-08-31)

A forecast schedule engine, game calendar, moon phases, wind/humidity, a triple-feature NL Editor
power-up (ghost previews, populate_area, selective apply, mechanic inference, lore-aware prompts,
palette shortcut), a sky widget driven by live state, trigger effects for time/weather, and
moonlight descriptions. **2633 passing**.

### 🌦 Weather & Sky (engine)

- **Forecast engine** (`engine/weather_forecast.py`): authored (hourly/weekly/yearly), deterministic
  state-machine, random, or hybrid modes. Zero authored entries = strict no-op — existing scenarios
  are unaffected. GM/trigger `forecast_override` with duration countdown & auto-revert.
- **Calendar** (task-228): `game_day/month/year` derived from ticks + `calendar_config`
  (`minutes_per_day`, `days_per_month`, `months_per_year`), exposed in `/api/state`. `set_game_time`
  / `set_game_date` effects.
- **Moon phases** (task-229): deterministic 30-day cycle (`new → crescent → quarter → gibbous →
  full → waning`). Outdoor night areas add the moon's `light_bonus` to ambient light (full moon
  +25, stormy nullifies it, foggy halves it). `blood_moon` override stains the sky red (+30).
  Moonlight lines in area descriptions.
- **Wind** (task-231): `none/breeze/wind/gale/storm/hurricane` — accelerates heat propagation
  (stronger wind wins), wind chill resisted by `wind_resistance%`, extiguishes lit items on
  gale+ (10%–60% chance/tick), drains Energy on exterior moves. New item properties
  `wind_resistance`, `water_resistance`.
- **Humidity** (task-232): `dry/humid/wet/flooding` — affects effective temperature (hot +2/+3/+4,
  cold -1/-2/-3), saps Social in humid air, flooding adds +1 Energy cost to movement.
- **`effective_temperature`** now accepts `wind_level` + `humidity` kwargs (backward-compatible).
- **Trigger effects** (task-234): `set_time`, `set_date`, `set_weather`, `forecast_override`,
  `adjust_forecast`. `set_environment`/`adjust_environment` extended with `weather`, `wind`,
  `humidity`, `transparent` keys + cycling. New trigger types: `on_turn_start`, `on_turn_end`,
  `on_dawn`, `on_dusk`, `on_day`, `on_night`, `on_full_moon`, `on_blood_moon` (one-shot per
  game-day via last-fired cache). New conditions: `date_equals`, `moon_phase_equals`, `weather`.
- **Settings**: `GET/POST /api/settings/forecast`, `POST /api/settings/forecast-override`,
  `/api/state` exposes `game_day/month/year`, `moon_phase`, `forecast_schedule`, `forecast_override`.
- **Engine Config**: `forecast.apply_scope` (exterior/all), `heat.base_rate`/`heat.max_delta` now
  apply wind multiplier.

### 🌠 Sky Clock widget (GUI)

- **Top-bar live widget** (`static/js/sky-scape.js`): `🕐 09:40 · Jan Day 1 · 🌑 new moon · ☀️ clear
  · rain in 2h` — replaces the bare `#ui-time` clock. Driven by engine state, clickable → opens the
  **World Sky panel**.
- **World Sky panel** (modal): animated sky stage (gradient, sun arc, moon arc with v2 realistic
  moonrise/set, seasonal hill colors, weather layers with clouds/rain/snow/fog). Time skips
  (+15m/+1h/+1 day), weather override dropdown + duration + Set/Clear, forecast next-change
  indicator, GM override indicator. Ported from the qwen/GLM mockups and wired to engine APIs.
- **Design note** reconciling mockups + roadmap + implementation: `docs/design/sky-widget-reconciled.md`.

### ✨ NL Editor power-up (9 features)

- **Ghost-node canvas** — staged entities appear as translucent dashed nodes on the graph in real
  time; updates/deletes tint the live node amber/red; attach/detach get dashed ghost edges.
  Re-applies after every graph reload.
- **Auto-pan spotlight** — when a turn finishes with fresh staged ops, the camera gently pans to
  the newest staged target ("here's what I just drafted").
- **Selection-aware prompting** — the system prompt reports the currently-selected node as the
  default "this room/node"; `update_node`/`delete_node`/`get_node`/`spawn_library_item` auto-fill
  a missing id from the selection.
- **Inline staged property tweaker** — ✎ on any staged row → editable JSON payload, save/cancel.
- **Selective partial apply** — checkbox per op + **Apply Selected (n)**; unchecked ops stay staged.
- **`populate_area(area_id, theme)`** — one call stages a whole themed pass: 9 theme packs
  (apothecary, kitchen, garden, study, smithy, warehouse, shrine, bedroom, generic), each with an
  NPC, items, attachments, and area ambience.
- **Smart mechanic inference** — glowing crystal → `light_source`/`dim`/`lit`; roast chicken →
  `eat` action; plus sound/heat/weapon/armor/read/drink rules — all automatic from the name.
- **Lore & style awareness** — system prompt injects scenario name, theme, up to 6 world-lore
  entries, and the selection; rule 6 enforces style consistency.
- **`>` palette route** — Ctrl+K → `> make the tavern darker and add a violin` → Enter → NL Editor
  opens, input filled, agent runs in the background.

### 🛠 Fixes

- **`POST /api/graph/batch`** — NL Editor's Apply now sends all staged ops as one server-side
  batch, recording exactly ONE undo snapshot. A single Undo reverts an entire Apply. (Previously
  each per-op API call pushed its own snapshot, and several op types hit wrong routes giving 405 or
  silent no-ops.)
- **`update_node` flat patch** — the agent hands `{description: "..."}` and the PATCH route now
  accepts it (was silently ignored).
- **`link_to_library`** — `template_id` now correctly lands in `properties`.
- **`connect_areas`** — connection edges now carry `direction` + `visible_in_direction` props so
  exits actually resolve.
- **`search_library_areas`** — now searches `description` too (matching the items search).

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — the running process needs to pick up the new engine code
  (calendar, forecast, moon, wind, humidity, trigger effects, routes).
- Weather forecast scenarios: **zero authored entries = no behavioral change** — existing scenarios
  are unaffected. To use weather, author a forecast schedule via `/api/settings/forecast` or set
  a GM override via `/api/settings/forecast-override`.
- Moon/turn/time triggers fire only on nodes with attached trigger nodes of the matching type.
- The Sky widget's time skips (+15m/+1h/+1 day) adjust the clock display but do NOT run engine
  ticks — they're visual helpers. Use `/api/turn/apply` for actual world-time advancement.
- `wind_resistance`/`water_resistance` are item properties set via the inspector or library; no
  library items have them yet. They work as soon as set.
- The after-request hook's post-state snapshot push for simple graph edits (PATCH `/api/graph/node/`)
  still makes the first Undo a no-op — the batch endpoint is exempt but the per-edit quirk remains.

### 🧪 Behind the scenes

- New test file: `tests/test_graph_batch.py` (6 tests), `tests/test_engine_config.py` baseline
  updated for `forecast.apply_scope`.
- Task vault: 227/228/229/231/232/234/378/379/387 — all implemented in this session.
- Full suite at **2633 passing**.

---

## 1.2.0 — "Craft & Carry" (2026-08-31)

Items stopped being cardboard props. Uses, durability, weight, freshness, stacking, crafting,
teaching, auto-dressing, gated shortcuts — and a pile of the item/gameplay todo queue landed in
one pass, tested with **2615 passing**.

### 🧰 Items grew up

- **`max_uses` + weight reconciliation**: a half-eaten loaf weighs what's left
  (`base_weight × uses/max_uses`); infinite-use items stay static; `combine` merges two
  identical stacks (uses summed, clamped at max, source destroyed), `split <item>` divides one
  into parts — capacity re-checked, "stackable twins" ignore the auto-renamed copy suffix.
- **Armor & equipment wear on hit**: outermost armor/clothing decrements uses; at 0 it breaks —
  back to carrying + `on_break` trigger. **No raw numbers anywhere**: prompts read
  `[pristine/worn/battered/about to break/broken]`, the HTC chips and paperdoll modal show
  plain words, the item inspector has a durability bar.
- **`on_use_progressive`** trigger type — fires on every use; gate thresholds with the existing
  `uses_reached`/`uses_above` conditions.
- **Freshness**: `perishable` food decays per tick → `spoiled` (fires `on_spoil`), cooking —
  use fresh food on an oven/stove/heat source → `cooked`, decay halts. Examine and prompts say
  it in plain words: `(fresh)`, `(cooked)`, `(spoiled)`.

### 🗺 Gated paths & movement

- **`requires_item` on ways** — a bike lane needs a bike, a fly path needs an item tagged `fly`:
  visible-but-blocked without the gear, open with it. Prompt exit lines show `(needs: bike)`.
- **Over-encumbrance = one size larger**: ≥50% load bumps your effective size tier — narrow
  passages stop fitting.
- **Chain follow-ups (task-104)**: the dash→go chain generalized — `lead` → go/approach/
  release, `grab` → approach/release. One same-turn follow-up, agent-decided.

### ⚒ Crafting & knowledge

- **Full recipe system**: recipe graph nodes + `engine/crafting.py` — inputs (consumed or not),
  conditions (`state_equals`/`has_item`/`random_chance`/`skill_check`), outputs hydrated from the
  library, learning via `global` / `skill:<name>` / `item:<name>` / discover-on-first-craft,
  persisted `crafting_known`. Commands: `craft`/`make`. 🧪 Recipes panel in the agent inspector.
- **`teach <recipe | skill:NAME> to <character>`** — teacher must know it, student must be
  present; recipes transfer, skills +1.
- **`use N items on target`** — structured `amount` on use_on (`use 2 eggs on pan`) validates
  against tracked uses and consumes N; prompt shows the syntax.

### 🧍 Characters dress themselves

- **🤖 Auto-Dress from Interests** (Inventory tab): scans the item library for wearable pieces
  matching `interest_tags`, equips through the normal stacking rules, weather-aware
  (hot → skips heavy insulation, cold → wants it), idempotent by construction.
- **✨ Generate from Personality** (Bio tab): the character's LLM gets the full system tag list
  and answers with JSON/CSV tags → sets `interest_tags` in one click.
- **🌊 Simultaneous Mode (experimental)** — every autonomous character acts on its own
  countdown derived from Social/traits/Energy (high-Social acts more, exhausted slower).
  Chaos by design; sequential mode untouched; off by default.

### 👁 Senses & health

- **`scry` effect**: a frozen distant-area view (rendered description + ambient light + exits) —
  the shared observer path is untouched. Editor entry with area picker + lead-in/fail text.
- **`proximity_effect` items** (EMF-style): BFS room-distance readings on examine — sharp when
  they're right here, needle-jumps adjacent, faint blip beyond, prose only.
- **Context-aware vitals**: isolated-wording only when you're actually alone and quiet; company,
  addressed-to-you, noisy rooms, and visible food/drink all change the lines. Sanity is now a
  neutral stress curve — no more "the shadows seem to watch you" in a bright Taco Bell.
- **Encumbrance in the prompt + HTC** — natural language ("at the edge of your capacity"),
  never numbers.

### 💬 Input & feedback

- **Invalid-action auto-retry** (setting, off by default): one same-turn retry with the error
  fed back for rejected and engine-failed actions.
- **Appearance grammar guardrail**: third-person directives + few-shots, validator catching
  `you is`/`body is who` leaks, one silent repair pass, safe fallback — broken text never
  persists (it re-sends into every prompt forever).
- **Carried/worn prompt lines**: full untruncated description + allowed actions +
  (known / not yet examined) + durability + freshness.
- **Gear totals strip** in the Inventory: armor / best weapon / insulation / resistances as
  pills with "from: …" contributor tooltips — one place, no per-item duplication, same
  aggregation rules as the engine.

### 🧪 Trigger-effect templates

- **42 library items** — `template_<effect>` (e.g. `Template: Scry`), each with a wired
  `on_use` trigger demonstrating that effect; generator at `tools/gen_effect_templates.py`
  (re-run after new effect types, a coverage test guards it) + index in
  `docs/virtualWorld/Templates/trigger-effect-template-items.md`. Scenario-ending/room-spawning
  ones are loudly flagged ⚠️.

### 🎓 Help, tips & guided tours

- **❓ Help Center** (top bar or **F1**): a coach-tip system that fires *when you touch the
  thing* — welcome tip on first load, inspector tips per view type (area/item/way/agent),
  button-triggered tips for Settings, the Game menu, Overlays ▾, More ▾, Triggers, ▶ run,
  auto-dress, crafting, and a ⚠️ warning when Simultaneous Mode flips on.
- **Spotlights**: "Show me" physically highlights the UI element the tip describes (the card
  stays put; ESC/✕ clears).
- **Guided tours**: *First five minutes*, *Triggers & effects*, *Scenario workflow* — ordered
  chains with Next steps.
- **State**: tips remember themselves (localStorage per-id) with session re-shows; the index
  lists every tip with one-click replay and Reset all. No second system — tips point at the
  real UI, and the registry is one easy-to-extend array.

### 🛠 Fixes

- **⋯ More ▾ and Overlays ▾ dropdowns** were opening *invisibly* — the toolbar's
  `overflow-y:hidden` clipped them; now visible.
- **`take` puts everything in a hand first** (generic held; hands full → one item auto-stowed
  to carrying, then pick up, same turn; `two_handed` needs both hands; intrinsic abilities skip
  to carrying). New **`stow`** verb.
- **Saved worlds are graph-only** — no more redundant per-room `exits`/`exits_authoring` in
  scenario files (runtime `/api/state` payload still computes exits live).

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — engine + route changes need the fresh process; static
  JS/UI is reload-only.
- The **mature-tags → inspection reveal** discussion stays open: newer item mechanics
  (freshness/proximity/max_uses) aren't yet wired into the tag-reveal pattern in the item
  inspector — say the word and they get the same treatment.

---

## 1.1.0 — "The World Is Yours" (2026-08-30)

The big one: authoring stops fighting you. Everything below shipped in one working session, tested with 2500+ automated tests.

### 🌍 Scenario workflows — no more losing work

- **Scenario status chip** (top bar): `📦 <scenario> ●` lights up the moment the live world drifts from its source, with **💾 Commit** and **🌀 Restart** right there. Commit writes your live world into the scenario source so Restart keeps your changes — the old "I built it and the restart ate it" trap is dead.
- **Honest Save menu**: `💾 Commit Scenario` (server-side, updates the source you're working on) vs `📤 Export Scenario File…` (download), no more pretending a download saved your scenario.
- **Import preview**: before `Load JSON…` touches your world you see rooms/items/ways/characters, format, and sanity notes (dangling exits, players in missing rooms) — then **Apply (Undo protects)** or **Cancel**.
- **🔬 Deep audit** (import preview + Scenario Manager): the full trigger validator runs against a file *before* you load it — "3 errors · 2 warnings · 4 info" with the top issues.
- **🗂 Scenario Manager**: every `data/scenarios/*` file listed with stats — Open (undo-protected), Audit, Copy, Rename, Delete, Refresh.
- **Changes-since-source diff** endpoint: structural diff (rooms/players/env/exits) between live world and source — the backend for reviewable commit/discard.
- **Restart stays undo-safe**; undo now shows **labels** via the visible **📜 history dropdown**.

### ⚡ Authoring speed

- **Ctrl+K command palette**: type `kitchen`, jump to it. Type `save`, run it. Nodes, system actions, panel tabs — one fuzzy search.
- **🧩 Trigger snippets**: one click fills an entire trigger — Chest, Light Source, Heat Source, Recorder (captures recent speech!), First Aid, Book, Whispering Door.
- **Spawn item** editor fields for **Place into (area/container)** and **Capture recent speech** — the recorder/chest recipes survive saving.
- **📋 Duplicate room** (with items, contents, triggers — `"Kitchen (2)"`) and **duplicate item** (`"Lantern (copy)"`, placement preserved).
- **🕘 Recently-edited rail**: last 10 nodes you touched, click to jump back.
- **Keyboard map**: **Ctrl+S** commit, **Ctrl+Z / Ctrl+Shift+Z** undo/redo (typing-safe).

### 🧲 Trigger system — way more toys

- **New effect types**: `spawn_way` (runtime doors, one-way supported), `spawn_area` (runtime rooms), `set_way_target` (portals/elevators — repoint a door at runtime), `set_way_view` (see-through / view text).
- **New condition**: `item_relationship` ("does this item have anything inside?" by edge type, with target filter).
- **New template params**: `{uses}`, `{weight}`, `{current_state}`, `{name}` and **`{vital:Thirst}`** readouts in messages.
- **Result**: recorded during authoring — the spread of "flavor" engines you can build with effect-composition is dramatically wider.

### 🩺 Conditions — six new ways to be in danger

- **wet** — soaked clothing keeps only 20–60% of its insulation (levels 1–3).
- **injured** / **bleeding** — body-part wounds, level-scaled HP drain, ends on fix/bandage/medicine.
- **hypothermia** — level-scaled Energy/HP drain, dexterity auto-fails, staged symptoms (shuddering → shaking → warm and sleepy).
- **suffocating** — blocks actions + movement, drains, staged symptoms, ends on breathe.
- **petrified** — stone: blocks everything, +5 defense, STR/DEX/CON saves auto-fail.
- All six live in the data-driven condition library — **browser-editable**, like every other condition.

### 🗺 World creation

- **✨ Scenario from Text**: one premise sentence → AI drafts rooms, doors, items, characters, lore → review cards (accept per room, regenerate a room, prune items) → apply, undo-safe. TemplateLoader now carries item tags + light/heat props and a supporting `characters` cast.
- **Save/Load modal**: autosave slot (pinned AUTO), per-save stats (time/turn/player/room counts/size), overwrite-in-place, rename, delete, and **app version** stamped on every save.

### 🛠 Fixes & honesty

- **Temperature rounding**: no more `-10.452438125°C` anywhere — stored and displayed at 0.1°.
- **Honest defaults**: the Light Level field says "— unset (engine uses Dim) —" instead of pretending; heat-source inputs show real placeholders; Issues panel gets an **⚙ quick-fix** and info-level notes for defaulted mechanics (light/heat) instead of false broken-tag warnings.
- **`go to the doorway` now walks you up to the door and stops** — crossing is explicit (`go through`, `go <room>`, `dash`); new **`approach`** verb everywhere (MCP + prompts + GUI).
- **Character knowledge** moved into a proper modal (Advanced tab → Knowledge): category tabs, search, bulk select, stale-ref cleanup — and the per-entity "Known by" panels removed from items/areas/ways.

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — the running process needs to pick up the new engine code.
- `give`/`steal` item matching is still strict (bug-35 filed — typos like `jumptuit` fail); take/equip no-op wording is being reworked (bug-25 reopened).
- `llm_respond` (trigger-driven chat) is **blocked** — the engine has no LLM provider; needs a host-side decision.

### 🧪 Behind the scenes

- New test files: `test_template_loader`, `test_trigger_effect_ways` (12), `test_more_conditions` (11), `test_scenario_commit` (5), `test_undo_history` (5), `test_duplicate` (4), `test_scenarios` (7), `test_scenario_diff` (4) + validator tests — suite at **2507 passing**.
- Task vault restructured: 20 new tasks (367–386) from the workflow audit; duplicate numbers resolved; sequence doc accurate.
