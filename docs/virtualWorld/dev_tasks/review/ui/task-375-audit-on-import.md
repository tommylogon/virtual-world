---
type: task
status: review
area: ui
priority: medium
---

# task-375: audit-on-import

**Filed**: 2026-08-30
**Status**: In Review — implemented 2026-08-30 as part of task-369's import preview.

## What was built

- The `🔬 Deep audit` button in the import-preview dialog (`static/js/ui/saveload-view.js`)
  runs `TriggerValidator` against the *incoming* world dict BEFORE any state mutation —
  issues are listed in the preview with severity (err/warn/info); the user can still
  `[Apply anyway]` (undo-protected) or cancel.
- No separate route: reuses `POST /api/triggers/validate` (validator panel path) on an
  in-memory copy.

## Note

Filed separately from 369 but landed in the same dialog. Task 369's doc is the canonical
entry; this file records the distinction (validate-before-load vs preview counts).
