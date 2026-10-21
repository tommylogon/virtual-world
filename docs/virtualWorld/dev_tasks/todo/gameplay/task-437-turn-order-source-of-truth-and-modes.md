---
blocked_by: [task-436]
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[Simulation Model]]"
---

# task-437 - One turn order, owned by the engine, with simultaneous as a mode

**Status:** todo
**Area:** gameplay / time / engine
**Depends on:** task-436 (timeframe-and-flow model - done)
**Absorbs:** task-310 (reroll initiative / random order), task-101 (simultaneous room turns)
**Related:** task-244 (human turn parameters), task-241, task-338 (turn queue docs)

<!-- deps:start -->
**Blocked by:** [[task-436-task-durations-and-remove-action-cost-time]]
<!-- deps:end -->

## Why

There is no single answer to "who acts first", and the order that matters most is
the only one nobody chose.

Four orders exist today:

| Where | Order | Chosen by |
| --- | --- | --- |
| Frontend turn queue (`static/js/agent/turn-queue.js`) | sequential (alphabetical) / random / initiative | the player, via `config.turnOrder` |
| `BackgroundSimulation.process_due` | **dict insertion order** | nobody - an accident |
| `run_social_pass` | its own per-area order | nobody |
| `process_simple_npcs` | its own order | nobody |

So a character can be 3rd in the queue the UI shows and 19th in the order the
world actually resolves them - and the world's order is the one that decides who
gets the last food, the bed, or the clear path.

`turn_order` is also **dead data**: `tools/build_scenario.py:261` stamps
`"sequential"` into every scenario and **no Python reads it**.

### Measured evidence

Reversing the roster order in `process_due`, changing nothing else, moved a
one-game-week soak at T=15 as follows (survival unchanged at 23/23):

| | normal | reversed |
| --- | --- | --- |
| Energy | 76.1 | 80.1 |
| Thirst | 15.0 | 18.4 |
| Sanity | 82.0 | 78.3 |
| Entertainment | 40.5 | 38.2 |
| HP | 96.2 | 96.9 |

Insertion order is therefore a **material, invisible determinant** of outcomes.
That is the thing to remove: not because a metric drifted, but because the world
is quietly cheating in favour of whoever was registered first.

## The dial

One setting, four modes, answering one question - *how does a timeframe resolve?*

- **sequential** - one fixed order, applied serially.
- **random** - a fresh seeded sequence each timeframe, applied serially.
- **initiative** - a seeded d20+DEX sequence each timeframe, applied serially.
- **simultaneous** - no sequence: resolve against a snapshot, commit together.

Three share an implementation shape; `simultaneous` does not. That is a difference
in mechanism, not in kind, so it belongs on the same dial - which also means any
two modes can be A/B'd against each other, which is how the "does order actually
matter to how this feels" question gets answered.

**Simultaneous is not a reason to skip contention work**: handling only *contended*
resources (the last item, one bed, a shared door) is a legitimate internal
optimisation of the mode, not a different mode.

## How

1. **The engine resolves and stores.** At the start of a timeframe the engine
   resolves the order once - seeded - and **stores the resolved list for that
   timeframe** as a fact. The simulation reads it, the API exposes it, the UI reads
   it.
   - Do **not** let both sides compute it. If the server shuffles and the client
     shuffles independently you get the current divergence plus non-determinism.
     **Share the data, not the logic.**
2. **Ids, not names.** The queue is name-based today, which contradicts
   `[[Simulation Model]]` (`id_backed_character_identity`, task-316) and breaks the
   moment two characters share a name.
3. **Read `turn_order` for real.** The engine reads it from the scenario/engine
   config, so the setting stops being dead data and the client-side value stops
   being the authority.
4. **Frontend keeps the cursor, loses the ordering.** `currentTurnIndex`,
   `advance()`, the turn panel: presentation, stays. `initialize()`'s sorting,
   `reshuffleRandom()`, `rerollInitiatives()`: deleted, replaced by reading the
   server's list. `config.turnOrder` becomes a display of the server's mode, not a
   client-side decision.
5. **`simultaneous` implementation, in two stages.**
   - **Stage 1 - snapshot decisions, serial deterministic commit.** Each
     character's flow reads the world as it stood at timeframe start, then effects
     apply in a fixed commit order. Cheap, removes the *information* advantage
     (which is what the measurement above is measuring). Does **not** make
     contention fair: the commit order still decides who gets the last item.
   - **Stage 2 - intent/effect separation with explicit conflict resolution.**
     `_act` emits what the character *tries* to do; a commit step applies it and
     resolves collisions deterministically. This is the real thing, and it is what
     makes the mode's contract true.
6. **The contract, stated once, tested:** in `simultaneous`, the outcome does not
   depend on processing order. That is checkable - reverse the roster and the
   result must not move.
7. **Determinism is mandatory.** Conflict resolution, shuffles and initiative
   rolls must all be seeded, or soaks and tests stop being reproducible.

## The payoff beyond fairness

Intent/effect separation makes **"a player is an agent with a different
controller"** structurally true rather than merely asserted: human, agent, simple
NPC and soak NPC all emit the same kind of thing into the same resolver. Today
`_act` mutates the world directly, which is why the four levels *look* like four
different systems even though the model says they are one.

It also unifies the human turn with the timeframe: the player's action becomes an
intent folded into the same commit, instead of a special path.

## Acceptance

- The order the UI shows **is** the order the world resolves in.
- Reversing the roster changes nothing observable in `simultaneous` mode.
- Same seed + same scenario ⇒ identical outcomes, in every mode.
- `turn_order` is read by the engine and is no longer dead scenario data.
- No character is identified by name in the resolved order.

## Notes

`task-310` is already implemented on the frontend (`reshuffleRandom`,
`rerollInitiatives`) and sits in `review/` as though it were not. Its remaining
work is exactly step 1–4 above - moving the decision to the server. `task-101` is
step 5.

## What

Give the engine one turn order and make it the only one. Today four orders
run at once: the client queue resolves one from `config.turnOrder`, while
`BackgroundSimulation.process_due`, `run_social_pass` and
`process_simple_npcs` each walk their own roster in whatever order it
happens to be in. The order that decides who gets the last food, the bed or
the clear path is therefore an accident of registration order rather than a
choice anyone made, and the card's own measurement shows it is material -
reversing the roster moves Energy, Thirst, Sanity and Entertainment at a
one-week soak. The work is to move the resolution into the engine: at the
start of each timeframe the engine resolves the order once, seeded, stores it
as a fact for that timeframe, and the API and the UI both read that stored
list instead of computing their own - share the data, not the logic. One
setting with four modes (sequential, random, initiative, simultaneous)
answers the single question "how does a timeframe resolve?", and
simultaneous in particular must not depend on processing order at all. The
resolved order is carried by opaque character ids, not by names, and
`turn_order` stops being dead scenario data.

## Reconnaissance (2026-10-20) - VERDICT: STILL_VALID

Re-checked the four-order claim against the live code. Nothing newer has moved
the turn order under the engine; the card is accurate as written, and its
"Dependency reality" note that task-436 is done still holds.

**The order is still client-owned.** `static/js/agent/turn-queue.ts` (326
lines) still resolves the order itself: `switch (config.turnOrder)` at line 85,
`config.turnOrder === 'random'` at line 163, `config.turnOrder === 'initiative'`
at lines 244 and 291. It reads `config.turnOrder`, never a server-resolved list.
There is no `resolvedOrder`, `turnOrder`, or `turn_mode` field in the engine:
a scan of `engine/*.py` for `turn_order|turnOrder|turn_mode|turnMode|simultaneous`
returns exactly one hit, `engine/character_appearance.py:916`, which is the word
"in" a comment about simultaneous drawing, not a mode.

**`turn_order` is still dead scenario data.** `tools/build_scenario.py:318`
still stamps `"turn_order": runtime_overrides.get("turn_order", "sequential")`,
and a repo-wide scan for `turn_order` in `.py` files outside `dev_tasks/`,
`.kilo/`, `docs_combined.md` and `git-history.txt` returns no readers.

**task-533 did not absorb this card.** task-533 ("Simultaneous mode never runs
the world turn pipeline") is `done`, but it is a different claim: it fixes the
simultaneous-mode *pipeline*, not the *ordering*. The mode dial this card asks
for (sequential / random / initiative / simultaneous on one engine-owned
setting) is still not implemented. Confirmed by the absence of any
`turn_mode`/`simultaneous` switch in `engine/`.

**task-465 (turn mode dial) did not land either.** task-465 is `done` ("Turn
mode dial: fold Simultaneous into the mode dropdown + add Simultaneous per
room"), but its scope is the UI dropdown and per-room simultaneous, not the
engine-owned resolved order this card's step 1-4 require. The frontend still
computes the order; the server still does not own it.

**task-310 is still in `review/`** and its remaining work is still exactly this
card's step 1-4. task-101 is still in `review/` and is still this card's step 5.

**Line numbers in the card's "Why" table are current.** `static/js/agent/turn-queue.js`
is 326 lines (the `.ts` is the source; the card's `151-158` range is inside
`advance()`, which still increments and wraps the index). `routes/action_handlers.py`
does not exist - the decay handler moved; `routes/action.py:108` registers
`POST /api/world/timeskip`, and `engine/timeskip.py:179/273` are the two
advance entry points. That drift is recorded, not a change in fact.

The card stays in `todo`.

## Steps to verify

1. Compare the engine's resolved order for one timeframe against the client
   queue, the Turn Order panel and the event-stream "up next" strip.
   - expected: all three list the same character ids in the same order as the
     server-resolved value.
   - observed: not run. Measured 2026-10-20: there is no engine-resolved
     order to compare against. `static/js/agent/turn-queue.ts` still resolves
     it client-side (`config.turnOrder` at `:85`, `:163`, `:244`, `:291`), and
     a scan of `engine/*.py` for `turn_order|turnOrder|turn_mode` returns no
     reader at all.
2. Reverse the roster and run the same seed in simultaneous mode.
   - expected: observable resolution does not move when the roster is
     reversed.
   - observed: not run. Measured 2026-10-20: no `simultaneous` mode switch
     exists in `engine/`, so the mode cannot be exercised. The card's own
     earlier measurement (reversing the `process_due` roster moved Energy
     76.1 to 80.1 and Thirst 15.0 to 18.4 at T=15) is the standing evidence
     that order still decides outcomes.
3. Run the same seed and scenario twice in each supported mode.
   - expected: identical outcomes every time, and the UI order is the exact
     order the world consumed.
   - observed: not run. Measured 2026-10-20: `tools/build_scenario.py:318`
     still stamps `"turn_order": runtime_overrides.get("turn_order",
     "sequential")` into every scenario and no Python reads it, so the
     setting is still dead data and there is nothing yet to make
     deterministic.
4. Give two characters the same display name and inspect the queue and the
   event attribution.
   - expected: each slot stays distinguishable by opaque character id, and no
     resolution relies on names.
   - observed: not run. Measured 2026-10-20: the queue is still name-based
     (`static/js/agent/turn-queue.ts`), so two same-named characters cannot
     be told apart by the order.

## Files

- `engine/background_simulation.py:229` - `process_due`, one of the four
  order-bearing walks; its roster iteration is dict insertion order today
- `engine/background_social.py:827` - `run_social_pass`, the second
- `virtual_world_engine.py:831` - `process_simple_npcs`, the third
- `engine/character_appearance.py:916` - the only current mention of
  "simultaneous" anywhere in `engine/`, and it is a comment about
  simultaneous drawing, not a mode
- `static/js/agent/turn-queue.ts:85` - `switch (config.turnOrder)`, the
  client-side resolution to be replaced by reading the server's list.
  `initialize()`'s sorting, `reshuffleRandom()` and `rerollInitiatives()` go
  with it; `advance()` (`:188`), `currentTurnIndex` and the turn panel stay
  as presentation
- `static/js/agent-engine.ts` - the client that drives `step()` per actor
  and posts the turn; it consumes the order rather than computing it
- `static/js/event-stream.ts` - renders the "up next" strip, the third
  surface that must project the engine's list
- `tools/build_scenario.py:318` - stamps `turn_order` into every scenario;
  becomes the setting the engine reads instead of dead data
- `tests/test_turn_panel_affordances.py` - the existing turn-surface
  regression suite; a new engine-side determinism test for each mode belongs
  beside it

## Browser UI and intended live verification

Intended UI home: enable turn-based play and compare the Turn Order panel, the event-stream “up next” strip, and the `/api/state` resolved-order value for the same timeframe. All views must project the engine-resolved order rather than compute separate queues.

Current availability: the card reports that scenario `turn_order` is dead data and that the client queue is name-based. An engine-owned resolved order, ID-backed queue, and mode agreement are planned; this card does not claim those changes are live.

Live steps when available:
1. Load a seeded scenario with three uniquely identified characters, enable sequential mode, and inspect Turn Order and the event-stream `up next` strip before the first action.
   - expected: both surfaces list the same character IDs in the same order as the server-resolved timeframe value.
2. Reverse the character roster in the scenario and run the same seed in simultaneous mode.
   - expected: observable resolution is unchanged by roster order; simultaneous processing does not inherit an arbitrary roster ordering.
3. Run the same seed and scenario twice in each supported mode, then compare the resolved order and outcomes.
   - expected: each repeat is deterministic and the UI order is the exact order consumed by the world.
4. Give two characters the same display name and inspect the queue and event attribution.
   - expected: each slot remains distinguishable by opaque character ID; no resolution relies on names.

This section is not a claim that planned UI exists or works today.
