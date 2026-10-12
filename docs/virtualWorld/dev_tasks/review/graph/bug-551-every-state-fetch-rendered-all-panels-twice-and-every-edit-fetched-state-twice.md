---
type: bug
status: review
area: graph
priority: medium
wiki: "[[graph-canvas]]"
---

# bug-551: Every state fetch rendered all panels twice and every edit fetched state twice

**Filed:** 2026-10-12
**Related:** 

## What

worldState.fetch() emitted BOTH the update event (main.ts handler, which called ui.renderAll) and the state:updated bus event (ui-controller subscription, which also calls renderAll), so a single fetch re-rendered every left panel twice - and an agent click did two fetches, so four. Separately, one edit fetched state twice: app.py broadcasts world_changed for every mutating /api/ call so the SSE refetches, AND many call sites also call worldState.fetch() explicitly. Landed fixes: main.ts no longer calls ui.renderAll (the state:updated subscriber owns rendering); worldState.fetch now coalesces concurrent requests into a single in-flight request, with at most one trailing fetch so a change that lands mid-fetch is never dropped; ui-controller.selectAgent no longer fetches at all. Needs live verification.

## Why

TODO

## How

TODO

## Steps to verify

1. Open DevTools -> Network, filter /api/state. Optionally start a Performance recording.
   - expected: monitoring active
   - observed: TODO
2. Click a character in the Agents list.
   - expected (fixed): one /api/state fetch (the SSE-triggered one, coalesced), and each left panel re-renders ONCE, not twice
   - observed: TODO
3. Make several rapid edits in a row (paint cells, toggle a way, rename a node).
   - expected: the panels still update after the burst; nothing is left stale (the trailing fetch covers a change that lands mid-fetch)
   - observed: TODO
4. Watch for the failure this change could cause: a panel that lags or misses the very last edit.
   - expected: no missed update; if you see one, note the exact edit sequence
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
