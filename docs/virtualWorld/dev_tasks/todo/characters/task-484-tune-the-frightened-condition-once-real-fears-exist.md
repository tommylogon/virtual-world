---
type: task
status: todo
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

