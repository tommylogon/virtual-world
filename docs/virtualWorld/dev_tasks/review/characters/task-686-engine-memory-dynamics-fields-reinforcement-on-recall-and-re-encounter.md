---
type: task
status: review
area: characters
priority: high
parent: task-685
---

# task-686: Engine: memory dynamics fields + reinforcement on recall and re-encounter

**Filed:** 2026-10-04
**Related:** task-685, task-346, task-403

## Goal

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
  — derived, never persisted.
- Reinforcement triggers: (a) every recall path —
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
