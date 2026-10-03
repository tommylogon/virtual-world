---
type: task
status: todo
area: gameplay
priority: medium
---

# task-681: Fumbling in the dark: a partial, unnamed result instead of a dead verb

**Filed:** 2026-10-04
**Related:** 

## Goal

In an area below 20 ambient light the panel now offers Feel around the shape (panel-side masking shipped), but engine/items/examine_actions.py line 143 raises a too-dark error, so the verb still returns nothing. Decide and implement the dark examine semantic: the natural one is a partial, unnamed impression (shape, texture, temperature) with no name revealed, rather than an error. Scope it so agents in the dark get the same partial read instead of being handed an exception string. This changes dark-area behaviour for the agent prompt path too, so it needs its own decision rather than a panel-side patch.

## Acceptance

- TODO
