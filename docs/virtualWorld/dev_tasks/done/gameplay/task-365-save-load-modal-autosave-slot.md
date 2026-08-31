---
type: task
status: done
area: gameplay
priority: high
---

# task-365: Save/Load modal + autosave slot

**Filed**: 2026-08-30
**Status**: Done — implemented + live-verified 2026-08-30.

## What was built

- `version.py` (APP_VERSION = "1.0.0"), stamped into every save's
  `_save_metadata` and shown in the modal.
- Autosave slot `saves/autosave.json` (keeps `_save_metadata`,
  `autosave: True`), pinned to top of the save list; boot autosave unchanged.
- Richer save/load modal (`static/js/ui/saveload-view.js`): per-save stats
  (game time, turn, player, scenario, PCs, areas, size), auto badge, version
  badge, overwrite-slot 💾, rename ✏️ (label + file), delete.
- Backend: `_save_game` slot support, save + rename routes, traversal
  hardening (`_safe_save_path`), list stats.
- Tests: `tests/test_saveload.py` (10).
