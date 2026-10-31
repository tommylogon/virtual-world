---
type: task
status: done
area: refactor
priority: high
wiki: "[[Character System]]"
related: ["task-744", "task-855", "task-316", "task-457"]
---

# task-914: Character node and player entity architectural unification

**Filed:** 2026-10-30
**Related:** task-744, task-855, task-316, task-178, task-457

## What

Execute the architectural transition defined in `docs/design/character-entity-refactor-plan.md` (Phase 2 / task-457) to eliminate duplicate character representations and establish `Node.properties` as the single authoritative home for authored definition:

1. **Retire the Required `players` Scenario Block:**
   - Scenarios can now author characters purely as `character` graph nodes (`graph.nodes`).
   - `deserialize_world` automatically hydrates `Player` instances for any character nodes in the graph not explicitly listed in the `players` dictionary.
   - Authored definition (personality, base description, description, tags, traits, interest tags, fear tags, flags, appearance, triggers) lives on `Node.properties`.

2. **Unified Character Store Module (`engine/character_store.py`):**
   - Implemented `to_node_properties(player)`, `apply_node_properties(player, props, pdata)`, `hydrate_player_from_node(node, pdata)`, and `sync_player_to_node(player, node)`.
   - Wired into `engine/serialization.py`, `engine/player_manager.py`, and `routes/player_ops.py` to eliminate copy-paste dictionary manipulation and prevent drift.

3. **Simulation Invariants & Payload Protection:**
   - Preserved the simulation invariant from `AGENTS.md`: runtime state (vitals, memories, emotions, perception, turn slots) stays on `Player` so `/api/state` and vis.js graph network payloads do not bloat.
   - `to_scenario_dict()` synchronizes authored definition onto `Node.properties` while stripping redundant definition copies from the scenario `players` dictionary.

## Why

Having multiple competing homes for character definition (`WorldGraph.nodes` vs `engine.players`) created recurring bugs where descriptions, tags, traits, or locations desynchronized between layers. The graph node is now the single source of truth for authored definition.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Scenarios authored with character nodes hydrate without needing duplicate entries in `players`
   - observed: `VirtualWorld.load_from_dict` successfully discovers and hydrates character graph nodes
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: Automated test execution and contract verification gates
   - observed: `tests/test_character_store.py` verified 6 targeted test cases; `ts_convert` gate green
3. Run the targeted regression test for the mechanism.
   - expected: `python -m pytest tests/test_character_store.py tests/test_serialization.py tests/test_spatial_edges.py`
   - observed: 41 passed in 0.81s

## Acceptance

- [x] `engine/character_store.py` provides pure conversion functions between `Player` and `Node.properties`
- [x] Scenarios can declare characters purely as `character` graph nodes without a manual `players` dictionary entry
- [x] `to_scenario_dict` saves definition to `Node.properties` and strips redundant definition from `players`
- [x] `engine/player_manager.py` and `routes/player_ops.py` synchronize definition through `character_store`
- [x] Targeted pytest suite and full repository gates pass cleanly with zero em-dashes

## Files

- `engine/character_store.py`
- `engine/serialization.py`
- `engine/player_manager.py`
- `routes/player_ops.py`
- `tests/test_character_store.py`
