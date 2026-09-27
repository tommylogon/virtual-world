---
type: task
status: review
area: ui
priority: medium
---

# task-531: Graph workspace: contextual scope bar (breadcrumb, counts, WorldPainter)

**Filed:** 2026-09-27
**Related:** task-530 task-397

## Goal

Second tier of the graph-toolbar redesign in docs/design/graph-toolbar-mockup.html: a
scope bar that appears under the primary bar when a world scope is loaded, with a zone
breadcrumb, loaded-node counts, and the two ways out — open the scope in the
WorldPainter, or go back to the whole world. task-530 ships only the scope chip plus
the node-count stat.

**Decided while filing this (2026-09-27):** the mockup's `⤓ Generate` and `✕ Clear`
are **not** part of it. Generation belongs to the WorldPainter's own toolbar, which
already carries `⚙ Generate` / `🧹 Ungenerate` (`worldpainter/editor.js:436-438`) and
is the only surface that can paint or compile a grid — a Generate button in the graph
workspace would duplicate a control that cannot do the job. `✕ Clear` was dropped
rather than mapped onto "show whole world", which is already a button beside it.

## Acceptance

- [x] A `#scope-bar` row under the toolbar, shown **only** while a scope is loaded
      (the whole-world view keeps the chip alone).
- [x] A zone breadcrumb `world › West woods`, root first, ending on the loaded scope.
      Built from `parent_id` in the already-fetched flat scope list
      (`graphManager._scopeSummaries`), so no request per scope change — the only
      endpoint that returns a breadcrumb is the WorldPainter's per-scope grid payload.
      Each ancestor crumb loads that scope; the current one is `aria-current`.
- [x] Loaded-node counts on the bar ("53 areas · 77 ways · 130 loaded", plus
      characters/items when present), from the dataset actually on the canvas.
- [x] The scope chip's own count steps aside while the bar shows it, so the numbers
      are never stated twice. Below 1240px the bar is dropped and the chip keeps
      reporting.
- [x] `🖌 Open in WorldPainter` opens the painter **already scoped** to the loaded
      scope — `VW.worldPainter.open(scopeId)` takes the id (`editor.js:152-179`).
- [x] `← Show whole world` unloads the scope (`setScopeFilter('')`) and keeps the
      picker's value in step.
- [x] A scope that is not in the manifest (stale selection) falls back to the
      picker's own label instead of an empty trail; a `parent_id` cycle cannot hang
      the trail.
- [x] `breadcrumbTrail()` is pure and unit-tested (root-first order, empty for the
      whole world / an unknown scope, orphan parent, cycle).
- [x] `loadScopeFilterOptions()` re-syncs the bar, so a scenario switch (which resets
      `_scopeFilter` without touching the picker) cannot leave a stale bar up.
- [x] Verified in the browser: West woods shows `world › West woods · 53 areas · 77
      ways · 130 loaded`, the crumb navigates up, and Open in WorldPainter lands on
      the painter's own `world › West woods` view with its painted grid.

## Notes

- Several scopes in the kraktooth_goblin_camp world (`world`, `deep_woods`,
  `deep_woods_2`) have **no** nodes of their own, so the bar correctly shows an empty
  count and a blank canvas for them. That is the scope graph saying so, not a bug.
- Switching scope does not re-fit the camera (pre-existing: `loadGraphData` restores
  the saved viewport). Left alone — it belongs with task-526/527 territory.
