---
type: task
status: todo
area: ui
priority: high
---

# task-712: A failed scope fetch silently resets the filter to Whole world, which will promote the whole cast

**Filed:** 2026-10-05
**Related:** task-710,task-397

## Goal

network-manager.loadGraphData() catches ANY failure from getScopeSubgraph and silently resets graphManager._scopeFilter to null, falling back to the whole world. Once the scope filter drives the promoted set (task-710), that fallback stops being a rendering fallback: it promotes every character in the game.

It is also broader than the comment claims. The comment says 'Stale selection (e.g. after a scenario load)', but the catch is on the whole fetch, so a transient 500, a network blip, or a proxy timeout all demote-to-Whole-world too. Nothing distinguishes a scope that no longer exists from a scope that failed to load.

The filter is also cleared with no notification: the picker's value is set to '' and
the user sees the whole world with no indication anything went wrong.

**Code** (`static/js/graph/network-manager.ts`, in `loadGraphData`):

```js
const scopeId = graphManager._scopeFilter || null;
if (scopeId) {
    try {
        const sub = await ApiClient.getScopeSubgraph(scopeId, true);
        ...
    } catch (err) {
        // Stale selection (e.g. after a scenario load): drop it and
        // fall back to the whole world rather than showing nothing.
        graphManager._scopeFilter = null;
        const sel = document.getElementById('graph-scope-filter');
        if (sel) sel.value = '';
        ...
    }
}
```

`getScopeSubgraph` throws on any non-OK response (`static/js/api.ts:240`), and a
network failure rejects the fetch — so the catch covers both.

## Why it is worse than a rendering bug

Today the cost of a false reset is a slow canvas. After task-710 the cost is the
whole cast at full LLM fidelity, chosen by a network blip the user never sees.
The failure mode is also *silent in the expensive direction*: the graph looks
fine, it just looks like the whole world.

## Acceptance

- [ ] A **404 / unknown scope** still falls back, because there is genuinely
      nothing to show — but the user is told the scope went away rather than
      being handed a whole world with no explanation.
- [ ] A **transient failure** (5xx, timeout, offline) does **not** clear the
      filter. It retries, or surfaces an error and leaves the selection intact.
      The distinction the code does not currently make.
- [ ] The filter reset is reported to the user by whatever mechanism this codebase
      already uses for it (`toastError` is available and in use elsewhere).
- [ ] A regression test that a failed subgraph fetch leaves
      `graphManager._scopeFilter` set. As shipped it does not.
- [ ] Verified in the browser, not only in a unit test: select a scope, break the
      request, and confirm both the picker and the promoted set are unchanged.

## Sequencing

Harmless until task-710 ships; a live hazard afterwards. If 710 lands first, land
this in the same change.
