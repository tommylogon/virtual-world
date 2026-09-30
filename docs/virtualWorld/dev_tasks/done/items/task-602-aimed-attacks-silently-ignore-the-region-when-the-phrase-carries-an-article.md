---
type: task
status: done
area: items
priority: high
---

# task-602: Aimed attacks silently ignore the region when the phrase carries an article

**Filed:** 2026-09-30
**Related:** 

## Goal

resolve_region() returns None for 'the head', so 'attack X on the head' degrades to an un-aimed d20 hit-location roll. Confirmed live: 6x 'on the head' never landed on the head; dropping 'the' worked every time.

## Acceptance

- TODO
