---
group: Triggers
---
# Vitals Readout as Trigger Condition and Message

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Idea

---

## Idea

New triggers and conditions for using vitals readout as a condition, and getting a vital readout as a message. Example: a thermostat that shows the character's core temperature, hunger, conditions, etc.

## Notes

- The condition half already exists: `vital`, `vital_above`, `vital_below`, `temperature_above/below`, `area_temp` are implemented in `engine/trigger_system.py`.
- What's missing is the readout-as-message half: a message template placeholder (e.g. `{vital:Thirst}`) so an item's `message` effect can print a current vital value.
- Small completion of the existing system â€” no new condition machinery needed.

## Related

- `developer ideas.md` line 4
- `engine/trigger_system.py`, `engine/effects.py` (`handle_adjust_vital`, `_render_template`)

