---
type: task
status: todo
area: refactor
priority: low
---

# task-441: Split the frontend giants and the trigger test module

**Filed:** 2026-09-21
**Supersedes:** task-314's frontend and test scope
**Related:** task-216 (trigger editor inspector work), task-218 (the module-per-concern shape)

## Goal

Extract focused modules from the oversized JS files, and split the single trigger test
module so failures isolate cleanly. **One file per commit, no behaviour change.**

## Measured targets (2026-09-21)

| File | Lines | Suggested seam |
|------|------:|----------------|
| `static/js/inspector/agent-view.js` | 2276 | sub-views: memory, plans, vitals, relationships, paperdoll (task-314's wave-2 attempt produced `inspector/agent/agent-header.js` and was **abandoned** — that orphan was deleted 2026-09-21; restart from the live file, do not resurrect the snapshot) |
| `static/js/shared/trigger-graph.js` | 2116 | layout/rendering from node/edge editing |
| `static/js/shared/trigger-editor.js` | 2022 | rendering vs validation vs serialization |
| `static/js/item-library.js` | 1401 | list/editor/import from rendering |
| `static/js/main.js` | 1060 | init wiring and cross-module event subscriptions |
| `tests/test_trigger_system.py` | 2724 | split by subsystem (evaluation, effects, conditions, scheduling) — 14 classes in one module |

`static/js/library-browser.js` overlaps `item-library.js` — decide ownership before
splitting either.

## Approach

1. **One file at a time.** Pick the smallest target first as the proof of pattern.
2. **No behaviour change.** Keep `window.Foo` namespaces and re-export moved members as
   thin delegates where call sites use them (the `graph/projector.js` pattern in
   task-314's wave 1).
3. **Add the `<script>` tag in the same commit.** Task-314's wave 2 left
   `way-view-triggers.js` / `way-view-connections.js` unloaded and threw on open for two
   files; the orphan above is the other half of that failure mode. Verify with
   `node --check` on every touched file.
4. **Record what moved** as a table in this file.

## Acceptance

- Each split lands with the host file's line count materially reduced, the new module
  loaded by `templates/index.html` (if browser-global), and no orphan left behind.
- `node --check` clean on all touched JS; `node tools/unit/run.cjs` still green except
  known pre-existing failures.
- For the test split: each new test module runs standalone, and the total test count is
  unchanged.

## Non-goals

- Behaviour changes or UI redesign.
- `static/js/graph/network-manager.js` — already split in task-314 wave 1
  (`projector` / `overlays` / `tooltips` / `focus`).
- Backend splits (task-440).
