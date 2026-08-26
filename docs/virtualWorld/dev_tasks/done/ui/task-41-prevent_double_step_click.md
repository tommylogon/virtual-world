---
group: Tech Debt & Testing
wiki: "[[UI & Settings/Inspector Panels]]"
---

# Prevent Double-Click on Step Button

**Priority**: Medium

## Summary

Clicking the Step (⏭) button rapidly while a step is in progress queues up multiple `stepOnce()` calls, causing overlapping agent turns and confused state. The step button should be disabled while a step is in progress.

## Current State

`config.busy` is already set during `step()` and `updateButtons()` already disables the button based on `config.busy || config.running`. But `stepOnce()` only checks `config.running`, and the button disable happens after the first `await` — so rapid double-clicks before the async yield can slip through.

## Fix

Add `config.busy` check to `stepOnce()`:

```js
if (config.busy || config.running) { ... return; }
```

## Audit

**Status**: Ready to test
**How to test**:
- Click the Step (⏭) button rapidly multiple times. Verify only one step executes per click — the button should disable during execution and no overlapping agent turns occur.

## Files Changed

- `static/js/agent-engine.js` — add `config.busy` check in `stepOnce()`
