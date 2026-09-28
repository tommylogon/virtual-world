---
type: task
status: done
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

## Implementation — 2026-09-28 (WT-C)

### The soak's diagnosis was half right, and the wrong half was load-bearing

*Right*: the background tier never called `engine/fear.py`. `fear_sources` and
`apply_frightening` existed and worked, and nothing in
`engine/background_simulation.py` or `engine/background_social.py` ever asked.
So zero was structural, not a low rate — "no mechanic exists" was correct.

*Wrong*: nothing would ever have been afraid even once something did ask.
`fear_sources` matched a co-present character on the **graph node's** `tags`
property. A character node is created bare —
`Node(id=..., type="character", name=pname)` at `engine/serialization.py:552`
and again on the add path — so it never carries `tags` at all. Meanwhile every
shipped character puts its species in `player.tags`: `"goblin"`, `"teen"`,
`"female"` in `data/library/characters/Arix.json:47` and in every block of
`data/scenarios/kraktooth_goblin_camp.json`. Nothing read that.

So `fear_tags: ["goblin"]` on a human would have done **nothing**. The mechanic
was inert twice over, and only the first half was visible in the telemetry.

Fixed in `engine/fear.py` (not `serialization.py`, which is a hub):
`character_tags(gs, other)` now reads `other.tags`, the trait keys and the node,
and `fear_sources` and the new `fear_sources_for_character` both go through it.
`tests/test_fear_threat_response.py` asserts the node really is bare, so the day
that changes the test is the one that has to move.

### What was built

- **`engine/background_social.py`: `run_fear_pass(gs, tick)`** — for every
  background character, ask `engine/fear.py` what it fears, apply the
  source-gated `frightened` condition, and record a **visible action**: a line, a
  `threat:` trace in `lived_log`, a `threat`-type memory, a Social cost, an
  `afraid` spike on the affect map, and a closeness cost toward the source.
- **Four reactions** — `flee`, `hide`, `freeze`, `shout` — chosen by a draw
  seeded from `(character, source, tick)` like every other roll in the module, so
  a replay reproduces the same camp history and five characters do not flee in
  lockstep. This answers open decision 2: fear moves someone, and the action is a
  `threat:` one, because there is no `plan:` substrate to run to and inventing
  one is not this task.
- **Fear pre-empts sociability.** `perform()` returns `None` when the actor fears
  the target, so a human does not chat with the goblin that frightens them. The
  gate is checked *before* the action draw, not after, or the social roll would
  still decide.
- **Cooldown** (`FEAR_COOLDOWN_MINUTES = 45`) so a condition lasting thirty
  minutes logs one flight, not thirty. The condition keeps refreshing meanwhile.
- **`engine/background_simulation.py`: one call**, before the social pass, so
  something frightening can pre-empt it. `run_fear_pass` is inside the existing
  `try`, so a fear failure cannot take the social passes down with it.

### Open decisions, settled

1. **Fear of what** — answered by *authoring*, not by code. `fear_tags` already
   existed and is already serialized (`engine/serialization.py:346`). The
   question "species or territory" is task-549 and task-550's; this task only had
   to make the field mean something. Both are expressible: species through
   `player.tags`, territory once areas have tags (below).
2. **Does fear move anyone** — yes, four ways, recorded as `threat:`. See above.
3. **Eldenford road guard** — not used as a datapoint. He is a single authored
   character in a different scenario; the test scenario here is authored
   specifically to provoke a response, which is what acceptance asks for and is
   reproducible without a 3-day soak.

### A second dead branch, recorded not papered over

`fear_sources` also looks for an **area**'s `tags`. `Area.__init__` has no tags
parameter and `add_area` (`engine/movement.py:68`) writes only `description` and
`environment`, so that branch can never fire either. Wiring it means adding a
`tags` property to areas — a data-model change in `area.py`/`movement.py`, which
is task-550's territory, not something to smuggle in here. Recorded with a test
that asserts the current state so it cannot drift unnoticed.

### The remaining half is data, and it is not mine

`data/scenarios/kraktooth_goblin_camp.json` has `"fear_tags": []` on **all 28
characters**, including the five humans. With the pass in place the mechanism is
ready and the table would still read zero — because nobody has authored a single
fear. That file is task-408's (WT-A), so it is handed over rather than edited.

### Handed to WT-0 / WT-A

- **WT-A (task-408, the goblin camp)**: give the five humans
  `fear_tags: ["goblin"]`. The `goblin` tag is already on every goblin. That one
  edit is what turns this task's calibration table from a test fixture into a
  measured soak, and it needs no code change.
- **Nobody (parked, task-550)**: area `tags`, which would make the area branch of
  `fear_sources` live and give territory something to be afraid of.
- **WT-0**: nothing. No hub file was touched.

### Verify

`python -m pytest tests/test_fear_threat_response.py -q` — 21 tests. And
`python -m pytest tests/ -q -k "fear or threat or background"` — 160 tests.

The new file covers both halves: a shipped-style `player.tags` entry is enough to
register a fear source; the character node really is bare (the bug, pinned); trait
keys still count; a character with no `fear_tags` is never frightened; **a goblin
is not afraid of goblins**, which is what lets a camp exist; someone in another
area is not a source; and areas cannot be a source yet. On the pass: a fear
records a `threat:` action with a line, a memory, the `frightened` condition
carrying its source, a Social cost, an `afraid` spike and a closeness cost; every
reaction has a line; the draw is deterministic; five characters do not flee in
lockstep; the same flight is not logged on consecutive ticks; **a goblin camp of
goblins produces nothing**, which is the honest result; and fear pre-empts
sociability toward the source but not toward anyone else.

## Calibration data for task-484

The table task-484 was waiting for, now that fears actually exist:

| observation | value | where it comes from |
|---|---|---|
| fear source | any co-present character whose tags intersect `fear_tags` | `engine/fear.py fear_sources` |
| condition | `frightened`, source-gated, 30 game minutes by default | `FEAR_DURATION_MINUTES` |
| trigger | co-presence in one area — there is no distance or line-of-sight model | `fear_sources_for_character` |
| re-log gap | 45 game minutes per character | `FEAR_COOLDOWN_MINUTES` |
| Social cost | −2 to −6 by reaction | `FEAR_COSTS` |
| `afraid` spike | +6 to +11 on the affect map | `FEAR_COSTS` |
| closeness toward source | −1 to −5 by reaction | `FEAR_RELATIONSHIP` |
| reaction mix | flee 3.0 (+2 cowardly), hide 2.0 (+1 loner), freeze 1.5, shout 1.0 (+1.5 hostile) | `choose_fear_reaction` |
| resolution | deterministic from (character, source, tick) | `random.Random` seeded per draw |

What this does **not** give 484: a frequency. The rates above are hand-chosen
weights, not measurements, and the only way to get a measured frequency is to
re-run the Kraktooth soak once the humans carry `fear_tags` — which needs
WT-A's task-408 first. 484 should stay blocked on that, or be closed as
not-yet-earned, and this table is what makes either call an evidence-based one
rather than a date-based one.
