---
type: task
status: todo
area: docs
priority: medium
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
