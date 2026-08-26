# Task 289 — Generic Template-Link & Sync System for All Node Types

## Status

Todo — design + API contract drafted 2026-08-17, awaiting implementation.
Partial: `refresh-to-world` works for **items and ways** only; areas/characters
return 400 and there is no `break-template-link` yet.
See **task-317** (bidirectional sync unification) for the World→Library half and
the empty-world-never-clobbers guard added 2026-08-20.

## Goal

Generalize the existing `refresh-from-library` item sync into a first-class template-link system that works for **areas, ways, items, and characters**. Authors can bind a placed node to a library template, sync changes from that template, and break the link to make the node standalone.

## Why

- `labs.json` currently has 36 rooms with many near-duplicates (e.g., `Task 3 - area 1 closed door` / `open door`). Drift between them is already happening.
- Only items have a partial `library_id` + `refresh-from-library` endpoint. Areas, ways, and characters have no equivalent.
- Without a template link, updating a canonical room/way/item/character requires manually editing every placed copy.

## Design Decisions

1. **`library_id` on every node** — a string field storing the source library file stem (e.g., `lab_table`, `blackout_goggles`). Absent or empty = standalone.
2. **`POST /api/nodes/<node_id>/sync-from-library`** — generic endpoint that:
   - reads the current library file by `library_id`
   - overwrites mutable fields on the node to match the library definition
   - returns a diff of what changed
3. **`POST /api/nodes/<node_id>/break-template-link`** — strips `library_id` and marks the node as standalone. Does not alter node data.
4. **Mutable field whitelist per node type** — not everything should sync. Example:
   - **items**: `name`, `description`, `tags`, `triggers`, `equip_slots`, `defense`, `damage`, `insulation`
   - **areas**: `name`, `description`, `environment`, `properties.tags`
   - **ways**: `name`, `description`, `properties`
   - **characters**: `name`, `description`, `stats`, `skills`, `traits`, `behaviors`
   - Never sync: `id`, `type`, spatial edges (`in`, `on`, `beside`, `connection`), `current_state`, `position`, player-specific data
5. **Frontend UX**:
   - Inspector panel shows "Linked to library: `<name>`" with a **Sync** button and a **Break Link** button.
   - Library browser shows "X placed instances" next to each entry.
   - Sync produces a toast with "Updated N fields" or "Already up to date."

## Implementation Steps

1. **Backend: generic sync endpoint**
   - Add `POST /api/nodes/<node_id>/sync-from-library` in `routes/nodes.py` (or equivalent).
   - Add `POST /api/nodes/<node_id>/break-template-link`.
   - Extract mutable-field logic into `engine/sync.py` with a registry per node type.
   - Reuse the existing item `refresh-from-library` logic as the template.

2. **Backend: `library_id` on all node types**
   - Ensure `area`, `way`, `character`, and `item` nodes all accept and persist `library_id`.
   - World serialization/deserialization must preserve it.

3. **Frontend: inspector integration**
   - Show template-link status and action buttons in the area/way/item/character inspector panels.
   - Wire buttons to the new endpoints.

4. **Frontend: library browser**
   - Show instance count for each library entry.
   - Allow bulk "Sync all instances" from the library view.

5. **Testing**
   - Unit tests for sync diff, break-link, and mutable-field whitelisting.
   - Smoke test: place an item from library, edit its description, sync, verify description reverts; break link, edit, sync again, verify no change.

## Out of Scope

- Template inheritance / variants (design #3 from earlier discussion). That is a follow-up task once basic sync is stable.
- Override tracking (design #2). Can be added later if authors need partial sync.
