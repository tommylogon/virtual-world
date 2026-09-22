---
type: task
status: todo
area: gameplay
priority: medium
---

# task-453: Save-format schema version and load-time compatibility/migration

**Filed:** 2026-09-22
**Related:** task-439, task-446, task-365

## Goal

Give the save/scenario payload an explicit **format schema version** and make load
check it, so a file written before a breaking format change can never load silently
wrong.

`_save_metadata.version` (from `APP_VERSION`, `routes/helpers.py:321`) is the **saving
app's** version, not a format marker. There is no compatibility check on either load
path (`POST /api/load`, `POST /api/load-game`). With `task-446` (id-first node
identity, in progress) and `task-439` (canonical area identity) changing how players
and areas are keyed, an old name-keyed save file already in `saves/` can be read
through new code and produce colliding or mis-attributed entries.

## Proposed shape

- Add `SCHEMA_VERSION` (single source, e.g. alongside `version.py`), stamped into
  `_save_metadata` / `_autosave_meta` and into scenario payloads written by
  `to_scenario_dict`/commit.
- On load, compare the file's schema version against the current one:
  - equal → load as today;
  - older and a registered migration exists → migrate in memory, load, and report
    "migrated from vN" to the caller/UI;
  - older with no migration, or newer than the app → refuse with a clear error
    (do not partially load).
- Keep `version` (app build) for display; keep it separate from `schema_version`.
- Migrations must be read-old/write-new and must not rewrite the source file unless a
  save/commit happens.

## Acceptance

- [ ] New saves carry an explicit `schema_version` distinct from the app `version`.
- [ ] Loading a save/scenario with a missing or older schema version either migrates
      (with a visible notice) or is refused with a specific error — never silently
      loaded as current.
- [ ] A save produced by a newer schema version than the running app is refused rather
      than misread.
- [ ] Existing autosave/scenario boot behavior is unchanged for same-version files.
- [ ] Migration of a legacy name-keyed payload cooperates with task-439/task-446
      (keys and display names both survive).

## Files

- `version.py` — schema version constant
- `routes/helpers.py` — `_save_game` metadata, `save_autosave` meta
- `routes/saveload.py` — `/api/load` and `/api/load-game` compatibility gate
- `engine/serialization.py` — migration hook in the load path
- `tests/test_saveload.py` — schema gate, migration, refusal coverage
