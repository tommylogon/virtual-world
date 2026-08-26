# Traits System

Traits are predefined character modifiers that alter gameplay through a tag-and-effect system. Each trait is defined in `engine/traits.py` with a unique ID, name, description, category, and a set of engine-recognized effects.

> **Design direction (2026-08-07):** The full v2 design — traits vs conditions split, condition catalog, `save_on` world-event consequences, acquired traits — lives in [[Rules Engine/Trait & Condition System (Design)|Trait & Condition System (Design)]], tracked as [[dev_tasks/review/characters/task-trait-condition-system-v2|task: Trait & Condition System v2]]. This page documents the current implementation.

## Architecture

Traits follow a registry/effect pattern:

1. **Definitions**: `TRAIT_DEFINITIONS` dict in `engine/traits.py:71-233` — all known traits and their effects
2. **Assignment**: Each player has a `traits` dict (`player.py:82-85`) mapping `trait_id → param_value`
3. **Resolution**: `TraitSystem` class (`engine/traits.py:239-404`) resolves trait IDs into engine-readable effect values at runtime
4. **Library Files**: `data/library/traits/*.json` — one file per trait, synced with the engine definitions

The engine code never hard-codes trait names outside of `traits.py`. All trait effects are looked up dynamically through `TraitSystem` static methods.

## Trait File Format

Trait library files (e.g., `data/library/traits/dark_vision.json`):

```json
{
  "id": "dark_vision",
  "name": "Dark Vision",
  "description": "Can see in complete darkness.",
  "category": "physical",
  "params": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Trait identifier, matches `TRAIT_DEFINITIONS` key |
| `name` | `string` | Human-readable display name |
| `description` | `string` | What the trait does |
| `category` | `string` | `"physical"` or `"mental"` |
| `params` | `object|null` | Parameterized trait config: `{type, label, placeholder}` |

Currently 29 traits are defined in `TRAIT_DEFINITIONS`.

### Exploration / Novelty Traits (task-136)

These traits drive the Entertainment novelty system (`movement.py:226-240`, `tick_manager.py:127-143`, `item_actions.py`, `player.py`):

| Trait | Effect on Entertainment | Effect on behavior |
|-------|------------------------|-------------------|
| `curious` | +50% from new places/things | More likely to examine items, explore exits |
| `adventurous` | Entertainment doesn't decay in unfamiliar areas | More willing to take risks, go somewhere unknown |
| `homebody` | No boost from new places or things | Reluctant to leave familiar areas |
| `wanderlust` | Gains Entertainment from moving between areas even if visited before | Prefers to keep moving, rarely stays put |
| `impatient` | Faster Entertainment decay when inactive | Acts before considering consequences |
| `patient` | Slower Entertainment decay; tolerates repetitive activities | Less driven by boredom, stays put longer |

Entertainment novelty boosts are granted for: first visit to an area (+15, `movement.py`), first discovery of an item (+8, `ItemActions._register_item_discovery`), and first meeting a new character (+10, `Player.register_first_meeting` / `update_relationship`).

## Trait Assignment

Traits can be assigned to characters via:
- The Inspector UI (traits/tags panel in the character inspector)
- API: `POST /api/players/<name>` with `{"traits": {"dark_vision": true, "fast_healer": true}}`
- API: `POST /api/registry/characters` to save to the library
- Programmatically: `player.traits["dark_vision"] = True`

The `tags` field (`player.py:86-88`) is separate from traits — tags are free-form identity markers like `"vampire"`, `"faction:guard"`, `"synthetic"`. Traits have engine effects; tags are checked by items/triggers/conditions.

## TraitSystem API

### Query Methods

All static methods on `TraitSystem`:

| Method | Returns | Description |
|--------|---------|-------------|
| `get_definition(trait_id)` | `dict` or `None` | Get the trait definition |
| `has_trait(player, trait_id)` | `bool` | Check if player has the trait |
| `get_trait_param(player, trait_id)` | any | Get parameter value for parameterized traits |
| `has_effect(player, effect_key)` | `bool` | Check if any trait grants an effect |
| `get_effects(player, effect_key)` | `list` | Collect all effect values for a key |
| `get_first_effect(player, effect_key)` | any | Get first matching effect value |
| `get_vital_multipliers(player)` | `dict` | Merged vital multipliers |
| `get_action_cost_mods(player)` | `dict` | Additive action cost modifiers |
| `get_sense_blocked(player)` | `str` or `None` | Blocked sense ("sight"/"hearing") |
| `get_disabled_slots(player)` | `set` | Disabled equipment slot names |
| `get_allergen_tag(player)` | `str` or `None` | Allergen this player reacts to |
| `get_energy_curve(player)` | `dict` or `None` | Energy curve config |
| `get_hp_regen_multiplier(player)` | `float` | HP regen multiplier |
| `is_immune_to_condition(player, condition)` | `bool` | Condition immunity check |
| `process_tick_effects(player, tick, area_node)` | `list[str]` | Apply per-tick trait effects |

## Effect Keys and What They Do

### `VITAL_MULTIPLIER` (key: `"vital_multiplier"`)
Multiplies the baseline decay rate for a specific vital. Applied in `tick_turn()` (`tick_manager.py:108-114`):

```python
rate = p.decay_rates.get(stat, default_decay)
mult = trait_multipliers.get(stat, 1.0)
p.vitals[stat] = max(0, p.vitals[stat] - int(rate * mult))
```

**Example**: `glutton` multiplies Hunger decay by 2.0 → hunger drops twice as fast.

### `ACTION_COST_MOD` (key: `"action_cost_mod"`)
Additively modifies action costs. Applied in `apply_action()` (`tick_manager.py:27-31`):

```python
trait_mods = TraitSystem.get_action_cost_mods(target)
for tk, tv in trait_mods.items():
    lk = str(tk).lower()
    cost[lk] = max(0, int(cost.get(lk, 0)) + tv)
```

**Example**: `hardy` reduces energy cost by 1 (`"energy": -1`).

### `DARK_VISION` (key: `"dark_vision"`)
Boolean. Player can see in total darkness (light level <= 20). Both `dark_vision` and `darkvision` trait IDs provide this effect (`traits.py:198-211`).

### `IS_SLASHER` (key: `"is_slasher"`)
Boolean. Horror monster flag that:
- Exempts the character from all vital decay (`tick_manager.py:104-106`)
- Grants dark vision
- Is checked by `player_manager.is_slasher()` for hunt targeting
- Both `slasher` and `is_slasher` trait IDs provide this

### `BLOCK_SENSE` (key: `"block_sense"`)
Blocks either `"sight"` or `"hearing"`. Affects narration (the LLM is told the character cannot perceive that sense).

**Traits**: `blind` (blocks sight), `deaf` (blocks hearing).

### `DISABLE_SLOT` (key: `"disable_slot"`)
Disables an equipment slot name. The character cannot equip items there.

**Trait**: `one_armed` disables `"hand_right"`.

### `HP_REGEN_MULTIPLIER` (key: `"hp_regen_multiplier"`)
Multiplies the natural HP regeneration rate (default 1 HP/tick when conditions are met). Applied multiplicatively in `tick_turn()` (`tick_manager.py:275-277`):

```python
regen_base = 1
regen_mult = TraitSystem.get_hp_regen_multiplier(p)
p.vitals["HP"] = min(100, p.vitals["HP"] + max(1, int(regen_base * regen_mult)))
```

**Traits**: `fast_healer` (2.0x), `slow_healer` (0.5x).

### `ENERGY_CURVE` (key: `"energy_curve"`)
Defines a peak hour and off-peak energy modifier. Applied in `process_tick_effects()` (`traits.py:378-385`):

```python
peak = curve.get("peak_hour", 12)
off_mod = curve.get("off_peak_mod", -2)
current_hour = (tick // 60) % 24
if abs(current_hour - peak) > 4:
    player.vitals["Energy"] = max(0, player.vitals.get("Energy", 50) + off_mod)
```

**Traits**: `night_owl` (peak 22, -2 off-peak), `morning_person` (peak 6, -2 off-peak).

### `ALLERGIC_TO` (key: `"allergic_to"`)
Parameterized trait. Player takes damage when near items/areas with a matching tag. Applied in `process_tick_effects()` (`traits.py:368-376`):

```python
allergen = TraitSystem.get_allergen_tag(player)
if allergen and area_node:
    area_tags = area_node.properties.get("tags", [])
    item_tags = _collect_item_tags_in_area(area_node)
    if allergen in area_env.get("air", "") or allergen in area_tags or allergen in item_tags:
        player.vitals["HP"] = max(0, player.vitals.get("HP", 100) - 3)
```

**Trait**: `allergic` with `params: {type: "string", label: "Allergen tag"}`. The player must specify e.g. `{"allergic": "pollen"}`.

### `GROUP_ENERGY_DRAIN` (key: `"group_energy_drain"`)
Per-tick energy drain when more than N other characters are in the same room. Applied indirectly through `tick_turn()`.

**Trait**: `introvert` (group drain = -2 energy).

### `SOCIAL_GAIN` (key: `"social_gain"`)
Per-tick social vital gain from being near others.

**Trait**: `extrovert` (social gain = +2).

### `NO_ENTERTAINMENT_DECAY` (key: `"no_entertainment_decay"`)
Boolean. Prevents Entertainment from decaying naturally. In fact, Entertainment increases by the decay rate each tick (`tick_manager.py:116-118`).

**Trait**: `apathetic`.

### `WAKE_THRESHOLD` (key: `"wake_threshold"`)
Minimum noise level required to wake this character (1=whisper, 5=scream). Lower = harder to wake.

**Traits**: `light_sleeper` (threshold 3), `heavy_sleeper` (threshold 1).

### `IMMUNE_TO_CONDITION` (key: `"immune_to_condition"`)
Grants immunity to a specific condition. Checked by `is_immune_to_condition()`.

**Trait**: `immortal` provides immunity to `"dead"` — HP stops at 1.

## Complete Trait Reference

| Trait ID | Name | Category | Effects |
|----------|------|----------|---------|
| `glutton` | Glutton | physical | Hunger decay ×2.0 |
| `cleanfreak` | Clean Freak | physical | Hygiene decay ×1.5 |
| `night_owl` | Night Owl | physical | Energy peak at 22:00, -2 off-peak |
| `morning_person` | Morning Person | physical | Energy peak at 06:00, -2 off-peak |
| `fast_healer` | Fast Healer | physical | HP regen ×2.0 |
| `slow_healer` | Slow Healer | physical | HP regen ×0.5 |
| `one_armed` | One-Armed | physical | Disables hand_right slot |
| `small_bladder` | Small Bladder | physical | Bladder fill rate ×1.5 |
| `big_bladder` | Big Bladder | physical | Bladder fill rate ×0.5 |
| `blind` | Blind | physical | Blocks sight |
| `deaf` | Deaf | physical | Blocks hearing |
| `introvert` | Introvert | mental | Group energy -2, social gain 0 |
| `extrovert` | Extrovert | mental | Group energy 0, social gain +2 |
| `apathetic` | Apathetic | mental | No entertainment decay |
| `allergic` | Allergic | physical | HP -3/tick near allergen |
| `light_sleeper` | Light Sleeper | physical | Wake threshold 3 |
| `heavy_sleeper` | Heavy Sleeper | physical | Wake threshold 1 |
| `immortal` | Immortal | physical | Immune to dead condition |
| `dark_vision` | Dark Vision | physical | Can see in darkness |
| `darkvision` | Dark Vision (Alt) | physical | Can see in darkness |
| `slasher` | Slasher | physical | Is slasher + dark vision |
| `is_slasher` | Is Slasher (Alt) | physical | Is slasher + dark vision |
| `hardy` | Hardy | physical | Action energy cost -1 |
| `size_tiny` | Tiny Size | physical | ~45 cm tall — fits any passage |
| `size_small` | Small Size | physical | ~90 cm tall — crowds normal doorways slightly |
| `size_normal` | Normal Size | physical | ~170 cm — the default when no size trait is set |
| `size_huge` | Huge Size | physical | ~3.4 m tall — must crawl small tunnels, blocked by tiny |
| `size_giant` | Giant Size | physical | ~7 m tall — blocked by anything under `huge` |
| `size_titanic` | Titanic Size | physical | ~14 m+ — blocked by anything under `giant` |

### Size Traits (task-187)

The six `size_*` traits are **mutually exclusive** and drive the passage system (see [[World Building/Doors & Connections]]): ways carry a `max_size` property, and `engine/size.py` resolves a tier index from whichever `size_*` trait is present (default `normal` when none). One tier over a way's `max_size` auto-crawls; two or more tiers over blocks the move entirely. Crawl is flavor + gating only — it does not scale costs (the way's `cost.time` is a duration hint for future stateful actions, not per-action clock advancement). Size is purely a trait tier model — there is no height property.

## How the Engine Applies Traits

### Per-Tick Processing

`TraitSystem.process_tick_effects()` is called from `tick_turn()` (`tick_manager.py:267-270`):

1. **Vital multipliers**: Applied during decay in `tick_turn()` via `get_vital_multipliers()`
2. **Allergic reactions**: Checks room environment tags and item tags against the player's allergen
3. **Energy curves**: Checks current in-game hour against peak/off-peak configuration
4. **Condition immunity**: Checked by `conditions.py` before applying conditions

### Action Cost Modification

When any action is performed, `apply_action()` (`tick_manager.py:14-46`):
1. Looks up base action costs
2. Gets trait-based action cost mods via `TraitSystem.get_action_cost_mods()`
3. Applies additive modifiers (e.g., `hardy` reduces energy cost)

### HP Regen

Each tick, if the player is well-fed (Hunger > 25, Thirst > 25, Energy > 25, Sanity > 25, Temperature 35-39), natural HP regen occurs. The regen multiplier from traits is applied.

### Sense Blocking

When the LLM generates narration, blocked senses are communicated via `get_sense_blocked()` so the narration omits sight or sound cues.

## Trait Library CRUD

The library browser can create, read, update, and delete trait entries:

- `GET /api/registry/traits` — list all traits
- `POST /api/registry/traits` — create or update a trait entry
- `DELETE /api/registry/traits/<id>` — delete a trait

Storage is in `data/library/traits/` as individual JSON files.

## Related tasks

- [[dev_tasks/review/characters/task-24-traits_conditions_emotions_editor|task-24: Traits, conditions, emotions editor]]
- [[dev_tasks/inprogress/items/task-106-tag-library-and-multiselect|task-106: Tag library and multiselect]]
