---
type: task
status: review
area: ui
priority: medium
---

# task-720: Add node type filter to ValidatorPanel

**Filed:** 2026-10-06
**Related:** 

## Goal

Add a node type dropdown selector in the ValidatorPanel toolbar that filters validation results by node type. Backend /api/triggers/validate needs a node_type query parameter threaded through to the validator.

## Acceptance

- ValidatorPanel toolbar has a node type `<select>` dropdown (all types shown, "All" default).
- Selecting a type refreshes results via `/api/triggers/validate?node_type=<type>` and shows only matching nodes.
- Backend `routes/triggers.py` `/api/triggers/validate` accepts `node_type` query param and threads it to `world.validate_triggers(node_type=...)`.
- `virtual_world_engine.py::validate_triggers` filters nodes by type before validating.
- Existing `node_id` filter still works; `node_id` + `node_type` together are honored.
- Panel header shows filtered count (e.g., "3 issues in logic_trigger nodes").

## Related Files

- `static/js/validator-panel.ts`: add filter dropdown, wire refresh with `node_type`.
- `templates/index.html`: validator section markup (toolbar).
- `routes/triggers.py`: add `node_type` query param.
- `virtual_world_engine.py::validate_triggers`: add type filter.
