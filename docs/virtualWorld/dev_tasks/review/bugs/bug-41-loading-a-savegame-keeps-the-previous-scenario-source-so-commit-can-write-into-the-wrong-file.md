---
type: bug
status: review
area: bugs
priority: high
---

# bug-41: Loading a savegame keeps the previous scenario source so Commit can write into the wrong file

**Filed:** 2026-09-22
**Related:** task-365, task-368

## Symptom

Load savegame **B** while scenario **A** is open. The world contents become B, but the
save/load model is now internally inconsistent:

- `world._scenario_source` still points at scenario A's file.
- `world._scenario_name` is overwritten from B's payload.
- The scenario chip (task-367) and `GET /api/scenario/status` therefore report one name
  while the commit target is a different scenario.
- `POST /api/scenario/commit` (or an editor "Commit Scenario") then writes **B's
  runtime state** into **A's scenario file**, destroying A's authored content.
- `_edit_seq`/`_commit_seq` are not synced, so the chip's dirty dot is unreliable.
- The boot autosave slot is not refreshed, so a server restart can restore pre-load
  state.

## Root cause

`POST /api/load-game/<filename>` (`routes/saveload.py:331-344`) only does
`_push_undo_snapshot` + `app.world.load_from_dict(data)`.

`load_from_dict` (`engine/serialization.py:440-450`) sets `_scenario_name` from the
payload but never touches `_scenario_source`; the attribute is only changed by
`set_scenario_source` (`virtual_world_engine.py:781-793`).

Compare the savegame branch of `POST /api/load` (`routes/saveload.py:92-118`), which
deliberately sets `app.world._scenario_source = None` when `_save_metadata` is present,
and syncs `_commit_seq`. That route got the semantics right; the dedicated load-game
route did not, and the two have drifted apart.

## Fix

Extract one helper (e.g. `_adopt_loaded_world(app, data)`) that both routes call after
`load_from_dict`, so the two paths cannot diverge again. A savegame is a runtime
snapshot, not a scenario source, so the load-game path should:

1. Clear `world._scenario_source = None` (do not inherit the previously open scenario).
2. Set `world._scenario_name` from the save payload, and do not imply a writable
   source.
3. Set `world._commit_seq = getattr(world, '_edit_seq', 0)`.
4. Persist the autosave slot (`save_autosave`) so a restart matches the loaded state,
   unless `TESTING`.

Keep `/api/load`'s existing `persist:true` scenario-load branch unchanged.

## Acceptance

- [x] Load a savegame while a scenario is open: `_scenario_source` is `None` and the
      chip reflects the loaded world, not the stale scenario.
- [x] With a stale source previously attached, Commit after a savegame load cannot
      overwrite any scenario file. (The commit target is derived from
      `_scenario_source`, which is now cleared, so there is nothing to overwrite.)
- [x] `_commit_seq == _edit_seq` after load, so the dirty dot starts clean.
- [x] Restarting the server after a savegame load restores the loaded state.
      (`_adopt_loaded_world` calls `save_autosave` unless `TESTING`.)
- [x] `POST /api/load` with a `_save_metadata` payload keeps its current behavior
      (source cleared), and the `persist:true` scenario-load branch is untouched.

## Fix — 2026-09-24

One helper, `_adopt_loaded_world(app, data, *, autosave=True)` (`routes/saveload.py`),
now runs after `load_from_dict` in every runtime-snapshot path:

- clears `world._scenario_source = None`,
- sets `world._scenario_name` from the payload (never the stale scenario),
- sets `world._commit_seq = world._edit_seq`,
- refreshes the boot autosave (`save_autosave`) unless `TESTING`.

Callers: `/api/load`'s `_save_metadata` branch (autosave on) and its ephemeral
branch (autosave off), and `/api/load-game/<filename>` — so the two routes can no
longer drift apart (the drift that caused the bug). The `persist:true`
scenario-load branch is unchanged.

Tests (`tests/test_saveload.py::TestLoadGameAdoption`, 5): stale source cleared on
load-game; name taken from the payload not the stale scenario; `_commit_seq`
synced; `/api/load` with `_save_metadata` clears the source; autosave refreshed
(and *not* written for ephemeral loads).


## Files

- `routes/saveload.py` — `load_game` (331-344), `load_world` (75-124), new shared helper
- `engine/serialization.py` — `load_from_dict` name handling (440-450)
- `tests/test_saveload.py` — regression coverage for the load-game path
