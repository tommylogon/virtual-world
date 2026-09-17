---
type: task
status: todo
area: world
priority: high
---

# task-397: World scopes, hierarchy manifest, and server graph projection

**Filed:** 2026-09-08  
**Prototype:** Millbrook Falls / The Pines

## Goal

Add a hierarchy *over* the existing area/way/item graph so the editor and
runtime can address a world, settlement, building, or room group without
inventing a second spatial model. A scope is a durable grouping and load/view
boundary; its leaf areas remain normal `area` nodes and all existing movement,
trigger, item, and character rules continue to use them.

The first deliverable is a scoped API response. It must not send every node and
edge to the browser merely to hide them client-side.

## Why this is needed

`GraphNetwork.loadGraphData()` currently fetches all graph nodes and all graph
edges, then `GraphProjector` hides most of them locally. The inhabited/items
toggles are useful presentation controls but cannot make a million-node world
cheap. `WorldGraph` is also one in-memory node dict plus one edge list, so
scope metadata must be introduced before chunk persistence can be added safely.

## Data model (v1)

Persist a top-level `world_scopes` manifest, separate from graph nodes:

```json
{
  "millbrook_falls": {
    "id": "millbrook_falls",
    "kind": "settlement",
    "name": "Millbrook Falls",
    "parent_id": null,
    "children": ["downtown", "the_pines"],
    "state": "materialized",
    "generation": null
  },
  "the_pines": {
    "id": "the_pines",
    "kind": "building",
    "name": "The Pines Apartment Complex",
    "parent_id": "downtown",
    "children": ["pines_floor_1", "pines_floor_2", "pines_floor_3"],
    "state": "materialized"
  }
}
```

Each materialized area gains `properties.world_scope_id`. Scope children may
be other scopes, or the manifest may list `area_ids` at the leaf. Scope records
may exist with `state: "unmade"`; no graph nodes are required until task-398
generates them.

Do not add fake `area` nodes for continents, buildings, or floors. A character
always remains in a real area, as today.

## API and editor

1. Add serialization/load support for `world_scopes` on `VirtualWorld`.
2. Add a read-only `GET /api/world/scopes/<scope_id>` endpoint returning only:
   - direct child scope cards: id, name, kind, state, area/character/item
     counts, and whether any character is present;
   - direct leaf area summaries when the selected scope is a leaf;
   - boundary-way summaries, never every contained item.
3. Add `GET /api/world/scopes/<scope_id>/graph` with explicit `depth` and
   `include_items` limits. It is the future replacement for full-graph editor
   loading; v1 may read the current in-memory graph but must return only the
   requested projection.
4. Add a scope breadcrumb/tree UI above or beside the graph. Clicking a card
   changes the requested scope. Existing item reveal and inhabited filters keep
   working inside the returned projection.
5. An unmade scope card shows `Generate` only when it has a generation recipe
   (task-398); it must not fabricate nodes merely by being rendered.

## Pines acceptance

- The root view shows `Millbrook Falls`, `Downtown District`, and `The Pines`.
- Opening The Pines shows floors/apartments or the existing leaf areas, without
  dumping unrelated Pines items into the graph canvas.
- `Apartment 3B` can appear as an unmade scope even before it has areas.
- Existing `pines.json` loads unchanged when it has no manifest.
- Save/load preserves the manifest and every existing test scenario remains
  backward-compatible.

## Non-goals

- No physical graph unloading yet (task-401).
- No procedural generation here (task-398).
- No change to `simple_npc`, `autonomy`, action commands, or turn ordering.

## Existing work and risks

- task-303 and task-319 are client-side visibility filters, not server-side
  scale solutions. Preserve their UX but do not extend their all-node dataset
  approach.
- task-357 is a useful raw graph-bundle/import design, but its current import
  model is not a scope manifest or streaming model. Do not couple this task to
  structure import.

## Verification

- Pytest serialization fixture: absent, materialized, and unmade manifests.
- Route tests prove an endpoint response excludes nodes outside the requested
  scope.
- Browser test: scope navigation preserves current camera/filter behavior.

