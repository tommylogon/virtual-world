---
type: task
status: todo
area: docs
priority: medium
---

# task-672: Inspector Panels doc describes controls and node types that do not exist

**Filed:** 2026-10-02
**Related:** task-251, task-512

## Goal

Correct docs/virtualWorld/UI & Settings/Inspector Panels.md against measured behaviour. Three verified defects: (1) the Agent View section claims a 7-tab interface (Profile/Inventory/Behaviors/Memories/Lore/Agent/Relationships); actual is 4 tabs - Inventory, Bio, Images, Advanced. (2) The Item View section lists 7 actions; ALL_ACTIONS in item-view.js is 15 (examine take use open close eat drink read light activate equip unequip throw break drop). (3) The 'Inspector.js Dispatch' snippet switches on node types 'room' and 'door'; the live graph has 659 nodes with types area 207, way 361, item 34, logic_trigger 33, character 23, plan 1 - zero room, zero door. Real dispatch is inspector.js:67-89 on area/item/way/character/logic_trigger plus a by-name fallback; the snippet is also mis-cited as line 31 when showNode is line 50. Also record where Behaviors (conditional on the character having behaviours, agent-view.js:1143-1155) and World Lore (top menu templates/index.html:301 and inspector.js:42, not a tab) actually live, and that the Area View has 14 sections with zero input[type=range] so the documented environment sliders do not exist. Re-verify each count in a live browser before editing.

## Acceptance

- TODO
