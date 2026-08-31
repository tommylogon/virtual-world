---
group: Trigger System
---

# More Descriptive Template Parameters

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

## Problem

Only `{game_time}` and a few template parameters exist. Template authors want `{uses}`, `{weight}`, `{condition}`, `{condition_severity}`, `{condition_duration}`, `{condition_cause}`, `{condition_effects}`, etc.

## Design

- Pure templating done in `_render_template` context building â€” no engine logic change, just more context keys.
- The `{condition_*}` parameters only make sense once conditions are rich (task-190), so they should gate behind that work.
- Composes with aliases in labels, so template text stays readable.

## Files

- engine/trigger_system.py â€” extend context building (lines 1652-1704) with new template parameters
- engine/item_actions.py â€” expose item `uses` and `weight` to the template context

