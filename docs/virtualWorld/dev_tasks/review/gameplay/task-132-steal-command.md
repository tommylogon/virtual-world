---
group: Agent AI & Behavior
---

# Steal Command

**Filed**: 2026-07-30
**Priority**: Low
**Status**: Done

---

## Summary

Add a `steal <item> from <target>` command — Sleight of Hand vs Perception contest to take items from other characters.

---

## Implementation

- `engine/item_actions.py:steal_item` — parses item + target, finds item in target's inventory via `EDGE_CARRYING`/`EDGE_EQUIPPED`, rolls 1d20 + skill vs target's 1d20 + Perception
- Success: item edges moved from target to player, triggers `on_take`
- Failure: `ValueError` raised with roll details
- `routes/action.py` — registers `steal <item> from <target>` command
- `virtual_world_engine.py` — pass-through method

### Skill system
- Uses `player.skills["Sleight of Hand"]` (default 0) vs `target.skills["Perception"]` (default 0)
- Both roll 1d20 + modifier; higher wins (ties go to the thief)

### Files changed
- `engine/item_actions.py` — added `steal_item` method
- `routes/action.py` — registered `steal` command parser
- `virtual_world_engine.py` — `steal_item` pass-through
