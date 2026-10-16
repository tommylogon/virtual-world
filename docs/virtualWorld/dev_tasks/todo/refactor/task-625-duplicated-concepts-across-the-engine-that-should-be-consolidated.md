---
type: task
status: todo
area: refactor
priority: medium
---

# task-625: Duplicated concepts across the engine that should be consolidated

**Filed:** 2026-09-30
**Related:** 

## What

Cross-cutting: several concepts are implemented in more than one place with different behaviour, which is how the same fact ends up stored twice. Measured 2026-10-02: (1) a node's layout position has two homes — `graph_background.positions` (serialized, **0 entries** in the live world) and the node's `properties.x/y` (what the layout engine, `moveNode` and `GraphRelativeLayout.persistFrozenDrop` actually write); authoritative is `properties.x/y`, so the background `positions` map should be fed from it or retired. (2) the graph layout axis is expressed three ways — `graphManager._cardinalLayout` (now persisted as `config.graphCardinalLayout`), `config.graphLayoutMode` (`'free'`/`'levels'`), and the derived `activeLayout()` (`'graph'`/`'map'`/`'levels'`); bug-48 made `activeLayout()` the single UI source of truth, but the two underlying flags remain and can disagree in storage. (3) "Where I have been" has two stores — `player.visited_areas` vs `kind == "area"` observation memories — owned by task-430. (4) "What I have seen" has two stores — `player.discovered_items` vs `kind == "item"` observation memories — also task-430. (5) payload version constants were two ideas in one (`APP_VERSION` used as a stand-in for a format marker plus a hard-coded `2`); resolved by task-453 (`SCHEMA_VERSION` in `version.py`, `engine/schema.py`). Note `engine/structures.py::STRUCTURE_SCHEMA_VERSION` is a separate graft-format version and is correctly independent — that is not a duplication. Suggested order: #5 is done; do #1 and #2 as their own small changes (both are front-end/graph-boundary and testable), then defer #3/#4 to task-430.

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

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — this is an investigation and consolidation task across engine concepts; the card does not specify one user-facing feature or screen to change.

Current availability: the task reports duplicated concepts with differing behavior and requires each duplicate to be traced before selecting an authoritative representation. No consolidation is claimed as implemented.

Why no browser UI: a browser interaction cannot identify all duplicate stores or prove which runtime caller reads each one; that requires tracing sources, writers, and consumers first.

Alternative verification steps:
1. For each concept selected by the task, record the authored source, runtime writer, every reader/caller, and the serialized home before changing it.
   - expected: the inventory distinguishes true mirrors/projections from competing sources of truth and identifies the exact behavior mismatch.
2. After consolidating one concept, inspect the affected module callers and save/load representation.
   - expected: one authoritative value remains, derived projections are rebuilt from it, and existing scenario/save data still resolves through the documented migration path.
3. Run the focused regression tests for that concept and compare a small before/after scenario result.
   - expected: the duplicate behavior is gone while unrelated mechanics retain their measured output.

This section is not a claim that planned consolidation is complete today.
