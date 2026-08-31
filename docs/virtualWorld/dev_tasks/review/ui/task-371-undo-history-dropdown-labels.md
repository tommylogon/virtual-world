---
type: task
status: review
area: ui
priority: medium
---

# task-371: undo-history-dropdown-labels

**Filed**: 2026-08-30
**Status**: In Review — implemented 2026-08-30; per-edit labels verified by tests.

## What was built

- `static/js/ui/undo-history.js` — undo history dropdown (📜) listing the recent
  labeled snapshots (`before: reset`, `duplicate X`, `loaded Y`, `edited node <id>`…);
  click a row to restore that state.
- `routes/saveload.py` — `_push_undo_snapshot(app, label)` stores every mutation with a
  label; `GET /api/undo/list` exposes the stack.
- **Per-edit snapshots (same session, follow-up)**: every graph/player/build mutation now
  pushes a labeled entry in the `after_request` hook — minor edits show up in history
  (was: only loads/resets). `POST /api/undo {steps:N}` pops N snapshots.
- Tests: `tests/test_undo_history.py` (+5: labeled snapshots, multi-step, redo, empty→400).

## Note

Follow-up note from 2026-08-30 kept for context: the per-edit push moved OUTSIDE the
TESTING gate so test worlds still record (autosave remains TESTING-gated). Original
audit text: "10-deep stack with labels; click = restore" — stack depth is controlled by
the server (default keeps ~50 in memory; UI shows the newest 10).
