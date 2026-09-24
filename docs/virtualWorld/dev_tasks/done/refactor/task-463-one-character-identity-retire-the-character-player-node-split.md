---
type: task
status: done
area: refactor
priority: high
---

# task-463: One character identity - retire the character_/player_ node split

**Filed:** 2026-09-22
**Related:** task-408, task-316, task-446, task-457, task-439

## Goal

A character has exactly one graph node. Today the offline generator authors character_<slug> (description + in/carrying edges) while the runtime anchors player_<Name> (x/y + at/equipped/grappled edges) - the kraktooth scenario has 46 character nodes for 23 players, with a compatibility shim at engine/area_description.py:378. Pick one canonical node id (id-derived per task-316/446, unique names keeping the legacy derived id), merge authored nodes/edges into it at load, add a migration tool for existing scenarios/saves, and change tools/assemble_scenario.py + build_scenario.py + generate_scenario.py so the duplication cannot recur.

## Acceptance

- [x] A character has exactly one graph node. A load-time normalizer collapses
      the authored `character_<slug>` node into the runtime `player_<Name>`
      anchor: `engine/character_identity.py:collapse_character_identity`,
      called from `engine/serialization.py:load_from_dict`.
- [x] Retired ids stay resolvable: `WorldGraph.register_alias` /
      `_id_aliases`, so `graph.get_node("character_arix")` returns the
      canonical node and authored references do not dangle.
- [x] `character_<slug>` is an alias in the graph's id index; edges of every
      type are rewritten onto the canonical node and duplicate location edges
      deduped.
- [x] The `engine/area_description.py` `character_`/`player_` shim is gone;
      the "knows this character" check resolves the canonical anchor id
      (case-insensitively). The frontend `known` checks match it too.
- [x] Authored `known` lists naming a retired id are rewritten at load.
- [x] Offline migration tool: `tools/migrate_character_identity.py`
      (dry-run by default, `--write`, idempotent).
- [x] Generators emit the canonical node only: `tools/build_scenario.py`
      (`canonicalize_character_ids`) and `tools/assemble_scenario.py` (collapses
      a dual-identity seed).
- [x] Tests: kraktooth loads as 23 character nodes (not 46), no `character_*`
      orphans, location/possession resolve, and a save round-trips
      (`tests/test_character_identity.py`, 9 tests).

## Implementation notes

- Canonical id stays `player_<Name>` for a unique display name (no save churn);
  duplicates keep the task-446 `__<uid6>` suffix. The normalizer mirrors
  `PlayerManager.reindex` (`engine/character_identity.anchor_node_id`).
- The normalizer is pure data (no graph/Flask), so the loader and the offline
  tool share one definition. It works on shallow copies so a live
  `to_dict()` payload is never mutated through its shared property references.
- Migration is not run on the tracked kraktooth scenario (that data cleanup is
  task-408); the loader collapses it at load, and the next save writes the
  single-identity form.

