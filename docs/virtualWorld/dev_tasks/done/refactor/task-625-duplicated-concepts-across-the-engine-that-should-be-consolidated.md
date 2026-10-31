---
type: task
status: done
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
- **Items 1 and 2 are completed**: Retired redundant `graph_background.positions` map in favor of authoritative `node.properties.x/y`; unified layout configuration under `activeLayout()` and `config.graphLayoutMode`.

## Active Inventory

### 1. A node's layout position has two homes

`graph_background.positions` (serialized; **0 entries** in the live world, 2,763 stale entries in `kraktooth_goblin_camp.json`) versus the node's `properties.x/y` (what the layout engine, `moveNode`, and `GraphRelativeLayout.persistFrozenDrop` actually write).

- **Authoritative**: `node.properties.x` and `node.properties.y`.
- **Remedy**: Retired background `positions` map on serialization. `_applyPositions()` reads directly from `node.properties.x/y`. Stale positions map stripped from `kraktooth_goblin_camp.json` and scrubbed on load/save in `engine/serialization.py`.

### 2. The graph layout axis is expressed three ways

`graphManager._cardinalLayout` (Map, runtime; persisted as `config.graphCardinalLayout`), `config.graphLayoutMode` (`'free'`/`'levels'`), and derived `activeLayout()` (`'graph'|'map'|'levels'`).

- **Authoritative**: `activeLayout()`.
- **Remedy**: Unified layout selection via `graphManager.setLayout(layout: 'graph' | 'map' | 'levels')` driving `config.graphLayoutMode` as single source of truth.

## Resolved or Delegated Items (Historical Record)

3. **"Where I have been" has two stores** - `player.visited_areas` (area names) vs `kind == "area"` observation memories. **Owned by task-430**; do not separately refactor here.
4. **"What I have seen" has two stores** - `player.discovered_items` vs `kind == "item"` observation memories. **Also task-430.**
5. **Payload version constants** - `APP_VERSION` vs format marker. **Resolved by task-453** (`SCHEMA_VERSION`).
6. **Character definition vs Player** - Character definition properties vs `Player` fields. **Resolved by task-914**; node properties are the single persisted home.

## Acceptance (for Items 1 and 2)

- [x] Node positions in `graph_background.ts` read from and write to `node.properties.x/y`; `graph_background.positions` is removed from serialization.
- [x] Graph layout settings are consolidated onto a single configuration setting matching `activeLayout()`.
- [x] Scenario save and load preserves node coordinates without redundant coordinate dictionaries.
- [x] Front-end checks (`npm run build:ts`, `python tools/ts_convert.py check`) pass cleanly.

## Why

Dual-store concepts create silent drift where readers query different sources of truth. Consolidating onto one authoritative home, with derived projections rebuilt from it, removes an entire class of synchronization defects.

## Steps to verify

1. Node position inspection:
   - expected: Moving a node in the graph editor updates `node.properties.x` and `node.properties.y`; `/api/state` reflects these properties; no auxiliary position map is serialized.
   - observed: `graph_background.ts` writes `{}` to world block; `_applyPositions` reads `node.properties.x/y`; `kraktooth_goblin_camp.json` stripped of 2,763 redundant positions; `engine/serialization.py` scrubs on load and drops on scenario save.
2. Layout mode consistency:
   - expected: Toggling between Free/Graph, Levels, and Map views writes a single configuration value that cleanly drives `activeLayout()`.
   - observed: `graphManager.setLayout()` cleanly handles transitions between `'graph'`, `'map'`, and `'levels'`.

## Files

- `static/js/graph/graph-background.ts` - retired redundant positions serialization; read positions from node properties
- `static/js/graph-manager.ts` - unified layout mode state via `setLayout()` and `activeLayout()`
- `static/js/graph/toolbar.ts` - route `setLayout` through `graphManager.setLayout()`
- `static/js/config.ts` - consolidated `graphLayoutMode` configuration
- `engine/serialization.py` - scrubbed redundant positions map on load and omitted on scenario save
- `data/scenarios/kraktooth_goblin_camp.json` - cleared 2,763 redundant entries

## Verification (2026-10-31)
- Verified with targeted test selection:
  - `python tools/ts_convert.py check --lenient-guards`: gate green (build, typecheck, lint, module:check, unit all ok).
  - `python -m pytest tests/test_graph_background_layers.py tests/test_world_scopes.py tests/test_trigger_migration.py`: 48 passed.
  - Zero em-dashes introduced across all touched files.
