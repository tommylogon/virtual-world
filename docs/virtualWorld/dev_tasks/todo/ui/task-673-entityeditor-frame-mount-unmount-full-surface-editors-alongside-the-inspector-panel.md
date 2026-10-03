---
type: task
status: todo
area: ui
priority: medium
---

# task-673: EntityEditor frame: mount/unmount full-surface editors alongside the inspector panel

**Filed:** 2026-10-02
**Related:** task-251, task-512

## Goal

Phase 1 of docs/design/full-entity-editors.md. Add an EntityEditor that mounts a full-viewport editor surface for character, item and area, WITHOUT changing any per-editor layout yet. Requirements: (a) the new #entity-editor must be a different element from #inspector-panel - only panel.js may write to #inspector-panel, because mixing innerHTML writes with lit render() corrupts lit part tracking; (b) reuse the existing view modules agent-view.js, item-view.js, area-view.js as the single source of TemplateResults - do not fork them; (c) shared chrome: kind badge, inline-editable name, copyable node id, saved/in-flight indicator, close; (d) Esc and backdrop close, focus moves to the header name on open and returns to the opening element on close; (e) entry points - an expand control in the inspector header and double-click on a canvas node; (f) clicking a node still opens the contextual peek, so the peek remains the default. No layout change, no persistence change, no deep links (that is phase 5 and is not decided). Verify in a live browser that all three entity types mount and unmount cleanly and that lit part tracking is intact.

## Acceptance

- TODO
