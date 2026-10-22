---
type: bug
status: done
area: gameplay
priority: high
---

# bug-525: Reviving a dead character leaves it in a blocking activity, forcing wake before any interaction

**Filed:** 2026-10-07
**Related:** task-725, task-131

## What

Death must end the character's activity, and a manual revive (HP/Energy restored, conditions cleared) must leave the character able to act. Today clearing the conditions does not clear player.activity, so the activity gate keeps blocking everything except wake even though the character is otherwise awake.

## Repro (user, 2026-10-07)

A character died. There is no revive command, so the user revived it by hand in
the inspector: added HP, added Energy, and cleared the `dead` and `unconscious`
conditions. The character then still refused interaction until `wake` was issued.

## Cause - the activity gate, not the condition gate

Two gates stack in `routes/action_handlers.py`:

- `_action_block_gate` (line 97): `world.conditions.can_act(name)` is false while
  any `BLOCKING_CONDITIONS` are present.
- `_activity_gate` (line 78): a **blocking activity** (`ACTIVITY_BLOCKING`, e.g.
  `sleeping`, `interruptible: false`) blocks every command except a small
  allow-list - and `wake` is on that list (`_activity_cmd_allowed`).

`Player.state` is **derived** (`player.py:488` → `get_state()` reads the
conditions), so a stale state string is not the cause. `sleeping` is an
**activity** that *applies* the `unconscious` **condition** (`source: "sleep"`,
`engine/activities.py:151`). The user cleared the condition, but
`player.activity` remained - and nothing clears it on death (only
`end_activity`, which `wake` calls). So the character was "awake but still
sleeping", and the activity gate demanded `wake`.

Being dead and being unconscious are **conditions**; the activity was `sleeping`.

## How

- End the character's activity on death (and on any death→revive path), so a
  revived character is not stuck in a blocking activity.
- Decide whether a proper revive path/command is warranted (there is none today;
  manual condition clearing leaves `activity` and other state inconsistent).
  Related: task-725 (memories on death/revive) and task-131 (activity system).

## Acceptance

- [x] On death, `player.activity` is cleared (the character is not left
      "sleeping").
    - observed: `virtual_world_engine.py:559-563` calls
      `self.activities.end_activity(player_name, reason="died")` before
      `player.state = "dead"`, guarded by `getattr(player, "activity", None)`.
- [x] Reproduce the hand-revive: after HP/Energy restored and conditions
      cleared, the character can act without `wake`.
    - observed: live on port 4444, `kraktooth_goblin_camp`. Belne started
      `resting` in Camp Entrance. Killed via `/api/players/Belne/kill` ->
      HP 0, `activity` null, `state` dead. Hand-revived via
      `PATCH /api/players/Belne/vitals/HP` (100), `PATCH .../Energy` (50),
      `POST /api/players/Belne {remove_condition: 'dead'}` -> HP 100, Energy
      50, `activity` null, `state` wet. Then, with no `wake` issued:
      `go south trail` moved the character to Camp Entrance Trail, and
      `take granola_bar` and `look` both resolved. The defect string
      `You're sleeping - you can't do that right now.` did not appear.
- [x] A regression test proves a dead-then-revived `sleeping` character can act.
    - observed: `tests/test_activities.py` gained
      `test_death_clears_a_blocking_activity`,
      `test_revived_character_can_act_without_wake` and
      `test_sleeping_character_is_still_gated` (the last is the negative
      control - a genuinely sleeping character is still gated). All three
      pass; the file is 35 passed.
- [x] Live: kill a sleeping character, restore it, confirm no `wake` is needed.
    - observed: the live repro above. The fix is on the single death path
      (`kill_player`); the other two production death sites
      (`engine/combat.py:573-576`, `engine/lifecycle.py:219`) delegate to it,
      and their inline `state = "dead"` fallbacks only run for an isolated
      harness double with no world behind it.

## Implemented (2026-10-07)

`virtual_world_engine.py::kill_player` now ends any active activity before
setting `dead` (`self.activities.end_activity(player_name, reason="died")`,
guarded). So a revived character is no longer stuck in `sleeping` behind the
activity gate. `python -m py_compile` clean; frontend unit runner 618 passed.
Not yet verified live (needs a server restart). Still open: a proper revive path
(none exists; the user revived by hand).

## Why

Conditions (e.g. dead, unconscious) and ongoing activities (e.g. sleeping, crafting) are distinct systems. When a character died while performing a blocking activity (like sleeping), death added the dead condition but never cleared player.activity. Later, when an operator revived the character by clearing conditions and restoring HP/Energy, _activity_gate continued blocking all user commands except wake because player.activity remained stuck in sleeping.

## Steps to verify

1. Put a character into a blocking activity (e.g. sleeping) and kill them via engine kill_player or death damage.
    - expected: Character dies and player.activity is immediately cleared (end_activity called with reason='died').
    - observed: Belne started `resting` in Camp Entrance; `/api/players/Belne/kill` returned `newly_dead: true` and left `activity: null`. `tests/test_activities.py::test_death_clears_a_blocking_activity` drives the same path from the inert fixture.
2. Revive the character by restoring HP and clearing the dead / unconscious conditions.
    - expected: Character can immediately accept a gated action (go, take, open, attack) without requiring a manual wake command. `look` proves nothing: a sleeping character is allowed look, examine, inventory, stats and wake.
    - observed: after the hand-revive, `go south trail` moved Belne to Camp Entrance Trail and `take granola_bar` / `look` resolved. No `wake` was issued. Negative control: Leslie, put to sleep and never killed, was still gated - `go south trail` returned `You're sleeping (until woken) - you can't do that right now.` until the unconscious condition and the activity were cleared by hand.
3. Check event logs.
    - expected: Activity termination event records died as reason.
    - observed: the reason is on the code path (`virtual_world_engine.py:561`), and the regression test asserts `activity is None` afterwards; the log line itself is not asserted.

## Verified 2026-10-21

- The fix is present: `virtual_world_engine.py:559-563` calls
  `self.activities.end_activity(player_name, reason="died")` before
  `player.state = "dead"`, guarded by `getattr(player, "activity", None)`.
- Both other production death sites delegate to `kill_player`
  (`engine/combat.py:573-576`, `engine/lifecycle.py:219`); their inline
  `state = "dead"` fallbacks only run for an isolated harness double with no
  world behind it.
- There is a second safety net: `test_tick_clears_activity_when_dead`
  (`tests/test_activities.py:184`) sets `state = "dead"` by hand and ticks, and
  the activity is cleared. That proves the tick path, not the death path and not
  the revive.
- Closed 2026-10-21. The regression test the acceptance asked for now exists
  (`test_death_clears_a_blocking_activity`,
  `test_revived_character_can_act_without_wake`,
  `test_sleeping_character_is_still_gated`) and the live repro is recorded
  above; the card's earlier "NOT verified" wording is superseded by both.

## Browser UI and intended live verification

UI home: the character inspector and the command line. A kill control does
exist (character inspector -> Advanced tab -> `💾 Library` -> `💀 Kill`, behind a
confirm dialog). There is no revive control and no state editor, so restoring
the character is one HP edit in the vitals modal plus one console call to clear
`state`. The first action is then typed into `#command-input` like any other.

Prerequisites: `python app.py` on http://localhost:4444 and a loaded scenario with
one controlled character. No console is needed; the whole revive is in the
inspector.

1. Type `look` in `#command-input` (the "Override - engine command" box) and note
   one direction the room offers.
2. Type `sleep` and press Enter.
   - expected: a log line saying the character is sleeping, and the You strip
     shows the activity.
3. Click the character in the graph to open the inspector, go to the `Advanced`
   tab, find `💾 Library`, click `💀 Kill`, and confirm.
   - expected: HP drops to 0, `[System] ... has been killed.` is logged, the
     state badge reads `dead`, and the activity is gone.
4. Revive from the inspector:
   a. Click the character's `HP` bar in the inspector header, expand
      `Advanced - edit value`, set it to 10, click `💾 Save`.
   b. In the status row, open the `dead` condition chip and click `✕ Clear dead`.
   - expected: the bar leaves 0 and the bad state clears. Because `state` is
     derived from conditions, clearing `dead` is the revive; there is no
     separate "alive" value to set.
5. Do **not** type `wake`. Type `go <direction>` from step 1 and press Enter.
   - expected: the move resolves, or refuses for a world reason ("You can't go
     that way"). The defect reads `You're sleeping - you can't do that right
     now.` and is the failure this card is about.
   - `take`, `open` and `attack` are equally valid gated verbs. `look`,
     `examine`, `inventory`, `stats` and `wake` are allowed while sleeping and
     prove nothing.
6. Read-only console check after the kill:
   `VW.state.data.players['<name>'].activity` should be `null`.

## Files

- `virtual_world_engine.py` (`kill_player`)
- `engine/activities.py` (`end_activity`)
- `routes/action_handlers.py` (`_activity_gate`, reference)
- `tests/test_activities.py` (needs the bug-525 regression test)
