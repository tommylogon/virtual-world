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

**DECIDED 2026-09-30 by Tommy:** split defence into **damage reduction** and an
**evasion bonus**.

- `damage_reduction` -- how much damage does not get through.
- `evasion` -- a **signed** bonus applied on the attack side. Positive is harder
  to hit, negative is easier. Heavy armour is meant to be *easier* to hit and
  much harder to kill in, so plate needs a negative evasion, and an author
  writing that has to be a deliberate act rather than an omission.

Both replace the single `defense` integer, which is currently spent only as
flat damage reduction at `combat.py:250/260/367`. No evasion concept exists in
`engine/` today.

The two axes are deliberately anti-correlated, so the palette has to make the
trade legible: a player choosing between light and heavy is trading "how often I
am hit" against "how much each hit matters".

'defense' is one integer spent only as flat damage reduction (combat.py:250/260/367). Add a signed 'evasion' field applied on the attack side, so heavy armor is easier to hit but far harder to kill in. No evasion concept exists in engine/ today.

## Acceptance

- TODO
