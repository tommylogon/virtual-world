---
type: bug
status: review
area: ui
priority: high
blocks: [bug-518, task-610]
---

# bug-544: Disabling turn-based mode does not reset the controlled character's action slots

**Filed:** 2026-10-11
**Related:** task-518
**Blocks:** bug-518 (needs a live NPC turn), task-610 (its intimacy-action
follow-on verification is the same blocker — the controlled character cannot act).

<!-- deps:start -->
**Blocks:** [[bug-518-npc-action-results-render-as-you-in-the-turn-feed-because-result-rows-carry-no-actor]], [[task-610-human-turn-modal-exposes-3-of-23-backend-character-to-character-actions]]
<!-- deps:end -->

## What

With Turn-based mode OFF, the controlled character's action slots
(`Player.turn_slots`) are not refilled, so the human cannot act for that
character — the action is refused even though a fresh turn was requested.

User-reported (live, 2026-10-11):

1. Turn-based mode OFF.
2. Select the controlled character.
3. Step once.
4. **Expected:** the character has a full allowance (1 major · 1 minor · 3 free)
   and can act.
5. **Observed:** actions are not reset; the player cannot act for the controlled
   character.

This blocks **bug-518** (which needs a live NPC turn) and **task-610** — the
intimacy action from the HTC person menu cannot be exercised because the
controlled character has no action to spend (user, 2026-10-11). Same root cause,
one card.

## Why

The human action budget is the shared `major / minor / free` allowance
(task-352). If it is not refilled outside turn-based mode, a human cannot take a
turn at all in that mode, and anything needing a live human or NPC turn
(task-518) is blocked.

## How

Candidate path, to confirm before fixing (not independently reproduced — the
server was down during triage):

- `Player.turn_slots` is refilled by `engine/tick_manager.py:tick_turn()`
  (`action_tiers.reset_slots`) for **every** player, once per applied turn.
- `tick_turn()` runs from `ApiClient.applyTurn()`, which `TurnQueue.endTurn()`
  calls (`static/js/agent/turn-queue.ts:158-176`).
- In non-turn-based mode, `AgentEngine.stepOnce()` is supposed to close the turn
  via `TurnQueue.endTurn()` (`static/js/agent-engine.ts:1037-1044`), which should
  therefore reset the slots and refetch state.
- The composer reads `worldState.players[char].turn_slots`
  (`static/js/agent/human-turn-composer.ts:234-247`).

So the reset is expected on this path — the question is which link breaks. Check:
is `endTurn()` actually called in the user's flow (is `config.controllingPlayer`
set?), does `applyTurn()` reach `tick_turn()`, and does the refetched state carry
the reset slots for the character the panel is showing? Also note the mismatch
visible in the report: the pip strip can read full (`1 major · 1 minor · 3 free`)
while the result line says "no action left this turn", which suggests the
engine's `_slot_gate` and the client display are reading different states.

## Steps to verify

1. Turn-based OFF; select the controlled character; Step once.
   - expected: the pip strip shows a full allowance and an action is accepted.
   - observed: TODO
2. Turn-based ON, take the same action, for contrast.
   - expected: pips reset at the turn boundary.
   - observed: TODO
3. Note whether the pip strip and the engine's "no action left this turn" verdict agree.
   - expected: they agree.
   - observed: TODO

## Acceptance

- [ ] With turn-based OFF, after a step the controlled character has a full allowance and can act.
- [ ] The human turn panel's pips reflect the reset.
- [ ] A regression test proves the non-turn-based step refills the controlled character's slots.
- [ ] No regression to turn-based mode's slot reset.

## Resolution (2026-10-11)

Root cause is the **empty-`turn_slots` sentinel read as "spent"**, client-side.

`Player.turn_slots` starts as `{}` ("not started yet" — `player.py:393-397`) and
is *lazily filled* by the engine's `_slot_gate`
(`routes/action_handlers.py:364-366`: `if not _slots: reset_slots(...)`). The
server therefore treats `{}` as "no budget yet — fill it". The client treated
`{}` as "all slots spent", so a fresh turn was refused before the server could
fill it:

- `agent/human-turn-composer.ts` `turnSlots()` returned `{}` → `renderPips` drew
  all spent and `commitStep` blocked every action.
- `agent/prompt-builder/room-context.ts` `turnSlots()` returned `{}` → the turn
  prompt hid every verb (`computeItemActions` filters on a published budget).
- `agent-engine.ts` — the `_humanTurn` slot check and the agent loop's exit
  check both read `{}` as an empty budget, ending the turn after one step.

Fix — an empty `turn_slots` means "no budget published", not "spent":

- `agent/human-turn-composer.ts` — `turnSlots()` returns `null` for `{}`.
- `agent/prompt-builder/room-context.ts` — `turnSlots()` returns `undefined` for `{}`.
- `agent-engine.ts` — both slot checks end the turn only on a *published and
  expired* budget (`Object.keys(slots).length > 0 && !values.some(n > 0)`),
  never on `{}`.

`python tools/ts_convert.py check` green (build · typecheck · lint · module · unit).

**Still owed before `done`:** a live browser pass in the non-turn-based flow
(act → step → act) to confirm the human can act for the controlled character;
and a regression test — the reads are DOM/Lit code not covered by the Node unit
runner, so a pure seam or a browser assertion is needed.

## Files

- `static/js/agent-engine.ts` — `stepOnce` / `step` / `_humanTurn` slot checks.
- `static/js/agent/human-turn-composer.ts` — `turnSlots()` / pip rendering.
- `static/js/agent/prompt-builder/room-context.ts` — `turnSlots()`.
- `engine/tick_manager.py`, `engine/action_tiers.py` — slot reset (unchanged; verified correct).
- `routes/action_handlers.py` — `_slot_gate` (the lazy fill; unchanged).

## Browser UI and intended live verification

Intended UI home: Agent controls → “⏭️ Turn-Based Mode” checkbox (`#agent-turn-based`) → controlled character's human-turn panel → action-pip strip and command/action result in the event stream.

Current availability: The user report says non-turn-based mode leaves the character unable to act; the candidate tick/slot-reset path was not independently reproduced because the server was down during triage. The pips and engine verdict may read different values, so compare both.

Live steps when available:
1. Turn turn-based mode off, select the controlled character, clear the event stream, and step once.
   - expected: the pips show 1 major, 1 minor, and 3 free actions; a valid action is accepted and its result appears in the stream.
2. Exhaust an action slot, step again with turn-based mode still off, and try the same action.
   - expected: the controlled character's slots refill and the action succeeds without switching to turn-based mode.
3. Enable turn-based mode, take the same action, and advance through the turn boundary.
   - expected: slot pips reset at the boundary; the pips and any engine refusal describe the same remaining allowance.
4. Watch the browser Network panel and `/api/state` for the controlled character's `turn_slots` before and after each step.
   - expected: the UI pips match the state used by `_slot_gate` after the state refresh.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
