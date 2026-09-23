---
type: task
status: review
area: graph
priority: medium
---

# task-485: Derived parent-relative node layout (items/characters follow what holds them)

**Filed:** 2026-09-23
**Related:** task-464; task-481

## Goal

Positions must be a function of the graph relations, not saved snapshots: an item renders on a ring around the area or container that holds it, a carried/worn item rides its character, a logic_trigger sits on its host, a way sits between its two rooms. Re-derive on load, on stabilization, and after an area drag, so picking an item up and carrying it 300 rooms away moves its node automatically and reloads keep the mapping. Children are held (fixed, physics off); area nodes stay the only world coordinates.

## Acceptance

- TODO

## Acceptance

- [x] `static/js/graph/relative-layout.js` derives every node's position from the relations instead of a saved snapshot: nothing is stored per node, so a reload reproduces the same layout.
- [x] Parent resolution is data-driven: priority `carrying` > `equipped` > `at` > `in` > `triggers`, so a carried bag rides its carrier even when a stale `in` edge still points at the room it was left in.
- [x] The mixed `in` direction in the data is handled: `in` has no reliable direction (`Backpack -> Ink` vs `fireplace -> living_room`), so for `in` the end nearer the area roots is the parent, and only a strictly shallower node can be a parent (two-node container cycles stay parentless instead of each holding the other).
- [x] Ways sit at the midpoint of the rooms they connect and are placed before children, so a trigger hosted by a way has somewhere to sit.
- [x] Children are placed on a deterministic ring (depth radii 130/88/62, wider when a parent is crowded) and **held** (`fixed`, `physics: false`), so global central gravity can never drag them to the middle again. Areas keep physics and remain the only world coordinates.
- [x] Re-derived on load, on `stabilizationIterationsDone`, and on `dragEnd`, so moving a room carries its contents.
- [x] Hidden nodes are handled: positions come from the node bodies, not `getPositions()` (which drops filtered-out nodes), so a child of a hidden parent is still placed.

## Verification

Live against the real autosave (235 nodes) in the running app:

- resolution: items 97/97, characters 3/3, logic_triggers 97/97, ways 19/19 � **0 orphans**.
- placement holds: children sit 0-1px from their derived position and drift **0px over 3s** with area physics still enabled.
- follow: moving `area_living_room` by (+400, +200) moved all 10 of its items by exactly (+400, +200) (`allFollowed`).
- spread: median distance of items/characters from the layout centroid went from 411px (broken resolution, effectively clustering) to 1486px, i.e. spread out with their rooms.

`node tools/unit/run.cjs` -> 146 passed (13 new cases in `tools/unit/test_relative_layout.js`); `npm run lint`, `npm run typecheck`, `python tools/js_module_index.py --check` all clean.

## Found while doing this

- `bug-44`: the save's authored container contents (`item_Backpack -> item_Ink`, 21 edges) are stored opposite to the canonical `EDGE_IN` direction, so the engine's `get_edges_for_target(container, EDGE_IN)` readers cannot see them. The layout tolerates either direction; the engine does not.
- Area positions are still stored per world (`graph_background.positions`/`layoutLocked`), so mapping areas onto a background image still needs Save layout + Lock; that is now only about the rooms, not their contents.