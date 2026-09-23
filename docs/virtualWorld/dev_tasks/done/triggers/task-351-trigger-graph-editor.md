---
group: Trigger System
wiki: "[[Rules Engine/Triggers & Effects]]"
---

# Trigger Graph Editor — Node-Based Blueprint System

## Outcome (verified 2026-09-22) — Phase 1 closed; Phases 2–3 re-filed as task-442

This task's core deliverable — the node-based trigger graph editor — **shipped in Phase 1**
and is in daily use. Its remaining plan (Phase 2 browser, Phase 3 engine integration) is
real, unstarted work, so it has been **re-filed as [[dev_tasks/todo/triggers/task-442-trigger-blueprint-runtime-compile-and-browser|task-442]]**
rather than left to sit in the in-progress column as one open-ended task.

- **Phase 1 — done.** `static/js/shared/trigger-graph.js`: node renderer + sockets, drag-to-
  connect, right-click menu with search, inline field editing, SVG bezier wires,
  serialize/deserialize, blueprint I/O (`:1667-1765`), compile-to-engine (`:1984`),
  compile-to-behaviors (`:1832`), inspector + library-editor integration. Blueprint
  storage is real (`POST /api/library/triggers`, `routes/library_routes.py:48-60`;
  `data/library/triggers/` holds the six seeded templates plus scratch files).
- **One Phase-1 claim was false and is corrected below:** `reduce_uses` does not exist in
  the codebase — the effect registry has `adjust_uses` only
  (`engine/effect_handlers/equipment.py:182`), and it already accepts a negative delta.
- **Phase 2 residual** — the dedicated searchable blueprint browser (the directory and
  templates already exist) → task-442, slice 3.
- **Phase 3** — not started: no Python handles blueprints at all; condition branching and
  AND/OR/NOT are dropped or forced on compile → task-442, slices 1–2.
- Task-388 owns the editor's UI/UX work and the compile-honesty defects (#9–#11); this
  task is not superseded by it.

### Prior state (2026-09-21)

**Phase 1 is genuinely implemented** (the file's "12 of 12" is honest, bar one
false entry): node renderer and sockets, drag-to-connect, right-click context menu
with search, inline field editing, SVG bezier wires, serialize/deserialize,
blueprint save/load/export/import, inspector and library-editor integration, and
compile-to-engine — all in `static/js/shared/trigger-graph.js` (`_serializeGraph`
`:1622`, `compileToEngine` `:1984`, `compileToBehaviors` `:1832`, blueprint I/O
`:1667-1765`, sockets/wires `:1299-1503`). The blueprint storage claim is accurate:
`POST /api/library/triggers` (`routes/library_routes.py:48-60`, `triggers` in
`REGISTRY_TYPES` `routes/library_ops.py:16`) writing per-entry files under
`data/library/triggers/` (`routes/helpers.py:155-202`). The six seeded template
blueprints exist (the directory now holds nine files — the six templates plus
three scratch ones).

**One Phase-1 claim is false:** `reduce_uses` does not exist anywhere in the
codebase (grep finds it only in generated docs and this file). The effect registry
has `adjust_uses` only (`engine/effect_handlers/equipment.py:182`,
`engine/triggers/constants.py:75,115`), and it accepts a negative delta
(`:75-78`), so `reduce_uses` is either redundant or never added.

**Phase 2 — Blueprint Library: partially done by accident.** The two unticked
checkboxes (directory exists, templates seeded) are actually satisfied. What
remains is the **dedicated searchable blueprint browser** — today there is only
the in-editor `_loadBlueprint` picker (`trigger-graph.js:1714-1750`, a raw floating
div).

**Phase 3 — Engine Integration: not started.** No Python handles blueprints at
all (`grep blueprint *.py` → 0 hits). Specifically missing: runtime compile of a
blueprint to graph edges and trigger nodes; condition branching (YES/NO) compiled
to engine conditions — `_traceGraph` (`:2082-2113`) AND-folds conditions and keeps
only a NO-branch message as `fail_message`, dropping every other NO effect; and
AND/OR/NOT logic in branches — `compileToEngine` always emits `{operator:'and'}`
(`:1996`). Those latter two are also recorded as task-388 defects #9-#11.

**Relationship to task-388:** task-388 supersedes this editor's **UI/UX** work
(pan/zoom now exists at `:1113-1219`, so this file's "no pan/zoom" complaints are
stale) but explicitly leaves this task's Phase 2 browser and Phase 3 runtime
compile open. So this task is not superseded as a whole; its residual scope is
real and currently unowned.

**Filed**: 2026-07-27  
**Priority**: High  
**Status**: In Progress (Phase 1 mostly complete)  
**Updated**: 2026-07-31  

---

## Summary

Replace the current form-based trigger editor with a **node-graph editor** (Unreal Blueprint-style) where triggers are visually constructed by connecting nodes. The resulting trigger graph can be saved as a **blueprint** and attached to any item, way, or character.

## Architecture

```
                  ┌───────────────────────┐
                  │   TriggerGraphEditor   │
                  │  (static/js/shared/    │
                  │   trigger-graph.js)    │
                  └───────┬───────────────┘
                          │ builds / edits
                  ┌───────┴────────────────┐
                  │   Trigger Blueprint    │
                  │  (JSON serializable)   │
                  └───────┬────────────────┘
                          │ compiled to
                  ┌───────┴────────────────┐
                  │   Graph Edge + Node    │
                  │  (existing engine      │
                  │   format)              │
                  └────────────────────────┘
```

## Node Types

### Trigger Node (entry point)
- One per graph
- Sockets: `output` (bottom)
- Properties: trigger type (on_use, on_take, on_tick, etc.)

### Condition Node
- Sockets: `input` (top), `output_yes` (bottom), `output_no` (right)
- Properties: condition type + params (temperature_below, has_item, state_equals, etc.)

### Effect Node
- Sockets: `input` (top)
- Properties: effect type + params (message, spawn_item, adjust_environment, etc.)

## Blueprint System

- Blueprints stored in `data/library/triggers/*.json`
- Blueprint editor with name, description, tags
- Attach blueprint to item: creates graph edges + trigger nodes in world
- Detach/swap blueprints on existing items

## Implementation Plan

### Phase 1 — Core Node Graph (current)
- [x] `trigger-graph.js` — Node renderer, socket system, drag-to-connect wires
- [x] Node creation via right-click context menu with search
- [x] Inline field editing on nodes (no side panel)
- [x] Wire routing (SVG bezier curves)
- [x] Property panels (click node → edit params)
- [x] Serialize graph to JSON blueprint format
- [x] Deserialize JSON to rendered graph
- [x] Blueprint export/import (JSON file save/load)
- [x] Integration with item inspector (🧩 Graph button opens editor)
- [x] Integration with library editor (🧩 Graph button opens editor)
- [x] Compile graph to engine trigger format
- [x] Added trigger types: `on_use_on`, `on_toggle_on`, `on_toggle_off`, `on_depleted`
- [x] Added effect types: `adjust_uses` with `node_id` field — ⚠️ **CORRECTED 2026-09-22:** `reduce_uses` does **not** exist anywhere (`grep` finds it only in docs); `adjust_uses` covers it via a negative delta (`engine/effect_handlers/equipment.py:182`)
- [x] Added condition types: `uses_above`
- [x] Added `target_tag` field for `on_use_on` trigger nodes
- [x] Blueprint save to API/library (server-side blueprint storage via `data/library/triggers/` + generic library CRUD)
- [x] Template blueprints (6 pre-built: on_use→message, on_examine→reveal name, on_tick→warm room, on_use_on tag→message, on_toggle_on→set_state, on_depleted→message)

### Phase 2 — Blueprint Library
- [ ] `data/library/triggers/` directory
- [ ] Blueprint browser (similar to item library)
- [ ] Template blueprints (on_use → message, on_tick → adjust_environment, etc.)

### Phase 3 — Engine Integration
- [ ] Compile blueprint → graph edges + trigger nodes at runtime
- [ ] Compile condition branching (YES/NO paths) to engine conditions
- [ ] Support for AND/OR condition logic in branches

---

## Status Update (2026-07-31)

**Phase 1 completion: 12 of 12 items implemented**

✅ Done:
- Node renderer & socket system
- Drag-to-connect wires
- Right-click context menu with search
- Inline field editing (in node bodies, no side panel)
- Wire routing (SVG bezier curves)
- Serialize/deserialize to JSON blueprint
- Blueprint save to API/library (server-side blueprint storage via `data/library/triggers/` + `/api/library/triggers` generic CRUD; `Save Blueprint` / `Load Blueprint` picker / `Export` / `Import file` in the editor toolbar)
- Integration with item inspector & library editor
- Compile graph to engine trigger format
- Added trigger/effect/condition types (on_use_on, on_toggle_on, on_toggle_off, on_depleted, adjust_uses, ~~reduce_uses~~, uses_above, target_tag) — ⚠️ `reduce_uses` never existed; see the correction above
- Template blueprints (6 seeded: on_use→message, on_examine→reveal name, on_tick→warm room, on_use_on tag→message, on_toggle_on→set_state, on_depleted→message)

❌ Remaining (Phase 2 & 3, not started):
- Phase 2: Blueprint browser (dedicated UI beyond the editor picker)
- Phase 3: Runtime compile of blueprints → graph edges + trigger nodes; condition branching (YES/NO); AND/OR condition logic

**Phase 2 & 3**: Not started
## Follow-up (2026-09-02)

UX/viewport overhaul research for this editor filed as [[task-388-trigger-graph-editor-overhaul]]
(todo/ui): pan + zoom (currently absent, and Fit corrupts the coordinate model), wire deletion and
YES/NO branch coloring, cycle prevention, undo/multi-select, and compile-honesty findings
(fan-out and behavior NO-branch wires are silently dropped on save; behavior priority is derived
from node Y position, overriding the editable Priority field). Those compile findings should be
resolved as part of this task's Phase 3 engine work.
