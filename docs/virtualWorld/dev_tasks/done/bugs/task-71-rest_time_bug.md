# Rest Time Bug — Time Does Not Advance Across All Characters

**Filed**: 2026-07-17
**Priority**: High
**Status**: Done — fixed in code (rest() converts minutes→ticks, ticks all characters; engine/tick_manager.py:456-471). Audited 2026-08-03

---

## Summary

Multiple issues with rest/sleep:

1. **Time does not advance** when resting — the clock stays frozen despite the rest duration.
2. **Wrong duration math** — `rest 10` means 10 rest *ticks*, not 10 minutes. Each tick is 5 minutes, so `rest 10` = 50 minutes of rest, not 10.
3. **Multi-character desync** — if time does advance for one character resting, other characters' vitals don't decay proportionally, creating timeline inconsistencies.

## Actual Code Behavior

### `rest()` flow in `virtual_world_engine.py`

`rest()` calls `apply_action("rest", cost, player=self.player)` where `cost` has `"time": minutes`. `apply_action` then calls `advance_clock(cost["time"])` which increments `self.time_ticks` by that amount. However, no other characters' vitals are decayed for those elapsed ticks.

### `state_timer` handling

`rest()` sets `self.player.state = "sleeping"` and `self.player.state_timer = minutes`. The timer decrements 1 per tick in `advance_clock()`. Since rest consumes multiple ticks at once, the timer works but the player is only awake after all those ticks pass in the clock.

## Fix

1. Ensure rest correctly advances the clock
2. Rest should be N 5-minute ticks, not N abstract steps — duration = minutes / 5 (or rest explicitly in ticks)
3. Apply baseline vital decay to ALL characters (not just the rester) for each elapsed tick to keep the world simulation consistent
