---
group: Environment
---
# Default Time per Turn: 1 Minute Instead of 5

**Filed**: 2026-08-19
**Priority**: Low
**Status**: Cancelled (2026-09-02)

---

## Idea

Change the default time per turn from 5 minutes to 1 minute.

## Notes

- Risky as a silent *global* default change — it re-paces every existing scenario and anything tuned around the 5-minute tick (vital decay rates, starvation timelines, activity durations).
- Prefer a **per-scenario** clock setting instead (which is exactly `task-300`), and let authors opt into 1-minute turns.
- If a global default change is still wanted, it should be an explicit, documented decision with decay rates re-balanced around it.

## Related

- `developer ideas.md` line 8
- `task-300` (scenario clock start time), `task-304` (centralized config)

## Resolution (2026-09-02)

Cancelled in favour of the per-scenario path this task itself recommended:
task-300's clock settings plus `GET/POST /api/settings/time_per_tick` already
let each scenario opt into 1-minute turns without re-pacing every other
scenario. A global default change is deliberately not made.
