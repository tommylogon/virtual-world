---
area: triggers
type: task
status: review
priority: medium
related: ['task-200', 'task-203', 'task-308', 'task-47']
---

# Vitals Readout as Trigger Condition and Message

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Idea

---

<!-- deps:start -->
**Related:** [[task-200-more-descriptive-parameters]], [[task-203-set-adjust-parameters]], [[task-308-item-relationship-condition]], [[task-47-stateful_continuous_triggers]]
<!-- deps:end -->

## Idea

New triggers and conditions for using vitals readout as a condition, and getting a vital readout as a message. Example: a thermostat that shows the character's core temperature, hunger, conditions, etc.

## Notes

- The condition half already exists: `vital`, `vital_above`, `vital_below`, `temperature_above/below`, `area_temp` are implemented in `engine/trigger_system.py`.
- What's missing is the readout-as-message half: a message template placeholder (e.g. `{vital:Thirst}`) so an item's `message` effect can print a current vital value.
- Small completion of the existing system — no new condition machinery needed.

## Related

- `developer ideas.md` line 4
- `engine/trigger_system.py`, `engine/effects.py` (`handle_adjust_vital`, `_render_template`)

## What

TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
