---
group: Library
---
# Warn on Library/Instance Mismatch

**Filed**: 2026-08-19
**Priority**: High
**Status**: In Review — implemented 2026-08-19 (backend validator, left-panel World Issues)

---

## Idea

Warn when an instanced entity's properties no longer match its selected template in the library.

## Implemented

- `engine/trigger_validator.py` — `_validate_library_sync()` pass: items with `library_id` are diffed against `data/library/items/<library_id>.json`.
  - `library_entry_missing` — library file doesn't exist.
  - `library_mismatch` — differing sync props (name/description/tags/actions/uses/weight/equip_slots/current_state/light_level/target_temperature/heating_rate/contents/aliases), with `_props_match()` tolerating the hydration normalization (library `actions` string → node list).
- Surfaced in the left panel `#validation-section` via `/api/triggers/validate`.
- Tests: `TestLibrarySyncWarnings` (missing entry, mismatch, in-sync clean).

**Verified**: full suite 980 passed (+9 validator tests).

## Notes

- Directly targets the `bug_14` stale-copy trap: nodes placed via `build_item_from_library` snapshot the library entry at build time, and edits to the library entry don't propagate until `refresh-to-world`.
- Diff the node's properties against its `data/library/items/<library_id>.json` and surface a visible warning in the inspector / item library UI.
- Cheap to build on top of the existing library hydration code.

## Related

- `developer ideas.md` line 3
- `data/library/items/*.json`, `routes/library_routes.py`
