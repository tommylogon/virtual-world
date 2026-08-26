# Trait System Redesign — Data-Driven Traits with Engine Primitives

## Problem

Trait definitions are hardcoded in `engine/traits.py` as a `TRAIT_DEFINITIONS` dict with 22 entries. Adding a new trait requires a code change. The engine also references trait names directly via `TraitSystem.has_effect(player, "dark_vision")` — coupling engine code to specific trait names.

## Solution: Three Runtime Stores + JSON Traits

Traits become pure JSON, adding a new one never requires engine changes.

### Player Runtime State (what the engine reads)

```
player.capabilities    → set[str]       — permanent/modal binary things you CAN do or are
player.conditions      → set[str]       — temporary status effects with engine consequences
player.tags            → set[str]       — identity/classification for triggers to check
player (vitals,stats)  — adjustable by triggers (HP, STR, Athletics, Energy, etc.)
```

Engine code never references trait names. It only checks these fields.

### Trait JSON Schema

```json
{
  "id": "dark_vision",
  "name": "Darkvision",
  "description": "Can see in complete darkness.",
  "category": "physical",
  "params": null,
  "modifiers": {
    "capabilities": {"add": ["darkvision"]},
    "conditions": {},
    "tags": {}
  },
  "triggers": []
}
```

### Engine Primitive Fields

When a trait is gained, its `modifiers` are applied to the player's runtime stores. When lost, they are reversed.

```json
{
  "modifiers": {
    "capabilities": {"add": ["darkvision", "resistance:fire"], "remove": []},
    "tags": {"add": ["undead"], "remove": []},
    "speed": {"replace": 30},
    "size": {"replace": "medium"},
    "hp_per_level": 1
  }
}
```

- **Set fields** (capabilities, tags, resistances, immunities): additive — `add` inserts, `remove` deletes. Multiple traits contribute independently.
- **Scalar fields** (speed, size, vision): `replace` — takes the highest-priority value on gain, restores the previous value on loss. If two traits set speed, the highest wins.
- **Additive mods** (hp_per_level, skill bonuses): summed across all active traits.

### Trigger-Driven Behaviors

For everything beyond simple modifiers — active abilities, tick effects, reactions — traits define `triggers`:

```json
{
  "id": "north_born",
  "name": "North-Born",
  "modifiers": {
    "capabilities": {"add": ["resistance:cold"]}
  },
  "triggers": [
    {
      "trigger_type": "on_tick",
      "conditions": [{"type": "temperature_below", "value": 0}],
      "effects": [{"type": "adjust_vital", "params": {"vital": "Warmth", "amount": 5}}]
    }
  ]
}
```

These triggers use the existing trigger system's condition/effect format and are evaluated when the player possesses the trait.

### Rate Multipliers (Glutton, Fast Healer, etc.)

Some traits modify *decay rates* or *regen rates* rather than values (glutton: hunger decays ×2, slow_healer: HP regen ×0.5). These use additive modifiers that multiply the baseline rate:

```json
{
  "modifiers": {
    "rate_multipliers": {"Hunger": 2.0, "Thirst": 1.0},
    "hp_regen_multiplier": 0.5
  }
}
```

Stored on `player.rate_multipliers` dict. The tick system reads it during decay processing. Multiple traits multiply their contributions: glutton (×2) + another trait (×1.5) = ×3 total.

### Equipment → Trait Pipeline

Items grant traits through the existing trigger system — no change needed:

```json
{
  "triggers": [
    {"trigger_type": "on_equip", "effects": [{"type": "apply_trait", "params": {"trait": "hardy"}}]},
    {"trigger_type": "on_unequip", "effects": [{"type": "remove_trait", "params": {"trait": "hardy"}}]}
  ]
}
```

## Migration Path

1. Add `modifiers` and `triggers` to trait JSON schema
2. Update `TraitSystem` to load from JSON, drop hardcoded `TRAIT_DEFINITIONS`
3. Add `player.capabilities` runtime store
4. Refactor engine code: `TraitSystem.has_effect(player, "dark_vision")` → `"dark_vision" in player.capabilities`
5. Add effect types: `add_capability`, `remove_capability`
6. Add `player.rate_multipliers` dict + `set_rate`/`clear_rate` effects
7. Migrate all 22 existing traits to new JSON format
8. Wire `on_trait_gain`/`on_trait_loss` to apply/clear modifiers
