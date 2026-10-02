---
type: task
status: done
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

- [x] **Frustration accumulates when a build has no satisfying outcome**, and it
      is observable — a `frustrated` condition with a four-step `symptoms` ladder
      and a log line for the active player.
- [x] **It discharges under a defined condition rather than only expiring** — a
      release ends it (see below, which required fixing a pre-existing gap).
- [x] **Non-carriers are unaffected**, and nothing changes while
      `world.mature_content` is off.
- [x] **The ordinary release path is unchanged** — the first test in the file.
- [x] Tests in `tests/test_stimulation_paths.py` covering accumulation,
      discharge, and the unchanged ordinary path.

## Decisions, following the task's own recommendations

1. **A condition, not a vital** — mirroring `sensitized`, so it is visible in the
   existing condition/perception pipeline for free and needs no serializer
   change. `data/library/conditions/frustrated.json` is the authoring, with
   `stack: accumulate` so it is a *build* rather than a flag, `ends_on:
   ["duration", "release"]`, and `periodic: {Sanity: -1}` so it costs something
   while it lasts.
2. **What builds it**: a build that reaches the release threshold and is *refused*
   by the gate (task-488). The general case — stimulation above a threshold no
   release has cleared — is the same event here, because the only gate that
   exists is `single_track`.
3. **It discharges on release**, which required a real fix (below), and by
   duration. A frustration that can be worked off is the better loop.
4. **It does not gate.** Frustration is the visible *consequence* of a blocked
   build. If it ever blocked release on its own it would change the release
   cascade for every character in every world — which the task explicitly
   declines, and which would make it a second invisible gate.

## A pre-existing gap this task's acceptance exposed

`ends_on: ["release"]` was declared on **four** mature conditions
(`sensitized`, `highly_aroused`, `frantic`, and the new `frustrated`) and
**nothing ever honoured it**: `Player.end_instances(action)` existed, delegated
correctly to `condition_end_instances`, and had **zero callers**. So every one of
those conditions could only ever end by its duration expiring.

Fixed at the one place a release happens — the cascade in `_pleasure_tick` — which
makes the declaration true for all four and discharges frustration as a side
effect rather than a special case. This is the kind of thing AGENTS.md's "never
infer runtime behavior from existence" rule is about: the mechanism was complete
and correct and simply had no caller.

## Implementation — 2026-10-02 (WT-characters-engine)

### Files

- `data/library/conditions/frustrated.json` — **new** condition.
- `engine/tick_manager.py` — `_build_frustration`, and `p.end_instances("release")`
  in the cascade.
- `tests/test_stimulation_paths.py` — the `frustrated` tests.

### A bug the negative test caught

The gate's ancestor match was written `if key in region_chain(key)` — which is
true for **every** key — instead of `if named in region_chain(key)`. That made
`_single_track_designated` return the first recorded path regardless of what was
named, so the gate released everything and task-488 was a no-op. It is fixed, and
it is worth recording because the only thing that caught it was a test asserting
that a *wrong* path does not release: every other assertion in the file would
have passed.

### Verify

```
python -m pytest tests/test_stimulation_paths.py -q                           # 21 passed
python -m pytest tests/test_pleasure_system.py tests/test_body_parts.py \
  tests/test_conditions.py tests/test_traits.py \
  tests/test_stimulation_paths.py -q                                          # 225 passed
python -m pytest tests/test_condition_catalog.py -q                          # passed
```

**Full suite compared by failure NAME against the clean-master baseline**: 15
failed on both, `Compare-Object` empty.


## Related

- task-488 — the consumer this unblocks
- task-545 — supplies the path knowledge that makes "wrong path" frustration possible
- task-209 (done) — `sensitized`, the edging condition this mirrors
