---
group: Triggers
---

# Trigger Editor — Group Effects by Target Type

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: In Review — implemented 2026-08-10, no backend changes, JS syntax valid, full test suite unaffected

---

## Implementation

- `static/js/shared/trigger-editor.js` — added `_buildGroupedEffectOpts()` and `_buildGroupedCondOpts()` helpers; both render `<optgroup>` labels. Updated `show()`, `_addEffectRow()`, and `_buildConditionRowEl()` to use grouped options.
- `static/js/inspector.js` — added `group` property to all 20 effect types and all 15 condition types (in both `_addTriggerToNode` and `_editTriggerFromNode`).
- `static/js/item-library.js` — added `group` property to all 25 `ItemLibrary.EFFECT_TYPES` and all 15 `ItemLibrary.CONDITION_TYPES`. `_addConditionRow` uses the same grouped rendering.
- `node --check` passes on all 3 files.
- 824 tests pass, zero regressions.

## Effect Groups

| Group | Label | Effects |
|-------|-------|---------|
| `general` | ⚙️ General | message, teleport, end_scenario, restart_scenario, save, give_item, rename, set_hidden, add_tag, remove_tag, set_state, destroy_self |
| `character` | 🧍 Character | damage, heal, adjust_vital, apply_trait, remove_trait, apply_condition, remove_condition, give_item |
| `item` | 📦 Item | spawn_item, remove_item, adjust_uses, set_description, append_description |
| `way` | 🚪 Way | unlock_way |
| `area` | 🌍 Area/Environment | set_environment, adjust_environment |

## Condition Groups

| Group | Label | Conditions |
|-------|-------|------------|
| `general` | ⚙️ General | — Always fire —, random_chance, time_of_day, speech_matches, state_equals |
| `character` | 🧍 Character | vital, has_trait, skill_check, save_throw |
| `item` | 📦 Item | is_equipped, has_item, uses_reached |
| `area` | 🌍 Area/Environment | area_temp, weather |
| `tag` | 🏷️ Tag | has_tag |

## Verification

- Open trigger editor in inspector and item-library, verify grouped dropdown renders for both effects and conditions
- Add an effect/condition from each group, save, verify it persists
- No backend changes needed (frontend-only)


---

## Problem

The trigger editor's effect dropdown is a flat list of 20+ effect types. Authors have to scan the whole list to find the right effect, especially when some are character-specific (adjust vital, apply condition), item-specific (adjust uses, rename), way-specific (unlock way), or area-specific (set environment).

## Goal

Group the effect type dropdown by target category so authors can find the right effect faster.

## Groups

| Group | Label | Effects |
|-------|-------|---------|
| `general` | ⚙️ General | message, teleport, end_scenario, restart_scenario, save, spawn_item, give_item, destroy_self |
| `character` | 🧍 Character | damage, heal, adjust_vital, apply_trait, remove_trait, apply_condition, remove_condition, give_item |
| `item` | 📦 Item | remove_item, adjust_uses, rename, set_description, append_description, set_hidden, add_tag, remove_tag, destroy_self |
| `way` | 🚪 Way | unlock_way, set_state |
| `area` | 🌍 Area/Environment | set_environment, adjust_environment |

Note: some effects are cross-cutting (set_state, set_description work on any node). They're placed in the most common target group.

## Implementation

- `static/js/inspector.js` — add `group` property to effect types in both `_addTriggerToNode` and `_editTriggerFromNode`
- `static/js/item-library.js` — add `group` property to `ItemLibrary.EFFECT_TYPES`
- `static/js/shared/trigger-editor.js` — add `_buildGroupedEffectOpts()` helper, render `<optgroup>` labels in the effect `<select>`; update `_addEffectRow()` to use grouped options

## Verification

- Open trigger editor in inspector and item-library, verify grouped dropdown renders
- Add an effect from each group, save, verify it persists
- No backend changes needed (frontend-only)
