---
type: task
status: todo
area: items
priority: high
---

# task-604: Split defense into two anti-correlated axes: damage reduction and evasion

**Filed:** 2026-09-30
**Related:** 

## Goal

'defense' is one integer spent only as flat damage reduction (combat.py:250/260/367). Add a signed 'evasion' field applied on the attack side, so heavy armor is easier to hit but far harder to kill in. No evasion concept exists in engine/ today.

## Acceptance

- TODO
