---
type: task
status: review
area: ui
priority: medium
---

# task-721: Add orphaned node detection to ValidatorPanel

**Filed:** 2026-10-06
**Related:** 

## Goal

Add a new validation pass that detects orphaned nodes (nodes with zero incoming/outgoing edges) and reports them as warnings in ValidatorPanel with code 'orphaned_node'.

## Acceptance

- Orphaned nodes (zero incoming + zero outgoing edges) detected in a new validation pass.
- Each orphan reported as `{ severity: 'warning', code: 'orphaned_node', source_node_id, message, node_type }`.
- Orphaned nodes appear grouped in ValidatorPanel under their type.
- Filter dropdown (task-720) also filters orphaned node results.
- Detection runs against `world.graph.nodes` and `world.graph.edges`; no DB changes.

## Related Files

- `engine/trigger_validator.py`: add orphan detection pass.
- `static/js/validator-panel.ts`: render orphaned nodes in results list.
- `templates/index.html`: no markup change needed (reuses existing result rendering).
