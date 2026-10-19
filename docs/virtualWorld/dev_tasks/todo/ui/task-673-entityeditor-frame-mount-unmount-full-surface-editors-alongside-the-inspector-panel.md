---
type: task
status: todo
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-673: EntityEditor frame: mount/unmount full-surface editors alongside the inspector panel

**Filed:** 2026-10-02
**Related:** task-251, task-512

## What

Phase 1 of docs/design/full-entity-editors.md. Add an EntityEditor that mounts a full-viewport editor surface for character, item and area, WITHOUT changing any per-editor layout yet. Requirements: (a) the new #entity-editor must be a different element from #inspector-panel - only panel.js may write to #inspector-panel, because mixing innerHTML writes with lit render() corrupts lit part tracking; (b) reuse the existing view modules agent-view.js, item-view.js, area-view.js as the single source of TemplateResults - do not fork them; (c) shared chrome: kind badge, inline-editable name, copyable node id, saved/in-flight indicator, close; (d) Esc and backdrop close, focus moves to the header name on open and returns to the opening element on close; (e) entry points - an expand control in the inspector header and double-click on a canvas node; (f) clicking a node still opens the contextual peek, so the peek remains the default. No layout change, no persistence change, no deep links (that is phase 5 and is not decided). Verify in a live browser that all three entity types mount and unmount cleanly and that lit part tracking is intact.

## Acceptance

- TODO

## Browser UI and intended live verification

Intended UI home: Select a character, item, or area in the graph → contextual inspector peek → expand control in the inspector header. Double-clicking a canvas node is the second full-editor entry point; clicking once keeps opening the contextual peek.

Current availability: The task defines a new `#entity-editor` separate from `#inspector-panel`; the full-surface frame and entry points are planned, with no mount/unmount browser pass recorded.

Live steps when available:
1. At desktop width, select one character, one item, and one area in turn; for each, open the peek and activate its expand control.
   - expected: a full-viewport editor mounts for the selected entity using the existing view module; `#inspector-panel` remains the peek and is not overwritten by Lit rendering.
2. Close each editor with its close control, Escape, and backdrop; reopen it from the same peek.
   - expected: the editor unmounts cleanly, focus returns to the element that opened it, and reopening does not duplicate event handlers or corrupt the view.
3. Double-click each of the three canvas node types, then single-click one node.
   - expected: double-click opens the matching full editor; single-click still opens the contextual peek by default.
4. Open the editor, focus its header name, edit it, and close/reopen.
   - expected: focus begins at the name, the saved/in-flight indicator reflects the edit, and the name change round-trips without changing the entity layout or persistence model.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
