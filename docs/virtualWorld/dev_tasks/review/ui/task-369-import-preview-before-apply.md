---
type: task
status: review
area: ui
priority: medium
---

# task-369: import-preview-before-apply

**Filed**: 2026-08-30
**Status**: In Review — implemented 2026-08-30; preview + Deep audit live-verified.

## What was built

- `static/js/ui/saveload-view.js` — Load JSON… parses the file first and shows a
  **preview dialog**: counts (rooms/players/ways/items) + sanity issues (dangling exits,
  missing targets), with `[✅ Apply (Undo protects)]` / `[Cancel]` and a `🔬 Deep audit`
  button that runs the trigger validator on the incoming world.
- Apply rides `POST /api/load` with `persist: true` (GUI opt-in; see task-369/375 notes).
- Undo snapshot pushed before mutation — the preview never mutates.

## Note

The Deep audit button was added in the same session (validator on the throwaway world
dict). Original audit text asked for counts + sanity issues only; the audit is the
superset. task-375 (audit-on-import) is folded into this — no separate UI needed.
