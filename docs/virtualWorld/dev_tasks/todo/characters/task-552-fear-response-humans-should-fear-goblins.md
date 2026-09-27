---
type: task
status: todo
area: characters
priority: high
---

# task-552: Fear response: humans should fear goblins

**Filed:** 2026-09-27
**Related:** task-484,task-550

## Goal

A 3-day Kraktooth soak produced zero threat-tagged actions with five humans living inside the goblin camp, because nothing in the simulation can represent 'that is not mine' or 'that person frightens me'. Add a fear/territory response, and give task-484 the calibration data it has been waiting on.

## Measured (2026-09-27) — a 3-day soak produced zero threat actions

Kraktooth goblin camp, 3 days (4,320 ticks), 23 goblins and 5 humans, all
background, seed 1234. The `why` breakdown over every decided action:

| rule | share |
|---|---|
| `needs` | 82.2% |
| `social` | 16.3% |
| `traversal` | 1.0% |
| `forage` | 0.5% |
| `threat` | **0** |
| `plan` / `goal` / `schedule` / `agenda` | **0** |

Five humans lived inside the goblin camp for three days — in the chief's pit, the
cooking area, the workshop — and **not one goblin registered a threat response**.
The busiest room by shared occupancy was `Waste Disposal` at 45,844 shared ticks
across five pairs, i.e. the most sociable thing in the world is the latrine.

This is the finding the whole thing rests on: nothing in the simulation can
represent "that is not mine" or "that person frightens me". A threat response
therefore has no substrate to act on, which is why the number is zero rather than
low.

## task-484 has been waiting for exactly this

`task-484` is a deferred stub — "give 'frightened' real attack/defense modifiers
and an `ends_on` once authored fears are common enough to calibrate against" —
with `## Acceptance — TODO`. The calibration data is this table, and it says the
answer is *no fears are being generated at all*, so tuning the condition is
premature until something produces one. 484 should stay blocked on this task, and
this task should produce the fears.

## Open decisions

1. **Fear of what?** Species (task-549), territory (task-550), numbers, or being
   outnumbered? All four are plausible and they are not the same mechanic.
2. **Does fear move anyone?** A `frightened` goblin flees, hides, or freezes — and
   if it flees, is that a `plan:` or a `threat:` action? Right now `plan` is zero
   too, so nothing has anywhere to run *to*.
3. **Is the Eldenford road guard a datapoint?** He is the one human with a
   military job and he starts on the Human Road. He is the natural test case.

## Acceptance

- A character can be made afraid of another, and the fear produces a recorded,
   visible action rather than a silent vital.
- A test asserts a threat response occurs in a scenario authored to provoke one,
   so "zero threats" stops being indistinguishable from "no mechanic exists".
- task-484's calibration data is attached to it, so it can be un-blocked or closed
   as not-yet-earned on evidence rather than on a date.

## Related

- task-484 — the deferred tuning task this unblocks or refutes
- task-550 — territory is probably half of what is being feared
- task-549 — species is the other half



- TODO
