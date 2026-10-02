---
type: task
status: review
area: characters
priority: high
---

# task-654: player.equipped and the equipment graph edges are two sources of truth; the API writes only the first

**Filed:** 2026-09-30
**Related:** 

## Goal

POST /api/players/<name> with {equipped: {...}} returns 200 and updates player.equipped, but creates NO EDGE_CARRYING/EDGE_EQUIPPED edge. Everything that actually reads equipment reads the EDGES: engine/combat.py _best_weapon_node (weapon selection) and engine/equipment_bonuses.get_equipment_nodes (defense, insulation, resistances). So a client that equips a character through the API gets a silent no-op in combat and in damage reduction -- equipped items appear in the inspector and do nothing. Found while live-verifying task-607, and then confirmed properly by taking a weapon rather than writing the field.

**Confirmed by driving the app.** `take Rusty Hatchet` -> "You take the rusty
hatchet with your hand right." -> the next attacks read *"attacks Kiala with Rusty
Hatchet!"*, so `take` writes the real slot AND the graph edge. Writing the field
instead leaves the attacker fighting bare-handed. The two states are visible side
by side on the same character:

    equipped: { "hand":        ["item_spear"],           <- API write: inert
               "hand_right":  ["item_rusty_hatchet"] }  <- take: live

**There IS an equipment UI, and I was wrong to say otherwise.** I first claimed
"no equipment UI exists" from a single screenshot of the inspector, which was
scrolled to the middle. Re-checked by enumerating the whole panel: it has **26
sections**, and two of them are exactly this:

    ðŸ§  Equipment      âš”ï¸ 1dd+8 piercing  âš–ï¸ Carry Load: ...
    ðŸŽ’ Inventory      (0 carried, 1 worn) Nothing carri...

So the equipped hatchet is visible, and the inventory count ("0 carried, 1 worn")
correctly reflects what `take` did. The equipment surface exists and works; the
API write is the broken path, not the feature.

The retraction is recorded because it is the same error as Â§61, Â§20, Â§626, Â§639
and task-620: judging a surface from one viewport instead of walking it. I made
it again immediately after writing the rule into `AGENTS.md` and being told about
it three times.

**Separate observation, spotted in the same pass:** the Equipment section renders
the hatchet's damage as **`1dd+8 piercing`** -- a doubled `d`. Weapon damage is
`1d6` in the data, so `1dd+8` is either a display bug or a doubled parser token
in the readout. Worth its own look, and it is the kind of thing only visible by
reading the panel.

**Also confirmed while checking: the declared slot and the used slot disagree.**
All four weapon items in this world declare `equip_slots: ["hand"]`. `take`
equips into **`hand_right`**. So the vocabulary an author writes is not the
vocabulary the game uses, which is why a `hand` write is inert and a `hand_right`
one is not. Either the API writes the edges too, or the two fields are reconciled somewhere, or player.equipped should not be writable directly. Same class as task-292 (apron declares equip_slots but has no equip action) and task-632 (a field that serializes but is never populated).

**Second reproduction, from the other direction (2026-10-01, task-660
verification).** This task says the API writes `player.equipped` without the
edges. The inverse also holds: **deleting a graph node leaves `player.equipped`
pointing at it.** A duplicated item node was removed with
`DELETE /api/graph/node/heavy_black_boots_061fbea7` → `200 {"status":"success"}`,
and immediately afterwards:

    equipped: { "feet": ["heavy_black_boots", "heavy_black_boots_061fbea7"], ... }

The stale id survived the node. Nothing reconciles the two structures in either
direction, so they diverge silently and the field keeps pointing at something
that no longer exists.

Impact is bounded but real. `is_exposed` (`engine/body_parts.py:260`) does
`graph.get_node(outer_id)` and `continue`s on `None`, so a dangling id degrades
to "treated as uncovered" rather than raising — which means it changes
coverage maths silently. The equipment readout counts it as worn. The only
recovery is the manual write this task is already complaining about, i.e. the
API route that creates the original divergence.

Strengthens the case in the paragraph above: neither structure should be
independently writable. Whichever is authoritative, the other should be derived
or reconciled on change.

## Acceptance

- [x] An `equipped` payload written through the API updates the graph edges as
      well as the dict — every real item gets an `equipped` edge (item →
      character) carrying its `slot`, and the `carrying` edge is dropped.
- [x] The same writer returns items a later payload no longer claims to
      `carrying`, so nothing is orphaned out of the graph.
- [x] Slot markers (`__multi_slot_<id>`) stay dict-side and never become edges.
- [x] Entries that resolve to no item node are **reported**, not silently
      dropped.
- [x] The payload is normalised against the canonical slot set, so a partial
      write no longer deletes the slots it did not mention.
- [x] The inverse direction holds: deleting an item node prunes the dangling id
      from every character's `equipped`, instead of leaving the readout counting
      a worn item that no longer exists and `is_exposed` reading a missing node
      as "uncovered".
- [x] Both real readers — `combat._best_weapon_node` and
      `equipment_bonuses.get_equipment_nodes` — agree with the inspector, and an
      API write and a real `take` leave the same shape.
- [x] Regression tests in `tests/test_equipment_api_edges.py` (12 tests).

## Implementation — 2026-10-02 (WT-characters-engine)

### Files

- `engine/equipment.py` — `EquipmentSystem.set_equipped_payload` (the single
  writer) and `prune_dangling_equipped` / `prune_all_dangling_equipped`.
- `virtual_world_engine.py` — `set_equipped_payload` delegate.
- `routes/player_ops.py` — `POST /api/players/<name>` and
  `POST /api/players/import` route through the writer.
- `routes/library_ops.py` — the library character loader does too.
- `routes/graph_ops.py` — `DELETE /api/graph/node/<id>` prunes an item's
  dangling `equipped` ids.
- `tests/test_equipment_api_edges.py` — **new**, 12 tests.

### The decisions

1. **The edges are the load-bearing store and the dict is the read cache**, so
   the writer goes dict + edges and the existing `_sync_equipped_from_graph` is
   the authority check. That reuses the seam already in the module rather than
   adding a reconciliation path beside it.
2. **Not `take_item`'s auto-equip logic.** `take` is a *verb* with hands, a
   two-handed rule and a stow-the-previous-item rule; an API payload has none of
   that. Reusing the slot assignment would have made a data write depend on
   which hand happened to be free.
3. **The payload wins wholesale.** An `equipped` mapping is a complete statement
   of what is worn, so slots it omits are emptied and their items return to
   `carrying`. Partial-merge semantics were rejected because the previous state
   of a slot is exactly what a payload cannot describe.
4. **Pruning is on delete, not on read.** `is_exposed` degrades a missing node to
   "uncovered", so the dangling id was silently changing coverage maths. Fixing
   it at the only moment it can be introduced keeps the readers unchanged.

### A second bug found while closing this

The library loader assigned `player.equipped` twice: once raw at the top, then
again after resolving names to node ids. The first was dead. The second ran on
`cdata.get('equipped') or {}`, so **a library character with no `equipped` block
had its equipment cleared on import** — the raw assignment above it had been
preserving it up to that point. Both are gone; the resolved payload now goes
through the writer.

### The declared-slot / used-slot disagreement

Left as-is and **not** a bug in the engine. The library's weapon items declare
`hand_right` (6 of them), matching `EquipmentSystem.EQUIP_SLOTS` and `take`'s
hand logic; only the scenario the report was written against used `hand`. Three
library items declare slots outside the vocabulary (`bottom`, `ears`,
`shoulders`), which `equip_item` refuses with "Unknown slot". That is a data
problem in three item files and belongs with the item library, not with the
two-sources-of-truth bug.

### Verify

```
python -m pytest tests/test_equipment_api_edges.py -q      # 12 passed
python -m pytest tests/test_equipment_system.py tests/test_library_character_import.py \
  tests/test_character_loadout_check.py tests/test_auto_dress.py tests/test_armor_wear.py \
  tests/test_activities.py tests/test_edge_known.py -q      # 130 passed
```

The five failures in `test_scenario_data_integrity.py` / `test_character_identity.py`
are the documented pre-existing baseline and are unrelated.

