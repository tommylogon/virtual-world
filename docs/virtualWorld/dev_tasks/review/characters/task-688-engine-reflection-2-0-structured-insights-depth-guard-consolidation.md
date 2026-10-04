---
type: task
status: review
area: characters
priority: high
parent: task-685
---

# task-688: Engine: reflection 2.0 — structured insights, depth guard, consolidation

**Filed:** 2026-10-04
**Related:** task-685, task-350, task-96

## Goal

Reflection stops being summarize-only and starts changing the character, and
can no longer eat itself:

- **Client** (`memory-manager.ts reflect()`): fetch candidates = importance ≥ 6
  OR reinforcements ≥ 2, `reflection_depth == 0` only; new prompt asks for
  structured JSON: `{insights: [{belief, about[], confidence, emotional{label,
  intensity}, behavior, relationship{who,dim,delta}}]}`.
- **Backend** (`/memories/reflect`): accepts the legacy string-list payload
  unchanged, and the structured payload; each insight is stored as a
  `belief`-category memory (or `procedural` for `behavior`) with
  `reflection_depth: 1`, `source_memory_ids` (inputs), `confidence`,
  `entity_ids` resolved through `engine/matching.py` (never names-as-keys),
  and `rel:<name>` tags for relationship insights — which is exactly what
  `derive.py` folds into the per-person profile. One writer, no second store.
- **Depth guard, twice**: client excludes depth ≥ 1 inputs; backend rejects an
  insight whose source memories all carry `reflection_depth ≥ 1` unless
  `force: true`. Ladder: episodic → depth 1 → STOP.
- **Consolidation** (`memory_dynamics.consolidate`): deterministic,
  server-side, from the same tick hook as decay — when a retention cap or
  `memory.consolidate` config pressures the store, groups of ≥ 3 old
  low-importance episodic memories sharing an entity compress into one
  `semantic` trace memory whose `source_memory_ids` records exactly what was
  folded; originals removed. Off unless a cap is configured or the flag is on.

## Acceptance

- [ ] Unit: legacy payload still stores string insights (old callers/MCP/tests unaffected).
- [ ] Unit: structured payload produces belief memories with depth 1, source ids, confidence, rel: tags; the relationship delta is visible in `derive_person_profile` afterwards.
- [ ] Guard: an insight whose inputs are all depth-1 memories is rejected (HTTP 4xx) without force; accepted with force.
- [ ] Consolidation: 3+ same-entity low-importance episodes → one trace memory listing all source ids; store shrinks; important/reinforced/manual memories untouched.
- [ ] Wiring: a live reflect call for a character with ≥ 3 important memories writes at least one belief and the event stream reports it.

## Open questions

- Background/NPC characters never call client reflect(). Should the engine
  offer an MCP/tool-callable `reflect` for them (task-403 facade), or is that
  a separate task? Filed deliberately out of scope here unless wiring demands it.
- Should the emotional association of an insight also respike the live emotion
  system at reflect time (the client already respikes on recall)? Leaning no
  (double-counting); record the decision in the design doc when resolved.
