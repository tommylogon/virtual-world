# Task-239: Browser State Change Fires State-Change Triggers?

**Status**: Resolved 2026-08-30 — decision: direct editor state edits stay a cheat/direct-edit path and do NOT fire triggers (avoid cascades); the engine state-change path (set_state effect, movement toggles) remains the trigger-firing path. No code change.
**Source:** `dev_tasks/developer ideas.md` (change state in browser triggers state change triggers?)

## Goal

Determine whether setting a node's `current_state` in the editor (browser â†’ API) should
fire the same state-change trigger effects as in-game state changes, and implement it if so.

## Notes / open questions

- In-engine, state changes fire triggers (e.g. door `open`/`close` via items/triggers that
  gate movement). Editing state directly in the inspector currently bypasses that path.
- Should direct edits fire triggers, or stay a "cheat/direct edit" that only updates the
  node? Firing triggers on editor-state-change could cascade unintended effects.
- Investigate how the API state-update route handles `current_state` vs the engine
  `set_state` path; decide trigger firing scope (area-wide, item-owned triggers, etc.).
