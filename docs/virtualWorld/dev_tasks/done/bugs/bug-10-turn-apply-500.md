# Bug 10: `/api/turn/apply` returns 500 during turn advance

**Filed**: 2026-07-23
**Priority**: High
**Status**: Fixed (added `self.gs = player_manager` to TickManager.__init__)

## Summary

While running steps, `POST /api/turn/apply` returns 500. This occurs when `TurnQueue.advance()` wraps around to a new turn (all characters have acted) and the backend's `tick_turn()` is called via `turn-queue.js:100`.

## Root Cause

The route handler at `routes/action.py:515-524` calls `app.world.tick_turn()` which delegates to `engine/tick_manager.py:63`. The 500 could be caused by:

1. An exception in vital decay or condition processing
2. `TraitSystem.has_effect()` or `TraitSystem.get_vital_multipliers()` failing
3. Missing player attribute during processing

The specific `logger.exception()` in the handler will log the traceback to the server console. Check server logs for details.

## Files

- `routes/action.py:515-524` — route handler
- `engine/tick_manager.py:63-340` — `tick_turn()` implementation (vital decay, conditions, NPC processing)

---
_Audited 2026-08-03 � duplicate file consolidated into this record._
