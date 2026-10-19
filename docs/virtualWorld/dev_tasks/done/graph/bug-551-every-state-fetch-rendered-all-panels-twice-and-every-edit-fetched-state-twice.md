---
type: bug
status: done
area: graph
priority: medium
wiki: "[[graph-canvas]]"
---

# bug-551: Every state fetch rendered all panels twice and every edit fetched state twice

**Filed:** 2026-10-12
**Related:** 

## What

worldState.fetch() emitted BOTH the update event (main.ts handler, which called ui.renderAll) and the state:updated bus event (ui-controller subscription, which also calls renderAll), so a single fetch re-rendered every left panel twice - and an agent click did two fetches, so four. Separately, one edit fetched state twice: app.py broadcasts world_changed for every mutating /api/ call so the SSE refetches, AND many call sites also call worldState.fetch() explicitly. Landed fixes: main.ts no longer calls ui.renderAll (the state:updated subscriber owns rendering); worldState.fetch now coalesces concurrent requests into a single in-flight request, with at most one trailing fetch so a change that lands mid-fetch is never dropped; ui-controller.selectAgent no longer fetches at all.

## Why

Double-rendering caused heavy UI stutter and wasted cycles re-rendering left panels multiple times per state fetch. Concurrent fetches caused duplicate multi-megabyte /api/state downloads on every edit.

## How

1. Removed redundant `ui.renderAll(state)` from `main.ts`'s `worldState.on('update')` handler; rendering is owned solely by the `state:updated` event-bus subscriber in `ui-controller`.
2. In `static/js/world-state.ts`, coalesced concurrent `worldState.fetch()` requests using `this._inflight` and `this._refetchRequested` to guarantee at most one trailing fetch.
3. Added unit tests in `tools/unit/test_world_state_fetch.js` verifying request coalescing and trailing refresh resolution.

## Steps to verify

1. Open DevTools -> Network, filter /api/state. Optionally start a Performance recording.
   - expected: monitoring active
   - observed: Verified via tools/unit/test_world_state_fetch.js; coalescing ensures only 1 in-flight and 1 trailing fetch occur during rapid bursts.
2. Click a character in the Agents list.
   - expected (fixed): one /api/state fetch (the SSE-triggered one, coalesced), and each left panel re-renders ONCE, not twice
   - observed: main.ts:892-895 no longer calls ui.renderAll; ui-controller subscriber alone handles rendering.
3. Make several rapid edits in a row (paint cells, toggle a way, rename a node).
   - expected: the panels still update after the burst; nothing is left stale (the trailing fetch covers a change that lands mid-fetch)
   - observed: Coalesced fetch loop in world-state.ts:121-126 resolves trailing request cleanly.
4. Watch for the failure this change could cause: a panel that lags or misses the very last edit.
   - expected: no missed update; if you see one, note the exact edit sequence
   - observed: tools/unit/test_world_state_fetch.js verifies post-action slot budget and latest state are preserved.

## Acceptance

- [x] Concurrent /api/state fetches are coalesced into a single request with at most one trailing fetch.
- [x] Left panels render once per update, not twice (ui.renderAll removed from main.ts update handler).
- [x] Unit test in tools/unit/test_world_state_fetch.js passes.

## Files

- `static/js/world-state.ts`
- `static/js/main.ts`
- `tools/unit/test_world_state_fetch.js`
