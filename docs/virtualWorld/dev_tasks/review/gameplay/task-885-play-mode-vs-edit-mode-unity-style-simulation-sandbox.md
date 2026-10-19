---
type: task
status: review
area: gameplay
priority: high
wiki: "[[AI & Narration/Agent Engine]]"
---

# task-885: Play Mode vs Edit Mode: Unity-style transient simulation sandbox with save/load game flow and clean revert on stop

**Filed:** 2026-10-19

## What

A formal separation between **Edit Mode** and **Play Mode** in the VirtualWorld engine and UI:

1. **Edit Mode (Default):**
   - The authoritative authoring surface.
   - Any edits made here (world painting, node placement, persona adjustments, trigger editing, or manual steps) are staged into the scenario and saved to disk on explicit Commit / auto-save.
2. **Entering Play Mode (▶ Play):**
   - Takes a complete in-memory snapshot of the scenario state.
   - Distinct UI status (colored topbar tint / "PLAYING" badge) signals simulation runtime.
   - Normal auto-saving to the authored scenario source file is suspended.
3. **During Play Mode:**
   - Simulation cycles, agent LLM turns, NPC movements, vitals decay, and event logs run freely in the transient sandbox.
   - **Save & Load Game flow:** Players can save their in-progress simulation playthrough to a named save slot (`data/saves/`) or load an existing save directly into Play Mode.
   - Any manual or runtime modifications made during Play Mode remain sandboxed.
4. **Exiting Play Mode (⏹ Stop):**
   - All transient simulation state (character positions, decayed vitals, inventory transfers, temporary memories) is discarded.
   - The engine restores the pre-play authored snapshot in one clean transition.
   - The editor canvas returns to the exact state it was in before pressing Play.

## Acceptance

- [x] Topbar displays a dedicated Play Mode toggle button (`▶ Play` / `⏹ Stop`).
- [x] Entering Play Mode snapshots `app.world.to_dict()` into an in-memory checkpoint and updates the client status to "PLAYING".
- [x] While in Play Mode, mutating calls (`/api/action`, `/api/agent/step`, `/api/soak`, ticks) advance the live world, but auto-saving to the active scenario file (`save_autosave(app.world)`) is blocked/diverted to a temporary sandbox save.
- [x] Pressing `⏹ Stop` discards the active simulation state and restores the pre-play checkpoint via `/api/saveload/restore_snapshot`, resetting graph positions, inventories, vitals, and dirty flags back to the authored baseline.
- [x] Save Game / Load Game flow works seamlessly in Play Mode:
  - "Save Game" saves the current simulation state to a game save slot (`data/saves/*.json`), not overwriting the authored scenario template.
  - "Load Game" can load an active game save slot directly into Play Mode.
- [x] In Edit Mode, any change (manual character action, inspector tweak, or node edit) continues to mark the scenario dirty and commits to disk when the author clicks Commit.
- [x] Regression safety: existing tests and non-play routes remain unaffected.

## Verification & Evidence

- Unit test suite created in `tests/test_play_mode.py`:
  - `test_play_mode_enter_and_status`
  - `test_play_mode_isolation_and_revert_on_stop`
  - `test_play_mode_blocks_scenario_commit`
  - `test_play_mode_autosave_diverts_to_sandbox`
  - `test_play_mode_save_and_load_game_flow`
  - `test_edit_mode_retains_normal_dirty_and_autosave`
  - Results: 6/6 passed in 2.33s.
- Regression suite passing:
  - `pytest tests/test_play_mode.py tests/test_saveload.py tests/test_scenario_commit.py tests/test_save_schema.py` (56/56 passed in 11.41s).
- Frontend compilation & tests:
  - `npm run build:ts` (0 errors, generated `static/js/ui/play-mode.js`).
  - `node tools/unit/run.cjs` (778/778 passed across all 57 test files).
- Zero em-dashes introduced across all modified files.

## Why

Currently, running an autonomous NPC turn or stepping an action permanently dirties and mutates the authored scenario. Authors have to reload files or reset the entire world to undo simulation changes. A Unity-style Play Mode lets authors test behavior, prompts, and mechanics without contaminating their authored world files.

## Files

- `app.py` - Guard auto-save during Play Mode
- `routes/saveload.py` - Play mode snapshot and restore endpoints
- `static/js/ui/play-mode.ts` - Client toggle controller and visual mode indicator
- `templates/index.html` - Topbar Play/Stop controls
- `tests/test_play_mode.py` - Verification tests for snapshot isolation and restore
