# Auto-Closing Doors

**Filed**: 2026-07-17
**Priority**: Low
**Status**: Done — immediate auto-close shipped (engine/movement.py auto_close boolean); the tick-delay variant was never built. Audited 2026-08-03

---

## Summary

Doors that automatically close after use. Examples:
- **Convenience store door** — swings shut behind you
- **Unbalanced door** — slowly drifts closed on its own
- **Swing door / saloon door** — double swinging door that always returns to closed
- **Spring-loaded door** — snaps shut immediately

## Approaches

### Option A: Way property `auto_close`

Add a property to door nodes, e.g. `auto_close: true` or `auto_close_delay: 0` (ticks). When a player moves through the door, the engine automatically changes its state back to `closed` after the specified delay.

Implementation:
- Add `auto_close_delay` field to door node properties (0 = immediate, 1+ = wait N ticks)
- In the movement handler (`move_to_area()` or the `go` handler), after the move completes, schedule a state change back to `closed`
- If delay > 0, queue it on the tick system to fire later

### Option B: Trigger-based

Already possible using existing trigger system — players can create an `on_enter` or `on_exit` trigger on the door that fires `set_state` to `closed`. But this requires manual setup per door.

Expose this as a checkbox in the door inspector: "Auto-close" that creates the trigger automatically.

### Option C: Edge property

Add `auto_close` to the door connection edge instead of the door node, so each side of a door can have different auto-close behavior.

## Way Types

| Type | Behavior | Delay |
|------|----------|-------|
| Convenience store | Swings shut slowly | 1-2 ticks |
| Unbalanced | Drifts closed eventually | 3-5 ticks |
| Swing / saloon | Always returns to closed | 0 ticks (immediate) |
| Spring-loaded | Snaps shut fast | 0 ticks |

## Files Likely Affected

- `virtual_world_engine.py` — auto-close logic in movement handler
- `static/js/inspector.js` — auto-close property in door inspector
- `static/js/main.js` — auto-close option in connection modal
- `static/js/graph-manager.js` — property passthrough
- `world_template.json` / templates — default property

## Open Questions

- Should auto-close only fire when a player passes through, or also NPCs?
- Should a door that's `locked` still auto-close? (Probably not — it should remain locked)
- What about `blocked` or `broken` state ways?
