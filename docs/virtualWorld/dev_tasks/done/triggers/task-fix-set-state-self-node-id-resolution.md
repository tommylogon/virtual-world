---
group: Triggers
---

# Fix set_state/set_hidden "self" node_id Resolution + Live Door-Lock Trigger

**Filed**: 2026-08-09  
**Priority**: High  
**Status**: In Review — implemented 2026-08-09, full suite passes (752 passed; only the 11 pre-existing give-item failures remain).

---

## Summary

The trigger editor authors `node_id: "self"` for host-node effects — `set_state`/`set_hidden`/`adjust_uses` all default to `"self"` (trigger-editor.js:487,490,493) and the node picker even offers **self (actor)** (trigger-editor.js:316). But `handle_set_state` and `handle_set_hidden` never resolved `"self"` → they called `graph.get_node("self")`, got `None`, and silently no-opped. `handle_adjust_uses` already handled `"self"` correctly, and `_resolve_effect_target` (effects.py:681) already resolved it for `add_tag`/`remove_tag` — the door-lock effects were the gap.

This made the live door-lock trigger (`trigger_1786286403193_pkvw` on `way_task_18_door_1__open`, on_enter → set_state self → locked) silently do nothing.

## Fix

- **`engine/effects.py`** — `handle_set_state` and `handle_set_hidden` now resolve the target via `_resolve_effect_target`, so `node_id: "self"` (or blank) targets the node that fired the trigger (`item_node`), exactly like `adjust_uses` already did.
- **Live world** — `trigger_1786286403193_pkvw` switched from `on_enter` to `on_close` (node + edge properties). The door has `auto_close: true`, and movement runs `on_enter` triggers *before* auto-close (`movement.py:397-413`), which clobbered the `locked` state back to `closed`. With `on_close`, the sequence is: walk through → door swings shut → `on_close` fires → locked.

## Verification

- New pytest tests (all pass):
  - `test_set_state_self_resolves_to_host_node` (TestEffects)
  - `test_set_hidden_self_resolves_to_host_node` (TestEffects)
  - `test_on_enter_set_state_self_locks_door` (TestTriggerIntegration) — full chain via `_execute_triggers(way, "on_enter")`.
- Full suite: `pytest tests/ -q -k "not mcp and not emote"` → 752 passed, 1 skipped; the 11 give-item failures are pre-existing (verified identical on clean HEAD).
- Live graph verified: node + edge `trigger_type: ["on_close"]`, effects `{node_id: "self", state: "locked"}` intact.

## Authoring Note

Door-lock recipe (UI): Way inspector → ⚡ Triggers → ➕ Add.
- **Option A** (no auto-close): `on_enter` → `set_state` (node = the door, state = `locked`). Requires auto-close OFF, else the lock is clobbered.
- **Option B** (with auto-close): `on_close` → `set_state` (node = the door, state = `locked`). Door swings shut, then locks.

## Files Changed

- `engine/effects.py` — "self" resolution in set_state + set_hidden
- `tests/test_trigger_system.py` — 3 regression tests
- Live world (autosave): `trigger_1786286403193_pkvw` → on_close
