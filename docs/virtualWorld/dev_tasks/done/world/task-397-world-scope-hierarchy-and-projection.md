---
type: task
status: review
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

## Progress — 2026-09-23 (backend slice)

Landed (uncommitted):

- `VirtualWorld.world_scopes` manifest attribute (`virtual_world_engine.py`).
- Serialization round-trip in `engine/serialization.py` (`_serialize_world`
  writes `world_scopes`; `load_from_dict` restores a dict or `{}`), so
  `to_scenario_dict` carries it and legacy scenarios without a manifest are
  unchanged.
- `engine/world_scopes.py` — pure helpers: `normalise_manifest`,
  `root_scope_ids`, `direct_child_ids`, `area_ids_in_scope` (recursive),
  `scope_summary` (area/character/item counts, state, child ids),
  `boundary_ways`, and `project(manifest, graph, players, scope_id, depth,
  include_items)`.
- `routes/world_scopes.py` + `routes/world_scopes_ops.py`:
  - `GET /api/world/scopes` — top-level scope cards.
  - `GET /api/world/scopes/<scope_id>` — child scope cards, or leaf area
    summaries + boundary ways.
  - `GET /api/world/scopes/<scope_id>/graph?depth=&include_items=` — projection;
    items/edges included only when requested.
- `tests/test_world_scopes.py` (12) — recursion, cardinality, boundary ways,
  leaf vs building projections, manifest round-trip through `/api/load`, and
  backward compatibility with no manifest. Full suite: 3451 passed, 6 known
  pre-existing failures.

Still open in this task:

- Scope breadcrumb/tree UI above the graph (work plan step 4) and the
  unmade-scope `Generate` affordance (step 5, depends on task-398).
- `task-398` recipe/generation flow over `world_scopes`.

## Dependency reality (2026-09-24)

- **Not blocked by task-439.** The scope layer keys on node id / `world_scope_id`,
  so the "id-keyed saves" work in task-439 was not required to land this. The
  stale `439 → 397` block edge has been removed from task-439.
- **This task satisfies** the `397` dependency of task-398, task-400, task-401,
  task-402, task-411, task-495, task-496 and task-500.
- Remaining work here is the book/search UI (step 4), the `Generate` affordance
  (step 5), and the projection's scope-keyed fidelity handoff to task-500.

## Progress — 2026-09-24 (scope-filtered graph view)

The step-3 projection now has a consumer, which is also the fix for the
"densely painted world freezes the graph" failure:

- **`engine/world_scopes.project_subgraph(manifest, graph, players, scope_id,
  include_items=True)`** — a vis-loadable `{nodes, edges}` slice in the same
  shape as `WorldGraph.to_dict`. Membership is recursive: every area in the
  scope and its descendants, a `way` with **both** endpoints inside, a
  `character`/`player` standing in an included area, and (when requested) an
  `item` attached to one. Only edges with both endpoints included are emitted,
  so nothing dangles. Extracted `way_endpoints` so `boundary_ways` and this
  share one endpoint resolver.
- **`GET /api/world/scopes/<id>/subgraph?include_items=`** returns that slice
  plus the scope summary; **`GET /api/world/scopes?flat=1`** returns every scope
  depth-first with a `depth` field (`flat_scopes`, cycle-safe) for a picker.
- **Graph-view scope picker** (`#graph-scope-filter` in the toolbar): choosing a
  scope makes `GraphNetwork.loadGraphData` fetch the subgraph instead of
  `/api/graph/*`, so the browser never receives nodes outside the scope. The
  selection is part of the reload signature; a stale scope (e.g. after loading
  another world) falls back to the whole world and the picker is rebuilt on
  load. The empty selection is the unchanged whole-world path.
- Tests: `tests/test_world_scopes.py` +4 (subgraph membership, recursion without
  dangling edges, `include_items`, flat depth order) plus route assertions for
  `/subgraph` and `?flat=1`.

Still open: the breadcrumb/tree *panel* (this ships a flat picker), the
unmade-scope `Generate` affordance (task-398), and the projection's scope-keyed
fidelity handoff to task-500.

### Progress — 2026-09-25 (level-scoped view + drill-down)

The scope view was **recursive**, so selecting a parent flattened its whole
subtree — selecting the world root loaded every painted zone's cells at once.
That is the wrong default: a parent should read as a map (task-496 follow-up).

- `world_scopes.own_area_ids(graph, scope_id)` — the areas whose
  `world_scope_id` is *exactly* this scope, ignoring descendants.
- `project_subgraph(..., descendants=False)` is now **level-scoped by default**:
  a parent shows its own areas, so a placed child zone is a single feature cell
  (carrying `child_scope_id`) rather than its whole interior. `descendants=True`
  restores the recursive subtree (what "Whole world" wants).
- `GET /api/world/scopes/<id>/subgraph?descendants=1` exposes the opt-in;
  `ApiClient.getScopeSubgraph(scopeId, includeItems, descendants)`.
- **Drill-down:** double-clicking a feature cell in the graph loads its child
  scope (`GraphEventHandlers.onDoubleClick` → `graphManager.setScopeFilter`) —
  the graph equivalent of WorldPainter's `Open ▸`.

Tests: `own_area_ids`, level-scoped default (a parent is not flattened; an
organisational scope with no own cells is empty), descendant opt-in, and route
assertions for `?descendants=1`.

Note: an organisational scope with no painted cells of its own now shows an
empty canvas — drill to a child via the picker or a feature cell. A
children-as-cards fallback is a possible follow-up.

### Progress — 2026-09-28 (step 4: the scope hierarchy as a tree)

The step-4 ask was a scope breadcrumb/tree UI, and the world already had the
breadcrumb (task-531's contextual scope bar) and a *flat* picker with the names
indented by `depth`. What was missing was the tree: a world with a county over
two towns read as three unrelated entries, nothing said how big a scope was, and
nothing said whether anything had been built in it.

- **`static/js/graph/scope-tree.js`** (new) — `GraphScopeTree`. Nests the one
  payload the server already sends (`GET /api/world/scopes?flat=1`, which carries
  `parent_id` and `depth` per scope) into a collapsible tree. **No new endpoint
  and no per-scope request.**
  - Pure and unit-tested (16 in `tools/unit/test_graph_scope_tree.js`):
    `buildTree`, `visibleRows`, `toggleCollapsed`, `rowLabel`. The DOM half is a
    thin render over those.
  - A card states what the manifest says: `Apartment 3B — not built` for an
    `unmade` scope, `Millbrook Falls — 40 areas · 90 items · 3 here now` for a
    materialized one. An unmade scope showing "0 areas" would read as an empty
    room, which is a different fact.
  - **No Generate button.** Generating a scope is task-398's recipe flow and
    lives in the WorldPainter; a card offering one would be a promise the graph
    cannot keep. This is step 5's honest resting state, not a gap.
- **One writer.** The tree repaints from `GraphToolbar.syncScope()`, the same
  sync that repaints the breadcrumb, so the loaded scope is marked in both or in
  neither. The panel goes through `GraphToolbar.loadScope()`, which is what keeps
  the flat picker's value in step — two ways to change the loaded scope is how
  they drift apart.
- The flat picker stays. It is the one control that works without scrolling, and
  the tree is a second reading of the same list, not a replacement.

Four bugs the new unit tests caught, all in code I had just written:

1. `buildTree` reset `node.children` inside the placement loop, so a child listed
   *before* its parent was silently dropped from the tree. The tree depended on
   the order the list happened to arrive in — which for the real endpoint means
   it depended on the manifest.
2. `reaches()` read `parent_id` off the node object, which never carried it, so
   cycle detection always answered "no". A mutual `a ↔ b` parent link built a
   real cycle and the panel rendered nothing.
3. A duplicate scope id produced two cards.
4. `plural(n, 'here now')` produced "3 here nows".

`visibleRows` now also carries its own cycle guard: a card is rendered at most
once, because hanging the panel is the one failure the author cannot work around.

### Verification

- 16 unit tests for the pure rules, including the malformed manifests a
  hand-edited file produces: child before parent, missing parent, self-parent,
  a two-scope cycle, a duplicate id, an empty and a `null` list.
- Browser, against a live dev server with a four-deep scope hierarchy created
  through `POST /api/world/scopes`: the tree renders at four indent levels with
  twisties, `▸`/`▾` toggling hides the subtree while keeping the card, clicking a
  card loads that scope and marks it `aria-current`, and clicking "Whole world"
  clears it. `_scopeFilter`, the flat picker's value and the tree's selection
  were checked in step after each click and stayed in agreement.
- Camera/filter behaviour is untouched: the panel only calls the existing
  `loadScope` path, so `setScopeFilter`'s reload signature and the map's
  per-scope background refresh (bug-51) behave exactly as before.

### Still open

- Step 5, the unmade-scope `Generate` affordance. It depends on task-398's recipe
  flow; a card that offered it before a recipe exists would be the exact
  "fabricate nodes merely by being rendered" this task forbids.
- The projection's scope-keyed fidelity handoff to task-500.

