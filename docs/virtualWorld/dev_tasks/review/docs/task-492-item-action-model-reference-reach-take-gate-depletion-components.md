---
type: task
status: review
area: docs
priority: medium
---

# task-492: Item & action model reference (reach, take-gate, depletion, components)

**Filed:** 2026-09-23
**Related:** task-491

## Goal

Write the canonical technical page for the item/action model so these rules are discoverable without reading code: the actions list as the capability gate (take_item raises when 'take' absent, take_drop_actions.py:388-393), reach rules (engine/item_reach.py), depletion branching (generic use detaches; lit carried -> unlit + on_depleted; lit area -> burned out + removed; armor -> broken; food -> consume path), container nesting, and the planned part/component contract. Patterns to imitate: the item_reach.py module docstring and engine/item_actions.py facade docstring.

## Resolution (2026-10-02)

Written as `docs/virtualWorld/Items & Inventory/Item & Action Model.md`. Every
claim is anchored to the current code; the cited functions were verified to
exist (`engine/items/action_contract.py` `is_portable`/`is_part`/`parent_of`/
`portable_refusal` at :36/:48/:57/:70), and task-493's part/component contract is
**implemented**, not planned.

Two findings the page records that differ from the task's shorthand:

- The depletion branch is keyed on `is_part` (`engine/items/use_actions.py`),
  not on carried-vs-area: a non-part tears free from its placement, a part goes
  `unlit` and stays. The lit-in-area burnout and armor-break paths are separate
  handlers (`engine/tick_manager.py`, `engine/equipment.py`).
- Reach is a single rule in `engine/item_reach.py` consulted by use/use-on/eat/
  drink/place/toggle, and portability (`take` in `actions`) is now universal, not
  read only by `take`.

## Acceptance

- [x] One technical page documents actions-as-capability-gate (with the
      `take_item` example), the `item_reach` rules, every depletion branch,
      container nesting, and the part/component contract.
- [x] Claims anchored with `file:line` pointers; the part/component functions
      verified to exist.
- [x] Wikilinks in the page resolve (`python tools/doc_links.py --check` -> 0).
- [~] "Registered in the docs index": the vault has no separate note index to
      register into; reachability is via [[Items Overview]] / the Feature Map,
      not a registry edit.
