---
type: task
status: inprogress
area: graph
priority: medium
---

# task-618: Map mode draws four scattered images with edges over nothing

**Filed:** 2026-09-30
**Related:** 

## Goal

Map mode composites several unrelated background images at different scales; edges are drawn across empty space with no shared coordinate frame.

## Acceptance

- TODO

## Resolved 2026-10-02 (wt/graph-render)

**Root cause (measured).** The four images are the four painted scopes, authored
at their own `map_offset` (west_woods −28,−38; world −3,−7; goblin +−4,+13;
eldenford +42,−29 cells at a 330px pitch) — that separation is the world, not a
bug. The bug was the edges: grid-generated ways carry **no `cell`**, only a stale
canvas `properties.x/y` from a graph-mode save (e.g.
`way_west_woods_area_west_woods_10_14_area_west_woods_9_14` has `x:4058,y:2122`
while its areas sit at cell `(9,14)`/`(10,14)`). `_gridUpdates` used that `x/y`
verbatim, so the way stood thousands of px from its rooms. Painted ways were also
left to the solver (`physics:true`), which dragged them off their own cell.
Measured on `kraktooth_goblin_camp` in Map mode: **1164** connection edges longer
than 1000 graph units, max **18068**.

**Fix** (`static/js/graph/layout-engine.js`, `_gridUpdates`):
1. A way with no `cell` whose connected rooms are painted is placed at the mean
   of its rooms' anchors (pinned), instead of trusting the stale canvas `x/y`.
   A way with no painted rooms (hand-placed) still keeps its canvas `x/y`.
2. A way **with** a painted `cell` is pinned to that cell like an area, not
   simulated — the solver frame and the grid frame disagree, so physics moved it
   off its own cell (`_gridUpdates` computed 16509,−8484; the solver left it at
   15334,−7308).

**Evidence** (Playwright, port 4464, `kraktooth_goblin_camp`):

| metric | before | after |
|---|---|---|
| connection edges > 1000 units | 1164 | 21 (rendered DataSet) |
| longest edge | 18068 | 7763 (a genuine `Entrance to Eldenford interior` gateway) |
| painted way position | 15334,−7308 | 16509,−8484 (its cell midpoint) |

With edges hidden, the four scope images render cleanly; the remaining long
edges are the 7 real cross-scope gateways. Regression tests:
`tools/unit/test_graph_layout_engine.js` — the coordinate-less-way midpoint test
(new) and the painted-way-pinned test (updated from task-530, which left painted
ways to the solver; task-618 requires them pinned to their cell). 486 JS unit
tests pass.

## Reopened 2026-10-08 — back to inprogress (the "7 real gateways" line does not hold on the whole world)

The 2026-10-02 measurement was four scopes. The whole world is now **627 areas /
1380 ways**, and the long edges are many more than 7 gateways. Measured on
`data/scenarios/kraktooth_goblin_camp.json` at pitch 240:

- **469** edges draw >2000px — 418 `connection`, 34 `in`, 11 `at`, 3 `triggers`,
  2 `carrying`, 1 `beside`.
- Longest **11,763px**: `way_gateway_world_eldenford_interior` (a genuine
  cross-scope gateway); then 10,088px `beside` `player_Belne → player_Rikka`.
- **755 nodes carry no `world_scope_id`** (468 items, 235 `logic_trigger`, 27
  characters, 25 ways), so they get no scope offset and their edges cross empty
  space; 94 cross-scope connection edges touch a `None`-scope node
  (`goblin_camp ↔ None`, 47 each way), e.g. `area_side_tunnels → way_side_to_mine`
  at 6,801px.

So "the remaining long edges are the real cross-scope gateways" is not what the
whole-world view shows. The fix has to account for the unscoped nodes and the
stale canvas coordinates as well as the gateways.

**Landed 2026-10-08 (partial):** items/characters held in a painted area no longer
use their stale canvas coords, and painted nodes are placed from `cell × pitch`,
which removes the worst of the fan; the background art reads the same pitch
(`graph-background`). Still open: the 25 scope-less ways, the 235 `logic_trigger`
nodes with no `world_scope_id`, and the genuine cross-scope gateway edges.
