---
type: task
status: inprogress
area: gameplay
priority: high
---

# task-671: A timeskip intent that cannot be carried out is an outcome, not a silence

**Filed:** 2026-10-02
**Related:** task-670, task-464, task-475

## Goal

Measured 2026-10-02 on data/scenarios/kraktooth_goblin_camp.json. (a) travel by heading with no exit that way: full 30 min elapse, no interrupt, character does not move, summary reads 'travel for 30 min @ Animal Pens'. (b) same exit but the way is blocked: identical, and the refusal only reaches logger.info. (c) search for a named target that exists nowhere: the character NEVER leaves the room (a name with no tag only looks in the current area, then falls through to maintenance), runs the whole span, and never says not-found. Fix: a blocked/no-exit interrupt naming the obstacle, a named search that actually routes toward the target, and a conclusive 'there is no X' when the world holds no such node.

## Acceptance

- TODO
