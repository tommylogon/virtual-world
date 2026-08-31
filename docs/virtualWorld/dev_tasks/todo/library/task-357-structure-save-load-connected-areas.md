# Task 357 — Structure save/load: recursive connected-area bundles

**Status:** Todo — scoping done 2026-08-23, not started
**Related:** `todo/ui/task-237-save-area-to-library.md` (single-area save; implement as the
one-area special case of this task's traversal, don't build twice)

## Goal

Select an area and save it together with its connected ways and recursively connected
areas as one named bundle (e.g. all 12 `taco_bell_*` library areas wired together →
save as "Taco Bell"), then import the whole structure into another world (e.g. Pines)
with checkboxes for including items and characters.

## What exists today

| Piece | Location | Gap |
|-------|----------|-----|
| Graph serialize (nodes+edges) | `engine/serialization.py:197` → `graph.py:165` | Full-world only |
| Graph deserialize | `graph.py:246` `load_from_dict()` | **Clears** the graph — no merge path |
| Single-area library import | `routes/library_routes.py:546` | Imports area + items, **never creates ways/exits** |
| Character library import | `routes/library_routes.py` (`import/character`) | Single character only |
| Area library entries with exits | `data/library/areas/*.json` (`exits[].target_room_hint`) | Hints only, no hard links |
| Way↔area edge model | `engine/movement.py:79-89` | area →(connection, direction)→ way →(connection)→ area, both directions |
| Context menu / inspector UI | `static/js/graph/context-menu.js:30`, `static/js/inspector/area-view.js` | No structure actions |

## Plan

### Backend
1. **New engine module `engine/structures.py`** (< 600 lines rule):
   - `collect_structure(graph, root_area_id, include_items, include_characters)` — walk
     outward from the selected area over `EDGE_CONNECTION` (area→way→area, both hop levels)
     with a visited set so cycles can't loop forever. This auto-discovers the whole connected
     group from one click — no hand-picking areas. Collects area/way/item/character nodes plus
     ALL internal edges between them (`in/on/under/beside/at/connection/triggers/equipped/carrying`).
     Do NOT collect `unlocks`/`requires` edges — obsolete (see corrections.md
     `graph.unlock_edges_obsolete`); triggers carry that logic now.
   - Items recurse `contents`; characters bring equipped/carrying edges.
   - Boundary ways (other side outside bundle): keep the way + the near-side edge, mark far
     edge `properties.external: true` with `target_room_hint` (stub exit, wire up later).
   - Strip runtime artifacts: `discovered_items`-style flags, spatial position, `last_relation`;
     keep authored `current_state` (locked doors stay locked).
   - Returns `{root_area, nodes:{id:node_dict}, edges:[edge_dict]}` — raw graph shape so
     re-import needs no translation.
2. **Storage: `data/library/structures/<slug>.json`** — same per-file registry pattern as
   areas/items; register `structures` registry type in the registry helpers + library browser.
3. **Routes — new `routes/structures.py`** (library_routes.py is already 958 lines):
   - `GET /api/structures` — list saved bundles (name, root area, counts).
   - `POST /api/structures/preview` — body: `{area_id, include_items, include_characters}` →
     counts + area list BEFORE saving/importing (drives the dialog).
   - `POST /api/structures/save` — `{area_id, name, include_items, include_characters}` → writes bundle file.
   - `POST /api/structures/import/<structure_id>` — merge into CURRENT world:
     - New `graph.merge_nodes_edges(nodes, edges)` (add-only, never clear) on WorldGraph.
     - ID collision policy v1: if a node id/name already exists in target → suffix `_2`
       (ids lowercase everywhere, case-insensitive existence check) and remap every reference
       (edge endpoints + any id-bearing properties). Report the mapping in the response.
     - Dangling external stubs import as visible-but-dead exits until hand-wired.
     - After import: run trigger validation (`engine/trigger_validator.py`) + return summary.
4. **Tests** (pytest, WorldGraph fixture pattern from `tests/test_item_actions.py`):
   - Traversal correctness (cycle-safe, boundary stub marking, items/characters toggles).
   - Round-trip: build 3-area fixture → save → clear → import → structural equality.
   - Collision: pre-existing same-name area → suffix + remapped edges still resolve.

### Frontend
5. **Graph context menu** (`context-menu.js` area section): "🏗️ Save Structure…" →
   modal (reuse create-modal patterns): name field, live preview counts, checkboxes
   "Include items" (default ON) / "Include characters" (default OFF).
6. **Import UI**: structures list in the library browser (or saveload-view) — Import button
   per bundle with the same two checkboxes + post-import report toast.

## Considerations / decisions

- **Bundle format = raw graph subset**, not scenario-dict: lossless, and import is a straight
  node/edge replay; scenario format would need exits→ways reconstruction we'd have to debug twice.
- **Characters travel fully as agents.** Persona, description, stats, vitals, memories,
  `autonomy`, `simple_npc` etc. all live ON the character node (serialization.py:102-152) and
  come along with the bundle. The agent engine drives any autonomous character by name using
  the browser's global LLM config — so an imported miki keeps rambling in Pines with zero
  re-binding. Only global provider/API-key settings are browser-side IndexedDB, and those are
  per-browser anyway, not per character.
- **Import connects nothing automatically (by design).** The structure is internally wired;
  boundary exits land as dead stubs. Grafting = author adds one way manually
  (e.g. Pines street → Taco Bell lobby) wherever wanted.
- **No world lore** travels (lore is global, not per-area).
- **Autosave/scenario source untouched** — import mutates the running world only; standard
  reset semantics still apply.
- Follow-up idea (not this task): nuke obsolete `unlocks`/`requires` edges from engine + data
  entirely — triggers superseded them (corrections.md).

## Verification plan

- pytest suite green (`python -m pytest tests/ -q -k "not mcp and not emote"`).
- Manual E2E: select Taco Bell Dining Room in graph → Save Structure (items on, chars off)
  → verify `data/library/structures/taco_bell.json` contains 12 areas wired via ways →
  reset to Pines scenario → import → walk dining room ↔ restrooms ↔ kitchen in-game,
  puddle-relieve check near toilet-tagged fixture, trigger validator clean.
