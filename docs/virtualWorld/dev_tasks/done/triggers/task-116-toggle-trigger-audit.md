---
group: Trigger System
---
# Toggle Trigger & Event Stream Audit

**Filed**: 2026-07-29  
**Priority**: Medium  
**Status**: Done

---

## Summary

Ensure that all trigger effect messages from backend actions (especially toggle on/off) are:

1. **In the event stream** — visible to the human player in the UI
2. **Fed to the agents** — included in the LLM prompt context via "WHAT HAPPENED" or equivalent

Currently, the `on_toggle_on` trigger for the flashlight (message: *"You click the flashlight on. A bright beam cuts through the dark."*) does not appear in the log output. Only the base `toggle_item_status` message ("You turn the flashlight on.") shows.

### Investigation needed

- Trace the full call chain from `use_item` → `toggle_item_status` → `_execute_triggers` for toggles
- Verify trigger edges exist in the graph for toggle items
- Check if `_execute_triggers` is finding and executing the trigger effects
- Verify `toggleable_items.py` properly appends trigger outputs to the result string
- Check that the route handler (`routes/action.py`) sends the full multi-line result to the frontend
- Verify event stream displays all lines of the action result
- Verify agent prompt "WHAT HAPPENED" section includes trigger outputs

### Scope

- `engine/toggleable_items.py` — trigger execution and result building
- `engine/trigger_system.py` — `_execute_triggers` method, edge discovery, effect execution
- `routes/action.py` — result passing to frontend
- `static/js/event-stream.js` — rendering of action results
- `static/js/agent/prompt-builder.js` — inclusion in LLM context
