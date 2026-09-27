---
type: bug
status: todo
area: bugs
priority: medium
---

# bug-48: Map layout is silently ignored while Levels (hierarchy) is on

**Filed:** 2026-09-26
**Related:** task-496 task-526

## Goal

loadGraphData only applies the painted-grid layout when !levelsOn, so with the Levels toggle on, clicking Map changes nothing and a painted zone keeps its hierarchical arrangement (looks like physics is on / nodes cramped). Decide the rule: Map should force Layout=free/off (or Levels should not be selectable in Map mode), and the two toolbar toggles must reflect a single source of truth. Add a test or documented invariant so 'Map does nothing' cannot recur.

## Acceptance

- TODO
