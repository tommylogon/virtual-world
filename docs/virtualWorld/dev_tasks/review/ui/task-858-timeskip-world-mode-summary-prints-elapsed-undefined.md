---
type: task
status: todo
area: ui
priority: low
horizon: next
effort: S
wiki: "[[timeskip|Timeskip]]"
---

# task-858: Timeskip world-mode summary prints Elapsed undefined

**Filed:** 2026-10-17
**Related:** 

## What

`_summarize` in `static/js/ui/timeskip.js:177-187` has `if (data.mode === 'world') { ... } if (data.mode === 'soak') { ... } else { ... }`. The `else` binds only to the second `if`, so for `mode === 'world'` both the `No active character - the world advances.` line and the elapsed line run, and the elapsed line prints `Elapsed: undefined min (undefined ticks) -> ` because a world advance carries no `elapsed_minutes`, `ticks` or `clock_after`.

## Why

A world-advance skip (no active character) is a normal case, and its summary currently shows a broken line. `_summarize` is documented as pure and unit-testable, so the fix is small and safe.

## How

Change the second `if (data.mode === 'soak')` to `else if (data.mode === 'soak')` so `mode === 'world'` prints only its own line. Add or extend a unit test for `_summarize({ mode: 'world', order: null })` asserting no `undefined` appears and that the elapsed line is absent.

## Browser UI and intended live verification

Intended UI home: the timeskip result summary. Current availability: the bug is visible any time a timeskip runs with no active character. Live path: with no active character, request a timeskip and confirm the summary shows only the world-advance line, with no `Elapsed: undefined` line.

## Steps to verify

1. `node tools/unit/run.cjs` for the timeskip summary test.
   - expected: pass, and `_summarize({ mode: 'world' })` contains no `undefined`.
   - observed: TODO
2. Live: request a world timeskip with no active character.
   - expected: the summary shows only the world-advance line.
   - observed: TODO

## Acceptance

- [ ] `mode: 'world'` prints only the world-advance line.
- [ ] A unit test asserts `_summarize` never emits `undefined` for the world mode.

## Files

- `static/js/ui/timeskip.js` (`_summarize`)
