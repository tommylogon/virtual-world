# Character entity model refactor — plan

**Status:** proposed
**Phase-1 task:** task-463
**Related:** task-316, task-446, task-439, task-450, task-457, task-437, task-408, task-453

## Why

A character's data is spread across three storage shapes and, in authored data,
two node identities.

Measured (kraktooth_goblin_camp.json, 2026-09-22):

- **46 character graph nodes for 23 players.** Every character appears twice:
  `character_<slug>` (authored: `description` + `in`/`carrying` edges) and
  `player_<Name>` (runtime: `x`/`y` + `at`/`equipped`/`grappled` edges).
- Edge split: `in`(70) + `carrying`(4) hang off `character_*`; `at`(6) +
  `equipped`(4) + `grappled`(1) hang off `player_*`; no `in` edge targets a
  `player_*` node.
- The full definition lives in the `players` JSON map and the in-memory
  `Player`; the nodes hold almost nothing.
- **Location has four representations**: `Player.current_area` (a display
  name), a graph `in` edge, `legacy.current_area`, and the `area_presence`
  ledger.
- **Possession has two**: `carrying`/`equipped` edges and `Player.equipped`.
- **Two `_set_player_area` writers**: `engine/player_manager.py:226` (derives
  `area_<name.lower()>`) and `engine/matching.py:714` (resolves by node name).
- **A shim bridges the two identities**: `engine/area_description.py:378`.
- Blast radius: **403 `active_player` refs** (~50 non-test Python files), **410
  `current_area` refs**; the single-active-player assumption is baked into the
  engine.

Consequences: location and possession can disagree; the NL editor / inspection
surfaces see only half a character; authored edges can dangle when one identity
is removed; "who acts" is hard-coded to one character.

## Target model (north star)

1. **One identity.** Exactly one `character` graph node per character. Its id is
   derived from the stable opaque uid (task-316 / task-446); a unique display
   name keeps the legacy derived anchor for save compatibility, a duplicate gets
   a uid suffix. Names are addressing only, resolved by `engine/matching.py`.
2. **The node is the record.** Node `properties` hold the full definition
   (stats, vitals, skills, traits, tags, interest_tags, personality and
   descriptions, emotion, conditions, schedule, simple_npc/autonomy/behaviour,
   memories, relationships-by-uid). The `Player` object is a runtime view
   hydrated from the node. One module owns the mapping. Inventory and equipped
   stay **edges** (they are relationships, not properties).
3. **One location.** The graph `in` edge is the fact. `Player` holds an area
   **id** (task-439); the area name is resolved at the display boundary. One
   writer.
4. **One possession model.** `carrying`/`equipped` edges are the fact;
   `Player.equipped` is derived; one writer; the dead `Player.inventory` list
   is removed.
5. **Controller, not active player.** Each character has a controller
   (human / agent / simple / soak). `active_player` becomes a UI/observer
   concept (the primary controlled or watched character). Resolution order is
   engine-owned and id-keyed; `simultaneous` is a mode on the same dial
   (task-437).

## Non-goals

- World scopes / region decomposition (task-397, task-438).
- Library template link/sync mechanics (task-289, task-317).
- The goblin data cleanup itself (task-408) — this plan makes the duplication
  unable to recur.
- Save-format versioning mechanics (task-453) beyond depending on them.

## Phases

### Phase 0 — decisions and prerequisites

Defaults proposed (confirm before Phase 1 lands):

- **Canonical node id:** `player_<slug>` for a unique name (no churn on existing
  worlds); `player_<slug>__<uid6>` for a duplicate. Revisit pure-uid anchors once
  task-446 Slice B settles.
- **`players` JSON section:** keep it as a thin index (uid, name, area id) or
  drop it after a format version (task-453). Default: read both, write index-only.
- **`current_area`:** becomes a derived property backed by the `in` edge and an
  area id, not a stored display name.

Prerequisites: task-446 Slice A (done) for identity; task-439 required for
Phase 3 only.

### Phase 1 — one character identity · task-463

- Load-time normalizer: for each player, collapse the authored
  `character_<slug>` and the runtime `player_<Name>` into one canonical node;
  merge properties (authored `description` wins for prose, runtime node props win
  otherwise); rewrite every edge to the canonical id; keep the retired id in
  `WorldGraph._id_index` as an alias so authored edges/triggers do not dangle.
- Offline migration tool `tools/migrate_character_identity.py` for existing
  scenarios and saves.
- Fix the generators so it cannot recur: `tools/assemble_scenario.py:180`,
  `tools/build_scenario.py`, `tools/generate_scenario.py` emit the canonical node
  only.
- Remove the `engine/area_description.py:378` shim.
- Tests: kraktooth loads to 23 character nodes (not 46); no orphans; location,
  possession and targeting still resolve; a save round-trips.

### Phase 2 — the node is the record · task-457

- New `engine/character_store.py`: `to_node_properties(player)`,
  `apply_node_properties(player, props)`, `hydrate_player_from_node(node, ...)`;
  used by both runtime and `engine/serialization.py`.
- Load: hydrate the `Player` from node properties, fall back to the `players`
  section for legacy files, then backfill the nodes.
- Save: write node properties; the `players` section becomes index-only.
- Route every writer (actions, `routes/player_ops.py`, NL editor, library
  `_refresh_character`, effect spawns) through the store.
- Tests: a trait/stat/vital change persists through the node and is visible to
  the engine; an NL-editor edit takes effect; a legacy file still loads.

### Phase 3 — one location · task-439

- `current_area` holds an area **id**; `area_name` resolves at the boundary.
- Collapse the two `_set_player_area` implementations into one writer; remove
  `legacy.current_area` and the top-level `current_area`; decide `area_presence`'s
  fate (keep as a separate ledger only if it earns it).
- Tests: move, save/load, area listing, exits, "who is here".

### Phase 4 — one possession model · task-450

- Enforce one edge per item→owner; `Player.equipped` becomes derived; single
  equip/transfer writer; remove the dead `Player.inventory`.
- Tests: equip/unequip/drop/take round-trip, carry weight, bug-25 invariant.

### Phase 5 — controller and simultaneous · task-437

- Introduce a controller registry; `active_player` becomes a compatibility shim
  to the primary controlled character.
- Engine-owned seeded resolution order stored per timeframe; snapshot + commit
  for `simultaneous`.
- Migrate the ~403 call sites in slices; the frontend reads the server's order.
- Tests: reverse-roster invariance in `simultaneous`; the human is never
  auto-decided; the order the UI shows is the order the engine resolves.

### Phase 6 — save format version and migration · task-453

- Schema version on scenario/save, load-time migrators; the Phase 1/2 normalizers
  hook in here.

## Migration and compatibility rules

- **Read old, write new.** Never break a name-keyed or dual-node file.
- A unique name keeps its exact derived anchor id — no churn.
- Collapse is atomic, with one undo snapshot; retired ids remain as aliases in
  `_id_index`.
- Each phase lands behind a compatibility accessor; the suite stays green; no
  phase leaves the tree half-migrated.

## Risks

| Risk | Mitigation |
| --- | --- |
| Save/scenario corruption on node collapse | migration tool, atomic apply, undo, fixtures |
| Wide migrations drift (410/403 sites) | compat accessors, mechanical slices, tests |
| Dangling authored edges/triggers | alias retired ids in `_id_index`; rewrite edges atomically |
| Two writers re-introduced (editor vs runtime) | one `character_store` seam; grep guard |
| Per-node bloat in `/api/state` | character nodes are few; measure payload size |

## Acceptance

- Kraktooth loads as 23 character nodes; no `character_*` orphans; the shim is
  gone.
- One identity, one location representation, one possession representation.
- `simultaneous`: the outcome does not depend on processing order; the order is
  engine-owned and id-keyed.
- Old saves load unchanged; new saves round-trip; the suite is green apart from
  the known baseline.

## Task map

| Phase | Task |
| --- | --- |
| 0 decisions | this document |
| 1 one identity | **task-463** |
| 2 node is the record | task-457 |
| 3 one location | task-439 |
| 4 one possession | task-450 |
| 5 controller / simultaneous | task-437 |
| 6 format version | task-453 |
| supporting | task-316, task-446 (identity), task-408 (data cleanup), task-448 (ambiguous target UX) |
