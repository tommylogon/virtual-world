---
type: bug
status: review
area: characters
priority: high
---

# bug-516: refresh-to-world writes equipped verbatim, so a dict entry crashes /api/state; the import and refresh paths require contradictory equipped shapes

**Filed:** 2026-10-01
**Related:** task-519, task-654, task-659

## Relationship to task-519 — read this first

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

## Goal

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
