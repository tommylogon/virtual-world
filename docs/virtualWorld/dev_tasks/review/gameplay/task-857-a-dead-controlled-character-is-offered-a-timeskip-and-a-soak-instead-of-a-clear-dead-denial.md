---
type: task
status: review
area: gameplay
priority: medium
horizon: now
effort: S
wiki: "[[timeskip|Timeskip]]"
related: [bug-554, bug-555]
---

# task-857: A dead controlled character is offered a timeskip and a soak instead of a clear dead denial

**Filed:** 2026-10-17
**Related:** bug-554

<!-- deps:start -->
**Related:** [[bug-554-a-refused-timeskip-drops-the-engine-reason-behind-a-generic-400-message]], [[bug-555-ghost-mode-does-not-unblock-a-timeskip-or-a-soak-order-for-a-dead-character]]
<!-- deps:end -->

## What

The engine refuses a timeskip for a dead character (`engine/timeskip.py:243-245`: HTTP 400 with `reason: 'The dead do not wait.'`), which is correct - but only on the blocking path. The dead check lives inside `timeskip.advance`, and `handle_timeskip` chooses its branch first (`routes/timeskip_ops.py:115`), so a dead active character takes the shared-world branch whenever another live attended human exists and gets `{ok: true, mode: 'soak', order: {...}}` - a soak order declared on a corpse, which `soak._step_one` then immediately ends with `You died.` (`engine/soak.py:112-113`). `POST /api/world/soak` has the same gap (`handle_soak_declare`, `routes/timeskip_ops.py:186`; `soak.declare`, `engine/soak.py:33`). Nothing on the client gates the affordance either: the timeskip control stays available for a dead controlled character and only the failed request says no.

## Why

A dead character cannot act, so offering the action and failing the request is the wrong shape: the player learns they are dead only from a (currently generic) error. The player should be told up front, and the controls that imply agency (timeskip, declare soak) should not be offered. Ghost mode exists (`world.ghost_mode`, toggled by `POST /api/settings/ghost_mode`) and is precisely the state in which a dead character may keep acting, so the gate must be ghost-aware: block when dead and ghost mode is off, allow when it is on. See bug-555 for the engine-side inconsistency (the dead checks do not consult ghost mode today).

## How

Gate the timeskip and soak controls on the active character's state, ghost-aware: when `state === 'dead'` and ghost mode is off, disable them and show an explicit line (for example `You are dead. You cannot act. Ghost mode is off.`); when ghost mode is on, leave them enabled. Read `ghost_mode` from `/api/settings/ghost_mode` or the state payload rather than keeping a second copy. Add the matching dead-and-not-ghost guard to `handle_soak_declare` and to the shared-world soak branch of `handle_timeskip` so both paths refuse consistently instead of declaring an order on a corpse. The wording must not assert that death is irreversible.

## Browser UI and intended live verification

Intended UI home: the timeskip dialog and the soak controls (request a timeskip / declare soak). Current availability: neither is gated on death today; a dead character can open the dialog and gets a generic 400. Live path: make the active character dead (or load a save where they are), open the turn panel, and confirm the timeskip and soak controls are disabled with a clear dead-state line, and that no request is sent.

## Steps to verify

1. With the active character dead and ghost mode off, open the timeskip dialog.
   - expected: the control is disabled and an explicit dead-state line is shown; no request is sent.
   - observed: Verified in `tools/unit/test_timeskip.js`: `isDeadNoGhost` returns true; `timeskip-go` button is disabled and status displays "You are dead. You cannot act. Ghost mode is off."; `run()` returns early without posting.
2. Turn ghost mode on and reopen the dialog with the same dead character.
   - expected: the control is enabled (a ghost may act); the request is allowed.
   - observed: Verified in `tools/unit/test_timeskip.js` and `tests/test_timeskip.py`: `isDeadNoGhost` returns false when `ghost_mode` is true, enabling the button and allowing the timeskip request.
3. POST a soak declare for a dead character with ghost mode off.
   - expected: 400 with a clear dead refusal, and no order attached.
   - observed: Verified in `tests/test_timeskip.py::test_soak_declare_dead_character_gated_on_ghost_mode`: returns HTTP 400 with error and reason "The dead do not wait." and `hero.soak_order` remains None.
4. Repeat 1 and 3 with a live character.
   - expected: timeskip and soak behave exactly as before.
   - observed: Verified in `tests/test_timeskip.py`: all 68 tests pass without regression.

## Acceptance

- [x] A dead active character with ghost mode off cannot start a timeskip or declare a soak from the UI, and is told why.
- [x] With ghost mode on, a dead (ghost) character can still start a timeskip and declare a soak.
- [x] `POST /api/world/soak` refuses a dead character (ghost mode off) with a clear reason and attaches no order.
- [x] A live character's timeskip/soak behavior is unchanged.
- [x] The wording does not assert that death is irreversible.

## Files

- `templates/index.html` (timeskip/soak controls)
- `static/js/ui/timeskip.js`
- `routes/timeskip_ops.py` (`handle_soak_declare`)
- `engine/soak.py` (`declare` - reference)
