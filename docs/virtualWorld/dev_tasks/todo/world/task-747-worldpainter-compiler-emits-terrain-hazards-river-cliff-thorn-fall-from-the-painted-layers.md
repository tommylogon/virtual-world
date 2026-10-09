---
type: task
status: todo
area: world
priority: medium
---

# task-747: WorldPainter compiler emits terrain hazards (river, cliff, thorn, fall) from the painted layers

**Filed:** 2026-10-09
**Related:** task-496 task-525 task-529 task-745

## Goal

world_compile emits no triggers today; give it a hazards pass that reads data/worldpainter/hazards.json (task-745) and the painted layers and attaches a compact hazards:[...] descriptor to generated ways/areas (the engine expands it at load, so no trigger-node spam). Rules: a way crossing water with no bridge -> river; a way with requires: jump over water -> fall into the water; a _climb_step rising or falling -> cliff/fall, REPLACING the hard refusal task-525 chose where the author wants a check with a consequence; a thorn/bramble biome -> thorns. Severity from storey_delta (an 89-storey drop is lethal). Direction from the current layer, defaulting to the storey gradient. This also gives the on_fail hook its compiler side, and the hazard reader is what makes trigger-written condition tags (flooded) fire consequences. Depends on task-745 (layer+table) and task-746 (effect).

## Acceptance

- TODO
