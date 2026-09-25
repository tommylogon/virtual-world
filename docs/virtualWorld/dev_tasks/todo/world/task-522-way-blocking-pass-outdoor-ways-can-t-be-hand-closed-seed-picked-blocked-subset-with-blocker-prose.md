---
type: task
status: todo
area: world
priority: medium
---

# task-522: Way blocking pass: outdoor ways can't be hand-closed; seed-picked blocked subset with blocker prose

**Filed:** 2026-09-25
**Related:** 

## Goal

Secondary generation pass (item population / world state). Rule: a plain close action must NOT close an outdoor/outside way -- you cannot close a road into a forest or a cliff by hand. Blocking is done by an item or trigger setting the way state (fallen tree, barricade, rockslide, wolves den). At generation, deterministically mark a subset of outside ways blocked, each with a per-biome 'what blocks it' description.

## Constraints (decided with the user, 2026-09-25)

- **Determinism is non-negotiable.** The compiler has no `random`/clock; the
  blocked set must be a stable hash of `seed:way_id` so a regenerate reproduces
  the same world.
- **Never strand a pocket.** Do not block a *cut-edge* (bridge) of the scope's
  adjacency graph, or verify connectivity after choosing; blocking must not undo
  the island auto-linking (`link_islands`).
- **State shape.** The engine currently knows `open`/`closed` only. Decide
  between a real `blocked` state or `current_state: "closed"` plus a
  `blocked_by` / `blocked_description` property.
- **Which ways.** Outdoor/outside ways only (compiler-generated passages that
  leave the zone / have no door); interior doorways and gateways keep the normal
  toggle behaviour.
- **Blocker vocabulary.** Per-biome content (fallen tree, rockslide, flood,
  thicket, wolves) chosen by the same stable hash.

## Acceptance

- TODO
