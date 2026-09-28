---
type: task
status: review
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

## Progress — 2026-09-28

`engine/character_spatial.py` (extended in place), 35 tests in
`tests/test_spatial_invariants.py`, and 5 save/load round-trip tests added to
`tests/test_serialization.py`.

### The invariant, on the write path and off it

`set_character_position` already cleared before setting, so the invariant held on
the path everything used. What was missing was the other path: an effect
handler, an NL edit, or a load file that wrote an `at` edge directly. So:

- `enforce_single_at(graph, who, keep_target=None)` reduces a character to at
  most one `at`. Deterministic: lexicographically smallest target survives,
  **unless** `keep_target` names one — a caller that just moved someone must not
  have the move silently undone by an older edge.
- `check_spatial_invariants(graph)` is the validator the task asks for, because
  these are properties a save file or an NL edit can break with no code running.
  It reports `multiple_at_edges`, `dangling_at_edge` and `at_non_anchor_target`.
- `clear_at(graph, who)` is **demotion**, not deduplication, and is deliberately a
  separate function. Reducing to at most one must keep the last edge: a
  character standing at nothing is still standing somewhere. Only losing
  attendance takes the position away. My first version folded both into
  `enforce_single_at` and the demotion test caught it.

### Positional fidelity is an attendance tier

`apply_positional_fidelity(graph, node_for_character, attended, anchor_for=...)`
gives exactly the attended characters one `at` edge and nobody else one, and
returns the counts that are the whole point of the task:
`{"attended", "at_edges", "cleared"}`. Measured: **40 characters → 40 `in` edges
and 8 `at` edges**, not 40 × 40 pairs. An attended character with no anchor is
simply "in the area" — attending someone does not invent a place for them.

### Proximity is walked, never stored

`proximity_hops` returns 1 / 2 / `None` by walking `at` then
`beside`/`on`/`under`/`behind`; `proximity_phrase` renders at / by / across the
room. Nothing caches a distance, and the test proves why: adding a `beside` edge
changes the answer immediately and removing it un-applies immediately. A cached
distance would leave a stale one behind a re-authored edge.

`None` means *unreachable by this model*, not *absent* — the prose says "across
the room". The walk carries a `seen` set, so a `beside` cycle terminates.

### The anchor vocabulary

- **Pooled resource** — `spawn_from_pool` is bounded three ways, and all three
  have to hold or "gravel" becomes a way to manufacture items: at most
  `max_spawn` per call, at most `remaining` ever, and never more than asked.
  Spawned items are real nodes with an `in` edge into the anchor's area, stamped
  `spawned_from`. A pool outside any area spawns nothing rather than orphans.
- **Landmark cluster** — two nodes joined by `beside`; the cluster's *placed*
  member is the budget line and its partner is free, because "boulder by the old
  oak" is one description, not two.
- `select_area_anchors` is the 3–8 budget: pools first (one pooled node buys more
  per node than one rock), then landmarks, then the rest, ties by id. Clamped
  into the documented range, and it is a **ceiling, not a quota** — a sparse area
  gets what it has.

### Save/load

`engine/serialization.py` needed **no change**: the `at` edge, a pool's
`remaining` count, and the anchor selection all round-trip through the existing
generic edge path. The new tests assert that, including that a reloaded pool
does not refill and a reloaded budget does not change — an area that read
differently depending on how it was loaded would be worse than no budget.

### Not done

- Authoring anchors for existing areas is explicitly a non-goal, and the Pines
  world has none yet; the fixture tests build their own.
- `check_spatial_invariants` is a callable, tested against a broken graph, but it
  is not yet wired to a validation *surface* (there is no graph-validator route
  in the app to hang it on). That is a follow-up, not a claim.

