---
type: task
status: todo
area: refactor
priority: low
---

# task-625: Duplicated concepts across the engine that should be consolidated

**Filed:** 2026-09-30
**Related:** 

## Goal

Cross-cutting: several concepts are implemented in more than one place with different behaviour, which is how the same fact ends up stored twice.

## Acceptance

- TODO

## Inventory — 2026-10-02 (audit; not yet consolidated)

Concrete, measured duplications found while working the small-bugs cluster.
Each names the two stores and the authoritative side.

1. **A node's layout position has two homes.** `graph_background.positions`
   (serialized; **0 entries** in the live world — measured) and the node's
   `properties.x/y` (what the layout engine, `moveNode`, and
   `GraphRelativeLayout.persistFrozenDrop` actually write). The live-audit
   (`docs/live-audit/README.md` §4) reached the same conclusion. Authoritative:
   `properties.x/y`; the background `positions` map should either be fed from it
   or retired.

2. **The graph layout axis is expressed three ways.** `graphManager._cardinalLayout`
   (Map, runtime; now also persisted as `config.graphCardinalLayout` — bug-510),
   `config.graphLayoutMode` (`'free'`/`'levels'`), and the derived
   `activeLayout()` (`'graph'|'map'|'levels'`). bug-48 made `activeLayout()` the
   single UI source of truth, but the two underlying flags remain and can
   disagree in storage. A single persisted layout value would remove the class.

3. **"Where I have been" has two stores** — `player.visited_areas` (area names)
   vs `kind == "area"` observation memories. **Owned by task-430**; do not
   separately refactor.

4. **"What I have seen" has two stores** — `player.discovered_items` vs
   `kind == "item"` observation memories. **Also task-430.**

5. **Payload version constants** were two ideas in one (`APP_VERSION` used as a
   stand-in for a format marker, plus a hard-coded `2`). **Resolved by task-453**
   (`SCHEMA_VERSION` in `version.py`, `engine/schema.py`). Note
   `engine/structures.py::STRUCTURE_SCHEMA_VERSION` is a *separate* graft-format
   version and is correctly independent — that is not a duplication.

Suggested order: #5 is done; do #1 and #2 as their own small changes (both are
front-end/graph-boundary and testable), then defer #3/#4 to task-430.
