---
type: task
status: done
area: world
priority: high
---

# task-431: Baked `decay_rates` contradict the engine defaults, and break Social

**Filed:** 2026-09-21  
**Found while:** probing why Social is 0 for every character in a week soak
(task-423 recon).  
**Relates:** task-410 (food-limited survival), task-423 (social), task-425
(Entertainment), `tools/migrate_decay_rates.py`.

## Outcome (2026-09-21)

**Decision: the bake was stale, re-baked from the engine defaults.** The user's
call, on the evidence that three of eight vitals had drifted *upward* while five
matched exactly, and that the baked Social value silently disabled a shipped
mechanic (`SOCIAL_COMPANY_GAIN` 0.030 could never beat a 0.050 baseline).

Two changes:

1. **Re-baked every scenario** with `tools/migrate_decay_rates.py --all` — 93
   player records across 15 files. This turned up a second, larger class of drift
   the camp probe had hidden: **thirteen scenarios baked the legacy `1` for every
   vital** (the pre-2026-09 per-tick scale), which the per-minute engine applies
   as −1/min — vitals empty in about a hundred minutes. Those are fixed too.
   Verified mechanically that **only** `decay_rates` changed and every value
   equals the canonical default (17 JSON files, all clean). Three files the tool
   touched were reverted as semantic no-ops: `autosave.json`,
   `combat_pit.json`, `corsair.json` had an empty or absent `decay_rates`, which
   already means "use the engine defaults" — filling them would add churn *and*
   freeze the values against future recalibration.
2. **`SOCIAL_COMPANY_GAIN` 0.030 → 0.020**, equal to the Social baseline. The
   user's second decision: company is *maintenance* (it stops the rot), and
   **interaction is the source** (task-423). It was 0.030 against a 0.020
   baseline, and mere co-presence therefore filled Social.

Measured, one week, 23 background characters:

| | before | after |
|---|---|---|
| Social (15 min/tick) | 0 / 0 / 0 | **37 / 0 / 77** |
| Social (1 min/tick) | 0 / 0 / 0 | **34.3 / 0 / 80** |
| `social_breakdown` | **23 of 23** | **3 of 23** |
| Entertainment | 40.1 | 45.3 |

The two tick lengths agreeing is the property that matters.

### Not fixed here, and worth knowing

**Sanity is still 0 for all 23 characters**, and it is *not* the Social coupling:
with Social and Entertainment pinned at 100 for a whole week it is still 0/0/0
with all 23 `hallucinating`. Sanity is a meter with five drains and **no source**
(baseline 7.2/day alone empties an authored 65-90 in ~11 days). Filed as
**task-432**.

A regression guard now exists:
`tests/test_decay_rate_bake.py` fails if any scenario bakes a rate that
contradicts an engine default, with a `DOCUMENTED_DRIFT` allowlist for deliberate
per-scenario values, plus a test pinning `SOCIAL_COMPANY_GAIN <= baseline` so
co-presence cannot silently become the source again.

## Problem

Every character in `data/scenarios/kraktooth_goblin_camp.json` bakes a
`decay_rates` block. Three of those values disagree with `BASELINE_DECAY`
(`vital_rates.py`), and all three disagree *upward*, by 1.7x-2.5x:

| vital | engine default | baked | effect |
|---|---|---|---|
| Social | 0.020 | **0.050** | 2.5x |
| Hygiene | 0.020 | **0.050** | 2.5x |
| Entertainment | 0.030 | **0.070** | 2.3x |

Everything else matches (`Energy` 0.104, `Hunger` 0.0034, `Sanity` 0.005,
`Thirst` 0.025), and `Bladder` 0.42 is baked with no engine default — so this is
a partial, stale bake rather than a deliberate per-character profile. All 23
characters carry the identical values.

### Why this is a bug and not just difficulty

**Social is impossible.** `SOCIAL_COMPANY_GAIN` is 0.030/min and the baseline is
0.020, so company nets **+0.010/min** and Social should climb. With the baked
0.050 it nets **-0.020/min even while standing in a crowd**, so Social falls for
everyone no matter what.

Measured, one week at 15 min/tick, 23 characters background:
- baked rates: **Social 0 / 0 / 0** (avg/min/max) — with `SOCIAL_COMPANY_GAIN`
  firing 94 of 96 ticks for the sampled character, i.e. constant company.
- `--engine-decay`: **Social 99.2 / 84 / 100**.

The collapse then cascades, because Sanity is coupled to Social:

```
baked Social 0.050 > company gain 0.030
  -> Social falls even in company
  -> Social < 10  -> social_breakdown condition
  -> Social < 50  -> SANITY_PENALTY_SOCIAL_LOW   (tick_manager :565)
  -> Social < 25  -> SANITY_PENALTY_SOCIAL_VERY_LOW
  -> Sanity -> 0  -> hallucinating
```

After a week **every one of the 23 characters** carries both `social_breakdown`
and `hallucinating`. The camp ends with a population in collective psychosis,
and the cause is three numbers in the scenario file.

The one redeeming note: task-425's Entertainment work already overcomes its own
baked 0.070 (Entertainment ends at 40.1 with baked rates vs 45.3 with engine
rates), because fixtures and novelty are explicit sources rather than passive
trickle. Social has no equivalent explicit source yet — that is task-423.

## Decision needed

Which side is wrong?

1. **The scenario bake is stale** — re-bake from `BASELINE_DECAY`
   (`tools/migrate_decay_rates.py`), leaving the tuned engine defaults alone.
   Evidence for: three uniform values drifted upward while five match exactly,
   and the baked Social value silently disables a shipped mechanic.
2. **The engine defaults are wrong** — the camp is meant to be harsher, and
   `SOCIAL_COMPANY_GAIN` should exceed the intended baseline. Evidence for: it
   is a goblin camp; but then `SOCIAL_COMPANY_GAIN` must be raised above 0.050 or
   passive co-presence is dead by design.

Also worth deciding: with engine rates Social **pegs at 100** from mere
co-presence (+0.010/min is +14.4/day and nothing else competes). That is
harmless but inert. If interactions are supposed to be the social mechanism
(task-423), the passive `SOCIAL_COMPANY_GAIN` should probably drop to a
maintenance trickle and let explicit interactions carry the load — otherwise
task-423's Social deltas land on an already-capped vital.

## Acceptance

- A stated answer to "which side is wrong", recorded here.
- No shipped scenario has a baked rate that contradicts a tuned engine default
  without a recorded reason. (A test would be cheap: for each scenario, compare
  baked `decay_rates` against `BASELINE_DECAY` and fail on an undocumented drift.)
- A week soak at 1 and 15 min/tick ends with **Social above 0** and settling, and
  **no character in `social_breakdown`/`hallucinating`** unless something in the
  run actually caused it (starvation, an attack, a fear trigger).
- Sanity's own sources are *not* invented here — the coupling is left as authored;
  this task only stops Social from being impossible.

## Non-goals

- Retuning the whole survival balance (task-410 owns the food-limited constraint).
- Adding Sanity sources (comfort, company, fear relief) — task-425 non-goal.
- Per-character decay profiles; the bake is uniform today and stays so unless
  someone deliberately authors otherwise.
