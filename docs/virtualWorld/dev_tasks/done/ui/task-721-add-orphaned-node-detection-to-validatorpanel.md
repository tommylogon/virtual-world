---
type: task
status: done
area: ui
priority: medium
---

# task-721: Add orphaned node detection to ValidatorPanel

**Filed:** 2026-10-06
**Related:** 

## What

Add a new validation pass that detects orphaned nodes (nodes with zero incoming/outgoing edges) and reports them as warnings in ValidatorPanel with code 'orphaned_node'.

## Acceptance

- [x] orphaned nodes detected (4 found live). - [x] code 'orphaned_node', severity warning, carries source_node_id + node_type. - [x] grouped under their type in the panel; the task-720 filter applies.

## Related Files

- `engine/trigger_validator.py`: add orphan detection pass.
- `static/js/validator-panel.ts`: render orphaned nodes in results list.
- `templates/index.html`: no markup change needed (reuses existing result rendering).

## Steps to verify

- expected: orphaned_node warnings exist and group by type.
- observed (2026-10-10 live): API returns 4 orphaned_node warnings, e.g. item_creel_1791283157194_961, item_goblin_bone_club_8z7w; engine/trigger_validator.py _validate_orphaned_nodes (line 229/252) emits the code.

## Why

TODO

## How

TODO

## Files

- TODO
