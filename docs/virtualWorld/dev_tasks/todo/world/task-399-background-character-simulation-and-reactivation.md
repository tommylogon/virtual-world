---
type: task
status: todo
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
