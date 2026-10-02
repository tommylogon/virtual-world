---
type: task
status: review
area: graph
priority: medium
---

# task-622: Way node id is a generated filename and the UI invites renaming it

**Filed:** 2026-09-30
**Related:** [task-446]

## Goal

Way ids look like 'way_world_area_human_road_area_world_17_6' and the UI allows editing what should be an opaque identity.

## Acceptance

- TODO

## Resolved 2026-10-02 (wt/graph-render)

WorldPainter's grid compiler stamps `properties.generated` on every area/way cell
and derives the id from the cell (`way_eldenford_interior_area_eldenford_interior_10_3_area_eldenford_interior_10_4`) — a filename, not a name, regenerated on the
next compile. The inspector nevertheless rendered it in an editable "Node ID"
box with a 🔄 "sync ID from name" button, inviting a rename that cannot stick.

**Fix:** `InspectorHelpers.isGeneratedNode(nodeId)` (true when
`worldState.getNode(nodeId).properties.generated` is set). The four inspectors
(way, area, item, agent) render that id **read-only** for generated nodes and
keep the editable field + sync button for hand-authored nodes.

**Evidence** (Playwright, `kraktooth_goblin_camp`, port 4464) — `Node ID` row of
`#inspector-panel`, counting visible text inputs:

| node | `isGeneratedNode` | ID inputs | result |
|---|---|---|---|
| `way_eldenford_interior_…_10_3_…_10_4` (generated way) | true | 0 | read-only text |
| `area_eldenford_interior_10_3` (generated area) | true | 0 | read-only text |
| `area_abandoned_farm` (hand-authored) | false | 1 | editable |

Screenshots `inspector-genway.png` / `inspector-plain.png`. JS unit tests: 486
passed / 0 failed; eslint clean on the five touched files.
