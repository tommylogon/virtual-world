---
wiki: "[[World Building/Graph System]]"
---
# Edge Type Refactor — Spatial Relations + Cleanup

**Filed**: 2026-07-25
**Updated**: 2026-07-30
**Priority**: Medium
**Status**: In Review — completed 2026-08-05. Removed all legacy edge-type dead reads from frontend (world-state.js getInventory/area/container lists, prompt-builder.js carriedItems, agent-view.js, library-browser.js, layout-engine.js, trigger-helpers.js, world-export.js). Kept routes/graph.py cleanup tuples (they genuinely remove stale edges on writes) and edge-types.js migration mapping. Backend: 490 passed, 1 skipped. All touched JS pass `node --check`.

---

## Summary

Replaced the three legacy edge types (`location`, `carried_by`, `contains`) with eight new spatial edge types (`in`, `on`, `under`, `behind`, `beside`, `at`, `carrying`, `equipped`). All engine modules, routes, and tests updated. Frontend got edge type dropdown on creation + inspector type changer.

## Why

The old system had three overlapping edge types doing the same job differently:

| Edge | Problem |
|------|---------|
| `location` | Did double duty — item→room AND item→player. Every inventory check had to also scan `carried_by` as fallback. |
| `carried_by` | Redundant with `location` for inventory. Different code paths used different types, forcing every lookup to check both. |
| `contains` | Same direction as `location` (item→container), but a different constant. No semantic value over `in`. |

Result: every item search looked like:
```python
for edge in (get_edges_for_target(player_id, EDGE_LOCATION) +
             get_edges_for_target(player_id, EDGE_CARRIED_BY)):
```

## What It Offers

### Clean spatial vocabulary
- `in` — inside a room, container, or area
- `on` / `under` / `behind` / `beside` — spatial relations to furniture (defined, ready for `examine` enrichment)
- `carrying` — in a player's inventory (not equipped)
- `equipped` — worn/held in a body slot (slot in edge props)

All edges follow one direction: **source = thing positioned, target = location/owner**.

### No more dual-type queries
One `get_edges_for_target(player_id, EDGE_CARRYING)` replaces the old `location` + `carried_by` double-check everywhere.

### Forward-looking
Spatial types (`on`, `under`, `behind`, `beside`) exist in the graph API/UI. `examine` can later describe items "under the table" without engine changes.

### Backward compatibility
Old edges auto-migrate on `load_from_dict()`. Query backward compat via `resolve_edge_types()` — querying `"in"` still matches old `"location"` and `"contains"` edges.

## Implementation

### `graph.py`
- New constants: `EDGE_IN`, `EDGE_ON`, `EDGE_UNDER`, `EDGE_BEHIND`, `EDGE_BESIDE`, `EDGE_AT`, `EDGE_CARRYING`, `EDGE_EQUIPPED`
- `normalize_edges()` on load:
  - `location` (item→room, player→room) → `in`
  - `location` (item→player) → `carrying`
  - `carried_by` → `carrying`
  - `contains` → `in` (same direction, not reversed)

### Engine (14 files)
All `EDGE_LOCATION` / `EDGE_CARRIED_BY` / `EDGE_CONTAINS` → `EDGE_IN` / `EDGE_CARRYING`.

### Routes (2 files)
`action.py`, `items_registry.py`.

### Tests (4 files)
`test_combat.py`, `test_equipment_system.py`, `test_ghost.py`, `test_matching.py`.

### Frontend
- `edge-types.js` — shared config with colors/icons/valid source-target combos
- `graph-manager.js` — edge inspector type dropdown, `_createEdgeWithType()`
- `context-menu.js` — "Attach To…" / "Attach Edge…" items
- `network-manager.js` — edge colors via `EdgeTypes` config
- `event-handlers.js` — drag from any node triggers attach flow

## Migration Mappings

| Old Edge | New Edge | Direction |
|----------|----------|-----------|
| `location` (item→room) | `in` (item→room) | Same |
| `location` (item→player) | `carrying` (item→player) | Same |
| `location` (player→room) | `in` (player→room) | Same |
| `carried_by` (item→player) | `carrying` (item→player) | Same |
| `contains` (item→container) | `in` (item→container) | Same (direction was already item→container) |

## Left for Later

- Old constants kept in `graph.py` for backward compat layer (`normalize_edges`, `resolve_edge_types`)
- Docs still reference old names in some places
- Spatial type awareness in `examine` descriptions (Phase E) — not implemented

## Update 2026-08-04 — legacy writes eliminated, spatial discovery wired

### Legacy write sites removed

All live code that *wrote* `location`/`contains`/`carried_by` now writes the modern types:

| Site | Was | Now |
|------|-----|-----|
| `engine/trigger_system.py:815` (spawn item → area) | `location` | `EDGE_IN` |
| `routes/library_routes.py:156,165` (import inventory) | `carried_by` | `EDGE_CARRYING` |
| `routes/graph.py:294` (item → container) | `contains` | `EDGE_IN` |
| `routes/graph.py:302` (item → character) | `carried_by` | `EDGE_CARRYING` |
| `routes/players.py:342` (item → player) | `location` | `EDGE_CARRYING` |

Also fixed `routes/graph.py:285`: it wrote `contains` **container → child** (reversed). Now writes `in` **child → container** (modern direction), with cleanup for both old and new orientations.

### Spatial types now discovered in-room

`EDGE_ON`/`EDGE_UNDER`/`EDGE_BEHIND`/`EDGE_BESIDE`/`EDGE_AT` were defined in `graph.py` and creatable in the UI but **never queried** — an item placed `on` a table was invisible to every lookup (couldn't find/examine/take it). Now `get_edges_for_target(area, EDGE_IN)` also returns spatial edges:

- pointed at the area itself (e.g. `at` the room), or
- pointed at any node that is itself `in` the target (e.g. `on` a table that's `in` the room).

`SPATIAL_EDGE_TYPES` constant added in `graph.py`. New tests in `tests/test_spatial_edges.py` (7 tests). Backend suite: **449 passed, 1 skipped**.

### 2026-08-04 follow-up — `examine [object]` renders spatial relations

Task 4 (labs.json) needs an agent to report each item's position relative to the table. Bug: `examine table` flattened every related item under one "Inside you see:" line — the on/behind/beside/under distinction was lost before it ever reached the agent.

Fixed `engine/item_actions.py` examine handler to group related items by edge type and render each with its relation label:

```
On the table: Ink Pen.
Under the table: rug.
Behind the table: Painting of the Wandering Forests of Vald.
Beside the table: toy_box.
```

`in` relations keep the existing "Inside you see:" wording, so ordinary containers (chest, backpack) are unaffected. Nested containers work uniformly: `examine toy_box` still reports its own contents as "Inside you see: toy_soldiers." while the box itself reads as "Beside the table: toy_box." from the table's view.

New tests in `tests/test_item_actions.py::TestSpatialRelationExamine` (3 tests). Backend suite: **452 passed, 1 skipped**.

### 2026-08-04 follow-up — agent prompt lists spatial relations inline

Task 4 still failed live: the base prompt's item list (`fmtItems` in `static/js/agent/prompt-builder.js`) flattened everything from `getItemsInArea()` into `- name: desc` lines, so the agent had to *invent* positions ("painting hangs on the wall" — actually behind the table). The relation data existed in the graph the whole time; only `examine table` surfaced it, and the agent never examined.

Fixed in `prompt-builder.js` (frontend-only):
- `buildRelationMap()` — walks `worldState.graph.edges`, maps each item to its `on`/`under`/`behind`/`beside`/`at`/`in` relation when the edge's target is another item present in the area (the anchor). Edges pointing at the area itself (e.g. `table` → room) stay flat.
- `indefiniteArticle()` — a/an for the inline phrasing.
- `fmtItems` now renders related items as `- on the table is an Ink Pen: ...` in the full-description branch and `on the table is an Ink Pen` in the names-only branch, so all light branches share it.

Example output for Task 4 (labs.json):
```
- table: A long table.
- beside the table is a toy_box: A small wooden toy box in the corner, ...
- behind the table is a Painting of the Wandering Forests of Vald: ...
- on the table is an Ink Pen: Using Ink, an Ink Pen is used to write or draw.
- under the table is a rug: A faded Persian rug covering most of the floor.
```

### Still open (compat-safe, low priority)

- Read/cleanup tuples in `routes/graph.py:83,293,301,312` still list legacy names — harmless (they clear old edges from stale saves).
- Frontend `world-state.js:146` default inventory list and `prompt-builder.js:596` still include `location`/`carried_by` — defensive fallbacks, no writes.
