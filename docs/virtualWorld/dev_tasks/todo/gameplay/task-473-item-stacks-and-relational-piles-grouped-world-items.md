---
type: task
status: todo
area: gameplay
priority: medium
---

# task-473: Item stacks and relational piles (grouped world items)

**Filed:** 2026-09-23
**Related:** task-471, task-470, task-424, task-9

## Goal

Group world items so a camp can hold a 50-use pile of raw meat or a herb pile of distinct herbs without hundreds of nodes. Two models: (a) HOMOGENEOUS STACK - one node carrying N uses; taking spawns one discrete item into the taker's inventory and decrements; placing a matching item (same key tags) adds a use and removes the node. (b) RELATIONAL PILE - a container holding distinct child items, so different herbs with different effects coexist and can be taken individually. Uses drive crafting/cooking (raw_meat + campfire -> cooked_meat, spending a use), reduce wild-item count, and keep soak search/forage output tidy. Needs: an explicit stack marker in the item schema, take-from-stack and merge-on-put in the item actions, capacity/weight interaction with containers, and save/load of uses.

## Acceptance

- TODO
