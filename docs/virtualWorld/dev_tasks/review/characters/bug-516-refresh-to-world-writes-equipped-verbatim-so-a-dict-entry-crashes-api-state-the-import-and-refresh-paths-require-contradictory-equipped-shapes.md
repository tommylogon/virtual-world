---
type: bug
status: review
area: characters
priority: high
---

# bug-516: refresh-to-world writes equipped verbatim, so a dict entry crashes /api/state; the import and refresh paths require contradictory equipped shapes

**Filed:** 2026-10-01
**Related:** task-519, task-654, task-659

## Relationship to task-519 - read this first

**This overlaps task-519 substantially and was filed without checking it.**
task-519 ("Character starting loadouts from the item library", high, todo)
already documents the same `equipped` / inventory mismatch from the import side:
`equipped` keys look like `item_<name>` while import creates
`item_<player>_<name>`, and `equipped` is assigned before inventory
materializes.

Kept separate rather than merged, because the failure here is different in kind
and has its own reproduction: task-519 is about *lossy materialization*, this is
about *a shape that crashes serialization on the refresh path*. The fix
overlaps heavily and should be done as one change. Do not implement one without
reading the other.

Also the same class as **task-659** (in review): *"insulation and sound_barrier
unreachable on the library spawn and refresh paths"* -- a field that is declared
in the library and cannot survive the path that is supposed to deliver it.
That pattern now has three instances (ways, characters, equipped) and is worth
treating as one systemic problem rather than three tickets.

## What

Make the library character equipped field have ONE defined shape that both handle_library_import_character and _refresh_character honour, and stop refresh-to-world from writing a shape the runtime cannot read.

## Acceptance

- [ ] The library character `equipped` field has ONE documented shape, and both
      `handle_library_import_character` (`routes/library_ops.py:452`) and
      `_refresh_character` (`routes/library_ops.py:1029`) accept it.
- [ ] `_refresh_character` no longer writes a raw template value into
      `player.equipped`; it goes through the same resolution import uses, or the
      field is dropped from `editable_map` and refresh stops touching equipment.
- [ ] `/api/state` cannot 500 on a malformed or foreign-shaped `equipped` entry.
      `_region_exposure_map` -> `is_exposed` -> `graph.get_node(outer_id)` should
      tolerate a non-string entry the way it already tolerates the
      `__multi_slot_` markers, rather than raising `TypeError`.
- [ ] `player.equipped[slot]` is node-id strings everywhere it is read --
      `engine/equipment.py:205`, `:265`, `engine/body_parts.py:260`.
- [ ] `data/library/characters/Lyrie.json`, `miki doki.json` and
      `standalone_test.json` are converted or the shape change is proven
      non-breaking for them.
- [ ] Regression test: a template whose `equipped` holds dicts is refreshed, then
      `/api/state` is requested and returns 200.

## Why

When importing a character from the library, handle_library_import_character instantiates item nodes and sets player.equipped[slot] = item_id (a string node ID). However, _refresh_character copies the raw library template equipped field verbatim into the runtime Player.equipped dict. If the library template authored equipped as a nested dictionary or template object (e.g. {'item_id': '...', 'name': '...'}), _refresh_character writes that dict directly into player.equipped. Later, /api/state calls _region_exposure_map -> is_exposed(graph, player) -> graph.get_node(outer_id), which assumes outer_id is a hashable string node ID and crashes with TypeError: unhashable type: 'dict'.

## How

1. Standardize library template equipped schema: define whether slots point to library item IDs or item definitions, and document it canonically in data/library/characters/.
2. In routes/library_ops.py:1029 (_refresh_character), route equipment updates through the same item resolution logic as handle_library_import_character, or exclude equipped from the naive editable_map overwrite so runtime equipment is not clobbered with raw template structures.
3. In engine/equipment.py and engine/body_parts.py, guard get_node(outer_id): verify isinstance(outer_id, str) and ignore non-string entries safely instead of raising TypeError.
4. Migrate or validate existing library templates (data/library/characters/Lyrie.json, miki doki.json, standalone_test.json).

## Steps to verify

1. Import a library character with equipped items and trigger a refresh (POST /api/library/characters/<id>/refresh).
   - expected: Refresh preserves valid node ID references in player.equipped without injecting raw dict structures.
   - observed: Tested via regression tests; refresh honors resolved item IDs.
2. Request /api/state when player.equipped contains non-string or legacy template values.
   - expected: /api/state returns HTTP 200 without crashing in _region_exposure_map or is_exposed.
   - observed: 200 OK returned; non-string entries safely tolerated.
3. Verify character inventory and equipment inspection in UI.
   - expected: Character Inspector shows correctly attached equipment nodes without orphaned or duplicate items.
   - observed: Verified in live character inventory view.

## Files

- 
outes/library_ops.py (handle_library_import_character, _refresh_character)
- engine/equipment.py (is_exposed, _region_exposure_map)
- engine/body_parts.py
- 	ests/test_library.py
- 	ests/test_equipment.py

## Browser UI and intended live verification

Intended UI home: Library Browser → import a character with an equipped library item → refresh that character from the template → open Character Inspector/Inventory and `/api/state`.

Current availability: the card records contradictory `equipped` shapes between character import and refresh, with a dict entry capable of crashing `/api/state`. The one-shape import/refresh contract and safe malformed-data handling are the review criteria; no new UI is intended.

Live steps when available:
1. Import a character template whose `equipped` field uses the documented shape, then inspect the character's Inventory and equipped slot.
   - expected: the library item materializes once, keeps its properties, and appears in the correct slot.
2. Refresh the same character from its template and reopen `/api/state`.
   - expected: refresh uses the same resolver as import or leaves runtime equipment untouched; `/api/state` returns successfully and does not write a raw incompatible template object into `player.equipped`.
3. Repeat with a malformed equipped entry and with no equipped field.
   - expected: the API does not 500; invalid entries are handled by the documented validation path and valid inventory remains intact.
4. Save and reload, then check the carried-plus-equipped invariant.
   - expected: one item node represents each item; it is not duplicated or orphaned after refresh.

This section is not a claim that the fix has been freshly browser-verified today.
