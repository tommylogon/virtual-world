---
type: task
status: done
area: refactor
priority: high
wiki: "[[Characters/Agent Engine|Agent Engine]]"
---

# task-899: agent-engine: 10 fixes for step/run lifecycle, state leaks, and race conditions

**Filed:** 2026-10-22
**Related:** 

## What

Fix 10 issues in agent-engine.ts around step/run lifecycle, state leaks, and race conditions

## Why

Found during code review: stepOnce missing cleanup, stale state leaking between runs, unbounded history growth, missing timeouts, duplicate fetch logic, controllingPlayer resolution scattered, turnNumber desync, max-steps counter wrong for single steps, reflection never fires in simultaneous mode, and null-check ordering bug

## How

Apply 10 targeted fixes in agent-engine.ts and turn-queue.ts

## Browser UI and intended live verification

Intended UI home: simulation controls (Run, Pause, Step Once)

Current availability: always

Live steps when available:
1. Load any scenario with characters
2. Click Run - verify it starts
3. Click Pause - verify it pauses
4. Click Step Once - verify single step executes without Already running
5. Refresh page, click Step Once immediately - no Step cancelled
6. Run until a character dies - verify no memory leak in console
7. Run in simultaneous mode - verify reflection fires every 5 turns per character

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

All 10 fixes applied and verified: stepOnce has finally block, paused state reset, dead character cleanup, sim deadlines cleared on stop, turnNumber synced, LLM timeout added, fetch deduplication, controllingPlayer centralized, stepsRun reset in stepOnce, per-char turn counter for reflection, null-check moved up

## Files

- `static/js/agent-engine.ts`
- `static/js/agent/turn-queue.ts`
