---
type: task
status: done
area: characters
priority: medium
---
# task-484: Tune the frightened condition once real fears exist

**Filed:** 2026-09-23
**Related:** task-469; task-472; task-552

## Blocked on task-552, with the calibration data (2026-09-27)

The calibration this task is waiting on now exists, and the answer is that there
is **nothing to tune against yet**: no fears are being generated at all.

A 3-day Kraktooth goblin camp soak (4,320 ticks, 23 goblins and 5 humans, all
background, seed 1234) produced this `why` breakdown over every decided action:

| rule | share |
|---|---|
| `needs` | 82.2% |
| `social` | 16.3% |
| `traversal` | 1.0% |
| `forage` | 0.5% |
| `threat` | **0** |

Five humans lived inside the camp for three days — in the chief's pit, the cooking
area, the workshop — and not one goblin produced a `threat:` action. The mechanism
does not exist, so tuning `frightened`'s attack/defense modifiers or its
`ends_on` is premature: there is no producer to tune against.

**So this task stays blocked, deliberately, and should be closed rather than left
dangling if task-552 slips.** Tuning a condition that nothing applies is work
nobody can verify. The evidence belongs here so the decision can be made on a
measurement instead of on a date.

task-552 is the producer side: nothing in the simulation can represent "that is
not mine" or "that person frightens me". The natural test case is already in the
scenario — the Eldenford Road Guard Captain, the one human with a military job,
who starts on the Human Road and ends up in the goblin camp.

## Goal

Deferred from task-469: give 'frightened' real attack/defense modifiers and an
ends_on once authored fears are common enough to calibrate against.

## Acceptance

- TODO — blocked on task-552 producing fears. Do not start before then.

## Re-opened — 2026-09-28 (WT-C), after task-552 landed

task-552 shipped the producer side, so "do not start before then" is satisfied
in principle. It is not satisfied **in fact**, and the distinction decides how
much of this task is earnable now.

### What task-552 actually unblocked

`engine/fear.py` can now be made afraid of a co-located character, the fear is
applied with its source attached, and a background character reacts to it with a
recorded `threat:` action — 29 tests in `tests/test_fear_threat_response.py`.

But **no shipped scenario authors a single fear.**
`data/scenarios/kraktooth_goblin_camp.json` carries `"fear_tags": []` on all 28
characters, including the five humans. So the mechanism works and the *soak
table would still read zero* — there is no producer of fears **in any shipped
content**, and that file belongs to task-408 (WT-A).

### The honest split

**Done now — a correctness fix, not a tuning decision.**
`ends_on` was the one part of this task that was never actually a calibration
question. `frightened` gates behaviour toward one *named* source:
`engine.conditions.frightened_block` refuses an approach, a way, an area or an
item by name. A flag about a specific thing being present, kept after that thing
has left the world, is a stuck flag — and it sat there for its full 30-minute
timer regardless of whether the goblin was still standing there.

`engine.fear.release_absent_fears()` now lifts the instance whose source is
gone, called from both entry points (`react()` and `background_social.
run_fear_pass`) so detection and cleanup cannot disagree. It is **precise per
instance**: a character who fears two things and has lost one keeps the other
fear, which is why it does not simply call `end_instances` for everyone. The
reason string `"source_absent"` is declared on the condition's `ends_on` as the
documented cause, dispatched by fear.py rather than by a generic condition tick
— the same honest shape as every other `ends_on` entry in the catalog.

**Still not earned — the numbers.**
`defense_mod` (currently `0`), the check modifiers (`check_advantage` /
`check_disadvantage`, both empty), `speed_mult`, and `FEAR_DURATION_MINUTES`
itself are all **tuning**, and tuning needs a distribution. What exists today is
a table of hand-chosen weights in `engine/background_social.py` (`FEAR_COSTS`,
`FEAR_RELATIONSHIP`, `choose_fear_reaction`), not a measurement. Inventing a
`defense_mod` of −1 or −3 would be a guess dressed as a decision, and
`attack_mod: -2` was set before any fear had ever been applied, so it is not
evidence of anything either.

### Recommendation

**Stay blocked, or close as not-yet-earned.** The gate is now unambiguous and
one edit away: give the five Kraktooth humans `fear_tags: ["goblin"]` (the
`goblin` tag is already on every goblin) and re-run the 3-day soak. That
produces a real frequency, and with it the distribution the numbers need. Until
then this task has exactly one honest line of work left, and it is done.

If a decision is needed on whether `frightened` should affect defence at all —
which is a *design* question, answerable now — the current `defense_mod: 0` is a
defensible reading: adrenaline does not make you harder to hit, it makes you
fight worse. That is an argument, not a measurement, and is recorded here as
such rather than written into the condition.

