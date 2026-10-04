---
type: bug
status: review
area: bugs
priority: medium
---

# bug-520: Library browser can never open: itemLibRef snapshots window.itemLib, which nothing publishes

**Filed:** 2026-10-04
**Related:** 

## Goal

Open the library browser (Build > Library) and it silently never appears. Console:
`Uncaught (in promise) TypeError: can't access property "data", itemLibRef is undefined`
(libraries-browser.js:93). Reproduced live 2026-10-04 in a driven browser session on
kraktooth_goblin_camp; every open attempt, real mouse clicks included, died silently
because `open()` is async and the rejection was unhandled.

## Why

`library-browser.ts:45` snapshots `window.itemLib` at module load. But `itemLib` is a
top-level `const` in item-library.js - a global *lexical* binding, not a window
property (the exact trap the TS-migration rules warn about) - and the only publication,
`VW.itemLib = itemLib` in main.js, runs at main.js's load (index.html:1439), after
library-browser.js (index.html:1383). So the snapshot is always undefined and
`open()` throws at `itemLibRef.data = ...` before it ever sets `display: flex`.

## Fix (2026-10-04)

`itemLibRef` became a lazy function reading `VW.itemLib ?? window.itemLib` at call
time; the two call sites (`open()` data share, `switchTab('items')`) call it and
guard for undefined. `python tools/ts_convert.py check` gate green.

## Acceptance

- [x] Build > Library opens the modal (verified live after page reload)
- [x] Characters tab renders library entries

TODO

## Acceptance

- TODO
