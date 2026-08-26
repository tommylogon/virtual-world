# Combat System

## Overview

The Combat System handles player-vs-player and player-vs-NPC combat in VirtualWorld. It lives in `engine/combat.py` (class `CombatSystem`, ~120 lines). Combat uses D&D-style mechanics: d20 rolls, STR/DEX modifiers, skill-based damage bonuses, and a weapon discovery system.

## Core Combat Flow

The primary method is `CombatSystem._player_attack()` (`engine/combat.py:26`):

```python
def _player_attack(self, attacker_name: str, target_name: str, weapon_node=None) -> str
```

### Attack Resolution

0. **Approach target** — attacker steps **beside** the target (`approach_character` in `engine/character_spatial.py`; task-135).

1. **Fetch combatants**: `self.skills.get_player(attacker_name)` and `get_player(target_name)` — retrieves Player objects from the player manager.

2. **Roll initiative** (combined with attack):
   - Attack roll: `roll_dice(1, 20, attacker.stats.get("STR", 10))`
   - Defense roll: `roll_dice(1, 20, target.stats.get("DEX", 10))`
   - Both are `d20 + stat modifier`. Higher total wins.

3. **NPCAwareness trigger**: `self.npc_behaviors.process_npcs_on_combat()` is called to alert nearby NPCs of the combat.

4. **Hit or Miss**: If `attack_roll >= defense_roll`, the attack hits. Otherwise it misses.

### Damage Calculation (Hit)

**With Weapon** (`engine/combat.py:57-105`):
The `damage` field accepts unified damage notation — dice strings or flat numbers:

```
damage = weapon.properties.get("damage", 5)  # e.g. "1d6", "2d8+3", or 8
parsed = parse_damage(damage)                # from equipment_bonuses.py
if dice notation (count > 0):
    damage = roll_dice(count, sides, stat_mod + flat_bonus)
else (flat number):
    damage = roll_dice(1, flat_value, stat_mod)
```

Examples:
- `"damage": "1d6"` → rolls 1d6 + stat modifier
- `"damage": "2d8+3"` → rolls 2d8 + 3 + stat modifier  
- `"damage": 8` → rolls 1d8 + stat modifier (flat number = die size)

Slashers get an extra `attack_bonus` added to the roll. Weapon uses decrement by 1 when used.

**Without Weapon** (`engine/combat.py:71-84`):
```
damage = max(1, roll_dice(1, 4, str_bonus))  # d4 + STR modifier
```

### Damage Application

```
target.vitals["HP"] = max(0, target.vitals["HP"] - damage)
```

### Death Handling

When `target.vitals["HP"] <= 0`:
```python
target.state = "dead"
ghost_system.spawn_body_item(target_name, f"slain by {attacker_name}")
```

The target's state is set to `"dead"` (which clears all conditions and adds `"dead"` via `Player.state` setter at `player.py:152`). A body item is spawned in the room.

### Miss Handling

On a miss:
```
f"{attacker_name} swings the {weapon_name} at {target_name} but misses!"
f"{attacker_name} lunges at {target_name} but misses!"
```

## Weapon Discovery System

`WEAPON_KEYWORDS` (`engine/combat.py:10-14`) lists strings that identify items as weapons:

```python
WEAPON_KEYWORDS = [
    "cleaver", "knife", "letter_opener", "hatchet", "axe", "blade",
    "sword", "dagger", "machete", "club", "hammer", "spear", "shiv",
    "chainsaw", "crowbar",
]
```

The `_find_weapon_in_inventory()` method (`engine/combat.py:107`) searches a player's inventory (via `EDGE_CARRYING` edges) for items whose `name` or `properties.name` matches the weapon name. The search uses exact match on name.

## Integration Points

### Equipment System

The Combat System integrates with the equipment system through `EquipableItems` and `equip_slots` property on items. Weapons are typically held in `hand_left` or `hand_right` slots. The `_find_weapon_in_inventory()` searches the player's graph-connected items (both `EDGE_CARRYING` and `EDGE_EQUIPPED`), which covers equipped items.

### Skill System

The skill system (`engine/skills.py`) provides:
- `roll_dice(num, sides, modifier)` — used for attack/defense rolls and damage
- `add_log_entry(text)` — log combat events
- `record_turn_event()` — record events for NPC awareness
- `is_slasher(player_name)` — check if attacker is a slasher (gets damage bonus)

### Ghost System

When a character dies in combat:
- `ghost_system.spawn_body_item(target_name, cause)` — creates a body item in the room
- The dead character's state is `"dead"` — they enter ghost mode (if enabled)

### NPC Behaviors

`process_npcs_on_combat()` is called before each attack to alert NPCs:

```python
self.npc_behaviors.process_npcs_on_combat(
    {"combat_actors": [attacker_name, target_name]}
)
```

### Logging & Events

Each combat action records:
- Game log entry via `add_log_entry()` with `[COMBAT]` prefix
- Turn event via `record_turn_event()` with type `"combat"`, including room name

## Damage Types

The system doesn't use a formal damage type system. All damage is raw HP reduction. However, the modular effect system in triggers supports separate `"damage"` effect type which can be configured to target `"self"` or `"other"` characters (via `handle_damage` in `effects.py:81`).

## Non-Lethal Combat

The system does not have an explicit non-lethal option. All damage is lethal — when HP reaches 0, the target dies. There is no "unconscious from non-lethal damage" mechanic. However, the `rest` system and natural HP regen (`tick_manager.py:272-277`) allow recovery when conditions are met.

## Integration with Triggers

Combat can be triggered or modified through the trigger system:
- Items with `on_use` triggers can deal damage (`"damage"` effect)
- Weapons in the combat system are standard item nodes with `damage` property (unified: dice or flat)
- Combat damage bypasses the trigger system (it's direct HP manipulation)

## Equipment Defense Integration

When combat calculates damage, the target's **total defense** from equipped items is subtracted:

```python
target_defense = sum(item.defense for item in equipped if item tagged armor/clothing)
damage = max(1, rolled_damage - target_defense)
```

Defense comes from items with tags `armor` or `clothing` that have a `defense` field (see [[Equipment & Paperdoll#Equipment Bonuses]]). Multiple items stack — wearing boots (defense 1) + coat (defense 1) = total defense 2.

Hit messages show the full breakdown (attack roll + modifiers vs defense, damage roll/flat + type, armor absorption, resistance, HP before → after):

```
The Butcher attacks Kyrie Johansen with cleaver!
  Attack: d20(11) + 18 STR + 0 mod = 29 vs d20(5) + 5 DEX = 10 → HIT
  Damage: 2d6 (10) + 4 stat + 0 flat = 14 total, −0 armor
  Result: 14 slashing damage — Kyrie Johansen HP 50 → 36/50
```

- Attack line: `d20(raw) + STR value + condition/grapple mod = total vs d20(raw) + DEX = defense` then `HIT`/`MISS`.
- Damage line: `NdS (raw roll) + stat mod + flat (+ attack_bonus if slasher) = total, −N armor`; resistance appends `, N resisted (type)`.
- Result line: final damage + damage type, armor absorbed, and the target's HP `before → after/max`.

## Combat Limitations

- **No turn queue**: Combat is resolved immediately on the `attack` action. There's no initiative order or round structure.
- **No armor class**: Defense is purely DEX-based `d20 + DEX` roll.
- **No critical hits**: Attack rolls don't have critical hit/miss mechanics.
- **No ranged combat**: All attacks are melee-range.
- **No multi-target**: Single target per attack action.

## Related tasks

- [[dev_tasks/todo/gameplay/task-4-grapple_restrain_system|task-4: Grapple restrain system]]
- [[dev_tasks/review/items/task-54-weapon_system|task-54: Weapon system]]
