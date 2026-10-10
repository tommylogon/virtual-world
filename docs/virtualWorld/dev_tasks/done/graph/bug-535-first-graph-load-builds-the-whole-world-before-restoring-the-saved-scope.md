---
type: bug
status: done
area: graph
priority: high
---

# bug-535: First graph load builds the whole world before restoring the saved scope

**Filed:** 2026-10-10
**Related:** 

## What

On refresh the graph was built twice: GraphNetwork.init called GraphNetwork.loadGraphData() before graphManager._restoreScopeFilterOnce() ran, so the first load was always the whole world and the saved scope was applied a moment later. Fixed: restore the scope before the first load.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
