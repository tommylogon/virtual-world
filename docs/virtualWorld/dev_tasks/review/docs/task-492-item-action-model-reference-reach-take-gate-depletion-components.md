---
type: task
status: review
area: docs
priority: medium
---

# task-492: Item & action model reference (reach, take-gate, depletion, components)

**Filed:** 2026-09-23
**Related:** task-491

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — this card's deliverable is the canonical technical reference for item actions, reach, depletion, containers, and component contracts; it does not add a player-facing screen.

Current availability: the page documents the `take` capability gate, `item_reach`, depletion branches, containment nesting, and the planned part/component contract. Its link check is recorded as passing; “registered in docs index” has no separate index per the card.

Why no browser UI: browser actions can demonstrate examples but cannot replace or exhaustively verify the technical rules/reference page this card owns.

Alternative verification steps:
1. Read the completed item/action reference and trace each listed rule to the cited engine function and example.
   - expected: actions-as-capability-gate, reach, all depletion branches, nesting, and component contract each have a current source and a concrete author/player consequence.
2. Follow the page's item/way wikilinks and run `python tools/doc_links.py --check`.
   - expected: every link resolves; the page does not claim an unimplemented component operation as shipped.
3. Compare the depletion examples with the item/action behavior notes after code changes.
   - expected: generic use, carried/area light, armor, and food branches remain distinct and accurately described.

This section is not a claim that a new browser UI exists or is needed for this documentation task.
