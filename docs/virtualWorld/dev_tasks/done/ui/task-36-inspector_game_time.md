---
group: Prompt & Narrative Quality
wiki: "[[UI & Settings/Inspector Panels]]"
---

# Inspector: Show Game Time Instead of Ticks

**Filed**: 2026-07-17
**Priority**: Medium
**Status**: Implemented / Needs Review

---

## Summary

Inspector panels (memories, timeline, room event log, world lore) displayed raw tick numbers like `[Tick 42]` or `[T42]`. These now show `HH:MM` game time, matching the event stream format.

## Changes

- Made `EventBus.tickToTime()` public (was `_tickToTime`)
- Replaced tick displays in 5 inspector locations:
  - Memory list entries
  - Timeline entry badges
  - Timeline detail phase line
  - Area event log
  - World lore entries
- Replaced tick displays in 2 main.js locations:
  - Save slot list
  - Timeline popup header

## Files Changed

- `static/js/event-stream.js` — renamed `_tickToTime` → `tickToTime`
- `static/js/inspector.js` — 5 tick displays → `events.tickToTime(tick)`
- `static/js/main.js` — 2 tick displays → `events.tickToTime(tick)`