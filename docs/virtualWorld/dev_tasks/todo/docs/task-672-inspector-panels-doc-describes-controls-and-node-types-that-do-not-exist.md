---
type: task
status: todo
area: docs
priority: medium
wiki: "[[Feature Map]]"
---

# task-672: Inspector Panels doc describes controls and node types that do not exist

**Filed:** 2026-10-02
**Related:** task-251, task-512

## What

Correct docs/virtualWorld/UI & Settings/Inspector Panels.md against measured behaviour. Three verified defects: (1) the Agent View section claims a 7-tab interface (Profile/Inventory/Behaviors/Memories/Lore/Agent/Relationships); actual is 4 tabs - Inventory, Bio, Images, Advanced. (2) The Item View section lists 7 actions; ALL_ACTIONS in item-view.js is 15 (examine take use open close eat drink read light activate equip unequip throw break drop). (3) The 'Inspector.js Dispatch' snippet switches on node types 'room' and 'door'; the live graph has 659 nodes with types area 207, way 361, item 34, logic_trigger 33, character 23, plan 1 - zero room, zero door. Real dispatch is inspector.js:67-89 on area/item/way/character/logic_trigger plus a by-name fallback; the snippet is also mis-cited as line 31 when showNode is line 50. Also record where Behaviors (conditional on the character having behaviours, agent-view.js:1143-1155) and World Lore (top menu templates/index.html:301 and inspector.js:42, not a tab) actually live, and that the Area View has 14 sections with zero input[type=range] so the documented environment sliders do not exist. Re-verify each count in a live browser before editing.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: select an area, item, way, and character in the graph → inspect the right-hand Inspector and compare the visible tabs/actions with `UI & Settings/Inspector Panels.md`.

Current availability: the card records measured discrepancies: the character Inspector has 4 tabs (`Inventory`, `Bio`, `Images`, `Advanced`), the item Inspector exposes 15 actions, and the documentation dispatch example names obsolete `room`/`door` node types. The corrected page should match the live surfaces.

Live steps when available:
1. Open a character Inspector and count the visible tabs across the whole Inspector; open each tab and scroll to its bottom.
   - expected: the doc lists the actual four tabs and describes their controls without truncating the panel to a partial viewport.
2. Open an item Inspector and enumerate the available actions by interacting with its action menu; count all visible actions.
   - expected: the doc lists all 15 current item actions and their real names.
3. Select area, way, item, and character nodes; inspect the Inspector and the graph node `type` values in `/api/state`.
   - expected: the doc's dispatch example uses the graph's actual node types and matches the renderer reached for each node.
4. Re-read the corrected page while repeating the interactions above.
   - expected: every described tab/action/type corresponds to a visible control or returned node value; no obsolete `room` or `door` renderer is presented as current.

This section is not a claim that the documentation is corrected or freshly browser-verified today.
