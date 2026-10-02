---
type: task
status: cancelled
area: graph
priority: high
---

# task-614: Graph nodes are not rendered on the map at 636-node scale

**Filed:** 2026-09-30
**Related:** 

## Goal

Nodes do not appear on the map; hundreds of 40px-wide overlapping boxes make labels illegible at 205 areas / 636 nodes.

## Acceptance

- TODO

## Partially disconfirmed 2026-09-30 — left open, content-dependent

**At the scale of the loaded world the map is legible.** Screenshot
`audit/82-graph-default.png`: 19 areas on a painted exterior plus a painted
interior (Ground Floor / First Floor / Cellar), with readable labels --
"Frozen Lake Clearing", "Abandoned Hunter's Cabin", "Kitchen", "Upstairs Hallway",
"Guest Bedroom", "Dining Room", "Cellar (Below Kitchen)". The scope bar reports
"19 areas Â· 20 ways Â· 239 loaded". Nothing overlaps illegibly.

So the claim as written -- "hundreds of 40px-wide overlapping boxes make labels
illegible at 205 areas / 636 nodes" -- does **not** reproduce at 19 areas.

**But this is a scale claim, and this world is not that scale.** The finding was
recorded against `kraktooth_goblin_camp` (205 areas, 636 nodes), which is not the
scenario loaded, so the number it asserts is untestable here. Cancelling on the
strength of a 19-area world would be the mirror image of the error this audit has
been retracting all session.

**One real observation that does survive:** the map draws non-area nodes as small
unlabelled rectangles over the painted art (visible around the house), and with
98 `item` + 99 `logic_trigger` nodes among 239 total, most of what is on the map
is machinery rather than place. Whether that is noise or clutter depends entirely
on the 205-area case.

**To settle it:** load `kraktooth_goblin_camp` and screenshot the map at default
zoom. One screenshot decides this.

## Retracted 2026-10-02 (wt/graph-render) — does not reproduce

Loaded `kraktooth_goblin_camp` (658 nodes / 207 areas / 361 ways) on port 4464,
selected Map layout, and measured the **rendered DataSet**, not the DOM (vis
draws to a canvas). Nodes are rendered at every scope, with labels:

| scope | rendered nodes | areas | labels shown | blank area labels |
|---|---|---|---|---|
| `world` | 219 | 62 | 219 | 0 |
| `goblin_camp` | 71 | 21 | 71 | 0 |
| `eldenford_interior` | 190 | 71 | 190 | 0 |

Screenshots `scope-world.png` / `scope-goblin_camp.png` show readable labels
("Frozen Lake Clearing", "Camp Entrance", "Shivering Slums", "Deep Forest", …)
on their painted art. So the filed claim — "Nodes do not appear on the map" — is
false: they render, and at scope scale the map is legible.

**Surviving nuance.** The whole-world view (658 nodes across four maps totalling
~40,000px) fits everything into one viewport, so at that zoom the dots and labels
are sub-pixel — that is a fit-to-everything overview, not a render failure, and
the app already provides the two controls that fix it: the scope picker
(`setScopeFilter`, measured above) and the label LOD + 🔤 Names toggle. The
non-area markers (items/characters) are deliberately small unlabelled glyphs in
compact map mode to keep the art readable.

No code change was warranted; the finding is retracted with the measurement
above. The task-618 fix (same sweep) additionally removed the spurious long
edges that made the whole-world overview look broken.