---
type: task
status: todo
area: world
priority: medium
---

# task-735: Aging and lifecycle for long-horizon soaks: age, life stages, pregnancy and birth

**Filed:** 2026-10-08
**Related:** task-670, task-733, task-685

## Goal

Make a 10-year soak credible: a character has an age that advances with sim time (birth tick + elapsed), passes through life stages, and can conceive, gestate and bear children, with the offspring becoming real characters. This is the clock and demographics a long-horizon simulation needs, not just two fields.

## Grounding (measured 2026-10-07)

- A ViWo character has `size` and `species` (`player.py:280-288`) but **no `age`**
  and **no pronoun**.
- There is **no aging mechanic**. The only `age` in the tree is `age_effect`
  (task-537), which is a spell effect, not lifecycle.
- Time advances via timeskip and the soak (`docs/design/long-horizon-simulation-progress.md`,
  task-670). So a 10-year soak currently changes nothing about who ages, who can
  bear children, or who dies of old age.

## Design

`age` only means something with a clock. The system:

- **Age** — a birth tick (or an authored starting age resolved to a birth tick
  from the world's current date), so `age = elapsed / year`. Advances with sim
  time, not wall time.
- **Life stages** — child / adolescent / adult / elder, gating behaviour,
  capability and fertility. Feeds prose and prompts (task-733's `age` field).
- **Fertility + pregnancy** — conception given willingness, fertility by stage,
  gestation over sim time, birth, and the outcome (a child) becoming a real
  character (spawn-character, task-295) placed at the parent's location.
- **Death by age** — lifespan by species, so a 10-year soak actually loses people.

This is a demographics/lifecycle layer over the background simulation, not two
fields. `pronouns` (task-733) is the prose side and is trivial by comparison.

## Scale note

A 10-year soak with the now-permanent memory model is its own problem: memories
are never trimmed (task-727/lived-log work), so a decade of events is a large
per-character memory set. Aging/pregnancy must not add another unbounded store
per character.

## Open questions

- Is `age` a definition field (authored) or runtime (birth tick + elapsed)? The
  answer decides whether it lives on the node (task-724) or the Player.
- Does the world have a real calendar/date, or only `time_ticks`? Aging needs a
  year length.
- Pregnancy, birth, and child characters are a large content surface (do children
  get behaviours/plans?). Confirm scope before building.

## Acceptance

- [ ] A soak advances a character's age; life stage changes at defined thresholds.
- [ ] Fertility/willingness can result in pregnancy → gestation → birth over sim
      time, and the child exists as a character afterwards.
- [ ] Death by old age is possible.
- [ ] `age` and `pronouns` are available to prose/prompts.
- [ ] No additional unbounded per-character store is introduced.
- [ ] Live: run a timeskip across a life-stage threshold and observe the change.
