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

<!-- deps:start -->
**Parent:** [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]]
<!-- deps:end -->

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Character Inspector → Mind → Memories → **Reflect** → inspect structured insights and consolidated source links.

Current availability: the task describes structured reflection, a depth guard, and episode consolidation while preserving legacy string payloads. The complete structured flow is not claimed as available today.

Live steps when available:
1. Open a character with high-importance or reinforced memories and invoke Reflect.
   - expected: the request includes only entries meeting the candidate rule and depth zero; the result shows belief, sources, confidence, emotion, behavior, and relationship fields.
2. Open a returned insight in Mind and inspect its source memories and derived relationship view.
   - expected: depth is one, all `about[]` source IDs resolve, and the relationship delta appears in the character profile derived from that memory.
3. Attempt a reflection whose inputs are all depth one, first without and then with force.
   - expected: the first request is rejected with the expected 4xx and writes nothing; the forced request is accepted with explicit depth.
4. Consolidate three same-entity low-importance episodes and inspect the trace memory.
   - expected: one trace links all source IDs and the source memories follow the documented consolidation behavior.
5. Load a legacy string-list response through the old entry point.
   - expected: it still renders/stores legacy string insights without breaking existing callers.

This section is not a claim that the structured reflection UI is fully wired today.
