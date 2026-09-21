# task-436 — Task durations, and removing `ACTION_COSTS.time`

**Status:** steps 1–6 done — the per-turn action budget is replaced by the
timeframe-and-flow model. One substantial follow-up identified: **long tasks must
span turns as activities** (see the final section), which is what would make T=1
and T=15 agree exactly. Two cheaper attempts were tried and measured worse.
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

### Residual resolution dependence — open, root cause identified

Energy still differs between resolutions (T=1 67.1 against T=15 77.3). The first
explanation offered here — "`served` resets per turn" — was a guess, and two
attempts to fix it on that basis were made and **both measured worse**, so both
were reverted:

1. **Gate on the action's own duration instead of `served`.** Made it worse:
   Energy 64.0 / 75.6, Thirst 17.6 / 12.1. Gating on duration is far too
   permissive — it lets a character above the thirst threshold drink every two
   minutes.
2. **A `TASK_COOLDOWN_MINUTES` routine table** (eat 240, drink 45, wash 480, …).
   Also worse: Energy 60.7 / 80.3, Hygiene 55.8 / 69.3, against 67.1 / 77.3 and
   77.8 / 74.3 for `served`. More "realistic" intervals, worse convergence, and
   plausibly worse play (goblins washing twice a day sit at Hygiene 56).

**The actual root cause is an overdraft, not the gating.** At T=1 the timeframe is
one minute, `eat` reports 10, and the loop spends it anyway — so a character
performs fifteen whole tasks in fifteen minutes at T=1, while at T=15 the
timeframe only admits the two or three that fit. The binding constraint at T=15
is the timeframe itself, which is why no cooldown value could reconcile them.

**The fix is therefore the one the model already implies:** a task longer than the
remaining timeframe must **span turns as an activity**, exactly as eight hours of
sleep is 480 turns at 1 min/tick and 32 at 15. `p.activity` exists for this and
the flow loop already breaks when it is set — what is missing is that
`_consume_here`, `_relieve`, `_wash`, `_recreate` and `_recuperate` do not use it.
Until then, T=1 overdrafts every task cost and reads as the *unrealistic*
resolution; T=15's numbers should be treated as the reference.

`served` is kept as the shipping rule: it is the best-measured of the three, and
being turn-scoped it is also the simplest to reason about.

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
