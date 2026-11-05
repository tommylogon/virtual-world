---
type: task
status: todo
area: docs
priority: medium
wiki: "[[World Building/Ways]]"
---

# task-781: way_properties.py omits entry_phrase and requires_item, and --check does not validate values

**Filed:** 2026-10-11
**Related:** 

## What

tools/way_properties.py declares the way-property set and its page calls itself the single source of truth, but the engine reads two properties it does not declare: entry_phrase (area_description.py:696, world_compile.py:876) and requires_item (movement.py:507). Separately, way_property_index.py --check only compares the hand-maintained spawn lists, never a property values tuple, so current_state has drifted: it lists broken and omits hidden, and counts see_through as a state when the code treats it as a property override (barriers.py declared_state docstring says never see_through); max_size omits the accepted none. Add the two properties and validate values against engine/barriers.py WAY_STATES and the size tiers.

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

## Browser UI and intended live verification

Intended UI home: Not applicable — this task verifies the complete way-property vocabulary and its generated index/checker. A single Inspector view cannot prove that the declared property set is exhaustive or that every value tuple matches engine readers.

Current availability: the card identifies omitted `entry_phrase` and `requires_item`, and a drifted `current_state` list (`broken` listed, `hidden` omitted, `see_through` misclassified). The declaration/checker correction is planned.

Why no browser UI: the acceptance is exhaustive agreement between `tools/way_properties.py`, engine readers, allowed values, and generated reference output; this is a tooling contract rather than a browser behavior change.

Alternative verification steps:
1. Run `python tools/way_property_index.py --report` and inspect the complete property count and declarations from `tools/way_properties.py`.
   - expected: `entry_phrase` and `requires_item` are included; `hidden` is represented in the correct state set; `broken` and `see_through` are classified according to their engine semantics.
2. Run `python tools/way_property_index.py --check` after changing a declared value tuple without updating its generated page/check data.
   - expected: the check fails on that exact drift, then passes after the declaration and generated index agree.
3. Search the Way Inspector property editor for one example each of `entry_phrase`, `requires_item`, and a hidden state after the source contract is corrected.
   - expected: authoring controls expose the declared values the engine reads; the editor does not offer an undeclared substitute.

This section is not a claim that planned tooling checks are implemented or passing today.
