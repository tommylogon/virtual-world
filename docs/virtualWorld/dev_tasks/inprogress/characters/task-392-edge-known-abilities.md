---
type: task
status: inprogress
area: characters
priority: high
---

# task-392: EDGE_KNOWN — Graph-Native Ability/Spell Knowledge

**Filed**: 2026-09-03  
**Status**: In Progress — core implementation complete; QA in progress  
**Source**: Character backstory from `data/library/characters/Lyrie.json` — spells are currently forced to exist as carried/equipped intrinsic-ability items. We want a graph-native “character knows this spell” relationship instead of pretending every spell is a physical inventory slot.

## Summary

Add a new graph edge `EDGE_KNOWN` that represents a character's knowledge of an ability/spell/power item. This lets authors and systems express “Lyrie CAN create flame” without requiring the spell to be physically carried or equipped. The graph remains the source of truth; no parallel character registry is introduced.

## Current State (verified)

- Intrinsic-ability detection already exists: `engine/equipment.py:15-17` defines `INTRINSIC_ABILITY_TAGS = frozenset({"spell","ability","innate","intrinsic","power"})`.
- Current spell model: spells are item nodes attached via `EDGE_CARRYING` / `EDGE_EQUIPPED`, then hidden from other characters' appearance narratives via `_is_intrinsic_ability()` / `_drop_intrinsic_abilities()`.
- Item lookup (`player_manager.find_item_node`) checks only `EDGE_CARRYING` / `EDGE_EQUIPPED` and area `EDGE_IN` / container contents. There is **no known/learned lookup**.
- `use_item()` requires resolving an item node first; there is no casting path from abstract knowledge.
- UI/inspector has no control for setting a “known” relationship between character and item.

## Proposed Schema

```python
# graph.py
EDGE_KNOWN = "known"  # ability/spell item → character
```

Direction matches existing item→character edges (`carrying`, `equipped`):

```
item_Create_Flame ──known──► player_Lyrie
```

This keeps querying symmetric with current patterns:

```python
# Existing
get_edges_for_target(player_id, EDGE_CARRYING)  # inventory
get_edges_for_target(player_id, EDGE_EQUIPPED)   # worn/held

# New
get_edges_for_target(player_id, EDGE_KNOWN)       # known abilities
```

## Implementation Plan

### Backend

1. **Graph constant** (`graph.py`)
   - Add `EDGE_KNOWN = "known"`
   - Ensure it is included in `resolve_edge_types` / legacy migration docs if needed.

2. **Item resolution** (`engine/player_manager.py:119-173`)
   - Extend `find_item_node` to check `EDGE_KNOWN` edges after `EDGE_CARRYING` / `EDGE_EQUIPPED` and area/container lookups.
   - Priority order: carried/equipped → area/container → known. This preserves physical-item precedence.

3. **Cast / use flow** (`engine/items/use_actions.py`)
   - Allow `use_item()` to succeed when the item is resolved via `EDGE_KNOWN`.
   - Preserve current behavior for physical items; known abilities should not gain weight/capacity effects.
   - Optional: add a `cast` verb alias that explicitly targets known abilities first.

4. **Area description / inspector filters** (`engine/area_description.py`, inspector modules)
   - Known abilities should not appear in room listings or other characters' examine output. The existing intrinsic-ability filter already handles most of this for ability-tagged items; verify it still works when the item is only `EDGE_KNOWN` and not physically present.

5. **Serialization / save-load**
   - Generic edge serialization already covers `EDGE_KNOWN`; no special-case save logic should be needed. Add a regression test.

### UI / Frontend

6. **Inspector “Known By” / “Knows” control**
   - Add a relationship picker in the item/character inspector to create/remove `EDGE_KNOWN` between a character and an ability item.
   - Reuse the existing library search/select components where possible.

7. **Selectors / autocomplete**
   - Update `cast`, `use`, and ability-prompt selectors to include known abilities that are not currently carried.
   - Keep carried/equipped items first in the list.

8. **Prompt / narration**
   - Ensure ability lookups in prompts reflect known-but-not-carried spells.
   - Do not reveal known abilities to other characters; they remain invisible unless the caster uses them.

## Verification

- `pytest tests/ -q` green, including new tests for `EDGE_KNOWN` resolution, casting from known abilities, and serialization round-trip.
- Manual: import/create an ability item, mark it known for a character, verify `use <spell>` works without the item being in inventory/equipment/area.
- Manual: verify known abilities do not appear in room listings or other characters' examine output.

## Notes

- This is intentionally graph-native. No `Player.known_abilities[]` registry, no parallel store.
- Intrinsic-ability tag filtering remains useful for presentation hiding, even when the item is not physically present.
- Future work: `EDGE_KNOWN` can also be used for techniques, languages, recipes, and bestowed powers — not just spells.

## Progress

- [x] Graph constant added
- [x] Item resolution extended
- [x] Use flow supports known abilities
- [x] Examine resolves known abilities
- [x] Scene snapshot includes known_abilities
- [x] Frontend graph support
- [x] Inspector known abilities picker
- [x] Autocomplete includes known abilities
- [x] Prompt context shows known abilities
- [x] Tests added (7/7 green)
- [x] No `cast` verb — uses `use` / `use_on`
- [x] Abilities hidden from other characters' examine/room listings
- [ ] Manual QA: full playtest of `use <known ability>` end-to-end
- [ ] Inspector API route validation review
