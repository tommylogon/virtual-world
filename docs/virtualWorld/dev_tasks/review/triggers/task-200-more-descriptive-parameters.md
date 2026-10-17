---
area: triggers
type: task
status: review
priority: medium
related: ['task-203', 'task-297', 'task-308']
---

# More Descriptive Template Parameters

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

<!-- deps:start -->
**Related:** [[task-203-set-adjust-parameters]], [[task-297-vitals-readout-trigger-condition-message]], [[task-308-item-relationship-condition]]
<!-- deps:end -->

## Why

Only `{game_time}` and a few template parameters exist. Template authors want `{uses}`, `{weight}`, `{condition}`, `{condition_severity}`, `{condition_duration}`, `{condition_cause}`, `{condition_effects}`, etc.

## How

- Pure templating done in `_render_template` context building — no engine logic change, just more context keys.
- The `{condition_*}` parameters only make sense once conditions are rich (task-190), so they should gate behind that work.
- Composes with aliases in labels, so template text stays readable.

## Files

- engine/trigger_system.py — extend context building (lines 1652-1704) with new template parameters
- engine/item_actions.py — expose item `uses` and `weight` to the template context

## What

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO
