---
type: bug
status: done
area: bugs
priority: medium
---

# bug-44: EDGE_IN is inverted for authored container contents

**Filed:** 2026-09-23
**Related:** task-485

## Goal

Container contents authored in the item library land as container -> contained (item_Backpack -> item_Ink), but EDGE_IN is canonically contained -> container (place_actions.py:79, take_drop_actions.py:685, activities.py:505) and every reader looks up get_edges_for_target(container, EDGE_IN) (equipment.py:113, item_actions.py:141, matching.py:304, activities.py:466/541, item_reach.py:148). Autosave has 21 such inverted item->item edges (Backpack -> Ink/Book/Oil/..., grandfather_clock -> brass_key, medicine_cabinet -> antiseptic/bandages), so those contents are invisible to take/examine/search/lighting/reach. Fix the authoring path (or migrate the saves) so the item is the source; the graph layout works either way because it resolves by depth.

## Acceptance

- [x] Loading a world with container -> contained `in` edges reverses them to
      contained -> container (contents visible to take/examine/search again).
- [x] Legacy `contains` edges (container -> contained) migrate to `in` with
      endpoints swapped, not merely relabelled.
- [x] Canonical edges (contained -> container) and nested containers are left
      untouched; the 21 real-world edges across `world_template.json`, the
      autosaves and `The Valerious Case.json` are all repaired while the 21
      already-canonical edges in `data/scenarios/world_template.json` stay as-is.

## Resolution (2026-09-24)

Root cause: `Graph.normalize_edges` relabelled legacy `contains` edges to `in`
**without reversing the endpoints**. `contains` was container -> contained while
`in` is contained -> container (the lookups in `get_edges_for_source/target`
already treat a legacy `contains` edge as its reversed `in`), so every migrated
edge came out backwards. The library authoring paths
(`_spawn_library_item_node`, `place_library_item`, `serialization_template`,
`generate_scenario`) were already writing the canonical direction — the damage
was done entirely in that migration, then frozen into saves.

Fix in `graph.py`:

- `normalize_edges`: the `EDGE_CONTAINS` branch now swaps source/target.
- New `Graph.normalize_in_edge_directions()` (called from `load_from_dict` after
  endpoint normalization): reverses already-relabelled item -> item `in` edges
  whose source is *placed* (has an `in` edge to an area, or `carrying`/`equipped`
  to a character) and whose target is not. A container that sits in a room or on
  a character is placed; the contents reached through it never are. So a placed
  container with outgoing `in` edges to items is stored backwards.

Nested `pouch -> backpack` (neither placed directly) is untouched, as are all
canonical edges. Tests: `tests/test_spatial_edges.py`
(`test_legacy_contains_edges_are_reversed`,
`test_inverted_container_edges_are_reversed_on_load`,
`test_equipped_container_contents_are_reversed_on_load`,
`test_canonical_container_edges_are_left_alone`,
`test_nested_container_edge_is_untouched`).

The tracked `world_template.json` still stores the inverted edges, but they are
reversed on every load (and re-persisted by the next save/autosave), so no manual
data migration is required.

## Files

- `graph.py` — `normalize_edges` contains-reversal + `normalize_in_edge_directions`
- `tests/test_spatial_edges.py` — direction coverage
