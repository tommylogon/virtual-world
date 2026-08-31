---
type: task
status: review
area: ui
priority: medium
---

# task-373: changes-since-source-panel

**Filed**: 2026-08-30
**Status**: In Review — implemented 2026-08-31 (panel + extended diff + per-group apply).

## What was built

### Backend (`routes/saveload.py`)
- **`GET /api/scenario/diff`** extended beyond areas/players to the full group set:
  `added/removed/changed_areas`, `added/removed/changed_items`,
  `added/removed/changed_ways`, `added/removed_players`. Item/way drift is
  fingerprinted over the graph nodes (name + current_state + description),
  keyed by node id so a rename doesn't show as remove+add.
- **`POST /api/scenario/diff/apply`** — per-group action:
  - `{"commit": ["areas"|"items"|"ways"|"players"]}` merges the live values of
    that group INTO the source file (atomic tmp+replace write, resets commit_seq).
  - `{"discard": [...]}` restores that group FROM source INTO the live world,
    with a labeled undo snapshot pushed first (undoable). Areas restore
    description/environment/tags onto the live nodes (no remove/re-add churn);
    items/ways re-add from source; players only re-add (runtime memories never
    touched).

### Frontend (`static/js/ui/changes-panel.js`, new)
- Modal grouped by section: Rooms / Items / Ways / Players, each row shows
  count badge + up-to-4 names (kind-colored: green add / red del / amber chg).
- Per-section [💾 Commit] and [↩️ Discard] buttons, [💾 Commit All], [🔄 Refresh].
- Entry: 🎮 Game ▾ → "🔄 Changes since source…".

### Tests
- `tests/test_scenario_diff.py` (+5): item/way drift groups, commit-section
  (source file gains node), discard-section (live node removed + undo label),
  empty-body 400. Full suite 2511 passed.

## Note

The audit text asked for "per-group Commit/Discard; reuse sync-diff internals".
Commit is per-section (not per-node) for v1 — per-node commit would be
checkboxed UI over the same apply endpoint; noted as a possible v2.
