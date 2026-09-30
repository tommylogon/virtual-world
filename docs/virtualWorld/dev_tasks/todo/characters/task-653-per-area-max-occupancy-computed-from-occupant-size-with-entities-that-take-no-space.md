---
type: task
status: todo
area: characters
priority: high
---

# task-653: Per-area max occupancy computed from occupant size, with entities that take no space

**Filed:** 2026-09-30
**Related:** 

## Goal

DECIDED 2026-09-30 by Tommy. Each area gets a max occupancy, and occupancy is computed from the SIZE of what is standing in it, not a headcount. Some areas must hold a titanic dragon; some hold 4 normal-sized creatures; a fairy's house holds 7 small creatures. Some entities take up NO space at all -- a ghost is the example -- so size needs a zero-space flag distinct from 'tiny', because a 1cm spider is tiny but a ghost is intangible. This is the natural consumer of the size property from task-605: size already exists as a trait and is already used for way max_size gating, so occupancy is a second reader of the same axis rather than a new concept.

## Acceptance

- TODO
