---
type: bug
status: review
area: gameplay
priority: high
---

# bug-525: Reviving a dead character leaves it in a blocking activity, forcing wake before any interaction

**Filed:** 2026-10-07
**Related:** task-725, task-131

## Goal

Death must end the character's activity, and a manual revive (HP/Energy restored, conditions cleared) must leave the character able to act. Today clearing the conditions does not clear player.activity, so the activity gate keeps blocking everything except wake even though the character is otherwise awake.

## Repro (user, 2026-10-07)

A character died. There is no revive command, so the user revived it by hand in
the inspector: added HP, added Energy, and cleared the `dead` and `unconscious`
conditions. The character then still refused interaction until `wake` was issued.

## Cause — the activity gate, not the condition gate

Two gates stack in `routes/action_handlers.py`:

- `_action_block_gate` (line 97): `world.conditions.can_act(name)` is false while
  any `BLOCKING_CONDITIONS` are present.
- `_activity_gate` (line 78): a **blocking activity** (`ACTIVITY_BLOCKING`, e.g.
  `sleeping`, `interruptible: false`) blocks every command except a small
  allow-list — and `wake` is on that list (`_activity_cmd_allowed`).

`Player.state` is **derived** (`player.py:488` → `get_state()` reads the
conditions), so a stale state string is not the cause. `sleeping` is an
**activity** that *applies* the `unconscious` **condition** (`source: "sleep"`,
`engine/activities.py:151`). The user cleared the condition, but
`player.activity` remained — and nothing clears it on death (only
`end_activity`, which `wake` calls). So the character was "awake but still
sleeping", and the activity gate demanded `wake`.

Being dead and being unconscious are **conditions**; the activity was `sleeping`.

## Fix

- End the character's activity on death (and on any death→revive path), so a
  revived character is not stuck in a blocking activity.
- Decide whether a proper revive path/command is warranted (there is none today;
  manual condition clearing leaves `activity` and other state inconsistent).
  Related: task-725 (memories on death/revive) and task-131 (activity system).

## Acceptance

- [ ] On death, `player.activity` is cleared (the character is not left
      "sleeping").
- [ ] Reproduce the hand-revive: after HP/Energy restored and conditions
      cleared, the character can act without `wake`.
- [ ] A regression test proves a dead-then-revived `sleeping` character can act.
- [ ] Live: kill a sleeping character, restore it, confirm no `wake` is needed.

## Implemented (2026-10-07)

`virtual_world_engine.py::kill_player` now ends any active activity before
setting `dead` (`self.activities.end_activity(player_name, reason="died")`,
guarded). So a revived character is no longer stuck in `sleeping` behind the
activity gate. `python -m py_compile` clean; frontend unit runner 618 passed.
Not yet verified live (needs a server restart). Still open: a proper revive path
(none exists; the user revived by hand).
