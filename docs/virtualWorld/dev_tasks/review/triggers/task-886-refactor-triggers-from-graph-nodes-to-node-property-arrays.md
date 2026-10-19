---
type: task
status: review
area: triggers
priority: high
wiki: "[[World Architecture/Engine]]"
---

# task-886: Refactor Triggers from Graph Nodes to Node Property Arrays (Triggers as Data)

**Filed:** 2026-10-19

## Context and Problem

In VirtualWorld, `logic_trigger` nodes and `triggers` edges currently represent action triggers (e.g. `on_use`, `on_eat`, `on_take`, `on_examine`).
However, triggers are behavioral rules and event handlers - data and logic contracts, not physical entities in the spatial world.
Representing each trigger as a separate graph node with dedicated incoming and outgoing edges causes several recurring problems:
1. **Graph Bloat:** Every item with interactions has 1-3 extra nodes and edges.
2. **Dangling Edge Defects:** Deleting, moving, or instancing items frequently leaves behind dangling `triggers` edges pointing to nonexistent trigger nodes (e.g., `trigger_berries_on_eat_*`).
3. **Double Source of Truth:** `materialize.py` currently writes properties to *both* the `logic_trigger` node and the `triggers` edge, while execution checks the edge and falls back to the node.
4. **Violates Invariant:** In VirtualWorld invariants, knowledge and abstract rules are not physical graph entities.

## Target Architecture

1. **Storage as Node Properties:**
   - Instead of a standalone `logic_trigger` node and an `EDGE_TRIGGERS` edge, an item, area, character, or way owns its triggers directly in `properties["triggers"]` as a list of trigger definition dictionaries:
   ```json
   {
     "triggers": [
       {
         "id": "on_eat_1",
         "trigger_type": "on_eat",
         "conditions": [...],
         "effects": [
           {"type": "message", "params": {"text": "Sweet and tart."}},
           {"type": "adjust_vital", "params": {"vital": "Hunger", "amount": 10}}
         ],
         "once": false
       }
     ]
   }
   ```
2. **Trigger Execution Engine:**
   - Update `engine/triggers/execution.py`: evaluate `item_node.properties.get("triggers", [])`.
   - Provide backward-compatible fallback during migration to also check legacy `self.graph.get_edges_for_source(item_node.id, EDGE_TRIGGERS)`.
3. **Editor & UI Sync:**
   - Update Trigger Editor and Inspector panels (`static/js/inspector/trigger-helpers.ts`, `static/js/inspector.ts`) to edit `node.properties.triggers` directly instead of creating/linking separate graph nodes.
4. **Migration & Serialization:**
   - Add migration script / schema upgrade in `engine/serialization.py` to lift legacy `logic_trigger` nodes and `triggers` edges into the parent node's `properties["triggers"]` and prune the orphaned trigger nodes.

## Acceptance Criteria

- [x] `engine/triggers/execution.py` executes triggers directly from `node.properties.get("triggers", [])`.
- [x] Legacy trigger nodes and edges are migrated into parent node properties upon loading older scenarios.
- [x] No more dangling `triggers` edges or orphaned `logic_trigger` nodes are possible because triggers are contained in the entity's own dictionary.
- [x] Trigger inspector and creation workflows mutate `node.properties["triggers"]`.
- [x] All targeted trigger execution tests pass.

## Verification & Evidence

- Unit tests in `tests/test_trigger_system.py` expanded with direct property-based trigger suites:
  - `test_property_trigger_fires_without_graph_nodes`
  - `test_property_trigger_once_marks_fired`
  - `test_property_trigger_condition_gating`
- Test suites passing:
  - `pytest tests/test_trigger_system.py tests/test_trigger_validator.py` (213/213 passed)
  - `pytest tests/test_camp_trigger_wiring.py tests/test_nl_editor_trigger_authoring.py tests/test_speech_triggers.py tests/test_trigger_authoring.py tests/test_trigger_materialize.py` (32/32 passed)
- Frontend TypeScript & unit tests:
  - `npm run build:ts` (0 errors)
  - `node tools/unit/run.cjs` (778/778 passed across 57 test files)
