---
group: Equipment & Inventory
wiki: "[[Rules Engine/Combat System]]"
---

# Universal Weapon System

**Filed**: 2026-07-18
**Priority**: High
**Status**: In Review — implemented (code-verified 2026-08-11). Weapon damage/damage_dice/damage_type/resistances in `engine/equipment_bonuses.py:55-122`, `attack X with Y` combat resolution in `engine/combat.py`.

## Summary

Players should be able to attack each other using items as weapons. This includes both the slasher (Butcher) and normal characters (Kyrie with wrench, anyone with a cleaver, etc.).

## Current State

- `attack [target]` → routes to `_slasher_attack()` which only works for `is_slasher` characters. Non-slashers get bare-handed messaging but the combat logic doesn't use their STR properly.
- `attack [target] with [item]` → not parsed, target string includes `" with [item]"` → player not found
- `use [weapon] on [target]` → no `on_use_on` triggers on weapons → "Nothing happens"

## Command Syntax Choices

Two possible approaches. We should pick **one**:

### Option A: `attack [target] with [item]`
- Parses `"jake with cleaver"` → splits on `" with "` → target=Jake, weapon=cleaver
- Requires rewording the `attack` handler to search for `" with "` in the rest of the command
- Output example: *"You swing the cleaver at Jake. It connects — a deep gash opens across his arm. (-18 HP)"*

### Option B: `use [weapon] on [target]` (existing syntax)
- Already partially works: finds weapon item, finds target player via fuzzy name match
- Needs: add `on_use_on` trigger to weapon items with `adjust_vital` HP damage effect
- `effect_target: "other"` would need to apply to the target player
- But `use cleaver on jake` currently routes to `use_item_on()` which checks for `on_use_on` triggers on the item — so we just add the trigger

**Recommendation: Option A** — `attack [target] with [item]` — because:
- `attack` is the combat verb, not `use`
- Slasher-specific logic (`_slasher_attack`) can be generalized to accept a weapon parameter
- Clearer for players: `attack jake` (bare-handed) vs `attack jake with cleaver` (weapon)

## What Needs to Change

### 1. `app.py` — Parse `attack [target] with [item]`

```python
elif cmd.startswith("attack "):
    rest = cmd[7:].strip()
    weapon = None
    target = rest
    if " with " in rest:
        parts = rest.split(" with ", 1)
        target = parts[0].strip()
        weapon_name = parts[1].strip()
        # Look up weapon in player inventory
        inventory = world.get_inventory_items()  # returns item nodes
        weapon = next((item for item in inventory if item.name.lower() == weapon_name.lower()), None)
```

### 2. `virtual_world_engine.py` — Generalize `_slasher_attack`

Rename to `_player_attack` or add a weapon parameter:

```python
def _player_attack(self, attacker_name: str, target_name: str, weapon_node=None) -> str:
    """Player attacks another player, optionally with a weapon."""
    attacker = self.players.get(attacker_name)
    target = self.players.get(target_name)
    if not attacker or not target:
        return "You can't do that."
    
    # Base damage: STR bonus
    str_bonus = (attacker.stats.get("STR", 10) - 10) // 2
    
    if weapon_node:
        # Weapon damage from properties
        wp = weapon_node.properties
        weapon_damage = int(wp.get("damage", 0))
        weapon_name = wp.get("name", weapon_node.name)
        total_damage = max(1, weapon_damage + str_bonus)
        # Decrement uses if applicable
        uses = wp.get("uses", -1)
        if uses > 0:
            wp["uses"] = uses - 1
        target.vitals["HP"] = max(0, target.vitals.get("HP", 100) - total_damage)
        return f"You swing the {weapon_name} at {target_name}. It connects! ({total_damage} damage)"
    else:
        # Bare-handed
        total_damage = max(1, str_bonus)
        target.vitals["HP"] = max(0, target.vitals.get("HP", 100) - total_damage)
        return f"You punch {target_name} for {total_damage} damage."
```

### 3. Weapon Item Properties

Each weapon needs a `damage` field and optionally `weapon_type`:

| Item | Damage | Type | Special |
|------|--------|------|---------|
| Cleaver (Butcher) | 20 | blade | +STR bonus, slasher bonus |
| Wrench (Kyrie) | 12 | blunt | +STR bonus |
| Multitool (Jake) | 8 | blade | small, last resort |
| Hook (Butcher) | 15 | piercing | also used for grapple |

### 4. Relationship Impact

Attacking someone should affect relationships:
- `attack [target]` → -5 closeness
- `attack [target] with [weapon]` → -10 closeness (worse with a weapon)

### 5. Slasher Bonuses

If the attacker has `is_slasher` trait:
- Double STR bonus to damage
- Bonus damage based on attack_bonus stat
- Different narrative tone (more violent descriptions)

## Edge Cases

| Case | Behavior |
|------|----------|
| Target not in room | "They aren't here." |
| Weapon not in inventory | "You don't have that." |
| Weapon has 0 uses | "The [weapon] breaks!" (on_depleted trigger) |
| Target HP reaches 0 | Target enters `unconscious` or `dead` state |
| Attacker attacks self | "You can't attack yourself." |
| Slasher vs normal | Slasher gets damage bonuses, but normal characters can still hit |
| Multiple weapons in inventory | Pick the first match by name (fuzzy) |
