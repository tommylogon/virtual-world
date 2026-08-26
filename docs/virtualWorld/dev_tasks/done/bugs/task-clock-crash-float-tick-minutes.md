---
group: Tech Debt & Testing
---

# Clock Crash — Float time_per_tick_minutes Breaks /api/state

**Filed**: 2026-08-09  
**Priority**: High  
**Status**: In Review — implemented 2026-08-09, `/api/state` verified 200 again, regression test added.

---

## Summary

`GET /api/state` crashed with `ValueError: Unknown format code 'd' for object of type 'float'` (`engine/tick_manager.py:77`), taking down the whole frontend (500 on state fetch).

## Root cause

`time_per_tick_minutes` is stored as a float (`routes/settings.py:91` casts to `float`, so even "5" becomes 5.0). `get_current_time()` computed `total_minutes = time_ticks * time_per_tick_minutes` → float, then `f"{hours:02d}"` with float `hours` (result of float `//`) crashes — Python's `d` format code rejects floats.

## Fix

`engine/tick_manager.py`:
- `get_current_time()`: convert to whole seconds first (`int(total_minutes * 60) % 86400`), then derive hours/minutes/seconds with integer `//` and `%`. Fractional minutes now roll into real seconds (e.g. 2.5 min/tick → `12:02:30`) instead of being truncated.
- `rest()`: `ticks = max(1, int(minutes // time_per_tick_minutes))` — the float `//` result was also going to break `range(ticks)` for longer rests.

## Verification

- Live: `/api/state` returns 200 again (was 500).
- Unit: `test_get_current_time_with_float_tick_minutes` in `tests/test_engine_init.py` — 97 ticks × 2.5 min from 08:00 → `12:02:30`; 16/16 engine-init tests pass.
- Manual math check for 5.0 (16:05:00), 2.5 (12:02:30), 7 (19:19:00).

## Files Changed

- `engine/tick_manager.py` — float-safe clock + rest tick count
- `tests/test_engine_init.py` — regression test
