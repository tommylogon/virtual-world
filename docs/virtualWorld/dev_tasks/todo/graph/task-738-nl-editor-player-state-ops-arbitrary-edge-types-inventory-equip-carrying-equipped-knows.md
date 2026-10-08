---
type: task
status: todo
area: graph
priority: high
---

# task-738: NL editor: Player-state ops + arbitrary edge types (inventory, equip, carrying/equipped/knows)

**Filed:** 2026-10-08
**Related:** 

## Goal

The editor's op model is graph-shaped; it cannot touch Player state. Add staged ops for inventory add/remove, equip/unequip, and the real edge vocabulary (carrying, equipped, knows, owns, faction) instead of the spatial-only in/on/under/behind/beside/at enum. Route player_* ops to routes/player_ops.py on Apply. See docs/design/nl-editor-full-authoring.md.

## Acceptance

- TODO
