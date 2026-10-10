---
type: task
status: done
area: ui
priority: low
---

# task-770: Rename the Levels layout to Hierarchical and scope its use

**Filed:** 2026-10-10
**Related:** 

## What

Rename the Levels layout to Hierarchical and decide its role. vis hierarchical assumes a tree or DAG, but the world graph has cycles and mixed edge types. Either scope it to a containment-only view or remove it.

## Why

TODO

## How

TODO

## Steps to verify

- expected: the layout control names the layout Hierarchical, not Levels.
- observed (2026-10-10 live): #btn-layout-mode text is '🌳 Hierarchical' (data-layout=levels).

## Acceptance

- [x] The layout control and every policy string read 'Hierarchical' (verified: #btn-layout-mode = '🌳 Hierarchical', GraphPhysics.reason = 'Hierarchical owns node positions...').

## Files

- TODO
