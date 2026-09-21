---
type: task
status: todo
area: characters
priority: medium
---

# task-432: Sanity has no recovery source — it is a one-way meter

**Filed:** 2026-09-21  
**Found while:** verifying the task-431 decay re-bake (Sanity read 0 for all 23
characters in every soak, and stayed 0 after Social was fixed).  
**Relates:** task-431 (the decay re-bake), task-425 (Entertainment/novelty),
task-423 (social). `engine/player_conditions.py` (paranoid / hallucinating).

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
