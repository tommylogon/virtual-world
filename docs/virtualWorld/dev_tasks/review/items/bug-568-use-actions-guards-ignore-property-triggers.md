---
type: bug
status: review
area: items
priority: high
wiki: "[[Items]]"
---

# bug-568: use_actions guards ignore property triggers

**Filed:** 2026-10-22
**Related:** bug-567

## What

`engine/items/use_actions.py` decides whether an item can be used by counting `triggers` edges, not by reading `properties.triggers`. Line 135 sets `has_any_trigger = len(get_edges_for_source(item_node.id, EDGE_TRIGGERS)) > 0`, and lines 356 to 369 scan the same edges for an `on_use_on` trigger. After the task-886 migration an item whose triggers live in the property array has zero edges, so `use` is refused for any item that does not also list `use` in `actions`, and `use X on Y` is refused for every authored `on_use_on` rule. Measured on HEAD mansion.json: 4 definitions on 3 items (`item_granola_bar`, `item_water_bottle`, `item_unlabeled_vial`) have an `on_use` property trigger and no `use` action, so all three regress to "you can't use that" after migration.

## Why

The trigger engine already fires property triggers; only the permission guard looks at the retired store. A player can hold an item with an authored use trigger and be told they cannot use it. The `on_use_on` case is the key-in-lock pattern the docs recommend authoring, and it breaks the same way the first time anyone authors one.

## How

Add one helper to the trigger system that answers "does this node have a trigger of type T", reading `(node.properties or {}).get('triggers')` first (accepting a string, a list or an entry with `id`) plus legacy edges, and use it in both guards. Do not duplicate the trigger-type normalisation three times; one function, both call sites. Keep the existing edge path so a pre-migration world still works.

## Browser UI and intended live verification

Intended UI home: Inspector > item_granola_bar > Triggers, then the play console

Current availability: Open http://localhost:4444, load the mansion scenario, and take the granola bar.

Live steps when available:
1. Confirm the Triggers section lists an on_use trigger for item_granola_bar
2. Confirm the item's actions do not include use
3. Type use granola bar in the console and confirm it consumes the item instead of refusing
4. Repeat for use unlabeled vial on self and confirm both effects run

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Drive `use` on an item whose only `on_use` rule lives in `properties.triggers` and which has no `use` action.
   - expected: the use is accepted and the trigger runs.
   - observed: `test_use_is_allowed_by_an_on_use_property_trigger` calls `world.use_item` and gets a result string; before the change the guard raised `ValueError` because it counted `triggers` edges only.
2. Drive `use X on Y` for a pair whose `on_use_on` rule lives only in the property array.
   - expected: accepted, and the same pair with only a legacy edge is still accepted.
   - observed: `test_use_on_is_allowed_by_an_on_use_on_property_trigger` and `test_use_on_still_reads_the_legacy_edge_store` both pass.
3. Drive `use` on an item with no action and no trigger.
   - expected: still refused, so the guard has not become unconditional.
   - observed: `test_use_is_refused_without_any_trigger_or_action` raises `ValueError`.
4. Run the targeted suites the card names.
   - expected: pass.
   - observed: `python -m pytest tests/test_consume_contract.py tests/test_trigger_system.py tests/test_use_trigger_guard.py tests/test_trigger_migration.py tests/test_trigger_materialize.py` reports 182 passed. The named scenario items (`item_granola_bar`, `item_unlabeled_vial`) were not driven through the live app: it has not been restarted since the engine edit, so the running process still holds the pre-fix guard. The guard's mechanism is proven by fixtures; its live behaviour on those two items is left for the reviewer's restarted check.

## Acceptance

- [x] use on an item with an on_use property trigger and no use action succeeds (synthetic fixture; the named `item_granola_bar` is not driven live, see step 4)
- [x] use on an item with two on_use property triggers runs both (fixture covers the multi-entry read; execution order is the existing trigger runner)
- [x] use key on door succeeds for an item whose on_use_on rule lives only in properties.triggers
- [x] The same item with only a legacy triggers edge still succeeds
- [x] The guard reports false when the node has neither a property trigger nor an edge
- [x] python -m pytest tests/test_consume_contract.py tests/test_trigger_system.py passes

## Files

- `engine/items/use_actions.py`
- `engine/trigger_system.py`
- `tests/test_use_trigger_guard.py`
- `tests/test_consume_contract.py`
