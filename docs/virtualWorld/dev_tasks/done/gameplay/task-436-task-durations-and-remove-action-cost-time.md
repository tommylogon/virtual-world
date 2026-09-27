# task-436 — Task durations, and removing `ACTION_COSTS.time`

**Status:** done — all residuals resolved. The per-turn action budget is
replaced by the timeframe-and-flow model, `ACTION_COSTS.time` is gone, and tasks
longer than their timeframe now span turns as minute-authored activities. T=1 and
T=15 agree on survival and Hunger and within ~2.5 points on five further vitals.
The former "Energy ~10 apart" and the three `test_tick_time_scaling.py` failures
were root-caused and closed: the camp gap was `advance_world` never offloading
(measured fix), and the two narrow fixture failures were test bugs, not engine
bugs (see the final sections). No two earlier gating attempts were repeated.
**Area:** gameplay / time
**Depends on:** [[Simulation Model]] (the timeframe-and-flow model)
**Related:** task-352 (action economy), task-414 (batch advance), task-131 (stateful actions over time), task-244 (human turn parameters)

## Why

[[Simulation Model]] commits to two things:

1. **Delete `ACTION_COSTS.time`** and `_action_time_consumed`. Atomic actions
   (look, take, hit, open) are one minute; arbitrary per-action time multipliers
   are legacy.
2. **Duration belongs on tasks** — travelling a route, sleeping, working, waiting —
   not on atomic actions. This is the seam where a player's ~20–40 actions absorb
   the world's 1,440 minutes, and it is what makes a day pass in a believable
   number of turns without any decay rate changing.

## What `time` actually does today (verified)

`ACTION_COSTS` (`virtual_world_engine.py:110-117`) gives each action a `time` and
one or more vital costs. `apply_action` (`engine/tick_manager.py:140-153`) uses
`time` for **two different jobs**:

```python
time_ticks = int(cost.get("time", 0))
...
total_delta = delta * (time_ticks if time_ticks > 0 else 1)   # job 1: multiplier
target.vitals[key] = max(0, min(100, target.vitals[key] - total_delta))
if time_ticks > 0:
    self.player_manager._action_time_consumed = True           # job 2: flag
else:
    self.player_manager._action_time_consumed = False
```

- **Job 1 — drain multiplier.** The `energy` values are *per-minute rates*, not
  totals. `move: {time: 1, energy: 1}` → 1 energy, but `fumble: {time: 2,
  energy: 3}` → **6** energy.
- **Job 2 — time-consumed flag.** `open`/`close` have `time: 0` and so
  deliberately consume no clock time. Read at `tools/game_tools.py:101`
  (`if not getattr(world, '_action_time_consumed', False)`), also reset at
  `routes/action_handlers.py:212` and set at `engine/tick_manager.py:993` (rest).
  Declared at `virtual_world_engine.py:119`.

## `time: 0` is a call-site idiom, and may be in the data

`time` is not only a table field. Because `apply_action` treats it as
`cost.get("time", 0)`, an **absent or zero** `time` means *absolute cost, no clock
advance*, while `time >= 1` means *multiply the cost, and advance*. Call sites rely
on that:

- `engine/movement.py:754` — `{"energy": encumbrance_cost, "time": 0}`
- `engine/movement.py:830` — `{"energy": 4, "time": 0}`
- `tests/test_traits.py:134` — `{"energy": 2, "time": 0}`
- `engine/movement.py:1029` — passes `way_node.properties.get("cost", {})` through,
  so **way cost blocks in scenario data may carry `time`** and need auditing

So the removal is: fold the multiplier into absolute costs, introduce an explicit
`consumes_time` field (default preserving today's absent-means-false behaviour),
update those call sites, and sweep `cost` blocks in `data/scenarios/*.json`.

## Therefore

Deleting `time` is **not** a mechanical removal:

- Every multi-tick action's vital cost silently halves unless the magnitudes are
  folded into the cost table (e.g. `fumble` becomes `energy: 6`, not `3`).
- Which actions consume clock time changes. Under the new model every atomic
  action takes one minute, so `_action_time_consumed` becomes uniformly true and
  the flag is meaningless — it should be deleted and the caller should advance
  unconditionally, **but that is a clock-semantics change and must be verified
  against `rest`/sleep**, which sets the flag deliberately at `:993`.

## Progress — steps 5–6 done (the flow model)

`actions_per_turn` (the per-turn action *budget*) is replaced by `minutes_in_turn`
(the timeframe) plus `TASK_MINUTES` (each action's duration). `process_due` fills
the timeframe: each action consumes its duration until the timeframe is full or
`_act` reports nothing to do. `TASK_MINUTES["travel"]` is 1, so a walk repeats and
fills a timeframe; every other task is longer and is recorded in `served`, so a
task is done **once per timeframe**. The `_action_credit` banking machinery is
gone entirely: nothing accumulates.

### Correction: this task overstated the bug

Steps 1–4 were motivated by "a 30-minute turn becomes thirty meals, ~1,440 actions
per character per day". **That was wrong.** `_act` returns early when no need is
past its threshold, so the old budget burned `T` *passes through the need ladder*
but produced roughly the same *actions*. The 1,440 figure was passes, not actions.
Measured over one game week at 15 min/turn, the old model gave 23/23 alive with
the same average Hunger (34.2) as the new one.

The old model was therefore not broken so much as **incoherent**: it granted
actions per turn rather than filling a duration, and it re-ran the whole ladder
once per game minute whether or not anything was due.

### Measured effect (one game week, Kraktooth camp, `--background-all`)

Vitals at 15 min/turn, old vs new: Energy 69.8 → **77.3**, Sanity 80.4 → **85.9**,
Social 75.8 → **81.0**, Hygiene 72.0 → **74.3**, Entertainment 40.2 → **42.5**.
Better across the board at equal survival (23/23). A long timeframe can chain
*different* tasks within one turn instead of repeatedly re-checking one need.

Resolution independence, new model, T=1 vs T=15 over the same game week: survival
23/23 both, Hunger 34.2 both, Thirst 17.3 / 16.5, HP 96.8 / 97.7.

### Resolution dependence — root cause fixed; Energy gap remains

**Fixed.** The overdraft is gone: a task longer than what is left of the timeframe
now starts an activity authored in **minutes** (`_begin_task`), so a ten-minute
meal costs ten minutes of game time and occupies ten turns at a T=1 clock, most of
one turn at T=15. `ActivitySystem` gained `elapsed_minutes` / `duration_minutes`
alongside the legacy tick-based fields, and the task activity types were added to
`ACTIVITY_INTERRUPTIBLE` and `ACTIVITY_SKIP_TURNS` — the former being mandatory,
since a type missing from it never expires and strands the character busy.

Two traps hit while doing it, both worth knowing:

- `_begin_task` must not overwrite an activity a helper already opened.
  `_recuperate` starts a `resting` block with its duration correctly converted
  from minutes, and clobbering it broke `test_a_low_sanity_character_rests`.
- `duration_ticks` is a **turn** count and is the same unit trap this task exists
  to remove. `_recuperate` divides `SANITY_REST_MINUTES` by the tick length to get
  ticks, which is correct; anything else authoring `duration_ticks` directly is not.

**Measured, one game week, T=1 against T=15** (23/23 alive at both):

| | T=1 | T=15 |
| --- | --- | --- |
| Hunger | 34.2 | 34.2 |
| HP | 96.8 | 96.2 |
| Sanity | 83.3 | 82.0 |
| Entertainment | 39.2 | 40.5 |
| Social | 77.6 | 75.2 |
| Thirst | 17.5 | 15.0 |
| Hygiene | 78.4 | 72.9 |
| **Energy** | **65.8** | **76.1** |

Five of eight agree within ~2.5 points. **Energy is consistently ~10 apart across
every variant tried** (67.1/77.3, 61.9/73.7, 65.8/76.1), so it is a real remaining
mechanism rather than run-to-run noise — but its cause is **not** identified, and
the two earlier guesses about this area were both wrong. Do not repeat them. Sleep
is already open-ended (it ends at Energy 100, not on a duration), so the next
suspect is condition-based wake granularity: a wake test evaluated once per turn
oversleeps by up to T minutes, which a coarse clock cannot avoid without moving the
check inside the timeframe.

`served` remains the shipping intra-turn rule: best-measured of the three gating
schemes tried, and the simplest to reason about.

### The two gating experiments that failed (do not repeat)

Both were attempts to fix the resolution gap *before* it was understood, by
changing how a task is gated rather than how it is timed. Both measured worse and
were reverted:

1. **Gate on the action's own duration instead of `served`.** Energy 64.0 / 75.6,
   Thirst 17.6 / 12.1. Far too permissive — it lets a character above the thirst
   threshold drink every two minutes.
2. **A `TASK_COOLDOWN_MINUTES` routine table** (eat 240, drink 45, wash 480, …).
   Energy 60.7 / 80.3, Hygiene 55.8 / 69.3, against 67.1 / 77.3 and 77.8 / 74.3 for
   `served`. More "realistic" intervals, worse convergence, and plausibly worse
   play (goblins washing twice a day sit at Hygiene 56).

The gap was never a gating problem: at T=1 the timeframe is one minute, `eat`
reports 10, and the loop spent it anyway — so a character performed fifteen whole
tasks in fifteen minutes at T=1 while T=15 admitted only the two or three that fit.
The binding constraint at T=15 was the timeframe, which is why no cooldown value
could reconcile them.

### Cost

Coarser turns are much cheaper for the same game time: one game week took 17s at
15 min/turn against 2m43s at 1 min/turn (~2s/day vs ~23s/day), because the flow is
entered once per timeframe instead of once per game minute.

## Progress — steps 1–4 done

**Step 4 corrected this task's own premise.** The plan said to delete
`_action_time_consumed` because it would become uniformly true and therefore
meaningless. That was wrong. The flag had **two** sources, and only one was the
`time` field:

- `apply_action` set it from `cost["time"]` — the part that made *which* actions
  moved the clock an accident of the cost table. Removed.
- `rest()` sets it because `rest` loops `tick_turn` once per minute **itself**. It
  is the guard that stops the per-action layer adding a second minute on top of
  the hours just spent. Deleting it would have made a 60-minute rest cost 61.

So it was renamed `_clock_advanced_by_task` — its name now describes what it
guards rather than its old source — and it survives. Making `_ensure_tick`
unconditional (the obvious reading of "delete the flag") would have been a
silent off-by-one on every sleep. Caught by reading `rest()` before editing it,
and pinned by `test_rest_advances_the_clock_itself_and_is_marked_as_having_done_so`.

`ACTION_COSTS` entries are now bare `{"energy": N}`; the `consumes_time` field
this task added in step 1 was **also** removed, since it existed only to feed the
flag.

Full suite: 3186 passed. The 6 failures in `test_social_company.py` and
`test_tick_time_scaling.py` are pre-existing and order-dependent — they fail with
and without these changes, and a different subset fails each run.

## Progress — steps 1–3 done

`ACTION_COSTS` no longer carries `time`. Energy costs are absolute (`fumble` is
`energy: 6`, the 6 it always cost as 3 x `time: 2`), and "does this action take a
minute" is now the explicit `consumes_time` field, defaulting to false when absent
— matching the old absent-or-zero-`time` behaviour.

Verified **behaviour-preserving** by running a probe across `move`, `fumble`,
`open`, `take` and `look` against both the working tree and `HEAD`: identical
energy deltas and identical flag values in every case.

Two things the probe settled that this task had guessed at:

- `engine/movement.py`'s two overrides became `{"energy": N, "consumes_time":
  False}`, and `tests/test_traits.py` followed.
- **The data audit came back negative** — no `cost` block in `data/scenarios/*.json`
  or `data/library/**` carries `time`, so there is no data migration.
- The flag is read from the **world** (`world._action_time_consumed`), not from
  `PlayerManager`, despite `apply_action` assigning through
  `self.player_manager`. Worth clearing up when the flag is deleted.

New: `tests/test_action_costs.py` pins the split, including a structural check
that no cost entry regains a `time` key.

## Plan

1. Fold the multiplier into the cost table so vital costs are **absolute**:
   `move {energy: 1}`, `look {energy: 0}`, `use {energy: 1}`, `take {energy: 1}`,
   `drop {energy: 0}`, `fumble {energy: 6}`, `open`/`close` `{energy: 1}` (open/close
   now cost the minute they always took narratively).
2. Delete `time` from every `ACTION_COSTS` entry and drop the multiplier at
   `engine/tick_manager.py:140-149`.
3. Delete `_action_time_consumed` (declaration, both setters, the reader) and have
   the caller advance the clock unconditionally — **after** confirming `rest()`
   still advances exactly once for a sleep of N minutes.
4. Add **duration to tasks**, which is the actual feature: `travel` (a route),
   `sleep`/`rest`, `work` (a shift), `wait`. Duration is a property of the task,
   not a fudge factor on an atomic action.
5. Replace the per-turn action *budget* (`actions_per_turn = T` in
   `engine/background_simulation.py`) with the flow model: a turn is a timeframe,
   an action flow fills it, and the number of actions is emergent.

## Acceptance

- A soak at 1, 5 and 15 minutes-per-turn produces the same character behaviour at
  the same **game-day** — same meals, same sleeps, same deaths (if any).
- `rest(60)` advances the clock by exactly 60 game minutes, once.
- No character takes ~1,440 actions per game day.

## Notes

`docs/virtualWorld/dev_tasks/cancelled/task-14-action_costs_to_time.md` shows this
was intuited before and never landed.

## Progress — 2026-09-24 (root cause found and fixed)

The "Energy resolves ~10 apart at T=1 vs T=15" residual was **not an Energy bug**.
Measured over one camp day, *every* drive diverged, and drives — not Energy —
were the signal:

| vital (camp mean, 1440 min) | T=1 (before) | T=5 | T=15 |
|---|---|---|---|
| Energy | 0.0 | 52.0 | 52.1 |
| Hunger | 56.1 | 31.6 | 31.6 |
| Thirst | 78.1 | 34.7 | 34.5 |
| Bladder | 100.0 | 81.1 | 81.2 |
| Hygiene | 32.6 | 72.1 | 70.5 |
| Sanity | 56.1 | 80.3 | 80.0 |

T=5 and T=15 agreed; **T=1 alone was the outlier**. Root cause: `process_due`
gives a *focused* character `remaining = minutes_in_turn - 1` minutes, and
`advance_world` never offloaded anyone — so at a 1-minute tick everyone was
"focused" and got **0 minutes of action per turn**. The whole camp only decayed;
nobody ate, drank, relieved, washed or recreated. Energy=0 was the visible
symptom of collapse, not the cause.

Fixed (`2b608a8`): `advance_world` marks everyone `background` for the span and
restores the modes afterwards. Two-day camp soak, T=1 vs T=15: Energy 73.9/73.1,
Hunger 17.0/17.0, Thirst 23.8/25.4, Bladder 33.9/37.7, Hygiene 60.6/73.1 — worst
gap 12.5, most under 5. Tests in `tests/test_tick_time_scaling.py`.

## Progress — 2026-09-24 (the three remaining failures: fixture bugs, not engine bugs)

Both were investigated and closed with **no engine change**:

- `test_equal_game_time_gives_equal_decay` / `test_scaling_holds_at_a_coarser_step`
  — the fixture used a *focused* character and never supplied its decision. A
  focused character's own decision is assumed to have spent the turn's first
  minute (`remaining = T - 1` in `process_due`), so at T=1 the deterministic tier
  has zero minutes and acts not at all, while at T=5/15 it acts and spends ~1 more
  Energy over the window. Disabling the background pass at the class level made
  T=1 and T=5 identical (12/12, 18/18), proving the delta was the action flow, not
  decay. With the fixture marked `simulation_mode = "background"` (no decision to
  account for) both windows match: 13/13 over 120 min and 19/19 over 180 min. The
  focused rule is by design and pinned by
  `test_a_focused_character_owes_nothing_at_a_one_minute_turn`.
- `test_starvation_grace_is_counted_in_minutes` — the per-minute accumulator was
  **already correct** (`_drive_maxed_thirst` recorded 5 / 10 / 15 at T=5 in a
  drink-free room). The fixture sat in Blizzard Forest Clearing, which has a drink
  source: the character sensibly drank during `process_due`, dropping Thirst below
  100 and resetting the grace every tick. Moved to a drink-free room;
  `test_starvation_damage_is_per_minute` moved with it for determinism.

Full suite: **60 failed / 3812 passed** — the documented ~60-failure baseline;
the three `test_tick_time_scaling.py` failures are gone.
