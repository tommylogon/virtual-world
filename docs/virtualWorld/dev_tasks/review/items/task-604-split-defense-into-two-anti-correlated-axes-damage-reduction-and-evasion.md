---
type: task
status: review
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

- [x] An equipped item can carry a signed `evasion`; it is summed across worn
      pieces and applied on the attack side (`attack_roll >= defense_roll +
      evasion`). Positive is harder to hit, negative easier, omitted is 0.
- [x] `damage_reduction` is the canonical name for the old `defense` value, with
      `defense` still read as an alias so the ~1800 existing items are unchanged.
- [x] `aggregate_bonuses` returns both axes (`damage_reduction`,
      `damage_reduction_dice`, `evasion`) and keeps `defense`/`defense_dice` as
      aliases for existing callers.
- [x] Library placement copies both axes (`library_nodes.py`) and scenario
      assembly/sync round-trips them, so an authored axis is not silently lost.
- [x] Authored content exercising the trade: `plate_cuirass` (high DR, negative
      evasion) and `duelists_leathers` (low DR, positive evasion).
- [x] Isolation tests: `tests/test_defense_axes.py` covers the axes, aliases,
      and the evasion/miss contest.

## Resolution (2026-10-02)

Implemented. The two axes are deliberately anti-correlated in the authored
items: plate is easier to hit and hard to kill in; leather is the reverse.

- `engine/equipment_bonuses.py` reads `damage_reduction` (falling back to
  `defense`) and a signed integer `evasion`, returning both plus legacy aliases.
  Evasion is an int on purpose: a random per-hit contour would make a heavy suit
  sometimes easy and sometimes hard to hit for no authored reason.
- `engine/combat.py` computes `target_evasion` before the contest and compares
  `attack_roll >= defense_roll + target_evasion`; the log names it
  (`+ N evasion`) only when non-zero, so existing logs are unchanged.
- `engine/equipment.py:decrement_armor_uses_on_hit` no longer calls `int()` on
  `defense`, which would raise on a task-607 dice expression (`"d8"`).

Not done here: the editor palette that makes the trade visible is a UI surface;
the data model and combat resolution now carry both values for it to render.
