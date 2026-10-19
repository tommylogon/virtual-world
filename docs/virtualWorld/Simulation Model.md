---
type: doc
tags: [system/world]
---

# Simulation Model

## What you can do

Understand what kind of thing you are playing. There is one kind of entity in
VirtualWorld — a character — and it can run at four processing levels: a simple
NPC, an LLM agent, a human, or a ghost. They all share the same body, the same
clock and the same graph, so nothing one of them does contradicts what another
sees. Survival is infrastructure rather than a treadmill: the meters exist so the
world has consequences, not so you spend the game refilling them.

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

### Perception is a channel, not a radius (designed, not wired)

"Could they hear me?" was answered by a **hop radius** — `radius_hops: 2` — which
counts edges on the graph. A wall that happened to be one extra edge away did not
muffle anything, and a sound that crossed a room was identical to one that
crossed a corridor. It also made audibility a property of the *graph* rather than
of the world, which is why a text world and a gridded world could not share the
same attention budget.

The replacement is a **channel** with attenuation: sound carries through ways and
is blocked by closed ones, and an area is aware of whatever the signal reaches.
`engine/awareness.py` implements that seam (`AwarenessChannel` / `SoundChannel` /
`AwarenessIndex`) plus a test double for a second channel, but nothing in the live
loop consumes it. Promotion is **scope-driven** (task-710): the loaded scope *is*
the boundary, so the attended-set cap and tier selector these channels were meant
to feed (task-411 / task-418) is cancelled, and `radius_hops` / `hysteresis` are
retired.

## Where a character is (task-419, landed)

A character has **one** spatial anchor at a time, and it is **relational**: `at`
the piano, `at` the stranger, `in` the alley — a relation to another node, not a
coordinate in a room. Two consequences the old model got wrong:

- A position is **walked to**. Any action that physically involves something
  (`open`, `go`, `give`, `attack`) steps the character there through the normal
  action flow; there is no separate `examine` first.
- There is an **anchor budget**. A character at the piano and *also* at the door
  was a bug, not richness.

Full mechanics, relation vocabulary and code map:
[[Gameplay/Character Spatial Position]] — source of truth
`engine/character_spatial.py`.

## Scopes: a place is a node, not a range (task-397, landed)

A **world scope** is a named, addressable region of the world with a parent, so
`Millbrook Falls > Downtown > The Pines > Floor 2` is a path a system can name and
a user can navigate. A scope is the unit of loading, of generation and of
projection:

- A graph request may ask for **one scope's projection** instead of the whole
  graph. The editor does this; the default view does not reveal the items a scope
  merely contains.
- A scope carries its own membership, so moving a building's interior moves the
  whole interior rather than scattering its rooms.
- An **unmade** scope is a declared-but-unbuilt place. It is a valid thing to
  point at, which is what makes generation (below) and chunking (task-401)
  possible at all.

A zone is therefore addressed by scope; nothing in the model needs a second
spatial representation to describe "inside".

## Making a place (task-398, landed)

An unmade scope with a **recipe** can be built deterministically: the same seed,
recipe version and clean fixture produce the same patch, and a second run creates
no duplicate nodes. The first recipe is `apartment.v1`
(`engine/generation_recipes.py`), which builds a three-area interior with real
ways, real items placed through the ordinary spatial edges, and provenance on
everything it made.

The rule that keeps this from becoming a second authoring system: **generated is a
provenance flag, not an ownership claim.** Once a person edits a generated item,
that edit outranks the recipe and a later generation cannot erase it. Generation
is the sanctioned way to mint an unmade scope, never a way to overwrite a made
one.

The `Generate` button and the preview surface are not built yet —
**task-580**.

## Time: a turn is a timeframe

- A **turn** is a timeframe of N game minutes. The world clock may run faster or
  slower than realtime; the pace is a chosen dial, not a constraint.
- Inside a turn, **every** character performs an action flow bounded by the turn's
  action tiers (major: 1, minor: 1, free: 3, activity: 1, defined in `engine/action_tiers.py`).
- The number of actions per turn is bounded by this fixed tier ceiling rather than
  scaling with `time_per_tick_minutes`. Actions do not cost game minutes on the player path,
  while background/soak simulation fills the timeframe using `TASK_TIERS` and task durations.

So a 1-minute turn and a 15-minute turn offer the identical action slot budget for
attended characters, while a soak character's flow fills the timeframe within the same
action-tier ceiling.

> **Superseded:** a per-turn *budget* of actions (`actions_per_turn = T`) derived
> slots from minutes. That assumed one-minute actions with no durations, which turned
> a 30-minute turn into thirty cycles. The action-tier model (task-352) fixes the slot
> allowance per turn while task durations bound coarse background flows.

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

That task is still open, and the honest reading of where we are: the *item* half
is fixed, the *actor* half is not. The two whole-graph item passes are now one
**area-major sweep** (task-416, landed) — a lit object left in a room and a plain
item owning an `on_tick` trigger both belong to their *area*, so they are
evaluated area by area (`_sweep_area_items` in `engine/tick_manager.py`), and
co-presence is a live reverse index rather than a per-turn scan.

The **acting queue is deliberately untouched** by that work: characters still
walk `player_manager.players` in registry order, so log order, need-threshold
messages and death handling are byte-for-byte unchanged. Area grouping is used
only where it is a scoped-evaluation win. Ordering the *actors* is still
task-437, and until it lands a resolution-order bug is a real, reproducible
hazard.

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
- A skip advances whole **turns of the scenario's frame** (`time_per_tick_minutes`),
  so the clock (ticks x dial) stays consistent: a 1-minute world resolves
  interrupts every minute, a 5-minute world every 5. The dial is never changed by
  a skip.
- Interrupt and promotion use the shared relevance evaluator (**task-466**):
  death, threat, vital/condition crossing, involuntary action, discovery, arrival.
- Zero LLM calls inside a skip; exactly one bounded memory is written on resume
  (**task-412**). `sleep` is the existing precedent for a duration task with the
  world ticking.
- **In a shared world a skip is a per-character order, not a table-wide jump.** It
  is declared on that character's turn and carried by the normal turn loop exactly
  like an agent or a distant NPC; the character becomes genuinely background
  (`simulation_mode`) and is promoted back to their player early on fear, a hostile
  condition, a vital in its danger band, or a watched discovery (**task-481**).
  The blocking "advance the world N minutes" is only the fast path when nothing
  attended remains.

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
- [[Gameplay/Character Spatial Position]] — one `at` per character, and the
  relations a spatial anchor may hold.
- [[World Building/World Scopes]] — the scope hierarchy, projections, unmade
  scopes and generation recipes.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Commands]], [[Emotion & Mood — Whole-System Analysis]], [[Feature Ledger]], [[Feature Map]], [[History]], [[Patch Notes 2026-08-22 to 2026-09-22]]

<!-- connected:end -->
