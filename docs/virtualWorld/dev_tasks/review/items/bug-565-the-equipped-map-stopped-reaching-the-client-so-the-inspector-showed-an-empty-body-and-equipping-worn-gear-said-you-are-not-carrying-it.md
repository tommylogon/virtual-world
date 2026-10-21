---
type: bug
status: review
area: items
priority: high
wiki: "[[Ways]]"
related: [task-654, task-450, task-744, bug-524]
---

# bug-565: The equipped map stopped reaching the client, so the inspector showed an empty body and equipping worn gear said you are not carrying it

**Filed:** 2026-10-21
**Related:** task-654, task-450, task-744, bug-524

<!-- deps:start -->
**Related:** [[task-654-player-equipped-and-the-equipment-graph-edges-are-two-sources-of-truth-the-api-writes-only-the-first]], [[task-450-duplicate-item-instances-and-carry-equipped-invariant]], [[task-744-equipment-and-body-one-edge-truth-for-worn-gear-layered-coverage-body-marks-body-centric-ui]], [[bug-524-character-personality-and-appearance-descriptions-are-dropped-from-api-state-so-the-inspector-shows-undefined-blank-and-edits-look-unsaved]]
<!-- deps:end -->

## What

The character inspector showed an empty body and counted worn gear as carried, and equipping anything the character was already wearing answered "You aren't carrying 'X'." instead of "You're already wearing the X."

Three defects, one report (miki in the mansion scenario):

1. **`GET /api/state` no longer publishes `player.equipped`.** The lite-mode refactor (ddf032ff) rebuilt `_serialize_player` in `engine/serialization.py` and dropped `"equipped": dict(p.equipped)` together with `"skills": p.skills`. Every front-end reader of the map - the paperdoll (`static/js/inspector/paperdoll-view.ts:305`), the inventory list (`static/js/inspector/agent-view.ts:1032`), the equip picker (`paperdoll-view.ts:652`), the equipment narrative (`agent-view.ts:1518`), the auto-dress modal - then saw an empty map. The worn record itself was fine: the graph held 14 `equipped` edges for miki and `_sync_equipped_from_graph` rebuilt the map from them. The map simply stopped being published.

   Measured on the live app before the fix: `worldState.players['miki'].equipped` was `undefined`, all 13 paperdoll slots rendered `-`, and the inventory header read `(19 carried, 1 container)` for a character carrying 5 and wearing 14. After the fix: `(5 carried, 14 worn, 1 container)`, with the paperdoll showing NECK=syringe necklace, TORSO=grey-black striped hoodie, LEGS=Black Short Shorts, R.HELD=phone.

2. **`EquipmentSystem.equip_item` asked only the `carrying` edges "do you have this?"** A worn item is not carried, so equipping what the character was already wearing raised `You aren't carrying 'X'.` at `engine/equipment.py:142` and the correct `You're already wearing the X.` check at line 154 could never run. Worn counts as carried; the refusal and its reason are unchanged.

3. **The `+ Equip from Inventory` button could never offer anything.** `showEquipPicker` filters `equip_slots.includes(slot)` with `slot = 'all'`, and no item declares an `all` slot, so the button only ever toasted "No items in inventory that can be equipped to all."

A fourth defect sat underneath: **the loader wrote a `connection` edge for worn gear.** `engine/serialization.py` (the `equipped` block loop) created `type=EDGE_CONNECTION` - a way between two areas - where it should have created `EDGE_EQUIPPED`. The constant was swapped during the task-7 modularisation refactor (the `EDGE_EQUIPPED` import was dropped from the module's import line). Consequences: worn gear was invisible to every equipment reader that looks at `EDGE_EQUIPPED` (defense, insulation, resistance, coverage), and every worn item in every saved file grew a second, wrong-typed edge.

Measured: 98 `connection` edges pointing at a character across 6 scenario files, 95 of them duplicating a real `equipped` edge and 3 (`kraktooth_goblin_camp.json`: james's tunic, trousers and hiking boots) being the only record of that worn gear at all.

## Why

The inspector is where a character is read. A body that renders empty while the graph says otherwise is not a display nit - it is the surface telling the author the wrong thing, and it is what the report came in as.

The dropped payload key is the second half of the same split that task-654 closed on the write side: the edges are the load-bearing store, the dict is the read cache, and the API has to publish the cache. The `equipped` key was in the payload from the first release until ddf032ff removed it in passing, with nothing on the read side changed to match.

The `connection` edge type is not cosmetic either. `kraktooth_goblin_camp.json` recorded james's tunic, trousers and boots only as connections, so his clothing contributed no defense, no insulation and no body coverage to the camp - the file said he was dressed and the simulation said he was naked.

## How

1. `engine/serialization.py` `_serialize_player`: publish `"equipped": dict(p.equipped)` and `"skills": dict(p.skills)` again, next to the other runtime state. The map is the projection of the `EDGE_EQUIPPED` edges, and the live payload is where the UI reads it.
2. `engine/serialization.py` `to_scenario_dict`: `pdata.pop("equipped", None)`. A saved world is graph-only (task-222); the equipped edges carry the slot, so the players block must not carry a second copy of the same fact or the loader would rebuild the edges from it.
3. `engine/serialization.py` load path: write `EDGE_EQUIPPED` instead of `EDGE_CONNECTION` for the `equipped` block, and call `graph.normalize_item_hold_state()` afterwards so an item that is both carried and equipped ends up in one state (task-450: equipped wins).
4. `engine/equipment.py` `equip_item`: the "is this yours" check reads `EDGE_CARRYING` **and** `EDGE_EQUIPPED`, so a worn item reaches the "You're already wearing the X." refusal instead of the "not carrying" one.
5. `static/js/inspector/paperdoll-view.ts` `showEquipPicker`: `slot === 'all'` means any slot the item declares, so the filter is `slots.length > 0` instead of `slots.includes('all')`; the title reads "Equip to any slot".
6. Data: in the 6 scenario files, delete the `connection` edges that duplicate a real `equipped` edge, and retype the 3 that are the only record of worn gear into `equipped` edges (they carry the `slot` property). All six files stay in the canonical `json.dump(..., indent=2, ensure_ascii=False)` format - a load/dump round trip is byte-identical, so the diff is only the edges.

## Browser UI and intended live verification

Intended UI home: Inspector > an agent (miki) > Inventory tab, and the paperdoll figure above it.

Current availability: Every character in every scenario.

Live steps when available:
1. 1. Open the mansion scenario, select miki in the agent list, open the Inventory tab.
2. 2. Read the paperdoll: the worn items must be in their slots (NECK, TORSO, LEGS, R.HELD), not all dashes.
3. 3. Read the inventory header: it must read (5 carried, 14 worn, 1 container), not (19 carried, 1 container).
4. 4. Click the Equip button on a worn item in the inventory list, or type `wear black high-cut thong` in the command line: the answer must be 'You're already wearing the black high-cut thong.', not 'You aren't carrying ...'.
5. 5. Click `+ Equip from Inventory`: the picker must open and list the carried items that declare a wearable slot.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Load the mansion scenario, open miki in the inspector, Inventory tab.
   - expected: the paperdoll shows the worn items (NECK=syringe necklace, TORSO=grey-black striped hoodie, LEGS=Black Short Shorts, R.HELD=phone) and the header reads `(5 carried, 14 worn, 1 container)`.
   - observed: after the fix, on `VW_PORT=4455` with `data/scenarios/mansion.json` loaded: paperdoll slots NECK=syringe necklace, TORSO=grey-black striped hoodie, LEGS=Black Short Shorts, R.HELD=phone, 9 slots still empty; header `INVENTORY (5 carried, 14 worn, 1 container)`. Before the fix, all 13 slots read `-` and the header read `(19 carried, 1 container)`.
2. Wear something the character already wears.
   - expected: "You're already wearing the black high-cut thong."
   - observed: in the browser, `runAction('wear black high-cut thong', 'miki')` -> event stream `[Tick 4 | 08:00] World You're already wearing the black high-cut thong.` Before the fix the same call answered "You aren't carrying 'black high-cut thong'."
3. Open `+ Equip from Inventory`.
   - expected: a modal listing the carried items that declare a wearable slot.
   - observed: before the fix the button only toasted "No items in inventory that can be equipped to all."; after the fix the modal opens ("Equip to any slot") and lists the items that declare a slot.
4. `python -m pytest tests/test_equipment_payload.py`
   - expected: 10 passed.
   - observed: 10 passed. 8 of the 10 fail against the pre-fix engine (the payload tests KeyError on 'equipped', the wear test gets the 'not carrying' message, the loader test finds no equipped edge); the other 2 are the controls that must keep passing.
5. The equipment, save/load and library suites.
   - expected: green.
   - observed: `python -m pytest tests/test_equipment_api_edges.py tests/test_equipment_system.py tests/test_equipment_payload.py tests/test_saveload.py tests/test_serialization.py tests/test_save_schema.py tests/test_scenario_graph_only.py tests/test_scenario_commit.py tests/test_scenario_diff.py tests/test_scenarios.py tests/test_character_loadout_refresh.py tests/test_character_loadout_check.py tests/test_library_character_import.py tests/test_library_refresh.py tests/test_auto_dress.py tests/test_armor_wear.py tests/test_edge_known.py` -> 238 passed.
6. The one test whose assertion changed.
   - expected: the refusal stays, the message names the real reason.
   - observed: `tests/test_equipment_system.py::test_equip_same_item_twice_refused` asserted the old message ("You aren't carrying") for the same refusal. The refusal is unchanged; the assertion now names the accurate reason ("already wearing"), because the check that produces that message is now reachable.
7. The scenario data integrity file.
   - expected: no new failures.
   - observed: 8 failures and 13 errors are the pre-existing baseline (identical names on a stashed tree). One extra failure, `test_goblins_have_high_metabolism_or_a_documented_reason`, is NOT from this change: it reads `payload["players"]` for the goblin tag, and the in-flight migration has moved the tags and traits to the character nodes (`player_Arix` and 9 others carry `high_metabolism` there). Re-running it with the 7 `connection` edges restored fails identically, so the edge cleanup is not the cause.

## Acceptance

- [x] `GET /api/state` publishes `player.equipped` and `player.skills` for every character.
- [x] The published map matches the `EDGE_EQUIPPED` edges slot for slot.
- [x] A worn item is refused with "You're already wearing the X.", and a packed item still equips.
- [x] `+ Equip from Inventory` opens a picker that lists the carried items that declare a wearable slot.
- [x] The loader creates `EDGE_EQUIPPED` for an `equipped` block, and never a `connection` edge for worn gear.
- [x] A saved world carries no second copy of the equipped map in the players block.
- [x] No `connection` edge points at a character in any scenario file; the 3 that were the only record of worn gear became `equipped` edges.
- [x] Regression tests in `tests/test_equipment_payload.py` (10 tests).

## Files

- `engine/serialization.py` - publish `equipped` + `skills` in `_serialize_player`, pop `equipped` in `to_scenario_dict`, write `EDGE_EQUIPPED` in the load path, `normalize_item_hold_state()` after it.
- `engine/equipment.py` - `equip_item`: worn counts as carried.
- `static/js/inspector/paperdoll-view.ts` (+ emitted `.js`) - `showEquipPicker`: the `all` slot means any declared slot.
- `tests/test_equipment_payload.py` - new, 10 tests.
- `tests/test_equipment_system.py` - the second-equip assertion now names the real reason.
- `data/scenarios/mansion.json`, `kraktooth_goblin_camp.json`, `labs.json`, `taco_bell_date.json`, `world_template.json`, `The Valerious Case.json` - the duplicate `connection` edges removed, the 3 lonely ones retyped.
