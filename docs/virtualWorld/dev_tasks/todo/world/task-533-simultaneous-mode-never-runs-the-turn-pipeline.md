---
type: task
status: todo
area: world
priority: high
---

# task-533: Simultaneous mode never runs the world turn pipeline

**Filed:** 2026-09-27
**Related:** task-101 (simultaneous), task-352, task-436, task-437
**Origin:** found while scoping task-352 (action economy).

## Goal

Simultaneous mode should be **turn-based with the wait removed**: every autonomous
character resolves their turn without waiting for the previous one, and the world
still advances its clock — by the normal increment — once **all** characters have
finished their turns.

That is the whole fix. There is no separate clock model for simultaneous mode, and
the increment is unchanged: still `time_per_tick_minutes` per round.

## The defect

`config.turnBased` is forced off whenever a simultaneous mode is selected
(`static/js/config.js`):

```js
156: async setTurnMode(mode) {
158: if (window.VWSimultaneous.isSimultaneous(this.turnOrder)) {
159: this.turnBased = false;
```

But **every** call site that drives the turn queue is guarded by `config.turnBased`
— `static/js/agent-engine.js` — and
`static/js/agent/turn-queue.js` (`reconcile`) returns early without it. The run
loop excludes it explicitly (`agent-engine.js`):

```js
930: if (!config.turnBased && config.controllingPlayer && !config.simultaneousMode) { await TurnQueue.endTurn; ... }
```

So in simultaneous mode the queue never advances, `TurnQueue.endTurn` never runs,
`POST /api/turn/apply` is never sent, and **`TickManager.tick_turn` is never
called**. It is not that the clock stalls — the entire world turn pipeline is frozen,
and only the characters the frontend happens to step do anything.

Everything in `engine/tick_manager.py` is skipped:

| Skipped |
|---------|
| `promotion.flush(gs)` |
| `on_turn_start` triggers |
| `conditions.process_tick` |
| vitals decay, drive grace/drain |
| environment effects, activity ticks |
| lit/standing item `on_tick` triggers |
| **`advance_clock(1)`** |
| time triggers |
| `npc_behaviors.process_simple_npcs` |
| **`BackgroundSimulation.process_due`** |
| **`soak.apply_orders(gs)`** |
| delayed events |
| heat / temperature / air / sound propagation |
| `on_turn_end` triggers |

Observable consequences: nobody gets hungry, tired, dirty or sick; no background
character acts; no item ticks; no time passes; no soak order progresses; triggers
bound to the turn never fire. A simultaneous-mode session looks alive because the
LLM characters are being stepped, and nothing else is happening at all.

## Fix shape

Advance the world once per **round** — when every character has had their turn,
human included — rather than per queue wrap, so it is independent of the mode.
Concretely: track which characters have resolved this round and call
`TurnQueue.endTurn` (or `POST /api/turn/apply`) when the set is complete, in both
turn-based and simultaneous paths. `_simultaneousStep` (`agent-engine.js`)
already processes exactly one ready character per iteration (`ready[0]`, line 960),
so it has the per-round bookkeeping it needs.

### The human is a participant, not an exemption

Two separate things, and the fix must not conflate them:

- **Never auto-act the human.** `agent-engine.js`
 (`if (!events.isAutonomous(name)) return false;`) stays. The world does not
 puppet a player character in any mode.
- **But do wait for them.** The human is in the round. A round is not complete until
 the human has taken their turn, so a slow player — or one who stops mid-turn —
 simply stalls the world advance. That is correct, and it is already how turn-based
 behaves: the human sits in the turn queue, `step` awaits the composer, and the
 wrap to `endTurn` waits on them. The fix should reproduce that in simultaneous
 mode, not carve the human out of it.

So the round-completion condition is "everyone has taken a turn", and "everyone"
includes the controlling player. Do not implement the advance as "all autonomous
characters are done" — that would silently make the world run ahead of a human who
is still deciding, which is a worse bug than the one being fixed.

Note that `_simultaneousStep` is not truly parallel — it serialises one character
per loop iteration and paces them with per-character cooldowns
(`VWSimultaneous.cooldownFor` / `tickCountdowns`). That is fine and is what "don't
wait for the previous character" means in practice; it is only the *clock* that was
missing.

## Also in scope (same code path)

`world._clock_advanced_by_task` is initialised `False`
(`virtual_world_engine.py`), set `True` by `rest`
(`engine/tick_manager.py`), and **never reset**. After one `rest` anywhere in
the world's life, `tools/game_tools.py` short-circuits its per-action tick
permanently. `tests/test_action_costs.py` sets the flag explicitly rather than
exercising the lifecycle, so nothing covers it. Fix or remove it here.

## Acceptance criteria

- [ ] The world clock advances in simultaneous mode. Pinned by a test that runs a
 simultaneous round and asserts `time_ticks` moved.
- [ ] `tick_turn` runs in simultaneous mode: a test asserts vitals decay,
 `BackgroundSimulation.process_due` and `soak.apply_orders(gs)` are reached.
- [ ] The increment is unchanged — still `time_per_tick_minutes` per round, not per
 character turn. A round is the unit, not a turn.
- [ ] The human is a full participant: never auto-acted, but the round does not
 complete until they have taken their turn, so a slow player stalls the world
 advance rather than being run ahead of. Pinned by a test that starts a
 simultaneous round with a human mid-turn and asserts `time_ticks` has **not**
 moved until the human resolves.
- [ ] A stalled human does not deadlock the run loop — cancelling or skipping the
 turn must still be able to close the round.
- [ ] `_clock_advanced_by_task` is reset correctly or removed, with a test covering
 the `rest` → next-action lifecycle rather than setting the flag by hand.
- [ ] `static/js/agent/turn-queue.js` is not left with a `config.turnBased` guard
 that can silently disable the advance in a future mode. If the guard is
 load-bearing, say why in a comment.
- [ ] `docs/virtualWorld/Environment/Time & Weather.md` is corrected — lines 24, 77
 and 94 still describe `time_per_tick_minutes = 5` (the code default is 1),
 actions that "consume time", and costs "multiplied by time ticks consumed".
 All three are stale under task-436.
- [ ] `docs/virtualWorld/Simulation Model.md` is reconciled: it says every
 character fills a timeframe in every mode, which is currently untrue.
- [ ] Per the standing rule, the time model is documented in code comments and the
 user guide / technical docs, not only here.
- [ ] Full suite compared against the ~60 failed / 3239 passed baseline.

## Non-goals

- **Changing the increment.** It stays `time_per_tick_minutes` per round. An earlier
 draft of this task explored per-action weighted durations and a 5-second
 increment; both are dropped. A turn *is* a timeframe, so actions within a turn
 being free in time is correct, and how many of them you may do is task-352's
 question, not this one's.
- True parallelism (all characters resolving against a snapshot). `Simulation
 Model.md` already names that as the fourth mode on the resolution-order dial
 and points at task-437.
- Reactions or off-turn triggers.

## Related

- task-352 — action economy. **Independent of this task**: the tier budget bounds how
 many actions fit in a turn, the round increment bounds the time. An earlier draft
 claimed the two had to be decided together because of a per-action time cost; that
 was wrong, because a turn is already the timeframe.
- task-436 (review) — removed time costs from `ACTION_COSTS`; left the
 `apply_action` comment claiming the caller advances the clock.
- task-437 — resolution order; the per-round advance must not make order dependence
 worse.
- `docs/virtualWorld/Simulation Model.md` — the timeframe model.
