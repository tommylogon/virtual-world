---
blocked_by: [task-436]
type: task
status: todo
area: gameplay
priority: medium
---

# task-437 — One turn order, owned by the engine, with simultaneous as a mode

**Status:** todo
**Area:** gameplay / time / engine
**Depends on:** task-436 (timeframe-and-flow model — done)
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
| `BackgroundSimulation.process_due` | **dict insertion order** | nobody — an accident |
| `run_social_pass` | its own per-area order | nobody |
| `process_simple_npcs` | its own order | nobody |

So a character can be 3rd in the queue the UI shows and 19th in the order the
world actually resolves them — and the world's order is the one that decides who
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

One setting, four modes, answering one question — *how does a timeframe resolve?*

- **sequential** — one fixed order, applied serially.
- **random** — a fresh seeded sequence each timeframe, applied serially.
- **initiative** — a seeded d20+DEX sequence each timeframe, applied serially.
- **simultaneous** — no sequence: resolve against a snapshot, commit together.

Three share an implementation shape; `simultaneous` does not. That is a difference
in mechanism, not in kind, so it belongs on the same dial — which also means any
two modes can be A/B'd against each other, which is how the "does order actually
matter to how this feels" question gets answered.

**Simultaneous is not a reason to skip contention work**: handling only *contended*
resources (the last item, one bed, a shared door) is a legitimate internal
optimisation of the mode, not a different mode.

## How

1. **The engine resolves and stores.** At the start of a timeframe the engine
   resolves the order once — seeded — and **stores the resolved list for that
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
   - **Stage 1 — snapshot decisions, serial deterministic commit.** Each
     character's flow reads the world as it stood at timeframe start, then effects
     apply in a fixed commit order. Cheap, removes the *information* advantage
     (which is what the measurement above is measuring). Does **not** make
     contention fair: the commit order still decides who gets the last item.
   - **Stage 2 — intent/effect separation with explicit conflict resolution.**
     `_act` emits what the character *tries* to do; a commit step applies it and
     resolves collisions deterministically. This is the real thing, and it is what
     makes the mode's contract true.
6. **The contract, stated once, tested:** in `simultaneous`, the outcome does not
   depend on processing order. That is checkable — reverse the roster and the
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
work is exactly step 1–4 above — moving the decision to the server. `task-101` is
step 5.

## What

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

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
