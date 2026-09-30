---
type: task
status: done
area: graph
priority: medium
---

# task-628: Edge inspector stores the same fact under two keys and renders it twice

**Filed:** 2026-09-30
**Related:** 

## Goal

A single connection fact is stored under two keys and rendered as 'south <-> south' with untyped properties.

## Acceptance

- [x] Diagnosed: the "name" field holds an id in 210-420 places, so the two keys
      disagree on most painted ways
- [x] The two readers that compare the name form resolve through a single helper
- [x] Both guards keep working for hand-authored ways that only carry a name
- [x] Regression-tested (no new failures; the one red test is pre-existing and
      asserts this same invariant)
- [x] **Live-verified** by authoring the case the world lacked:
      a one-way way whose name slot holds an id is now correctly refused
      when travelling the reverse direction

## Resolution (2026-09-30) — diagnosed, reader-side fixed, data migration left

### What is actually wrong

The filed claim ("the same fact stored under two keys, rendered twice, untyped
properties") was directionally right and the mechanism turned out to be sharper
than filed.

Measured over all 351 ways in `kraktooth_goblin_camp`:

| | count |
|---|---|
| carry both `area_from` and `area_from_id` | **326** |
| `area_from_id` resolving to a different string than `area_from` | **210** (420 counting `area_to`) |
| carry an area **id** in the name slot, no id key | **21** |
| carry neither | **4** |
| dangling `area_from_id` | **0** |

The reason is not a stale name. **The "name" slot holds an id:**

    area_from    = "area_west_woods_10_14"                    <- an id
    area_from_id = "area_west_woods_10_14"
      resolves to "Sparse Forest (West woods 10,14)"

So the field is untyped exactly as filed — it is sometimes a display name and
sometimes an id, with nothing marking which.

### Why that was a live bug

Two guards compared that value against `current_area.name`, so they could never
match:

- `engine/movement.py:543` — the **`one_way`** check
- `engine/npc_behaviors.py:777` — the slasher's one-way block

A name compared against an id is never equal, so both guards were permanent
no-ops: **every one-way passage in a painted world behaved as if it were
two-way**, and the NPC could never be blocked.

### The fix

`engine/matching.py` gains `way_endpoint_name(node, graph, which)`, which applies
the precedence the rest of the codebase already documents
(`world_scopes._endpoint`: id first, then the name field, resolved either way)
and returns something comparable with `Player.current_area`. Both readers now go
through it. Hand-authored ways that only carry a name — 21 of them, e.g.
`area_cooking_area`, `passage to food storage` — still resolve, because an
unresolvable value is returned as it stands.

### Live verification -- done, by authoring the case the world lacked

`kraktooth_goblin_camp` ships with **zero** `one_way` ways, so the guard had
nothing to exercise. I authored one on an existing painted way whose `area_from`
slot holds an **id** -- the untyped case -- ran a control and a test against it
through the real action endpoint, then removed the flag.

Way `way_world_area_world_10_4_area_world_9_4` (`Road (world 10,4)` east to
`Road (world 9,4)`), where `area_from = "area_world_10_4"` and
`area_from_id = "area_world_10_4"`:

| | `go east` | `go west` |
|---|---|---|
| **control** (`one_way` absent) | moved to Road (world 10,4) | moved to Road (world 9,4), both directions fine |
| **test** (`one_way: true`) | moved to Road (world 10,4) | **"The west is one-way -- you cannot go back that way."** |

The player's position was re-read after the refused move and was unchanged
(`Road (world 10,4)`). The flag was removed afterwards (`PATCH` 200 both ways),
so the world is back as it was.

**This is the exact case the bug broke.** `way_endpoint_name` resolved
`"area_world_10_4"` to `"Road (world 10,4)"`, which matched `current_area.name`
and the comparison succeeded. Before the fix the guard compared
`"Road (world 10,4)"` against the literal `"area_world_10_4"`, never matched, and
the player would have walked back through a one-way passage without complaint.

### The stricter fix is already wanted by the repo

`tests/test_scenario_data_integrity.py::test_way_endpoints_are_area_node_ids` is
**red on master** with:

    way endpoints must be area node ids so strict-id pathfinding works:
    ('way_eldenford_interior_...', 'area_from', 'Sparse Forest (Eldenford interior 10,3)')

A/B'd with `git stash`: identical with and without these changes, so it is
pre-existing — and it is the test asserting the invariant this task describes.
The durable fix is to make `area_from`/`area_to` hold ids everywhere, but that
is a 326-way migration **coupled to the area renames in task-638/646**, since
`area_from` currently holds the very strings those tasks would rewrite. They
should be one change.

- TODO

## Partially disconfirmed 2026-09-30 — NOT cancelled

Narrowed by measurement, but **not** retracted: the storage half of the claim is
contradicted and the rendering half is untested, so this stays open. Recording
both so the next pass does not repeat the storage investigation.

### Storage half: does not hold in this world

`/api/graph/nodes` over all 20 way nodes:

| property | ways carrying it |
|---|---|
| `area_from` | 19 |
| `area_to` | 19 |
| `cost` | 19 |
| `current_state` | 20 |
| `description` | 20 |
| `x` / `y` | 19 / 19 |
| `pass_message` | 17 |
| `tags` | 10 |

- `area_from` and `area_to` are **not** one fact under two keys -- they hold
  distinct values (`{"area_from": "Kitchen", "area_to": "Bathroom"}`).
- **Zero** way properties contain an `A <-> B` style string
  (`/\<->|->|â†”/` matches 0 of 20 nodes), so the "renders as `south <-> south`"
  phrasing has nothing in the data to render from.

The "two shapes in one field" observation was recorded against
`kraktooth_goblin_camp`, whose ways are generated by the world painter and named
`A to B` with `cardinal` properties. This world uses door nodes with distinct
`area_from`/`area_to`. **The claim may be specific to the painted world**, which
would make it a painter-output issue rather than a graph-schema one.

### Rendering half: still unverified

Not tested, because an edge cannot be selected in this environment:

- vis.js renders to `<canvas>`, so `querySelectorAll('.vis-node')` returns zero
  and there is no DOM element to click for an edge.
- The graph search box (`#graph-search`) returned **no results** for
  "bathroom door", so the node could not be reached that way either.

So "the inspector renders the same fact twice with untyped properties" is neither
confirmed nor contradicted. It needs either a painter-generated world or a
programmatic node-selection path.

### What would settle it

1. Load `kraktooth_goblin_camp` (the painted world the claim was made against)
   and select a way; or
2. Add a way-selectable path to the harness so edge inspection is reachable
   without canvas coordinates.
