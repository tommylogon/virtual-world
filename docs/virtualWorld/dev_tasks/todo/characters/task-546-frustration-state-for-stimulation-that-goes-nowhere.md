---
type: task
status: todo
area: characters
priority: medium
---

# task-546: Frustration state for stimulation that goes nowhere

**Filed:** 2026-09-27
**Related:** task-488

## Goal

Stimulation with no route to release currently just sits on the meter. Give the engine a way to accumulate frustration (and release it) when arousal climbs with no satisfying outcome.

## Measured (2026-09-27)

- The pleasure vitals are `Stimulation`, `Arousal`, `Pleasure` (+ `Pain` in the
  report dict). There is **no** frustration value, condition, or accumulator
  anywhere in the engine today.
- `engine/tick_manager.py` has exactly one outlet for a full meter: the release
  cascade at `Stimulation >= 65 and Arousal >= 40`, which applies the satisfaction
  condition and resets the meters. A path that can never release therefore has
  nowhere to go but the same cascade.
- The nearest existing pattern is `sensitized` (an edging condition stacked by the
  tick pass while `50 <= Stimulation < 65`) — frustration is the same shape of
  thing with a different trigger, so a condition is the cheaper, more consistent
  representation than a new vital.
- Frustration needs an observable consequence to be worth building: it must feed
  at least one prompt line or behavior nudge, otherwise it is an invisible number.

## Open design decisions (settle before implementing)

1. **Condition or vital?** Recommendation: a `frustrated` condition with a tiered
   `symptoms` ladder, mirroring `sensitized`/`nipple_hard`, so it is visible in
   the existing condition/perception pipeline for free and needs no serializer
   change.
2. **What builds it?** Accumulated `Stimulation` above a threshold that no release
   has cleared, or (with task-545 in place) stimulation on any path other than the
   designated one. The second is what task-488 wants; the first is the general case.
3. **How does it discharge?** On release, on being touched on the right path, or
   only by its duration expiring. A frustration that can be worked off is a better
   play loop than one that only times out.
4. **Does it gate or only narrate?** If it ever blocks release on its own, it
   changes the release cascade for *everyone*, not just trait carriers.

## Acceptance

- Frustration accumulates when arousal climbs with no satisfying outcome, and it
  is observable (condition presence, symptom text, or a prompt line).
- It discharges under a defined condition rather than only expiring.
- Non-carriers are unaffected; nothing changes while `world.mature_content` is off.
- Test asserting accumulation, discharge, and that the ordinary release path is
  unchanged.

## Related

- task-488 — the consumer this unblocks
- task-545 — supplies the path knowledge that makes "wrong path" frustration possible
- task-209 (done) — `sensitized`, the edging condition this mirrors
