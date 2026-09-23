---
type: task
status: todo
area: world
priority: high
---

# task-419: Relational spatial model — one `at` per character, positional fidelity, anchor budget

**Filed:** 2026-09-20  
**Depends on:** task-416 (area index).  
**Relates:** task-411/418 (attendance), task-9 / task-398 (population and
generation), `engine/character_spatial.py`, `graph.py:465-470`.

## Position is a relation, not a coordinate

There is no metric space inside an area. A character's position is the set of
spatial edges it holds: `in`, `on`, `under`, `behind`, `beside`, `at`. Space
between areas is real and ordered, but it is measured in **time** (way travel
cost × `time_per_tick_minutes`), not in hops — hops are only a cached proxy.

## Invariant: at most one `at` per character

A character holds **exactly one** `at` edge at a time, or none. Not one per
target — one total. This means the whole world holds at most
`population` `at` edges, not O(n²), and a crowded area cannot blow up the edge
set.

`engine/character_spatial.py:114` (`clear_character_position_edges`) already
exists for this reason. This task makes the invariant explicit and enforced.

## Positional fidelity = attendance tier

This is what keeps `at` cheap. Positional detail is allocated by the same
attendance decision as everything else:

| Tier | Edges written | Count |
|------|---------------|-------|
| Background / co-present only | `in <area>` | population |
| Attended | `in <area>` + `at <anchor>` | ≤ cap |

So 40 characters in an area produce 40 `in` edges and at most 8 `at` edges. The
other 32 are simply "in the area." This removes the per-pair `at` churn and
removes any need for an anchor per character.

## Proximity = relational hop distance

`at` alone is binary, but composed with `beside`/`on` it yields an ordered,
discrete proximity:

```
you --at--> boulder --beside--> old oak
```

- **1 hop** — you are at it (the boulder).
- **2 hops** — a neighbour of your anchor (the oak).
- **unreachable** — elsewhere in the area; the prose says "across the room."

No coordinates. The `beside` chain *is* the coordinate system.

## Anchor vocabulary and budget

An anchor is a node that is an interaction target. Two shapes, both already
expressible:

- **Pooled resource** — "gravel on the ground": one node, described as a
  quantity, and on use/take it spawns a handful of real items bounded by the
  pool. Same model as the berry thicket: one bush, described as many, spawns
  berries.
- **Landmark cluster** — "boulder by the old oak": two nodes joined by
  `beside`, either of which can be the `at` target.

**Budget:** 3–8 anchors per wilderness area, chosen deterministically from the
area's anchor candidates (seeded, per task-398's generator contract). A forest
does not need 500 rocks; it needs a few pooled/landmark anchors that the prose
layer expands into "rocks", "undergrowth", "fallen oak."

## Acceptance

- No character ever holds two `at` edges (invariant test, and a validator).
- Background characters hold no `at` edge; attended characters hold exactly one.
- Proximity phrases are *derived* from the relation path, never stored.
- A wilderness fixture area has ≤ 8 anchors and still reads as populated.
- A pooled-resource anchor spawns a bounded handful on interaction and depletes.
- Save/load preserves the `at` edge and the anchor budget.

## Non-goals

- Room grids / intra-area coordinates (task-99) — explicitly not this model.
- Changing movement, `approach`, or sound rules.
- Authoring every anchor for every existing area.

## Verification

- Unit: invariant — attempt a second `at` edge, assert the first is cleared.
- Unit: proximity derivation returns 1 / 2 / unreachable for the three cases.
- Unit: pooled anchor spawns ≤ N items and decrements on depletion.
- Fixture: attended vs background positional edge counts on the camp.
