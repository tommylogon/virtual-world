---
type: task
status: inprogress
area: world
priority: high
---

# task-399: Background character simulation and reactivation memory

**Filed:** 2026-09-08  
**Depends on:** task-397 for scope activation. Uses existing Player memories,
activities, vitals, movement, and serialization.

## Goal

Let any existing character live cheaply while their scope is not actively
observed, without changing who that character is. This is an execution mode,
not a new character type and not a synonym for `simple_npc`.

```text
controller:       human | llm | simple_npc       (existing identity/control)
simulation_mode:  active | background           (new runtime fidelity)
```

An LLM-controlled character in background mode makes no LLM requests. A
simple-NPC-controlled character may also use background mode. The character's
name, traits, relationships, inventory, current area, vitals, activity, and
memories remain authoritative `Player` data.

## Background runner (v1)

Add a small deterministic module, e.g. `engine/background_simulation.py`.
It processes only due background characters, not every character every minute.
Persist `next_due_tick`, schedule/intent, seeded RNG state, and an append-only
facts log; browser-local LLM plans cannot be the source of truth after an
offload.
Each character has an authored/supplied schedule of high-level steps:

```json
{
  "start": "08:00",
  "activity": "work",
  "destination_scope_or_area": "daily_grind",
  "fallback": "wait",
  "vital_policy": "eat_when_hungry"
}
```

V1 operations are intentionally limited: sleep/rest, travel to an existing
target, work/wait, consume an explicitly eligible carried/reachable item, and
simple resource production/consumption. They must use existing movement/item
rules where exact resolution is needed, or record a structured deferred result
when the target scope is unmade/unloaded.

Cheap background meetings resolve from authored policies, relationships,
traits, vitals, and seeded randomness. They never trigger LLM conversation.
Combat, ambiguous theft/trade, a blocked/locked route, a trigger requiring
precise surroundings, or an encounter explicitly marked `requires_active`
must stop/background-defer and request scope activation instead of inventing
an outcome.

## Event and memory bridge

Record structured background events, not only prose:

```json
{
  "character": "miki",
  "start_tick": 10,
  "end_tick": 70,
  "kind": "sleep|travel|work|consume|meeting|deferred",
  "areas": ["apartment 1b"],
  "facts": ["drank item_energy_drink_01"],
  "importance": 1
}
```

On activation, consolidate the interval into at most one or a small bounded
set of normal `Player.add_memory()` entries with `source: "background"`.
Summaries are deterministic templates over recorded facts in v1; no LLM call
is permitted. Retain the structured event log for inspector/debugging, then
mark it consolidated so activation is idempotent.

Background events are private to the actor unless an existing perception,
communication, or explicit meeting rule gives another character knowledge.

## Pines proof

Create authored schedules for five existing Pines residents. Offload them,
advance eight in-game hours, then activate Miki by opening The Pines scope.
Verify no LLM calls occurred, Miki's location/vitals/item changes are real, and
her next active prompt receives a bounded subjective background memory.

Scope observation is an activation boundary: background residents inside the
opened scope become active before their next due action; residents outside it
remain background. An activate/offload transition must be atomic at its tick
so no action is resolved twice.

## Acceptance

- `simple_npc` and `autonomy` retain their present meaning and serialization.
- Background state/schedules/events survive save/load.
- Due scheduling avoids one global per-character/per-tick scan.
- A character receives no duplicate background memory after repeated activate.
- Meeting resolution is deterministic for a fixed seed and makes no LLM call.
- Exact/unsafe outcomes defer rather than fabricate facts.
- Activate/offload twice at the same tick, then save/reload: neither produces a
  duplicate action, character, item, nor summary memory.

## Non-goals

- A general economy, relationship simulation, or full offscreen combat system.
- Replacing existing LLM or simple-NPC loops.
- Background simulation across physically unloaded graph chunks (task-401).

## Progress — 2026-09-19

Foundation landed (see `docs/design/long-horizon-simulation-progress.md`):

- **The append-only facts log exists** as `engine/trace.py` (`record / recent /
  since / summarize_window / rollup / load / to_list`), bounded at 200 entries
  with salient-first retention. It round-trips through `Player.to_dict` /
  `_deserialize_player` and is wired to need tier crossings, deaths, and
  resolved actions. This is the objective substrate the "bounded subjective
  background memory" is summarized from — code writes the trace, the LLM writes
  memory, never the reverse (see `docs/design/trace-format.md`).
- **`docs/design/reversibility-contract.md`** defines what must stay live while
  backgrounded, the promote/demote handoffs, and the invariants across the seam.
- Vitals were recalibrated to a true per-minute scale (`vital_rates.py`) so a
  multi-day background span is survivable and needs actually move.

Still to build for this task (updated 2026-09-24):

1. ~~`engine/background_simulation.py` — process only **due** characters
   (`next_due_tick`), deterministic/seeded over schedule + needs + traits,
   writing the trace with reasons. Survival behaviors (eat/drink/sleep/work).~~
   **Done** — the module is 988 lines: due scheduling, the full survival ladder,
   schedule pursuit (`_pursue_schedule`, task-409 slice 1), background social
   (`engine/background_social.py`, task-423), traversal/foraging checks, and
   soak/timeskip hooks. See Progress below.
2. ~~`simulation_mode: active | background`, with atomic activate/offload at a
   tick; `trace.summarize_window` builds the promotion catch-up summary.~~
   **Done (2026-09-24).** `simulation_mode` + the promotion/demotion **memory
   bridge** landed in `engine/promotion.py` (absorbing task-412): `offload()`
   stamps the background boundary and `promote()` consolidates the span into one
   bounded `source: "background"` memory, idempotently. Atomicity and the
   scope-observation boundary also landed — transitions are *queued* and applied
   as one batch by `flush()` at the top of `tick_turn`, and
   `POST /api/world/scopes/<id>/observe` queues promotion for the scope's
   background residents. Soak orders keep their own `source: "timeskip"` resume
   memory (task-481) and are not routed through the bridge.
3. **Pines proof** — author schedules for five residents, offload/advance/
   activate, and a bounded `background` memory in Miki's next prompt. **Still
   open.** Deferred: the scenario content belongs to task-400/task-408, and
   task-409 slice 1 deliberately did not ship schedule data (it degraded
   Hygiene/Social/Entertainment in a measured soak).

## Progress — 2026-09-24

Promotion/demotion memory bridge landed; task-412 (which owned this seam) is
superseded and folded here.

- **`engine/promotion.py`** (new) — `offload()` / `promote()` / `pending_span()`
  / `summarize()`. Deterministic templated summary, no LLM. The span is
  `t > max(last_offload_tick, background_consolidated_through)`, so foreground
  actions between two spans are never summarized and repeated activation writes
  no duplicate memory. Bound: 300 chars; importance scales with salient events.
- **`player.py`** — `last_offload_tick` + `background_consolidated_through`
  fields, serialized in `to_dict`; restored in `engine/serialization.py`.
- **`engine/structures.py`** — resident materialisation now demotes through
  `promotion.offload(..., reason="materialize")`, so imported residents carry a
  real boundary stamp for a later activation to summarize from.
- **Tests** — `tests/test_promotion.py` (19): offload idempotence, no-op promote
  on an attended character, one bounded memory per span, no duplicate on
  repeated activation, a second span adds exactly one more, foreground markers
  never summarized, marks survive serialize/load; plus the atomic boundary
  (queue-then-flush, request collapse, missing-character drop, soak orders
  skipped, memory written at flush) and the observe route. Related suites
  (`test_trace`, `test_serialization`, `test_background_simulation`,
  `test_soak_chain`, `test_soak_orders`, `test_structures`, `test_world_scopes`)
  all pass.

## Progress — 2026-09-24 (slice 2: atomic transitions + scope boundary)

- **`engine/promotion.py`** — `request()` / `pending()` / `flush()` /
  `activate_scope()`. A tier change is *queued*, never applied mid-turn; the
  batch is applied in one place. Overlapping requests for one character
  collapse to the last, so a character cannot be resolved twice under two modes.
- **`engine/tick_manager.py`** — `tick_turn` flushes the queue first thing,
  before `on_turn_start` and before any character is processed, so the whole
  turn sees a single mode per character.
- **`routes/world_scopes.py` / `_ops.py`** — `POST
  /api/world/scopes/<id>/observe` queues promotion for the scope's background
  residents (soak-ordered and already-attended characters are skipped) and
  returns the queued/pending names. The change lands at the next tick.

Remaining for this task: the Pines proof (task-400).
