---
type: bug
status: review
area: triggers
priority: high
wiki: "[[Triggers]]"
---

# bug-566: Load crashes when properties.triggers is an object

**Filed:** 2026-10-22
**Related:** 

## What

`WorldSerializer._migrate_triggers_from_nodes_to_properties` assumes `node.properties['triggers']` is a list. When the value is an object (the `{item: {trigger_type: ..., effects: {item: [...]}}}` shape an item-library round trip can produce), `setdefault('triggers', []).append(...)` raises `AttributeError: 'dict' object has no attribute 'append'` and the whole scenario load fails. Reproduced against the working copies of `data/scenarios/mansion.json` and `data/autosave.json`: 12 nodes carry the object shape, and 11 files under `data/library/items/` do too. The migration also returns early when a graph has zero `triggers` edges, so a property-only world is never normalised and the bad shape survives on disk.

## Why

The next autosave load boots an empty world. The migration is the only path that turns legacy data into the property store, so it has to tolerate every shape already on disk, including the wrapper objects an earlier library save produced.

## How

Add `normalize_trigger_entry` and `normalize_trigger_list` to `engine/triggers/effect_resolution.py` (the module that already owns trigger-property shape resolution). A normaliser unwraps single-key wrapper dicts around a definition, unwraps the same wrappers around `effects` and `trigger_type`, drops non-dict entries and returns a list. Call it over every node with a `triggers` property before the edge loop in the migration, remove the `if not trigger_edges: return` early exit, and append into the normalised list instead of `setdefault(...).append(...)`. Use the same helpers in `materialize_trigger` so it cannot re-create the object shape. Keep edge merge precedence unchanged.

## Browser UI and intended live verification

Intended UI home: Not applicable: this is a load-path defect, it fails before the UI renders.

Current availability: Not applicable: a scenario load either raises or it does not.

Why no browser UI: The failure is an AttributeError during deserialisation, with no interactive surface involved.

Alternative verification steps:
1. Run a Python load of data/scenarios/mansion.json and confirm no AttributeError
2. Start the app on port 4444 and confirm the world list is populated after a restart
3. Open the inspector for item_water_bottle and confirm its triggers section lists an entry

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Load the working copy of the duplicated scenario through the real deserialiser.
   - expected: no `AttributeError`, every object-shaped `triggers` value becomes a list.
   - observed: `WorldGraph.load_from_dict` plus `WorldSerializer._migrate_triggers_from_nodes_to_properties` on `data/scenarios/mansion.json` and `data/autosave.json`: 12 object-shaped nodes before, 0 non-list values after, 190 entries, 0 `triggers` edges remaining. The pre-fix run raised `AttributeError: 'dict' object has no attribute 'append'` on the same input.
2. Normalise the wrapped library shape directly.
   - expected: one definition with list effects and list `trigger_type`, empty condition string dropped.
   - observed: `normalize_trigger_list({"item": {...}})` returns one entry; `trigger_type` is `["on_use","on_drink"]`; both effects survive the double `{"item": {"item": [...]}}` wrapper; `conditions: ""` is removed.
3. Load a property-only node with no `triggers` edge.
   - expected: the property list is normalised anyway (the old early return skipped it).
   - observed: `test_property_only_node_is_normalised_without_any_triggers_edge` passes with zero edges in the graph.
4. Run the targeted regression tests.
   - expected: the migration and materialiser suites pass.
   - observed: `python -m pytest tests/test_trigger_migration.py tests/test_trigger_materialize.py` reports 13 passed. `tests/test_use_trigger_guard.py` adds 4 passing guard tests against the same store.

## Acceptance

- [x] Loading the working copy of data/scenarios/mansion.json no longer raises AttributeError on a dict-shaped triggers property
- [x] A node whose triggers value is {item: {trigger_type: [on_use], effects: {item: [{type: message, params: {}}]}}} normalises to one list entry with list-shaped trigger_type and effects
- [x] A property-only node is normalised even when the graph has no triggers edges
- [x] An object entry plus a legacy edge with the same id still dedupes to one definition
- [x] python -m pytest tests/test_trigger_migration.py passes

## Files

- `engine/serialization.py`
- `engine/triggers/effect_resolution.py`
- `engine/triggers/materialize.py`
- `tests/test_trigger_migration.py`
