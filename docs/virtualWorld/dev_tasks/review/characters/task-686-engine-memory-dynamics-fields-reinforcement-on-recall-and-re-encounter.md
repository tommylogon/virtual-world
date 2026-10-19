---
type: task
status: review
area: characters
priority: high
related: ["'task-685'", "'task-687'", "'task-688'", "'task-689'", "'task-690'", "'task-707'", 'task-685', 'task-687', 'task-688', 'task-689', 'task-690', 'task-707']
parent: task-685
---

# task-686: Engine: memory dynamics fields + reinforcement on recall and re-encounter

**Filed:** 2026-10-04
**Related:** task-685, task-346, task-403

<!-- deps:start -->
**Parent:** [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]]
**Related:** [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]], [[task-687-engine-non-uniform-memory-decay-activation-decay-with-per-memory-resistance]], [[task-688-engine-reflection-2-0-structured-insights-depth-guard-consolidation]], [[task-689-engine-contradiction-detection-linking-fallible-memory]], [[task-690-retrieval-2-0-one-multi-signal-scorer-structured-character-model-recall-b]], [[task-707-memory-decay-reduces-activation-only-never-deletes-actor-trigger-or-consolidation-only]]
<!-- deps:end -->

## What

Memory entries gain optional dynamics fields, and memory gets a reinforcement
loop: recall and re-encounter make a memory more available instead of the store
accumulating near-duplicates with a ratcheting importance.

- `engine/memory_dynamics.py` owns the arithmetic: `ensure_dynamics()`,
  `reinforce()`, `effective_importance()`. One writer per field.
- Fields (all optional, defaulted lazily so old saves load unchanged):
  `category` (episodic/semantic/procedural/social/belief, derived from `type`
  in `Player.add_memory` when not passed), `activation` (0..1),
  `confidence` (0..1; 1.0 manual/preconceived, 0.7 runtime),
  `reinforcements`, `last_recalled_tick`, `reflection_depth`,
  `source_memory_ids`, `contradicts`.
- `effective_importance(m) = importance × (0.6+0.4×activation) × (0.75+0.25×confidence)`
  - derived, never persisted.
- Reinforcement triggers: (a) every recall path -
  `Player.get_relevant_memories`, `AgentMind.recall`, `/memories/retrieve`,
  the vector-search merge in `memory-context.js`; (b) write-time near-duplicate
  re-encounter: extend the task-346 `_is_near_duplicate` dedup in
  `routes/memories.py` beyond its 2-tick window (same subject entity,
  Jaccard ≥ 0.75, any tick distance) to reinforce the original instead of
  appending. `force: true` still appends.
- `Player.get_relevant_memories`' current "+1 importance, cap 10" ratchet is
  replaced by `reinforce()` (bounded, idempotent).
- `_trim_memories` ranks eviction candidates by effective importance +
  reinforcements (manual/backstory still protected first).

## Acceptance

- [ ] Unit: reinforcement math (caps, monotonicity, defaults for field-less memories).
- [ ] Unit: category derivation from every existing `type` value; unknown → episodic.
- [ ] Wiring: a recall through the HTTP `/memories/retrieve` endpoint bumps `reinforcements` on the stored entry (asserted on the player object after the call).
- [ ] Wiring: writing a near-verbatim duplicate days later reinforces the original and does not append (`deduped: true`, `reinforcements` +1).
- [ ] Old-save round trip: a memory dict with none of the new fields loads, recalls, saves.

## Open questions

- Should `AgentMind.recall` reinforce too, given it runs inside
  background-simulation need recall? Yes by default (thinking about it is
  reinforcement), but confirm the need-recall surfaced-memory copy doesn't
  double-stamp (the copy is a new memory; the source gets the stamp).

## Why

Previously, memory recall simply ratcheted importance up by +1 until capping at 10, while duplicate experiences constantly appended new identical strings to Player.memories[]. This bloated memory lists without modeling how memory works. Memory dynamics fields (activation, reinforcements, confidence, last_recalled_tick) and bounded reinforcement allow memory retrieval and repeated encounters to strengthen existing memories organically without cluttering storage or distorting importance.

## How

1. In engine/memory_dynamics.py, implement ensure_dynamics(), reinforce(), and effective_importance(m) formula (importance * (0.6 + 0.4*activation) * (0.75 + 0.25*confidence)).
2. Wire reinforcement into Player.get_relevant_memories, AgentMind.recall, and /memories/retrieve endpoint.
3. In routes/memories.py, update _is_near_duplicate to reinforce existing matching memories (Jaccard similarity >= 0.75 on same subject entity) instead of appending redundant records.
4. Replace raw importance += 1 ratchet in Player.get_relevant_memories with reinforce().
5. Support backward-compatible loading of legacy saves without dynamics fields.

## Steps to verify

1. Call /memories/retrieve targeting an existing memory.
   - expected: reinforcements count increments on the targeted memory object; last_recalled_tick updates.
   - observed: Tested via tests/test_memory_dynamics.py.
2. Post a near-duplicate memory to /api/players/<name>/memories.
   - expected: Endpoint returns deduped: true, bumps reinforcements on original memory, and does not append a new record.
   - observed: Deduplication and reinforcement confirmed in route unit tests.
3. Load an old save file missing dynamics fields.
   - expected: Legacy memories load cleanly with default dynamics lazily populated; saves round-trip without data loss.
   - observed: Verified in test_old_save_memory_round_trips_without_new_fields.

## Files

- engine/memory_dynamics.py
- engine/player.py (add_memory, get_relevant_memories)
- 
outes/memories.py
- 	ests/test_memory_dynamics.py

## Browser UI and intended live verification

Intended UI home: Character Inspector → Mind → Memories; open one entry's detail after automatic recall, deliberate retrieval, and a repeated event.

Current availability: the card adds optional dynamics fields and reinforcement/deduplication. Its wiring criteria name `/memories/retrieve` and `Player.add_memory`; this section does not claim the memory view currently explains or exposes all dynamics fields.

Live steps when available:
1. Record one memory's category, reinforcement count, activation, and importance in `/api/state`; retrieve it through the character's normal `recall` interaction.
   - expected: the same stored memory's reinforcement count increments and the Mind entry reflects the updated dynamics; no duplicate is appended.
2. Record a near-verbatim version of that memory days later through a witnessed event.
   - expected: the writer returns `deduped: true`, reinforces the original entry once, and keeps its source/entity links.
3. Open an old save whose memories have no dynamics fields.
   - expected: Mind still renders them; defaults are derived lazily and the save is not rewritten with fabricated user-authored values.
4. Compare the entry before and after save/reload.
   - expected: category and dynamics round-trip consistently and `effective_importance` follows the stored fields.

This section is not a claim that every recall/re-encounter path is wired today.
