---
type: task
status: done
area: ui
priority: medium
---

# task-720: Add node type filter to ValidatorPanel

**Filed:** 2026-10-06
**Related:** 

## What

Add a node type dropdown selector in the ValidatorPanel toolbar that filters validation results by node type. Backend /api/triggers/validate needs a node_type query parameter threaded through to the validator.

## Acceptance

- [x] node type select present, All default (verified).
- [x] selecting a type refreshes via ?node_type= and shows only matching nodes (270 item rows).
- [x] backend + engine filter threaded (validate_triggers node_type).
- [x] header shows filtered count ('in item nodes').

## Related Files

- `static/js/validator-panel.ts`: add filter dropdown, wire refresh with `node_type`.
- `templates/index.html`: validator section markup (toolbar).
- `routes/triggers.py`: add `node_type` query param.
- `virtual_world_engine.py::validate_triggers`: add type filter.

## Steps to verify

- expected: a node-type select filters the panel; header shows the filtered count.
- observed (2026-10-10 live): select options All/area/character/item/logic_trigger/way; picking item -> '270 (0 err . 53 warn) in item nodes' (from 4397); API ?node_type=item returns 270 item-only rows; reset restores 4397.

## Why

TODO

## How

TODO

## Files

- TODO
