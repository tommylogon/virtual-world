# Bug-15: Area inspector event log crashes — EventBus.getActionIcon is not a function

**Status:** Done — verified 2026-08-16 (browser re-check: area inspector event log renders), moved from todo.
**Area:** UI — Area Inspector being-view event log
**Observed:** Clicking an area in the map editor to open its inspector throws:
`area-view.js:72 Uncaught TypeError: EventBus.getActionIcon is not a function`

## Root cause (via git history)

The calls `EventBus.getActionIcon` / `EventBus.getActionColor` were introduced in
`c1fbe62d` (rooms→areas refactor) alongside matching `static getActionIcon()` /
`static getActionColor()` helpers in the `EventBus` class (`event-stream.js`). Renamed
`events.` → `EventBus.` in `d0be8ce0`. Both static methods were **deleted in `d3b402ec`**
("merge: resolve autosave.json conflict") but the area-view.js calls were never updated,
leaving them dangling. No test/lint runs the area-click → open-inspector path, so nothing
caught it.

## Fix

Restored the two static helpers into the `EventBus` class in
`static/js/event-stream.js` (right after `tickToTime`), exactly matching what `d3b402ec`
removed:

- `EventBus.getActionIcon(entry)` — icon from the event `result` string (`▶️` success /
  `⚠️` error / `✕` death-kill).
- `EventBus.getActionColor(entry)` — `var(--green)` / `var(--orange)` / `var(--red)`.

`EventBus.tickToTime` (also called by area-view) was unaffected.

## Verification

- `node --check static/js/event-stream.js` passes.
- `rg getActionIcon` now finds both the definition (event-stream.js) and the caller
  (area-view.js). Live click-an-area check in the browser pending.

## Prevention note

DOM inspector views have no unit-test coverage, and `node --check` can't catch callers of
undefined methods — only a lint pass with an undefined-reference rule or a browser E2E
step that opens an area of the map editor would have caught this.