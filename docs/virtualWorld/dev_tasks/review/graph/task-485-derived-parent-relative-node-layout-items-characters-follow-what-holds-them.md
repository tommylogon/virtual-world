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
- [x] Children are packed into a tight block beside their parent (items below, characters right, triggers left, nested contents tighter still) and hold a **parent-relative offset**. They are kept out of the *global* solver (`fixed: false, physics: false`) because central gravity is a field applied to every node every iteration: a child left in it is dragged off its parent however stiff its edge is, and holding it back needs a per-frame sweep of every child. The parent stays physics-driven, the child follows it, and a dragged child re-records its offset from where it was dropped.
- [x] Re-derived on load, on `stabilizationIterationsDone`, and on `dragEnd`, so moving a room carries its contents.
- [x] Hidden nodes are handled: positions come from the node bodies, not `getPositions()` (which drops filtered-out nodes), so a child of a hidden parent is still placed.

## Verification

Live against the real autosave (235 nodes) in the running app:

- resolution: items 97/97, characters 3/3, logic_triggers 97/97, ways 19/19 - **0 orphans**.
- at rest: the living room's 10 children sit 19-110px from the room, and the set is **identical after 2.5s** (no drift) and after moving the room (380, -160).
- follow: moving `area_living_room` by (350, -150) moved its item by exactly (350, -150); (400, +200) moved all 10 items by exactly (400, +200) (`allFollowed`).
- cost: an idle follow tick is **0.03ms** at 235 nodes. The pass is incremental - only parents that moved are visited, work is capped at `FOLLOW_BUDGET` per tick with the remainder queued, and the timer shuts itself down when physics is off and nothing is pending. Nothing is per-frame over the whole graph.
- negative result worth keeping: rebalancing the global physics does not fix clusters. `springConstant` 0.04 -> 0.14 *and* `centralGravity` 0.3 -> 0.06 (applied and verified in `network.physics.options`) changed the settled layout by 2px out of ~5900. Per-cluster force is not exposed by vis-network, so the only per-cluster control is the offset.
- spread: median distance of items/characters from the layout centroid went from 411px (broken resolution, effectively clustering) to 1486px, i.e. spread out with their rooms.

`node tools/unit/run.cjs` -> 151 passed (18 cases in `tools/unit/test_relative_layout.js`); `npm run lint`, `npm run typecheck`, `python tools/js_module_index.py --check` all clean.

## Layout modes (both implemented, switchable)

Two modes, toggled with the toolbar's `🌳 Levels` button and persisted as `graph_layout_mode`:

- **free** (default): force physics owns the areas; contents hold a parent-relative offset and are kept out of the global solver, so nothing drifts to the middle and nothing is stretched.
- **levels**: vis hierarchical layout (`direction: UD`, physics forced off). Every node is placed by relation level: rooms at the top, their contents below, nested contents below that, triggers below their host.

Because hierarchical levels come from edge direction, and the stored direction is not trustworthy, the layout edges are oriented from the resolved relations: attachment edges parent -> child (`levelEdge`), and room-to-door edges with the door as the child (`connectionLevelEdge`) - the door edges are stored both ways round, and that 2-cycle was what scrambled levels (153/197 -> 180/197 -> 100/100 visible children below their parent once oriented).

Also fixed while wiring it (all were silently re-enabling physics and would have dragged nodes off their levels):

- `GraphLayoutEngine.applyCardinalLayout` turns physics on; not called in levels mode.
- `_applyLockState` in `graph-background.js` "unfroze" physics for a new world.
- the persisted `graph.physics_enabled` preference was applied on load and on view-mode switches (`graph-manager.js`).
- switching back to free left `layout.hierarchical.enabled` true (vis merges options), so it is now set explicitly false.

Trade-off to decide: in levels mode the map is laid out by the graph, not by your background image, so the rooms no longer sit on their painted positions; it is wide (levels are shallow: all rooms are roots, their ways at level 1). Free mode keeps the image mapping and holds contents by offset.


- `bug-44`: the save's authored container contents (`item_Backpack -> item_Ink`, 21 edges) are stored opposite to the canonical `EDGE_IN` direction, so the engine's `get_edges_for_target(container, EDGE_IN)` readers cannot see them. The layout tolerates either direction; the engine does not.
- Area positions are still stored per world (`graph_background.positions`/`layoutLocked`), so mapping areas onto a background image still needs Save layout + Lock; that is now only about the rooms, not their contents.