# Task 357 — Structure templates: capture + materialize connected areas (with population)

**Status:** In Review — backend + routes + UI + tests implemented 2026-09-22
(see "Implemented" at the bottom). Scope **reframed 2026-09-22** from "save/load
a connected-area bundle" to the **structure-template → scope-materialization
layer**. The manual save/import UI is consumer #1, not the contract.

**Related:**
- `review/ui/task-237-save-area-to-library.md` — single-area save, implemented
  (the one-area special case of capture).
- `todo/world/task-397-world-scope-hierarchy-and-projection.md` — a materialized
  structure *is* a scope; this task is the source those scopes are made from.
- `todo/world/task-399-background-character-simulation-and-reactivation.md`,
  `todo/world/task-411-attention-budget-and-fidelity-tiers.md`,
  `todo/characters/task-412-promotion-demotion-and-trace-consolidation.md`,
  `todo/world/task-418-awareness-channels-audibility-over-radius.md` — fidelity
  tiers operate at this granularity; a stamped structure's residents arrive in
  `background` and promote/demote as the attended set changes.
- `todo/gameplay/task-427-creature-spawners-and-population-caps.md` — *dynamic*
  creatures are spawners inside a structure, not authored population.
- `todo/world/task-398-deterministic-structure-generation.md`,
  `todo/world/task-400-pines-world-scale-vertical-slice.md`,
  `todo/world/task-401-chunk-persistence-and-gateway-ways.md` — determinism,
  scale target, and boundary ways as future gateway ways.

## Why (the real use case)

Two layers:

1. **World population (primary).** A world is built by *stamping structures*, not
   by hand-placing every room, way, item and NPC. Author a town / camp / farm
   once, then materialize it wherever a world needs one — internally wired and
   already populated. "Populate the Pines" becomes "materialize these N
   structures with these population policies."
2. **Portable built places (secondary).** Move/duplicate a specific designed
   place between worlds or scenarios without re-wiring it (today the library
   stores areas and ways separately and importing an area creates **no exits**, so
   nothing built is reusable as a *place*).

Fidelity follows from the first layer: because `simulation_mode` (task-399) is an
execution mode on the same `Player`, a materialized structure's population can
come up in `background` and be promoted to `active` only when the attended set
(task-411/418) reaches it. The structure is the natural unit for that selection.

## Design decisions (settled)

- **Template semantics are the core; the fixed-identity snapshot is a special
  case.** A bundle stores resident *archetypes* (species/roles, schedules, vital
  policies) plus slots/params; instance identities are minted at materialization,
  deterministically from a seed. Named-resident packs (miki, jake) are archetypes
  with a pinned identity. This avoids the "five identical mikis" failure when
  stamping.
- **Node collisions remap ids only — never node display names.** The existing
  `WorldGraph.add_node` (`graph.py:121-139`) does the opposite (random suffix on
  *id and name* for item/character/logic_trigger, silent overwrite for `way`,
  `ValueError` for `area`), so materialization must **not** use it; it owns the
  remap. Every reference to a remapped id must be rewritten: edge endpoints plus
  id-bearing properties (`area_from`/`area_to`, `library_id`, `node_id`, trigger
  `target`).
- **Residents resolve by identity, and are never dropped.** The engine keys
  people by *name* (`player_manager.players`, `Player.node_id_for`,
  relationships), so a duplicate resident name **mints a unique instance**
  (`zombie` → `zombie 2`, anchor `player_zombie_2`). This covers the realistic
  population case (rabbit/deer/zombie). True duplicate *display* names (500
  literal "Jon"s) need the id-keyed identity refactor and are out of scope here.
- **Boundary ways are gateways, near-side only — grafting them is manual by
  design.** Model a boundary exit as a way node with only the near-side
  `area → way` connection edge — never an edge to a missing area id. Engines
  already tolerate a way with no far-side edge (`matching._collect_exits`,
  `area_description`, `examine_actions` leave `target_area` empty), so it renders
  as a visible-but-dead exit the author ties to the host world. Only the wiring
  *inside* the captured group is automatic.
- **Characters are `Player` payloads, not graph nodes.** Character state lives in
  `player_manager.players` (`_serialize_player`, `serialization.py:104-166`); the
  graph node is a bare anchor added at load (`serialization.py:459-462`). A graph
  -only bundle imports an inert anchor with no vitals/memories and nothing for
  the engine to drive, so the template must carry the player payload for its
  residents and materialization must deserialize them.
- **Deterministic ids.** Same template + seed + target scope → same ids. Use
  derived ids, not random suffixes (aligns with task-412 stable id and task-408
  dedup; guarantees "no duplicate character nodes / no orphan nodes").
- **Skip obsolete `unlocks`/`requires` edges** (triggers supersede them; see
  corrections.md `graph.unlock_edges_obsolete`). Constants still exist in
  `graph.py:475-476` but nothing consumes them.
- **No world lore travels** (lore is global), and runtime perception flags are
  stripped while authored `current_state` (a locked door) is kept.

## What exists today (verified 2026-09-22)

| Piece | Location | Gap |
|-------|----------|-----|
| Graph serialize (nodes+edges) | `graph.py:338` `to_dict()`; `engine/serialization.py:344` | Full-world only |
| Graph deserialize | `graph.py:425` `load_from_dict()` | **Clears** the graph — no merge path |
| Single-area library import | `routes/library_ops.py:567` `handle_library_import_area` | Imports area + items, **never creates ways/exits** |
| Single-way library import | `routes/library_ops.py` / route `/api/library/import/way/<id>` | Exists — usable for hand-grafting stubs |
| Character library import | route `/api/library/import/character/<id>` | Single character; player-state path exists |
| Registry pattern | `routes/helpers.py:155-184` (`data/library/<type>/*.json`) | Add `structures` to `REGISTRY_TYPES` (`library_ops.py:16`) + frontend type list (`library-browser.js:96`) |
| Way↔area edge model | `engine/movement.py:96` `connect_areas` (area→way→area, direction on area→way edge) | — |
| Boundary-stub tolerance | `engine/matching.py:105-112`, `engine/area_description.py:509-518` | Safe: missing far side is tolerated |
| Context menu / inspector | `graph/context-menu.js:46`, `graph/manager.js:221`, `inspector/area-view.js` | "Save to Library" (task-237) only; no structure actions |

Note: `data/library/rooms/` (3 files) is **not** a registry type and no library
code reads it — a legacy store that should not be confused with structures;
decide to ignore or delete.

## Data shape (sketch)

```jsonc
{
  "template_id": "taco_bell",
  "name": "Taco Bell",
  "root_area": "area_tb_dining",       // capture root; materialization root may differ
  "nodes": { "area_tb_dining": { ... }, "way_tb_north": { ... }, "item_...": { ... } },
  "edges": [ { "source": "...", "target": "...", "type": "connection", "properties": {} } ],
  "residents": [                        // Player payloads, not graph nodes
    { "template_key": "miki", "identity": "pinned|minted", "player": { ... },
      "schedule": [...], "vital_policy": "eat_when_hungry", "simulation_mode": "background" }
  ],
  "population": { "policy": "cap", "cap": 12 },  // per-materialization knob
  "boundary_exits": [ { "area": "area_tb_dining", "way": "way_tb_to_street", "direction": "out" } ]
}
```

## Plan (phased)

1. **Capture / serialize** — `engine/structures.py` `collect_structure(graph,
   root_area_id, include_items, include_characters)` returns
   `{root_area, nodes, edges, residents, boundary_exits}`. Walk outward over
   `EDGE_CONNECTION` (area→way→area) with a visited-area set; collect the full
   internal edge set; recurse item contents; snapshot resident `Player` payloads;
   mark boundary ways near-side-only; strip runtime artifacts. Keep it a raw
   graph subset so materialization is a straight replay (no scenario
   reconstruction).
2. **Materialize into a world/scope** — `materialize_structure(world, template,
   {target_root_area, host_anchor_way, seed, population_policy})`: clone
   nodes/edges with **deterministic id remap**, keep display names, rewrite all
   references, create resident anchors + deserialize `Player`s via the existing
   player path, land residents in `background` mode, register the scope entry
   (task-397) when that lands. Add-only: never touches existing nodes.
3. **Routes** — `routes/structures_ops.py` (`GET /api/structures`,
   `POST /api/structures/preview`, `POST /api/structures/save`,
   `POST /api/structures/materialize/<id>`) + thin `routes/structures.py`
   registration; add `structures` to `REGISTRY_TYPES`.
4. **UI** *(consumer #1)* — area context menu "Save Structure…" with a live
   preview (areas/ways/items/residents counts) and include checkboxes; library
   browser list + per-bundle Materialize with the same options and a post-import
   report.
5. **Tests** — cycle-safe capture; boundary stub renders/no crash; round-trip
   (build → capture → clear → materialize → structural equality); collision remap
   (ids only, display names preserved, references resolve); a resident
   round-trip proving the `Player` is live and in `background` after
   materialization; deterministic ids across two runs with the same seed.

## Considerations / risks

- Characters travel as full `Player` payloads. Resident instance identity is
  minted on a name clash (`miki` → `miki 2`); an explicit per-resident
  `pinned|minted` policy (pin a scene's exact cast vs mint a fresh generic
  resident every stamp) is still a follow-up.
- `add_edge` de-dupes case-insensitively on (source, target, type); remapped
  edges must be added after remap or they can drop.
- Do **not** rely on `add_node` for any of this (see decisions).
- Scopes (task-397) are the natural home for "which template made this"; until
  that lands, materialization can take a plain target root area and be upgraded
  to scope registration later.
- Autosave/scenario source untouched — materialization mutates the running world
  only.

## Verification

- pytest: new `tests/test_structures.py` green; no regressions (existing suite;
  known pre-existing failures: MCP `.fn` wrapper, social/tick scaling).
- Manual E2E: capture Taco Bell → reset to Pines → materialize → walk dining ↔
  restrooms ↔ kitchen in-game; residents present, in background, promotable;
  boundary exit shows as a dead stub; trigger validator clean.

## Implemented (2026-09-22)

**Engine — `engine/structures.py`**
- `collect_structure(world, root_area_id, include_items, include_characters)`:
  cycle-safe outward walk over `EDGE_CONNECTION`; item fixpoint through
  in/on/under/behind/beside/at; residents snapshotted as full `Player` payloads
  (anchors never emitted as raw nodes); boundary ways recorded and kept
  near-side-only; runtime props stripped; obsolete `unlocks`/`requires` skipped.
- `materialize_structure(world, template, seed, ...)`: add-only replay;
  deterministic id remap (SHA-1 of `template:seed:id`, node display names
  preserved); recursive reference rewrite (edge endpoints + `area_from`/`area_to`
  + equipped stacks + memory `entity_ids`); residents deserialized via the
  existing serializer path and landed in `simulation_mode="background"`; a name
  clash **mints a unique instance** (`zombie` → `zombie 2`, anchors
  `player_zombie_2`) rather than dropping the resident; returns a report
  (`renamed`, `minted_residents`, validator issues).
- `summarize_structure()` for listing.

**Routes**
- `routes/structures_ops.py`: `GET /api/structures`,
  `POST /api/structures/preview`, `POST /api/structures/save`,
  `POST /api/structures/<id>/materialize`, `DELETE /api/structures/<id>`.
- `routes/structures.py` thin registrar, wired in `app.py`.
- `structures` added to `REGISTRY_TYPES` (`routes/library_ops.py`), so it gets
  the generic library CRUD/listing for free.

**UI**
- `static/js/structures.js` — Save dialog (name, include items/residents, live
  preview of counts + boundary exits) and a Structures browser with
  Materialize/Delete; loaded from `templates/index.html`.
- Area right-click menu gains "📦 Save as Structure…"; toolbar gains
  "📦 Structures".

**Tests — `tests/test_structures.py` (14)**
- collect: connected areas/ways, cycle safety, item capture + runtime-prop
  stripping, characters excluded by default, residents-as-players, boundary
  near-side-only.
- materialize: round-trip restores structure + resident in background;
  collision remaps ids but keeps node names and resolves references; duplicate
  resident mints `miki 2`; deterministic ids across identical worlds; boundary
  stub is a dead exit; summary fields.
- routes: preview→save→list→materialize, and 404 for a missing structure.

**Not done / follow-ups**
- Scope registration (task-397) — materialization takes a plain target world
  today; when scopes land, record `{scope → template, seed}` and expose
  `target_scope`.
- **Boundary grafting is manual by design** (not a gap): an imported structure's
  external exits are dead stubs the author ties to the host world. Everything
  *inside* the group is wired automatically on materialize.
- **Duplicate display names** are now partly supported for players by task-446
  Slice A (step 1): the player registry accepts a repeated name via a stable
  id-derived key. Full id-keyed identity (relationships, `current_area`, item
  resolution) is task-446; until it lands, `mint` remains the default and
  task-357 keeps minting `miki 2`.

