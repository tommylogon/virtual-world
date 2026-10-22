---
type: bug
status: done
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

- [x] The library character `equipped` field has ONE documented shape, and both
      `handle_library_import_character` (`routes/library_ops.py`) and
      `_refresh_character` (`routes/library_ops.py`) accept it. Both call the same
      `_resolve_character_equipped`; the shape is now written down in
      `docs/virtualWorld/Characters/Characters Overview.md` (Equipment section).
- [x] `_refresh_character` no longer writes a raw template value into
      `player.equipped`; it resolves through `_resolve_character_equipped` and then
      `set_equipped_payload`.
- [x] `/api/state` cannot 500 on a malformed or foreign-shaped `equipped` entry.
      `is_exposed` skips any entry that is not a string (and the `__multi_slot_`
      markers) before `graph.get_node`, rather than raising `TypeError`.
- [x] `player.equipped[slot]` is node-id strings everywhere it is read. The line
      numbers this box originally cited moved with the file; the resolver is the
      single write path for import and refresh.
- [x] `data/library/characters/Lyrie.json`, `miki_doki.json` and
      `standalone_test.json` are node-id strings now (`miki doki.json` was renamed
      to `miki_doki.json`).
- [x] Regression test: a template whose `equipped` holds dicts is refreshed, then
      `/api/state` is requested and returns 200
      (`tests/test_character_loadout_refresh.py::test_refresh_with_dict_equipped_does_not_crash_state`).

## Verified 2026-10-21

- `python -m pytest tests/test_character_loadout_refresh.py` - 6 passed, including
  the dict-template regression, which also asserts the surviving slot value is the
  node id (`item_victim_plate`), not the dict.
- Guard checked directly against the thing `/api/state` calls, with a player whose
  `equipped` already holds junk (no refresh involved):

  ```
  dict entry         is_exposed=True  region_map_ok=True
  int entry          is_exposed=True  region_map_ok=True
  none entry         is_exposed=True  region_map_ok=True
  multi-slot marker  is_exposed=True  region_map_ok=True
  mixed              is_exposed=True  region_map_ok=True
  ```

  `_region_exposure_map` completes for every case; nothing raises.
- `python tools/character_loadout_check.py --report` - 73 character entries, 0
  errors, 9 unrelated `name_does_not_match_file` warnings. No `equipped_dict_entry`
  finding remains.
- Data shapes read directly: `Lyrie.json` -> `item_<Name>` strings,
  `miki_doki.json` -> `item_<slug>` strings, `standalone_test.json` ->
  `item_mystery_talisman`. All three keep the worn item in `inventory` as well,
  which is what the resolver needs.


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

- `routes/library_ops.py` (`handle_library_import_character`, `_refresh_character`, `_resolve_character_equipped`)
- `engine/equipment.py` (`set_equipped_payload`)
- `engine/body_parts.py` (`is_exposed` and the non-string guard)
- `tests/test_character_loadout_refresh.py`
- `docs/virtualWorld/Characters/Characters Overview.md` (documented shape)

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
