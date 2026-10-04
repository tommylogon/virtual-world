---
type: task
status: review
area: characters
priority: medium
parent: task-685
---

# task-689: Engine: contradiction detection linking fallible memories

**Filed:** 2026-10-04
**Related:** task-685

## Goal

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
