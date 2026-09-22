# Simulation Model

The reference model for how the world runs: one kind of entity at four processing
levels, one clock, and survival that is infrastructure rather than a treadmill.

Part of [[_Index]].

## One entity, four processing levels

**There is no difference between an agent and a player.** Both act, both take
actions, both spend time. The only difference is the *controller*:

| Level | Controller | LLM? | Notes |
| --- | --- | --- | --- |
| Soak NPC | cheap policy | no | Farthest from any observer; survives or doesn't. |
| Simple NPC | simple policy | no | Scripted/scheduled behaviour. |
| Agent | LLM policy | yes | Decides better, using the same action set. |
| Human | human policy | no (the human *is* the model) | Same engine path as an agent. |

All four exist **on the same scale**, in the same world, on the same clock, with
the same action flows. They differ in *how well* the next action is chosen and in
how much it costs to choose — never in what an action *is*.

This is why the engine must not privilege the player: the player's character runs
the same action flow as everyone else. The only special case is that **the engine
must never decide for the human** — who supplies the decision, not what kind of
thing the entity is. `BackgroundSimulation.process_due` is the shared executor;
it skips only the human's own character, and only for that reason.

## Cognition refines; it never creates capability

An LLM-driven character must be able to do only what the cheap policy could also
do — just chosen better.

If an LLM can do something the cheap tier cannot, then what the world becomes
depends on who happens to be watching it. Keep the cheap tier a *valid but
suboptimal* policy and scale becomes an engineering problem instead of a
correctness one.

## Attention and scale

The world is millions of nodes. Only the **perceivable slice** — the area you are
in, your neighbours, what you can see and hear — needs to be live. Everything else
runs the cheap policy.

- A human player in an area promotes nearby characters to LLM cognition.
- Editor focus does the same.
- Nothing else is promoted.

Scale is therefore bounded by *attention*, not by world size.

## Time: a turn is a timeframe

- A **turn** is a timeframe of N game minutes. The world clock may run faster or
  slower than realtime; the pace is a chosen dial, not a constraint.
- Inside a turn, **every** character performs an action flow that fills the
  timeframe. Actions have durations.
- The number of actions per turn is **emergent** — as many as fit — not a budget
  handed out per turn.

So a 1-minute turn holds one one-minute action, and a 30-minute turn holds
*eat (10) → walk (5) → talk (5) → wait (10)*. Four actions, not thirty. All
characters, at all four levels, use the same clock and the same flows.

> **Superseded:** a per-turn *budget* of actions (`actions_per_turn = T`) described
> one action per game minute. That assumed one-minute actions with no durations,
> which turns a 30-minute turn into thirty eat/drink/socialise cycles — 1,440
> actions per character per day. The timeframe-and-flow model replaces it.

### Resolution order

"Every character acts in the timeframe" implies the outcome should not depend on
the order they are processed in — otherwise whoever goes first gets the food, the
bed and the clear path for no in-world reason.

Today it does depend on it, and invisibly: the frontend queue has a chosen order
(sequential / random / initiative) but `process_due`, the social pass and the
simple NPCs each iterate a *different* order, with the background tier using dict
insertion order. Reversing the roster alone moved a one-week soak's Energy by 4
points. So the resolution order is world state and belongs to the engine, resolved
once, seeded, stored per timeframe, keyed by **id**, and then read by both the
simulation and the UI. `simultaneous` is the fourth mode on that same dial —
resolve against a snapshot and commit together — not a separate axis.

See **task-437**.

### Timeskip actions

The player can hand their character to a **deterministic policy for a span**:
declare an intent and a duration, and the world advances minute by minute at
maximum speed, interrupting back to the human the moment anything relevant
happens. This is the controller swap this model already implies — same Player,
same clock, same flows; only *who chooses* changes, and everyone else is already
at soak fidelity.

- **Intents:** `idle` (do nothing), `leisure` (eat/drink/roam), `search`,
  `explore`, `travel` (a known route, or a heading toward a belief).
- **No stasis, no protection.** Vitals decay and the environment applies; a wait
  in a forest with no food or water can kill. The skip removes *decisions*, not
  *consequences*.
- A skip always advances **1-minute ticks** regardless of the scenario's
  `time_per_tick_minutes` (which is restored afterwards), so interrupts land on a
  minute boundary. Normal play keeps the frame dial.
- Interrupt and promotion use the shared relevance evaluator (**task-466**):
  death, threat, vital/condition crossing, involuntary action, discovery, arrival.
- Zero LLM calls inside a skip; exactly one bounded memory is written on resume
  (**task-412**). `sleep` is the existing precedent for a duration task with the
  world ticking.

See **task-464** (hub), **task-467** (belief travel + maps), **task-468**
(background agendas that make interrupts actually happen).

## Survival: slack and emptiness

Survival is not a battery you must keep full. It is **maintenance with slack**:

- Meters are buffers with days-to-weeks of slack (roughly: water ~days, food ~weeks,
  sleep ~days).
- **Harm accrues only while a meter is empty, never from a meter being low.**
  A character at 5% water is *thirsty*, not dying, and stays alive indefinitely
  while they keep sipping.
- Partial intake extends the buffer. You never need to top up — you only need to
  not bottom out.

This is the mechanic that removes the treadmill: the routine is sufficient by
construction. The dials are **how much slack** and **how long emptiness takes to
hurt** — not the percent-per-minute rate.

## Routine over hunt

A believable world does not route survival through decisions. People eat because
it is mealtime and the food is *there* — larder, cookfire, well, bed. Survival
succeeds quietly in the background.

Deprivation, not maintenance, is the crisis. Starvation should be an **event**
(winter, siege, being lost, an injury) rather than a clock, so that:

- Running a week should kill nobody through neglect.
- Removing the infrastructure should produce a crisis over days.

Both together mean survival is something an infrastructure can *lose* — which is a
story — rather than a bar the player fights.

## What this commits us to

- **Delete `ACTION_COSTS.time` and `_action_time_consumed`.** Atomic actions
  (look, take, hit) are one minute. Arbitrary per-action time multipliers are
  legacy.
- **Duration belongs on tasks** (travelling a route, sleeping, working a shift,
  waiting), not on atomic actions. This is the seam where a player's ~20–40
  actions absorb the world's 1,440 minutes.
- **One executor for all levels** (done): focused and unfocused characters share
  the same deterministic action pathway.
- **Balance is authored per scenario** as slack and thresholds, so a horror
  scenario shortens slack rather than inflating rates.

## Related

- [[Time & Weather]] — the clock, calendar, and the author-in-game-minutes rule.
- [[Turn Queue & Human Turns]] — whose turn it is and what the human supplies.
- [[NPC Behavior System]] — the simple/background policies.
- [[Vitals System]] — the meters themselves.
- [[Activities & States]] — durations and blocking activities.
