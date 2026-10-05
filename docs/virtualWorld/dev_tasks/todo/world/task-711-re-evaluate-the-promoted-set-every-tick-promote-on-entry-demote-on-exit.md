---
type: task
status: todo
area: world
priority: high
---

# task-711: Re-evaluate the promoted set every tick: promote on entry, demote on exit

**Filed:** 2026-10-05
**Related:** task-710,task-399,task-670

## Goal

The scope selection is a standing rule, not a one-shot click. A character who walks into the selected scope promotes; one who walks out goes back to backsim. Re-evaluated per tick against the focused scope's own areas.

This is the continuous half of the feature; task-710 owns the resolution rule and the Whole-world mode.

Known accepted cost: each demote->promote cycle writes one bounded background memory, so a character pacing across the scope boundary accrues one per crossing. The designer has accepted this for now and will revisit it only if it shows up as a problem.

## The half that does not exist yet

There is currently **no focus-driven demote anywhere in the engine.** Verified by
grepping production writers of `simulation_mode`: `promotion.py` (the bridge
itself), `serialization.py` (load), `soak_runner.py` and `timeskip.py` (span-scoped,
restored on exit), `structures.py` (materialisation side effect) and `soak.py`
(per-character orders). `activate_scope` only ever queues `"active"`.

So promotion exists and demotion does not. Left as-is, walking into a scope
promotes its residents and they stay agents forever.

## Acceptance

- [ ] Each tick compares every character's current area against the focused
      scope's own areas and queues the transition both ways. Entry promotes,
      exit demotes.
- [ ] The negative case is tested explicitly: a character that **leaves** the
      selected scope goes background. A test that only proves promotion passes
      against the shipped code.
- [ ] Demotion goes through `promotion.offload` so the span boundary is stamped
      and the later promotion consolidates it. A demotion that merely sets
      `simulation_mode` would silently produce an unsummarised span.
- [ ] Characters holding a `soak_order` are never touched by either direction.
- [ ] Whole-world mode short-circuits: no per-tick comparison, no demotion, no
      queued transitions at all.
- [ ] Transitions land through `promotion.flush()` at one tick boundary, so a
      character cannot be promoted and demoted inside a single turn.

## Measurement, not assertion

The regression test should assert the *mode* of a named character read from
inside the tick, the way task-670 measures `simulation_mode` from within
`tick_turn` rather than after the restore. Asserting the end state after the
span passes even when the transition happened at the wrong moment.

## Accepted cost

Memory churn on the boundary is accepted by the designer for now and is recorded
here so it is a decision rather than an oversight. Revisit only if it becomes a
problem — the lever, if it does, is a minimum background span before a span is
worth summarising, or hysteresis on the boundary.
