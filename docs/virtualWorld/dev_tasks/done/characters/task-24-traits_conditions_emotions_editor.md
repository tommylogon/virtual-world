# Traits, Conditions & Emotions Editor

**Filed**: 2026-07-15 (updated 2026-07-22)
**Priority**: Medium
**Status**: Done — implemented in commit 8e6ad9f

---

## Summary

Characters have three separate systems: **traits** (permanent mechanical modifiers), **conditions** (temporary status effects), and **emotions** (current mood). These need a unified editor in the character inspector.

## Core Model

### Traits — permanent, engine-enforced

Traits are machine-readable modifiers that change how the engine treats the character. They are NOT personality — personality lives in the `personality` text field for the LLM.

| Trait | Engine Effect | Param |
|-------|---------------|-------|
| `glutton` | Hunger decay ×2 | — |
| `cleanfreak` | Hygiene decay faster | — |
| `night_owl` | Energy curve shifted to night hours | — |
| `morning_person` | Energy curve shifted to morning, -energy at night | — |
| `fast_healer` | HP regen ×2 | — |
| `slow_healer` | HP regen ×0.5 | — |
| `one_armed` | One hand slot disabled | — |
| `small_bladder` | Bladder decay faster | — |
| `big_bladder` | Bladder decay slower | — |
| `blind` | Perception checks auto-fail, LLM narrated without sight | — |
| `deaf` | Cannot hear, LLM narrated without audio | — |
| `introvert` | Energy drains faster when in groups | — |
| `extrovert` | Energy gains when socializing | — |
| `apathetic` | No entertainment gain/loss from normal decay | — |
| `allergic` | Takes damage or gains condition when near items with matching tag | `allergic:pollen` |
| `light_sleeper` | Wakes from loud noises | — |
| `heavy_sleeper` | Hard to wake | — |
| `immortal` | Cannot die, HP bottoms at 1 | — |

### Conditions — temporary

Conditions are temporary effects with a duration (in turns). They decay naturally or are cured.

| Condition | Effect | Duration |
|-----------|--------|----------|
| `poisoned` | HP decay per tick | N turns |
| `bleeding` | HP decay per tick, stops with bandage | Until treated |
| `broken_leg` | Movement speed halved | Until healed |
| `concussed` | -INT, -perception | N turns |
| `burning` | HP decay, spreads to flammable items | Until extinguished |
| `sick` | Vitals decay faster, -all skills | N turns |
| `exhausted` | -all stats, +sleep need | N turns |
| `drunk` | -DEX, -INT, +confidence, blurred narration | N turns |
| `high` | Variable effects based on substance | N turns |
| `blind_temporary` | Same as blind trait but temporary | N turns |
| `deaf_temporary` | Same as deaf but temporary | N turns |

### Emotions — current mood

Already partially implemented. Emotion + intensity slider, with optional description/context (e.g. "Feeling cheerful after talking with Miki").

### Tags — identity markers on characters

Characters can have tags, separate from traits. Tags are checked by items, triggers, and conditions:

```
tags: ["vampire", "faction:guard", "synthetic", "faction:crows", "nobility"]
```

Example: A silver chain item has a trigger `on_equip: if target tags includes "vampire" → set condition "burning"`. The engine checks the wearer's tags, not traits.

### What goes where

| Quality | Goes In | Example | Handled By |
|---------|---------|---------|------------|
| "I eat a lot" | Trait | `glutton` | Engine (hunger ×2) |
| "I'm brave" | Personality | `personality: "Brave to a fault..."` | LLM |
| "I'm a vampire" | Tags | `tags: ["vampire"]` | Engine (items check this) |
| "I hate mods" | Personality | `personality: "Distrusts anyone with cybernetics..."` | LLM |
| "I'm a guard" | Tags | `tags: ["faction:guard"]` | Engine (uniform gives this tag) |
| "I'm allergic to bees" | Trait | `allergic:bee` | Engine (checks bee-tagged items) |

## Allergy System (Parameterized Trait)

`allergic:<tag>` is a special trait with a parameter:

```python
traits = {"allergic": "pollen", "glutton": True}
```

When the engine processes an action that involves an item or room with the matching tag:
- Eating something with tag `pollen` → applies `poisoned` condition for N turns
- Entering a room with air tag `pollen` → applies coughing/discomfort
- Equipping something with tag `pollen` → same

The trigger system can also check: `if character has trait "allergic:<X>" and action involves tag "X" → apply effect`.

## Editor UI

### Traits Section

```
🧬 Traits
[+ Add Trait]

Current traits:
[Glutton] [Night Owl] [Allergic: Peanuts ✕] [Blind]
                      [pollen ■]
```

- Click [+] → searchable dropdown of predefined traits
- Some traits accept parameters (allergic → tag input)
- Each shows a tooltip with engine effect description
- [✕] removes trait
- Traits are permanent — no duration

### Conditions Section

```
⚠️ Conditions
[+ Add Condition]

[🔥 Poisoned ⏱ 5] [🦴 Broken Leg ⏱ ∞ (needs treatment)]

Active conditions with remaining duration.
Click condition → set duration, remove, or describe effects.
```

- Conditions auto-decay each turn
- Can be removed manually (GM override)
- Duration shown as remaining turns (∞ for permanent until cured)

### Emotions Section

Already exists — enhance with:
- Description/context field ("Feeling cheerful after talking with Miki")
- History log (previous emotions + triggers)

## Engine Integration

### Trait effects applied in `_update_vitals()`
- Check player traits each tick
- Apply multipliers (glutton → hunger ×2)
- Apply special cases (allergic checks air tags in current room)

### Condition effects applied in `_update_vitals()` and action handlers
- Check active conditions before actions
- Apply damage/penalties per tick
- Decay durations

### Tag checks in item triggers and conditions
- `has_tag: vampire` condition on items/triggers
- `target_has_tag: faction:guard` — check target character's tags

## Files Affected

- `player.py` — ensure `traits`, `conditions`, `tags` stored cleanly
- `virtual_world_engine.py` — trait processing in `_update_vitals()`, condition tick/decay, tag checks in triggers
- `static/js/inspector.js` — traits/conditions/emotions editor in character inspector
- `static/js/api.js` — trait/condition/tag API methods
- `app.py` — trait/condition/tag endpoints

## Implementation

### Engine — `engine/traits.py` (new)
- 23 trait definitions with full effect specs: glutton, cleanfreak, night_owl, morning_person, fast_healer, slow_healer, one_armed, small_bladder, big_bladder, blind, deaf, introvert, extrovert, apathetic, allergic (parameterized), light_sleeper, heavy_sleeper, immortal, dark_vision, darkvision (alias), slasher, is_slasher (alias), hardy
- `TraitSystem` with static methods: `has_trait`, `has_effect`, `get_effects`, `get_action_cost_mods`, `get_vital_multipliers`, `get_sense_blocked`, `get_disabled_slots`, `get_hp_regen_multiplier`, `is_immune_to_condition`, `get_allergen_tag`, `get_energy_curve`, `process_tick_effects`

### Wiring
- **`tick_manager.py`**: Trait action cost mods replace ad-hoc dict iteration. Vital multipliers applied in `tick_turn()`. `process_tick_effects()` handles allergic reactions and energy curves. HP regen multiplier for fast/slow healer.
- **`lighting.py`**: `TraitSystem.has_effect(player, "dark_vision")` replaces ad-hoc `traits.get("dark_vision")`.
- **`player_manager.py`**: `is_slasher()` delegates to `TraitSystem.has_effect(player, "is_slasher")`.
- **`effects.py`**: `handle_apply_trait`, `handle_remove_trait` — add/remove traits via triggers.
- **`trigger_system.py`**: `apply_trait`, `remove_trait` in EFFECT_TYPES. `has_trait` condition type.

### Player model
- **`player.tags`** — new field for identity markers (`["vampire", "faction:guard"]`).
- **`player.to_dict()`** — now includes `traits` and `tags` in API responses.
- Serialization/import/update routes all handle both fields.

### Inspector UI — `static/js/inspector/agent-view.js`
- **Stats tab**: Traits section with colored badges + ✕ remove. Dropdown populated from library to add traits. Parameterized traits prompt for value.
- **Bio tab**: Tags section with badge display + text input + Add button. Remove via ✕.
- Library data loaded async via `ApiClient.getLibraryType('traits')`.

### Library
- 23 trait definition files in `data/library/traits/`.
- Library Browser Traits tab can view/edit metadata.

### Tests
- `tests/test_traits.py`: 57 tests covering all trait definitions, effect resolution, tick processing.
- `tests/test_conditions.py`: 38 tests for condition system.
