# Task-246: Graph — Show All or Selected Floors of Areas

**Status:** Done — implemented 2026-08-16, live-verified. Moved to review/.
**Source:** `dev_tasks/developer ideas.md` (option to show all or select floors of areas only)

## Goal

Add a graph filter to show all areas or a selected floor/subset of areas (e.g. basement /
ground / upper), so large multi-floor scenarios can be navigated without clutter.

## Notes / open questions

- How floors are modelled: area `properties` tag (`floor`) vs by connected area group.
  **Decided: area `properties.floor` (integer).** The picker derives available floors from area nodes on the graph.
- UI: a floor picker in the graph toolbar (All / per-floor), filtering area+child nodes.
  **Implemented: `<select id="floor-filter">` in the graph toolbar,** next to Triggers/Items toggles.
- Interaction with existing `_showItems`/`_showTriggers` toggles and the tag filter overlay:
  floor filter should compose with them. **Done — composes at load time** (areas outside the
  floor plus their unlinked children are omitted; edges to hidden endpoints skipped; the
  items/triggers toggles still gate their respective node kinds).

## Implementation

- `static/js/graph-manager.js`: added `_floorFilter`/`_floorOptions` state,
  `setFloorFilter()`, `refreshFloorOptions()`, `floorFilterActive()`.
- `static/js/graph/network-manager.js`: in `loadGraphData()` when a floor is active, compute
  the set of visible areas (floor match) and the child nodes directly linked to them; only
  those render, and edges whose endpoints are hidden are skipped. Populates the picker after load.
- `templates/index.html`: added the floor filter `<select>` to the graph toolbar.

## Verification

- `node --check` on both JS files; `pytest` guard suites pass (62).
- Live (world has floors 0 and -1): All floors → 51 nodes (areas on 0 and -1). Floor "0" →
  only 0-floor areas + children. Floor "-1" → only the 1 cellar area + its 4 children.
  Composes with item/trigger toggles.