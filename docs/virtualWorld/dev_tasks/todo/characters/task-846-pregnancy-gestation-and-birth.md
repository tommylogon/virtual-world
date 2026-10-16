---
type: task
status: todo
area: characters
priority: medium
related: [task-735]
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
system (willingness, gestation tracking, infant behaviors) — it does
not belong inside the clock card.

## How

- Fertility by life stage (lifecycle engine owns stages; this card
  reads them).
- Willingness as an explicit gate (boundaries/consent vocabulary from
  the persona schema — never implied).
- Gestation as bounded per-character state (a due tick + stage, not an
  event store — the 735 scale note applies here too).
- Birth spawns via the existing spawn-character path (task-295) with
  `birth_tick` set to the birth tick, so the child enters the clock
  already.

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

- `engine/lifecycle.py` — stages read here
- `engine/spawn.py` or task-295 path — birth delivery
- `tests/test_pregnancy.py` (new)
