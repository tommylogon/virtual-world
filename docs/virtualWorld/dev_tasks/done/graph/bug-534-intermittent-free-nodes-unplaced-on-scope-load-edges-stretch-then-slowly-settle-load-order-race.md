---
type: bug
status: done
area: graph
priority: high
---

# bug-534: Intermittent: free nodes unplaced on scope load, edges stretch then slowly settle (load-order race)

**Filed:** 2026-10-10
**Related:** 

## What

Reproduced intermittently: reloading/deep-woods sometimes yields total edge length ~6.38M px (nodes flung, edges stretched, settling slowly over >1.5s), other times ~328K px (placed, instant). Same scope, same code, non-deterministic. Root cause: on load the free content nodes (items etc.) are unplaced at the instant the solver starts, so physics flings them outward and edges stretch until it converges; painted areas/ways are seeded from cell so they snap in <1s. Fix: apply all positions (seed painted from cell, place content relative to its area) synchronously before the solver runs, so the load is deterministic and does not depend on winning a race.

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
