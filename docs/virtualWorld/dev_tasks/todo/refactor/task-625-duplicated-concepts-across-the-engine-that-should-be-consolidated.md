---
type: task
status: todo
area: refactor
priority: medium
wiki: "[[Feature Map]]"
---

# task-625: Duplicated concepts across the engine that should be consolidated

**Filed:** 2026-09-30
**Updated:** 2026-10-31
**Related:** task-453, task-430, task-914

## What

Cross-cutting: several concepts were implemented in more than one place with different behavior, storing the same fact twice.

STATUS UPDATE (2026-10-31):
- **Item 5 is completed**: Resolved by `task-453` (`SCHEMA_VERSION` in `version.py`, `engine/schema.py`).
- **Character node vs player duplication is completed**: Resolved by `task-914` and codified in AGENTS.md simulation invariants (persisted definition lives on node properties; runtime state lives on Player; `to_scenario_dict` strips player definition copies).
- **Items 3 and 4 are delegated**: "Where I have been" (`visited_areas` vs area memories) and "What I have seen" (`discovered_items` vs item memories) are owned by `task-430`.
- **Remaining active scope**: Items 1 and 2 below.

## Active Inventory

### 1. A node's layout position has two homes

`graph_background.positions` (serialized; **0 entries** in the live world) versus the node's `properties.x/y` (what the layout engine, `moveNode`, and `GraphRelativeLayout.persistFrozenDrop` actually write).

- **Authoritative**: `node.properties.x` and `node.properties.y`.
- **Remedy**: Retire the background `positions` map or feed it directly from node properties. Do not serialize an empty or divergent `positions` dictionary in scenario files.

### 2. The graph layout axis is expressed three ways

`graphManager._cardinalLayout` (Map, runtime; persisted as `config.graphCardinalLayout`), `config.graphLayoutMode` (`'free'`/`'levels'`), and derived `activeLayout()` (`'graph'|'map'|'levels'`).

- **Authoritative**: `activeLayout()`.
- **Remedy**: Unify the configuration into a single persisted layout mode enum (`layout_mode: 'graph' | 'map' | 'levels'`) to prevent flag desynchronization.

## Resolved or Delegated Items (Historical Record)

3. **"Where I have been" has two stores** - `player.visited_areas` (area names) vs `kind == "area"` observation memories. **Owned by task-430**; do not separately refactor here.
4. **"What I have seen" has two stores** - `player.discovered_items` vs `kind == "item"` observation memories. **Also task-430.**
5. **Payload version constants** - `APP_VERSION` vs format marker. **Resolved by task-453** (`SCHEMA_VERSION`).
6. **Character definition vs Player** - Character definition properties vs `Player` fields. **Resolved by task-914**; node properties are the single persisted home.

## Acceptance (for Items 1 and 2)

- [ ] Node positions in `graph_background.ts` read from and write to `node.properties.x/y`; `graph_background.positions` is removed from serialization.
- [ ] Graph layout settings are consolidated onto a single configuration setting matching `activeLayout()`.
- [ ] Scenario save and load preserves node coordinates without redundant coordinate dictionaries.
- [ ] Front-end checks (`npm run build:ts`, `python tools/ts_convert.py check`) pass cleanly.

## Why

Dual-store concepts create silent drift where readers query different sources of truth. Consolidating onto one authoritative home, with derived projections rebuilt from it, removes an entire class of synchronization defects.

## Steps to verify

1. Node position inspection:
   - expected: Moving a node in the graph editor updates `node.properties.x` and `node.properties.y`; `/api/state` reflects these properties; no auxiliary position map is serialized.
   - observed: `graph_background.positions` is currently empty (0 entries) while `properties.x/y` carries live coordinates.
2. Layout mode consistency:
   - expected: Toggling between Free, Levels, and Map views writes a single configuration value that cleanly drives `activeLayout()`.
   - observed: Dual boolean/string flags currently coexist.

## Files

- `static/js/graph/graph-background.ts` - retire redundant `positions` map
- `static/js/graph-manager.ts` - unify layout mode state
- `engine/serialization.py` - ensure positions are only serialized in node properties

## Browser UI and intended live verification

Intended UI home: Graph canvas view and Toolbar layout selectors.

Live steps when available:
1. Drag a node to a new position on the canvas.
2. Save scenario and reload.
3. Verify the node appears in the exact dragged position and node properties carry the updated coordinates.
4. Switch layout mode between Graph, Map, and Levels; verify toolbar selector and canvas agree.

## Refactor discipline (applies to this task)

1. **Dedup & reuse pass (mandatory).** Scan touched concerns for duplicate logic; consolidate onto one owner.
2. **Agent-experience & cleanliness (mandatory).** Keep modules under ~600 lines where seams allow; add one-line module docstrings.
3. **No behaviour change unless the card says so.** Extraction and consolidation only.
4. **One file/concern at a time**, verified with a targeted test selection.

## Reconnaissance (2026-10-31)
- Measured: Items 3-4 belong to task-430. Item 5 resolved by task-453. Character definition resolved by task-914. Item 1 (`graph_background.positions`) has 0 live entries. Item 2 has coexisting flags in `graph-manager.ts`.
- Verdict: STILL_VALID, narrowed to Items 1 and 2. Status remains todo.
