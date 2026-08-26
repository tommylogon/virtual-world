---
group: Trigger System
wiki: "[[Rules Engine/Triggers & Effects]]"
---

# Trigger Graph Editor — Node-Based Blueprint System

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
- [x] Added effect types: `adjust_uses`, `reduce_uses` with `node_id` field
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
- Added trigger/effect/condition types (on_use_on, on_toggle_on, on_toggle_off, on_depleted, adjust_uses, reduce_uses, uses_above, target_tag)
- Template blueprints (6 seeded: on_use→message, on_examine→reveal name, on_tick→warm room, on_use_on tag→message, on_toggle_on→set_state, on_depleted→message)

❌ Remaining (Phase 2 & 3, not started):
- Phase 2: Blueprint browser (dedicated UI beyond the editor picker)
- Phase 3: Runtime compile of blueprints → graph edges + trigger nodes; condition branching (YES/NO); AND/OR condition logic

**Phase 2 & 3**: Not started