# Skills System

Skills are numeric proficiencies that modify dice rolls for action resolution. The system is stateless — all dependencies (player manager, logging) are injected via the `SkillSystem` constructor (`engine/skills.py:12-26`).

## Skill Values

Characters have a `skills` dict (`player.py:75-80`) mapping skill names to numeric values:

```python
self.skills = {
    "Athletics": 1, "Acrobatics": 1,
    "Stealth": 1, "Perception": 1,
    "Survival": 1, "Persuasion": 1
}
```

Skills are not fixed to these six — characters can have any skill name. Example custom skills from library files:
- `"Performance": 5` (Miki, ASMR artist)
- `"Investigation": 3` (Jake, intuitive pattern-seeker)
- `"Investigation": 2` (Miki, investigator)

Values typically range 0-5 but there is no upper limit enforced.

## Skill Checks

### Mechanics

Skill checks use a D20 roll + skill value vs. a Difficulty Class (DC):

```python
def skill_check(self, skill_name, difficulty_class=10, use_active_player=True):
    player = self.player_manager.get_active_player_obj()
    skill_value = player.skills.get(skill_name, 0)  # defaults to 0 if skill missing
    roll = random.randint(1, 20)
    total = roll + skill_value
    success = total >= difficulty_class
```

(`engine/skills.py:43-91`)

### Difficulty Classes

| DC Range | Description |
|----------|-------------|
| ≤5 | very easy |
| 6-10 | easy |
| 11-15 | medium |
| 16-20 | hard |
| >20 | very hard |

(`engine/skills.py:74-83`)

### Return Value

Returns a tuple of `(success: bool, total: int, message: str)`.

Example output:
```
[Skill Check] Perception vs DC 12 (medium): roll=8 + 3 = 11 => failure
```

(`engine/skills.py:86-91`)

### When Skills Are Not Found

If a player does not have a skill, `player.skills.get(skill_name, 0)` returns 0 — the roll becomes just `1d20 + 0`. No error is raised.

## Dice Rolling

```python
def roll_dice(self, num_dice=1, sides=20, modifier=0):
    total = sum(random.randint(1, sides) for _ in range(num_dice))
    return total + modifier
```

(`engine/skills.py:30-39`)

Used by both `skill_check()` and the combat system for attack/defense rolls.

## Player State Remedies

The `player_state_remedy()` static method (`engine/skills.py:95-110`) returns hints for recovering from conditions:

| State | Remedy |
|-------|--------|
| `sleeping` | wake up |
| `unconscious` | receive medical attention |
| `bound` | struggle free |
| `exhausted` | rest and eat |
| `injured` | heal with medicine |
| `dead` | create a new character |

## LLM Call Logging

`log_llm_call()` (`engine/skills.py:114-135`) is a stub for logging LLM request/response pairs to the turn event stream. Currently disabled (immediate `return` at line 125). When enabled, it records prompts and responses (truncated to 500 chars) to `logging_events.record_turn_event()`.

## Combat Integration

The combat system (`engine/combat.py`) uses `SkillSystem` for dice rolling and player lookups:

### Attack Resolution (`combat.py:26-105`)

```python
attack_roll = self.skills.roll_dice(1, 20, attacker.stats.get("STR", 10))
defense_roll = self.skills.roll_dice(1, 20, target.stats.get("DEX", 10))
```

- Attack roll = `1d20 + STR` modifier
- Defense roll = `1d20 + DEX` modifier
- If attack >= defense: hit

### Damage Calculation

- **With weapon**: `1d<weapon_damage> + STR bonus` (`combat.py:46-55`)
  - Slasher characters get an additional `attack_bonus` on damage
- **Unarmed**: `1d4 + STR bonus` (`combat.py:72-73`)
- STR bonus = `max(0, (STR - 10) // 2)` (`combat.py:50`)

### Weapon Discovery

`WEAPON_KEYWORDS` (`combat.py:10-14`) lists 15 weapon types (cleaver, knife, hatchet, axe, blade, sword, dagger, machete, club, hammer, spear, shiv, chainsaw, crowbar). Items whose names match these keywords are treated as weapons.

## Skill Checks in the Inspector UI

The Inspector UI shows player skills in the character editor panel. Skills can be edited inline as numeric values. There is no skill progression system — skill values are set manually by the user/developer or imported from character library files.

## Skill-Based Action Resolution

Skills affect gameplay through:

1. **Direct `skill_check()` calls**: Trigger systems and commands can call `skill_check()` to resolve actions (e.g., `fumble_around()` for discovering hidden ways uses Perception DC 12)
2. **Item skill checks**: Items in the library can have `skill_check` properties (e.g., `{"skill": "Athletics", "DC": 15}`) — but this is stored in library data and checked manually by triggers
3. **Missing skill checks**: When a player lacks a required skill, the roll defaults to a flat `1d20 + 0`

## Skill Assignment via API

- `POST /api/players` creates a player with optional `skills` field
- `POST /api/players/<name>` updates skills via `{"skills": {"Perception": 4, "Athletics": 2}}`
- `POST /api/players/import` sets skills during character import

## Frontend Display

Skills are displayed in the Inspector UI's character editor panel. Each skill shows its name and current value as an editable numeric input. Custom skills (non-default) are displayed alongside the defaults.

## Related tasks

- [[task-3-equipment_system|task-3: Equipment system]]
- [[dev_tasks/review/items/task-54-weapon_system|task-54: Weapon system]]
