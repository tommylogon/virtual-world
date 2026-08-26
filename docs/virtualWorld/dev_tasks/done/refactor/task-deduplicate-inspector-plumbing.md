---
group: Refactor
---

# Deduplicate Inspector Shared Plumbing

**Filed**: 2026-08-09
**Priority**: Low
**Status**: In Review — implemented 2026-08-09, node harness 19/19 checks pass, full suite 787 passed (only the 11 pre-existing give-item fixture failures).

---

## Summary

The inspector views (`way-view`, `item-view`, `area-view`, `agent-view`, `paperdoll-view`, `memory-view`, `behaviors-view`, `lore-view`, `trigger-helpers`) each re-implemented the same plumbing in slightly different ways: an HTML-escaping `esc()`, the field-lock toggle trio, and a ~80-line "AI Improve" flow. This consolidation moves the shared logic into `inspector/helpers.js` so the views stop carrying their own copies.

## Changes

### `inspector/helpers.js` (new shared helpers)

- `InspectorHelpers.esc(text)` — HTML-escape double quotes (was 9+ local copies)
- `InspectorHelpers.escId(nodeId)` — escape single quotes for inline-handler embedding
- `InspectorHelpers.renderLockToggle(field, lockedFields, escapedId)` — field-lock toggle span
- `InspectorHelpers.toggleFieldLock(nodeId, field)` — toggle a field's locked state
- `InspectorHelpers.getLockedFields(props)` — read the locked-fields list
- `InspectorHelpers.improveWithAI(nodeId, spec)` — shared AI Improve flow:
  existence/description/API-key checks, button busy state, LLM call + JSON
  extraction, update + refresh + re-render, error handling. Callers supply
  `{ btnId, system, buildPrompt, apply }` — only the schema-specific parts.

### Views delegating to helpers

- **way-view.js** — `esc` + lock-toggle trio delegate to helpers; `improveWayWithAI`
  now calls `InspectorHelpers.improveWithAI` with way-specific system/buildPrompt/apply.
- **item-view.js** — same for its lock-toggle trio and `_improveItemWithAI`.
- **area-view.js** — `esc` + `improveRoomWithAI` delegate.
- **agent-view.js / memory-view.js / behaviors-view.js / lore-view.js / paperdoll-view.js** —
  local `const esc = ...` replaced with `InspectorHelpers.esc` (where semantics matched).
- **trigger-helpers.js** — `InspectorItemView._renderLockToggle` → `InspectorHelpers.renderLockToggle`.

### Deliberately NOT deduplicated

- `paperdoll-view.js:221` — its `esc` also escapes single quotes (`&#39;`), which the
  shared `esc` does not. Semantically distinct; kept local.
- The per-type `showX` entry points and their field layouts stay in their own views —
  this pass only removes the duplicated *plumbing*, not the view content.

## Verification

- `node --check` on all 10 touched files passes.
- Node harness loads all views against stub globals: all 19 checks pass —
  shared helpers exist and behave, every view's public `showX`/improve entry points
  still resolve, and no view re-implements the double-quote `esc` locally.
- No stale references to `InspectorItemView._renderLockToggle` / `InspectorWayView._toggleFieldLock` remain.
- Full pytest suite: 787 passed, same 11 pre-existing give-item fixture failures — no regression.
