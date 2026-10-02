---
type: task
status: review
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

## Acceptance (as planned)

Outcome and the one deviation (an unstamped payload is current-format, not v1)
are recorded under **Resolution** below.

## Files

- `version.py` — schema version constant
- `routes/helpers.py` — `_save_game` metadata, `save_autosave` meta
- `routes/saveload.py` — `/api/load` and `/api/load-game` compatibility gate
- `engine/serialization.py` — migration hook in the load path
- `tests/test_saveload.py` — schema gate, migration, refusal coverage

## Resolution — 2026-10-02

A schema field already existed but was a half-measure: `save_autosave` hard-coded
`'schema_version': 2` (initial release, `170d5f1`) and `load_autosave_if_exists`
had an inline bladder v1→v2 migration — but **nothing read it on the load
routes**, `_save_game` never stamped it, and `to_scenario_dict` never stamped it.

Implemented:

- `version.py` — `SCHEMA_VERSION = 2`, documented as the payload *format* version,
  distinct from `APP_VERSION` (app build). No more magic `2`.
- `engine/schema.py` (new) — `schema_version_of`, `migrate`, `SchemaError`, and a
  `SCHEMA_MIGRATIONS` registry. `migrate` returns `(data, from_version)`, applies
  registered migrations in memory (read-old/write-new; never rewrites the
  source), refuses a version newer than the app, and refuses an older version
  with no registered step.
- `routes/helpers.py` — `save_autosave` and `_write_autosave_slot` and
  `_save_game` all stamp `SCHEMA_VERSION`; the autosave boot path now calls
  `migrate()` instead of its inline bladder block, so the one gate is shared.
- `routes/saveload.py` — `/api/load` and `/api/load-game` migrate before
  `load_from_dict`; a refusal is a 400 with the specific reason, a migration
  returns `schema_notice`.
- `engine/serialization.py` — `to_scenario_dict` stamps `schema_version` too.
- `static/js/ui/saveload-view.js` — `doLoadGame` / import-apply toast
  `schema_notice`, so a migration is visible.
- `tests/test_save_schema.py` — 12 cases: reader, same-version no-op, explicit
  v1 migration, newer refusal, stamping on save/autosave, and both load routes.

### Decision: an *unstamped* payload is current-format, not v1

The acceptance said "missing … migrates or is refused". The evidence says
otherwise, and blindly migrating is actively harmful here: `save_autosave` has
stamped `schema_version: 2` since the initial public release — the same commit
that introduced the bladder migration — while `_save_game` and
`to_scenario_dict` wrote current-format payloads **without** the field. So an
unstamped file is a current-format save/scenario, and assuming v1 would invert
the Bladder vital of every existing one. `LEGACY_SCHEMA_VERSION` is therefore
`SCHEMA_VERSION`: missing loads as current, an **explicit** older version
migrates/refuses, a newer one is refused. This keeps the real safety property
(after a breaking change, a stamped old file can never be read as current) while
not corrupting the files that predate the field.

### Verification

- `python -m pytest tests/test_save_schema.py tests/test_saveload.py -q` → 45 passed.
- Full suite A/B against a clean `master` worktree: **identical failure-name
  set** (15 both sides); my run 6623 passed vs 6607 baseline.
- Live (port 4471, real `api.loadGame` + `SaveLoadView.doLoadGame`):
  - `schema_version: 1` file → `{"status":"success","schema_notice":"Migrated save from schema v1 to v2."}` and the toast `ℹ️ Migrated save from schema v1 to v2.` rendered.
  - `schema_version: 999` file → `{"error":"This file was written by a newer version (schema v999); this app reads up to schema v2. Update the app to load it."}` (400), world untouched.
- `node tools/unit/run.cjs` 485 passed; `npm run lint`, `npm run typecheck` clean.

### Acceptance

- [x] New saves carry an explicit `schema_version` distinct from `version`.
- [x] An explicitly older save/scenario is migrated with a visible notice, or
      refused with a specific error (newer); never read as current.
- [x] A save from a newer schema version is refused rather than misread.
- [x] Existing autosave/scenario boot behavior is unchanged for same-version
      files (stamped 2 → no-op; A/B-identical).
- [ ] Migration of a legacy **name-keyed** payload cooperating with
      task-439/task-446 is **not** done here — this task provides the gate and
      the registry; the name-keyed migration is content that belongs with those
      tasks. No checked-in file needs it today.
