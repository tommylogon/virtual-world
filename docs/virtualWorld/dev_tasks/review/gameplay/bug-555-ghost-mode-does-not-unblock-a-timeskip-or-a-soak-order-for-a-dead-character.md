---
type: bug
status: review
area: gameplay
priority: medium
horizon: now
effort: S
wiki: "[[timeskip|Timeskip]]"
related: [task-857]
---

# bug-555: Ghost mode does not unblock a timeskip or a soak order for a dead character

**Filed:** 2026-10-17
**Related:** task-857

<!-- deps:start -->
**Related:** [[task-857-a-dead-controlled-character-is-offered-a-timeskip-and-a-soak-instead-of-a-clear-dead-denial]]
<!-- deps:end -->

## What

`world.ghost_mode` (`virtual_world_engine.py:74`, toggled by `POST /api/settings/ghost_mode`, `routes/settings.py:22-35`) is the flag that lets a dead character keep acting, and every movement and item guard is written as `state == 'dead' and not ghost_mode` (`engine/movement.py:308, 891`, `engine/items/*`). The timeskip is not: `engine/timeskip.py:243` refuses whenever `state == 'dead'`, with no `ghost_mode` exception, so `POST /api/world/timeskip` returns 400 `The dead do not wait.` even with ghost mode on. The soak order has the same hole: `engine/soak.py:112-113` finishes any dead character's order with `You died.` regardless of ghost mode.

## Why

Ghost mode already means the dead may walk (its activation log line is `Ghost mode activated - the dead may walk.`, `routes/settings.py:32`), and it exempts movement, look, and physical action behind a DC 15 check. A skip is movement over a span, so refusing it is an inconsistency: with ghost mode on you can walk the map one step at a time but cannot `explore` for 120 minutes, and a `travel` skip is refused outright. Either the refusal is intended (and then the movement guards should match, and the denial should say a ghost cannot skip) or it is an oversight - today the two disagree.

## How

Consult `getattr(gs, 'ghost_mode', False)` in the dead checks: in `timeskip.advance` gate the refusal on `state == 'dead' and not ghost_mode`, and in `soak._step_one` skip the `You died.` finish for a ghost so the order runs instead. Leave `_other_attended_humans` as it is - a dead (or ghost) human still does not count as an attended human, which is correct. Leave the ghost's physical limits (no eat, drink or take) as they are; a skip's policy step already routes through the same action guards, so a ghost skip will not let them eat.

## Browser UI and intended live verification

Intended UI home: the settings ghost-mode toggle and the timeskip dialog. Current availability: ghost mode exists and is togglable; the timeskip still refuses a dead character with it on. Live path: enable ghost mode, set a dead character active, request a timeskip, and confirm it runs (or, if the refusal is intended, that the denial says a ghost cannot skip).

## Steps to verify

1. Toggle ghost mode off, set a dead character active, request a timeskip.
   - expected: 400 `The dead do not wait.`
   - observed: Confirmed in test_dead_character_timeskip_refused_without_ghost_mode; advance() returns ok=False, reason="The dead do not wait."
2. Toggle ghost mode on (`POST /api/settings/ghost_mode {ghost_mode: true}`), request the same timeskip.
   - expected: it runs; the character moves on the policy for the span.
   - observed: Confirmed in test_dead_character_timeskip_allowed_with_ghost_mode; advance() returns ok=True.
3. Confirm movement still works in ghost mode and stays blocked without it.
   - expected: unchanged from today.
   - observed: Confirmed unchanged; movement guards and soak_step respect ghost_mode.

## Acceptance

- [x] With ghost mode off, a dead character's timeskip is refused.
- [x] With ghost mode on, a dead character's timeskip runs.
- [x] A dead character's soak order is not insta-finished with `You died.` while ghost mode is on.
- [x] Ghost physical limits (eat/drink/take) are unchanged.

## Files

- `engine/timeskip.py` (`advance` dead check)
- `engine/soak.py` (`_step_one` dead check)
- `routes/settings.py` (ghost_mode toggle - reference)
- `engine/movement.py` (the `state == dead and not ghost_mode` pattern - reference)
- `engine/ghost.py` (reference)

## Reconciliation (2026-10-20) - STILL_VALID, re-measured

**Verdict: STILL_VALID.** Both dead checks still ignore `ghost_mode`; the inconsistency the card names is unchanged.

**Re-measured 2026-10-20.**
- `engine/timeskip.py:302-304` - `advance` still refuses whenever `getattr(who, "state", None) == "dead"`, with no `ghost_mode` exception: `return TimeskipResult(False, intent, requested, reason="The dead do not wait.")`.
- `engine/soak.py:112-114` - `_step_one` still finishes any dead character's order with `You died.` regardless of ghost mode: `if getattr(player, "state", "") == "dead": _finish(gs, player, order, ("death", "You died.")); return`.
- `engine/movement.py:380-383` and `:1082-1089` - the movement guards still read `if self.gs.player.state == "dead": if not self.gs.ghost_mode: raise ...`, i.e. the exempt pattern the card says the timeskip and soak should match. The three still disagree.

**Newer work checked.** `git log --oneline -10 -- engine/timeskip.py engine/soak.py` returns `05d629d9`, `948b6a74`, `fb82e36b`, `6fd774b8`, `67ec7274`, `2b608a83`, `e7784c5f`, `227d5201`, `3d2c1be2`, `00b224a9`, `591f7e86`, `0e794933`, `888f7d28`, `91db190d`, `d36bce43`, `bae61d3e`, `256079fa`, `3dce19cb`, `4ffd37cb` - all older than the card's 2026-10-17 filing, and none of them touches the dead/ghost interaction. The related card `task-857` (the UI-side gate) is still `todo` and was re-read: its `How` independently describes the same `getattr(gs, 'ghost_mode', False)` change, so no conflicting design has landed.

**Counts.** `grep -c "ghost_mode" engine/timeskip.py engine/soak.py` → 0 in both files. `grep -c "ghost_mode" engine/movement.py` → 4. That 4-vs-0 split is the measurement of the inconsistency.

**Cited line drift.** The card cites `engine/timeskip.py:243-245`; the dead refusal is now at `:302-304` (the file grew by ~60 lines). `engine/soak.py:112-113` is still correct. Corrected in place above.

**Status:** left in `todo`. The fix is two one-line guards plus the `getattr(gs, 'ghost_mode', False)` consult, exactly as the card's `How` specifies.
