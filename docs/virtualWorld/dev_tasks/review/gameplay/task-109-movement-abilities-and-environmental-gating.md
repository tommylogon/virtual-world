---
related: [task-230]
area: gameplay
wiki: "[[Items & Inventory/Items Overview]]"
blocked_by: [task-110]
type: task
status: review
priority: medium
---

# Task 109: Movement Abilities and Environmental Gating

**Status**: Todo
**Priority**: Low (design phase)
**Filed**: 2026-07-26
**Depends on**: task-110 (Stat Modifiers system — item-granted abilities)

---

<!-- deps:start -->
**Blocked by:** [[task-110-see-through-windows]]
**Related:** [[task-230-outdoor-lighting-time-of-day]]
<!-- deps:end -->

## What

Design question deferred from the Stat Modifiers brainstorming session (2026-07-26):

How should item-granted movement abilities (fly, glide, dive) interact with the room/exit/navigation system?

### The question

Items like jetpacks (fly), wingsuits (glide), and scuba gear (dive) grant the player new movement capabilities. How should these work with the existing room/exit graph?

### Possible models

1. **Traversal-enabling** — Opens new exits/paths that only exist when the item is active (e.g., jetpack reveals a "fly up to cliff ledge" exit)

2. **Environment-gating** — Lets the player survive/enter areas with hostile environments (scuba → underwater areas, EVA suit → vacuum)

3. **Fast travel / room skipping** — Allows moving from A to C without passing through B (fly over intermediate areas)

4. **Existing exit filtering** — Some exits are already conditionally visible (hidden ways, skill checks). Could movement abilities just be another condition gate on exits?

### Related concepts

- Windows / see-through connections (task-?? — not yet filed)
- Light spill through open ways (task-230)
- Skill-check-gated traversal (triggers on ways)
- Room environment system (temperature, air, light)

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
