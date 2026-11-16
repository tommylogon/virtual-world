---
type: task
status: todo
area: characters
priority: medium
related: [task-735]
wiki: "[[Characters/Persona]]"
---

# task-846: Pregnancy, gestation, and birth

<!-- deps:start -->
**Related:** [[task-735-aging-and-lifecycle-for-long-horizon-soaks-age-life-stages-pregnancy-and-birth]]
<!-- deps:end -->

## What

Split from task-735, which ships the clock, the stages, and old-age
death. This card is the rest: conception given willingness and
fertility-by-stage, gestation over sim time, birth, and the child
becoming a real character (spawn-character, task-295) at the parent's
location.

## Why

A 10-year soak that ages and kills but never births is half a
demography. But pregnancy is its own consent-gated, content-heavy
system (willingness, gestation tracking, infant behaviors) - it does
not belong inside the clock card.

## How

- Fertility by life stage (lifecycle engine owns stages; this card
  reads them).
- Willingness as an explicit gate (boundaries/consent vocabulary from
  the persona schema - never implied).
- Gestation as bounded per-character state (a due tick + stage, not an
  event store - the 735 scale note applies here too).
- Birth spawns via the existing spawn-character path (task-295) with
  `birth_tick` set to the birth tick, so the child enters the clock
  already.


## Browser UI and intended live verification

Intended UI home: Character Inspector -> Mind -> Bio / Lifecycle panel and Conditions tab.

Current availability: Planned; lifecycle clock and reproductive cycles are implemented in tasks 735 and 928, while gestation and birth delivery pipeline are in progress.

Live steps when available:
1. In Character Inspector -> Mind -> Bio, observe the pregnancy status and gestation progress of an expecting character.
   - expected: Gestation progress and estimated due date/stage are displayed.
2. Advance world simulation ticks past the gestation duration.
   - expected: A birth event fires, and the newborn character node is materialized at the parent's area.
3. Select the newborn character in the Agents list.
   - expected: Character Inspector shows valid node, birth tick, and relationship edge to the parent.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Run a controlled fertility/gestation sequence across the authored duration.
    - expected: pregnancy and birth visible as events; the child is a
      real character node with a valid location and private Player state.
    - observed: TODO
2. Confirm willingness gating with an unwilling pair.
    - expected: no conception, named reason.
    - observed: TODO

## Acceptance

- [ ] Conception requires willingness + fertility-by-stage.
- [ ] Gestation elapses over sim time to a live birth event.
- [ ] The child is a real character (node + Player + birth_tick).
- [ ] No unbounded per-character store.

## Files

- `engine/lifecycle.py` - stages read here
- `engine/spawn.py` or task-295 path - birth delivery
- `tests/test_pregnancy.py` (new)
