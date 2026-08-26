---
group: Graph & Area UX
---
# One-Way Ways/Doors

**Filed**: 2026-07-30  
**Updated**: 2026-07-30  
**Priority**: Low  
**Status**: Done  

---

## Summary

Ways (doors, passages) that can only be traversed in one direction — e.g. a one-way door, a jump-down ledge, a slide, a portal that only goes one way.

---

## Implementation

### Backend

- `movement.py:connect_areas` — added `one_way` parameter; sets `one_way: True` on way node properties
- `movement.py:move_to_area` — checks `way_node.properties.one_way` + compares `current_area.name` against `area_from`; raises `ValueError` with message if traversing from wrong side
- `npc_behaviors.py:_get_path_to_area` — BFS skips one-way ways when current node is not the source area
- `npc_behaviors.py:_get_nearest_player_to` — same BFS skip
- `npc_behaviors.py:slasher_hunt` — checks one-way before moving; returns descriptive message if blocked
- `routes/graph.py:build_connect_legacy` — accepts `one_way` in POST data, passes to way node props
- `virtual_world_engine.py:connect_areas` — passes through `one_way` parameter
- `mcp_server.py:connect_areas` — exposes `one_way` parameter in MCP tool

### Frontend

- `way-view.js` — checkbox toggle in way inspector: `➡️ One-way (traversable only from area A → B)`
- `way-view.js` — `one_way` included in library save payload
- `network-manager.js` — one-way ways rendered with blue border (`#58a6ff`) and ` →` label suffix
- `network-manager.js` — tooltip shows `➡️ One-way (from <area_from>)`

### Files changed

- `engine/movement.py` — 2 changes (connect_areas param, move_to_area check)
- `engine/npc_behaviors.py` — 3 changes (two BFS checks, slasher_hunt check)
- `routes/graph.py` — 1 change (accept one_way in POST)
- `virtual_world_engine.py` — 1 change (pass through one_way)
- `mcp_server.py` — 1 change (one_way param + body)
- `static/js/inspector/way-view.js` — 2 changes (checkbox + library save)
- `static/js/graph/network-manager.js` — 2 changes (node rendering + tooltip)

## Related

- [[todo/gameplay/task-99-room-grids-and-movement|task-99: Room grids and movement]]
