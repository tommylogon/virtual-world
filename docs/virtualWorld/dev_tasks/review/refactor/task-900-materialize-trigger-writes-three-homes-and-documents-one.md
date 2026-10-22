---
type: task
status: review
area: refactor
priority: medium
wiki: "[[Triggers]]"
---

# task-900: materialize_trigger writes three homes and documents one

**Filed:** 2026-10-22
**Related:** bug-567

<!-- deps:start -->
**Related:** [[bug-567-trigger-graph-editor-reads-and-writes-the-legacy-edge-store]]
<!-- deps:end -->

## What

`materialize_trigger` writes each definition to three places: the owner's `properties.triggers` array, a `logic_trigger` node, and a `triggers` edge (engine/triggers/materialize.py lines 134 to 151). Its module docstring argues for the node plus edge because "the rest of the engine reads the edge first", and claims "No parallel trigger format is introduced", without mentioning the property array it also writes. The module therefore re-creates the representation task-886 removed on every materialisation, which is why task-895 cannot retire it.

## Why

The legacy node and edge are dead weight that the validator, the inspector and every store-boundary fix has to dedupe around. A docstring that describes a contract the code no longer follows is worse than no docstring, because the next reader trusts it. The generated schema page and the task tree both point at this module.

## How

Decide the direction with task-895 rather than inventing a third path. In this pass, correct the module docstring and the `materialize_trigger` docstring to state all three writes, name the property array as the authoritative store, describe the node and edge as compatibility output until task-895 lands, and remove the claim that no parallel format exists. Add the task reference. Do not change runtime behaviour in this card; the behaviour change belongs to task-895.

## Browser UI and intended live verification

Intended UI home: Not applicable: this card changes documentation only.

Current availability: Not applicable: no runtime behaviour changes.

Why no browser UI: The deliverable is docstring accuracy in a Python module, verified by reading the file and running its existing test.

Alternative verification steps:
1. Read the module docstring and confirm it matches the three writes in materialize_trigger
2. Run python -m pytest tests/test_trigger_materialize.py

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Read the module docstring and compare it to the writes in `materialize_trigger`.
   - expected: all three writes named, the property array marked authoritative, the node and edge marked compatibility output pending task-895.
   - observed: the module docstring names `properties['triggers']` as the authoritative store and lists the `logic_trigger` node and the `triggers` edge as compatibility output written for the pre-task-886 readers, with the task-895 reference. The "no parallel trigger format" claim is gone.
2. Read the `materialize_trigger` docstring.
   - expected: it states the same three writes and why the extras exist.
   - observed: it names the property write as the authoritative one and the node plus edge as the legacy pair kept until task-895.
3. Run the module's test.
   - expected: unchanged pass.
   - observed: `python -m pytest tests/test_trigger_materialize.py` reports 7 passed.

## Acceptance

- [x] The module docstring names properties.triggers as the authoritative store
- [x] The materialize_trigger docstring says it also creates a node and an edge, and why
- [x] No docstring claims that a single store is written
- [x] python -m pytest tests/test_trigger_materialize.py passes unchanged

## Files

- `engine/triggers/materialize.py`
