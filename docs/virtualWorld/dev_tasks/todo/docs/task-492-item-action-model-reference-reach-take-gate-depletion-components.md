---
type: task
status: todo
area: docs
priority: medium
---

# task-492: Item & action model reference (reach, take-gate, depletion, components)

**Filed:** 2026-09-23
**Related:** task-491

## Goal

Write the canonical technical page for the item/action model so these rules are discoverable without reading code: the actions list as the capability gate (take_item raises when 'take' absent, take_drop_actions.py:388-393), reach rules (engine/item_reach.py), depletion branching (generic use detaches; lit carried -> unlit + on_depleted; lit area -> burned out + removed; armor -> broken; food -> consume path), container nesting, and the planned part/component contract. Patterns to imitate: the item_reach.py module docstring and engine/item_actions.py facade docstring.

## Acceptance

- One technical page under `docs/virtualWorld/` documents: actions-as-capability-gate (with the `take_item` example), the `item_reach` rules, every depletion branch, container nesting, and the part/component contract (once task-493 lands).
- It is registered in the docs index.
- Claims are anchored with `file:line` pointers and covered by a linked test where one exists.
