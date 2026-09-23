---
type: task
status: done
area: characters
priority: medium
---

# task-432: Sanity has no recovery source — it is a one-way meter

**Filed:** 2026-09-21  
**Found while:** verifying the task-431 decay re-bake (Sanity read 0 for all 23
characters in every soak, and stayed 0 after Social was fixed).  
**Relates:** task-431 (the decay re-bake), task-425 (Entertainment/novelty),
task-423 (social). `engine/player_conditions.py` (paranoid / hallucinating).

## Outcome (2026-09-21)

Both decisions taken as recommended: **sources are the existing fixtures + rest +
company** (no new subsystem), and the **self-drain is removed** from the two
breakdown conditions.

**The self-lock was the worse half.** `hallucinating` drained Sanity at -2/min and
`social_breakdown` at -1/min, against a passive baseline of 0.005/min — so
-2/min was 400x the baseline and -2880/day. A character who reached hallucinating
could never climb back out however well they lived, and low Sanity is what causes
the condition. Both drains are gone; the behavioural penalty (`attack_mod -2`,
`defense_mod -2`, and whatever else the condition carries) is the cost, which is
the same reasoning as "low Sanity makes a character dangerous, not dead".

**Sources**, all reusing what the world already models:

| source | where | a night / a block gives |
|---|---|---|
| sleep | `ACTIVITY_REGEN["sleeping"]["Sanity"]` = 0.025/min | ~12 over 8h |
| rest | `ACTIVITY_REGEN["resting"]["Sanity"]` = 0.05/min | ~3 over 60 min |
| meditation | `ACTIVITY_REGEN["meditating"]` (already existed at 0.05) | — |
| company | `SANITY_COMPANY_GAIN` 0.004/min while Social >= 70 | ~5.8/day |

The sleep rate is sized against what Sanity actually loses in *this* camp: 7.2/day
passive plus `ENV_DARK_SANITY` (the goblin camp is a cave, up to 28.8/day), so
roughly 20/day of inflow. The first attempt at 0.10/min overshot badly — every
character sat at 100 within a week, which just makes the meter inert — so the
rates are deliberately under the drain, with rest and company making up the rest.

**A rest step in the background tier**, because sleep alone could not help
everybody: `_tick_sleeping` wakes a character the moment Energy is full *before* it
checks any duration, so sleep cannot serve anyone who is not exhausted, and a
character whose day costs little Energy never slept and never recovered its mind.
That is who the five chronically low characters were. `_act` now rests for
`SANITY_REST_MINUTES = 60` when Sanity is low — a bounded block on purpose, since
`_act` skips anyone mid-activity and a sprawling rest would stop them eating.
(An earlier attempt that simply sent low-Sanity characters to *sleep* killed four
of them that way: they woke immediately on full Energy, looped, and starved.)

**Measured**, one week, 23 background characters:

| | before | after (15 min/tick) | after (1 min/tick) |
|---|---|---|---|
| Sanity avg | **0** | 80.3 | 76.0 |
| Sanity min | 0 | 13 | 23 |
| `hallucinating` | **23 of 23** | 4 of 23 | 4 of 23 |
| alive | 23/23 | 23/23 | 23/23 |

The same four are low at both tick lengths — Croak-Mother (Social 30),
Silver-Talon (39), Tusker (36), Old Iron-Back — so it is a property of the world
rather than noise: the sedentary, poorly-connected characters sit on the edge of
hallucinating while nineteen campmates are fine. Not darkness, which is what the
first hypothesis was; they are in the *lit* Camp Entrance.

**Knobs if they should be healthier:** `SANITY_THRESHOLD` (40),
`SANITY_REST_MINUTES` (60), the sleep rate, `SANITY_COMPANY_MIN_SOCIAL` (70).

`tests/test_sanity_sources.py` — 16 tests, including that the conditions no longer
drain Sanity (with a note on why), that a night beats the passive drain without
pegging the camp, that the company gain stays *below* the baseline (a steadying
influence, not a source), and that the rest block is bounded and expressed in game
minutes.

## Problem

Sanity is drained from at least five places and restored from none:

| drain | where |
|---|---|
| baseline `0.005/min` = **7.2/day** | `vital_rates.BASELINE_DECAY`, applied every tick |
| darkness (`ENV_DARK_SANITY`, light < 20) | `tick_manager` |
| low Social (`SANITY_PENALTY_SOCIAL_LOW` / `_VERY_LOW`) | `tick_manager` |
| low Entertainment (`SANITY_PENALTY_ENT_LOW` / `_VERY_LOW`) | `tick_manager` |
| `social_breakdown` (−1/min), `hallucinating` (−2/min) | condition `periodic` |

Authored Sanity is 65-90 across the camp. The baseline alone (7.2/day) empties
an 80 in about eleven days, so a one-week run drops roughly fifty points — and
nothing anywhere puts any back. `comfort` / `rest` / `meditate` end
`hallucinating` but are *ends_on* actions, not sources: ending a drain is not the
same as refilling the meter.

**Measured** (15 min/tick, one week, 23 background characters): Sanity
**0 / 0 / 0** — and with Social *and* Entertainment pinned at 100 for the whole
run it is *still* 0/0/0 with all 23 `hallucinating`. So this is entirely
independent of the Social coupling task-431 fixed; it is simply a meter with no
inflow, and every character therefore ends the week hallucinating by arithmetic
rather than by anything that happened to them.

## Design questions to settle

1. **What restores Sanity?** Candidates already present in the world model:
   sleep in a safe/sheltered place, company (it is a *social* animal need),
   comfort/recreation fixtures (the task-425 pattern), daylight, a religious or
   ritual site, and the `comfort`/`rest`/`meditate` activities becoming sources
   rather than just condition-enders.
2. **Is the baseline itself right?** A purely passive 7.2/day with no inflow
   means every character is guaranteed to reach 0 on a fixed schedule. Either the
   baseline drops to a trickle that only bites when nothing maintains it, or
   sources must comfortably exceed it — the same "maintenance vs source" shape as
   task-431's Social decision.
3. **Should `hallucinating` be reachable in a normal week at all?** Right now it
   is the default end-state. It should be what happens when someone is starved of
   rest/safety/company, not the baseline condition of the whole camp.

## Acceptance

- A one-week soak at 1 and 15 min/tick leaves Sanity **above 0 and settling**,
  with characters who are actually deprived (isolated, dark, no rest) the ones
  who drop.
- `hallucinating` is not universal; it correlates with something in the run.
- Sanity has at least one explicit authored source (fixture, activity, or tile)
  rather than existing only as a drain, so it is not hardcoded into the tick.
- The dark-room penalty still works, and a candle/lantern remains a real answer
  to it.
- Survival unchanged: Sanity must never drain HP (that is deliberate — it makes a
  character *dangerous*, not dead).

## Non-goals

- Fear/paranoia content, sanity-break narratives, or the `paranoid` branch.
- Reworking the Social/Entertainment coupling penalties; task-431 settled Social.
- Mental-health realism beyond a meter with believable sources and sinks.
