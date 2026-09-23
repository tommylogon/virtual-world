---
type: task
status: todo
area: items
priority: medium
---

# task-493: Item part/component model for devices

**Filed:** 2026-09-23
**Related:** task-299

## Goal

Define and implement the 'device assembled from items' model agreed in the task-299 discussion: parts are child items of a parent (non-takeable by default by omitting 'take' from actions, so no new edge type is required), each part carries its own triggers/state/uses, charge is the generic 'uses' rather than a new 'power' property, and depletion uses the existing patterns (carried lit -> unlit + on_depleted; detach/break per part). Cover addressing/naming, and align prompt visibility with engine/item_reach (single-level, state-blind today vs any-depth, state-gated). No per-item named verbs.

## Acceptance

- A device is a parent item with child part items; a part with no `take` in `actions` cannot be taken/dropped/stolen/put (tested), while staying reachable/usable via `item_reach`.
- Charge uses the generic `uses`; no new per-device-type property (no `power`/`charge` field) is added to the base item.
- Part depletion has an explicit, chosen semantic (e.g. carried lit → `unlit` + `on_depleted`) and does not silently detach unless intended (tested).
- Prompt visibility agrees with `item_reach`: depth and container-state gating match (fix the single-level, state-blind client listing).
- A worked example (e.g. a phone with a battery part) is authored in the library and exercised in a test.
