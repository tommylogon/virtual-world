# Task 336 — Lock/unlock player commands for ways (trigger-first)

**Status:** Todo — found 2026-08-23 during human-panel mockup work
(task-333 v2.3); design corrected by Tommy same day

## Why

Locked ways exist and are enforced — `move_to_area` runs skill checks for
locked/barred ways (engine/movement.py:134), doors carry `locked`/state
flags — but `routes/action.py` has no `lock` / `unlock` branches, so the
panel's Lock/Unlock context-menu entries have nothing to call.

## Design (trigger-first, per Tommy — NOT key_item_id on the way)

The requirement logic already exists and is author-owned via triggers.
labs.json is the reference: an `on_use_on` trigger on the keycard with an
**`unlock_way` effect** (success/fail messages, `way_id` param) — see
`trigger_1786290383828_2yj6`. Buttons/levers use `on_use` → `unlock_way`
+ `set_state`. Conditions on those triggers decide whether the actor has
the required key/item.

So the task is only to add the canonical VERBS and route them into that
existing machinery:

1. `lock <way>` / `unlock <way>` verb branches in `routes/action.py`
   (resolve way via matching, require AT/beside per task-135 spatial).
2. Resolution order for both verbs:
   a. trigger effects targeting the way (`on_lock` / `on_unlock` trigger
      types — new but symmetric with existing `unlock_way` effect; authors
      attach conditions like "has keycard" / "is restrained")
   b. existing `unlock_way` effect reused by (a)
   c. no trigger → generic fallback message ("there's no obvious lock you
      can work" / simple latch doors may just toggle state)
3. `_get_available_actions` way branch renders Lock/Unlock enabled/disabled
   with reasons from trigger presence + state — panel menus consume it
   automatically (task-333 contract).
4. Do NOT add key_item_id/lock_difficulty fields to ways — requirements
   stay in trigger conditions where authors already express them.

## Files

- `routes/action.py` — verb branches
- `engine/movement.py` — lock/unlock helpers near way toggling
- `engine/trigger_system.py` — `on_lock`/`on_unlock` trigger types +
  `lock_way` effect (mirror of `unlock_way`), `_get_available_actions` way branch
- `docs/virtualWorld/Triggers/` — effect/type doc update

## Verification

- labs.json keycard door: `unlock door 5` without card → trigger fail
  message; with card → success + state opens
- `lock` on a latch door toggles state; on keycard door → "no lock you
  can work"
- Panel menus show disabled Lock/Unlock with reasons (no trigger / already
  locked)
