---
type: task
status: done
area: ui
priority: medium
---

# Task-246: Graph — Show All or Selected Floors of Areas

**Status:** Done — implemented 2026-08-16, live-verified. Moved to review/.
**Source:** `dev_tasks/developer ideas.md` (option to show all or select floors of areas only)

## What

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

## How

- `static/js/graph-manager.js`: added `_floorFilter`/`_floorOptions` state,
  `setFloorFilter()`, `refreshFloorOptions()`, `floorFilterActive()`.
- `static/js/graph/network-manager.js`: in `loadGraphData()` when a floor is active, compute
  the set of visible areas (floor match) and the child nodes directly linked to them; only
  those render, and edges whose endpoints are hidden are skipped. Populates the picker after load.
- `templates/index.html`: added the floor filter `<select>` to the graph toolbar.

## Steps to verify

- `node --check` on both JS files; `pytest` guard suites pass (62).
- Live (world has floors 0 and -1): All floors → 51 nodes (areas on 0 and -1). Floor "0" →
  only 0-floor areas + children. Floor "-1" → only the 1 cellar area + its 4 children.
  Composes with item/trigger toggles.

## Why

TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Graph toolbar → menu → Show on canvas → Floors selector.

Current availability: The floor picker is implemented and was live-verified on
a world with floors `0` and `-1`; its current accessible values are derived
from area nodes' integer `properties.floor` values.

Live steps when available:
1. Open a multi-storey world, open the graph toolbar menu, and choose All
   storeys; note the rendered node count. Then choose floor `0` and floor `-1`.
   - expected: All shows 51 nodes in the recorded fixture; floor `0` shows only
     ground-floor areas and their children; floor `-1` shows the cellar area
     and its four children.
2. While floor `-1` is selected, toggle Item nodes and Trigger nodes separately.
   - expected: the floor filter composes with both visibility toggles and never
     shows children of areas on another floor.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
