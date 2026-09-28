---
type: task
status: review
area: world
priority: low
---

# task-498: Elevation-gated chained sightlines across ways

**Filed:** 2026-09-24
**Related:** task-496, task-418, task-421

## Goal

Extend beyond-visibility from per-adjacent-way to a chained line of sight: an observer sees along a run of open/see_through ways as long as the floor property does not change; a floor step (or the run turning) breaks the chain. Build on see_through and visible_in_direction and floor (engine/lighting.py, engine/area_description.py, engine/movement.py, engine/room_perception.py). Decide the range/depth cap and whether a sighted cell reveals room contents or only the area name/description. Must not regress tests/test_beyond_visibility.py.

## Acceptance

- An observer sees along a run of open/`see_through` ways whose `floor` is unchanged; a floor delta or a direction change breaks the chain (tests).
- The range/depth cap is configurable and documented.
- The "contents vs name/description only" question is decided and recorded.
- `tests/test_beyond_visibility.py` and the lighting tests still pass.

## Progress — 2026-09-28 (in `review`)

`engine/beyond_visibility.py` gains `sightline_run()` and
`chained_sightline_summary()`. The existing depth-1 `build_beyond_suffix` is
**untouched**, so task-201's behaviour is unchanged; the chain is a second,
explicit call the description builder can make.

### The two decisions the task asked to have made

**1. Depth cap: 3, configurable as `sightline.depth`.** A run of three open
doorways is a corridor you can see down; a run of four is almost always a plan
that has lost sight of its own exits. Higher values *compound* — each step reports
that room's contents — so a depth of five is effectively an inventory of the
building. The cap is a taste decision, so it lives in Engine Config where it can
be argued with, and is clamped so a negative value is a disabled sightline rather
than a crash.

**2. A sightline reveals a room's NAME and who or what is in it. It never reveals
its exits, its description, or anything past it.**

- *Contents are included* because excluding them would be inconsistent with the
  depth-1 behaviour task-201 established, and would make a corridor report **less**
  the further you could see — backwards.
- *Exits and descriptions are excluded* because those are what would let a
  character navigate a floor they have not walked. That is task-499's fog of war,
  and a sightline that handed over the exits would undo it without anyone having
  decided that it should.

Tested both ways: a room's `description` never appears in the clause even when it
is loaded with the word SECRET, and the word "exit" never appears.

### Two things the tests forced that are not obvious

**A straight run keeps the SAME compass direction at every hop.** My first version
flipped the direction each hop, which walks back down the corridor you arrived by
and reports an empty world. The turn-break is better than an explicit check
because the graph already encodes it: the edge out of a room names the direction
its way lies in, so looking east from a room whose only east way leads back the
way you came finds a way you have already seen and the run stops. No special case
needed — and a test asserts a corner stops it.

**A floor step breaks the chain on the way that CARRIES the new storey**, so the
room beyond the stairway is not reported — the line of sight left the floor it
started on, and the stairway is where it left. A stairway *between* two rooms is
still visible across; nothing beyond it is.

**A way with no `floor` recorded does not break the run.** A hand-placed way that
never declared a storey has not claimed a different one, and treating "unknown" as
"different" would blank every hand-authored corridor in the game. That is a real
population, not a theoretical one.

The solid states are read through `engine.barriers.declared_state` — the shared
ladder from task-421 — so a new way state cannot be "open by omission" here the
way it would have been for light and sound. A test walks all six.

### New tests — `tests/test_sightlines.py` (22)

A full open run and its per-step depth/direction; the cap at 3 and its
configurability, including a nonsense value and a negative one; a floor step up
and down; a stairway across-but-not-beyond; missing floors; a turn; a closed door
and a locked/blocked/hidden way each breaking the run while a window does not; a
cycle terminating rather than looping; a room with no way; every compass
direction; the contents-vs-name decision both ways; people named once; the empty
clause; a single step reading like the existing task-201 line; the graph not
mutated; and task-201's `build_beyond_suffix` still behaving.

`tests/test_beyond_visibility.py`, `test_area_description.py` and
`test_lighting.py` all still pass (85 together), as the task's last acceptance
line requires.
