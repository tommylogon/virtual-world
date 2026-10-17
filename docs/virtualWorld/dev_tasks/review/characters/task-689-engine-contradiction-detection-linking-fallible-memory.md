---
type: task
status: review
area: characters
priority: medium
related: ["'task-685'", "'task-686'", "'task-687'", "'task-688'", "'task-690'", "'task-707'", 'task-685', 'task-686', 'task-687', 'task-688', 'task-690', 'task-707']
parent: task-685
---

# task-689: Engine: contradiction detection linking fallible memories

**Filed:** 2026-10-04
**Related:** task-685

<!-- deps:start -->
**Parent:** [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]]
**Related:** [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]], [[task-686-engine-memory-dynamics-fields-reinforcement-on-recall-and-re-encounter]], [[task-687-engine-non-uniform-memory-decay-activation-decay-with-per-memory-resistance]], [[task-688-engine-reflection-2-0-structured-insights-depth-guard-consolidation]], [[task-690-retrieval-2-0-one-multi-signal-scorer-structured-character-model-recall-b]], [[task-707-memory-decay-reduces-activation-only-never-deletes-actor-trigger-or-consolidation-only]]
<!-- deps:end -->

## What

Characters may remember wrong things, and the system must not silently resolve
conflicts into objective truth. What it does instead is **mark** them:

- `memory_dynamics.detect_contradiction(new, existing_pool)` runs at write time
  (both `Player.add_memory` and the HTTP entry endpoint): when the new memory
  shares an entity with an existing one AND the pair shows negation asymmetry
  (one side asserts, the other denies — markers: never/not/didn't/denied/isn't/
  no longer — with ≥ 2 shared content words or Jaccard ≥ 0.4), link the ids
  symmetrically in `contradicts[]` and drop the older memory's confidence ×0.9.
- Conservative by construction: entity overlap AND shared content AND negation
  asymmetry, or no link. A wrong link is visible, removable, and never
  destructive (no deletes, no text rewrites, confidence loss ≤ 10% per link).
- The reflection prompt (task-688) receives contradicting pairs among its
  inputs and may emit a resolution belief with its own confidence; the
  episodes stay untouched and linked.
- Prompt rendering: a recalled memory with unresolved contradictions carries
  `(you are not sure — this conflicts with what you remember at tick N)`.

## Acceptance

- [ ] Unit: assert/deny pair with shared entity → both sides gain the link, older confidence drops; pair without shared entity → no link; pair with shared entity but no negation asymmetry → no link.
- [ ] Symmetry: both entries list each other; deleting one removes the link from the survivor.
- [ ] Wiring: a scenario where a character is told X, then told not-X, ends with one linked pair and no engine-side resolution.
- [ ] Editor: a contradicts link is visible and removable in the memory editor (task-691 stage 2; acceptance deferred to it if not landed together).

## Open questions

- Negation handling in English only for now ("no/n't" morphology). Is that
  acceptable for v1, or do authored scenarios need a language-neutral escape
  hatch (an explicit `contradicts` param on grant_memory effects)? Leaning:
  add the explicit param — it is two lines and makes authored drama reliable.

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

Intended UI home: Character Inspector → Mind → Memory Editor → open a memory pair linked as contradicts; remove the link from either entry and inspect both.

Current availability: the task adds write-time contradiction linking for shared entities and asymmetric assertions, without resolving which memory is objectively true. The visible, removable link flow is an acceptance criterion and is not claimed complete here.

Live steps when available:
1. Tell a character that a named person lives in a specific area, then tell the same character that the person does not live there. Open both memories in Mind.
   - expected: the two entries link to each other because they share the entity and negate each other; both confidences follow the authored reduction rule.
2. Add a third memory about a different entity and a second memory about the same entity without negation.
   - expected: neither unrelated nor non-contradictory pair gains a contradicts link.
3. Remove the link from one memory in the editor and reopen the other.
   - expected: the reciprocal link is removed symmetrically; no deletion of either memory occurs.
4. Ask the character which claim is true.
   - expected: the system surfaces the conflict as fallible memories and does not silently rewrite either into objective truth.

This section is not a claim that contradiction links are visible and editable today.
