---
id: 159
title: Saves and Reactions to Actions and Events
status: review
priority: medium
created: 2026-08-02
tags: [combat, skills, gameplay, reactions]
---

# Saves and Reactions to Actions and Events

## Summary

Give characters a chance to avoid traps, attacks, or other events via a saving throw / reaction roll. When something dangerous happens, the character rolls against a relevant stat or skill to dodge, resist, or avoid it.

## Status

**In Review — implemented 2026-08-07.** The unified save primitive + integrations landed together with task-4 (grapple), which was the first consumer of `saving_throw`.

## Problem (original, superseded)

The original write-up said there was "no unified save concept" and proposed adding `saving_throw`. That part is **outdated**: task-4's grapple work added `SkillSystem.saving_throw(player, stat, dc)` (`engine/skills.py:95`), which already:
- rolls `d20 + modifier` vs DC
- supports **any** player object — the active player or NPCs
- logs `[Save] STR vs DC 10: roll 2 + 0 = 2 => failure` to the event stream

What was still missing and is now implemented (2026-08-07):

- `saving_throw` only understood **stats**; now a check name in `{"STR","DEX","CON","INT","WIS","CHA"}` rolls the stat modifier `(value-10)//2`, and **any other name is treated as a skill** (raw skill value). Negative stat modifiers are no longer clamped to 0 (consistent with `skill_check`).
- No trigger condition existed to gate an effect on a save → added **`save_throw`** condition, mirroring `skill_check`, in both the flat item-trigger path (`_evaluate_trigger_condition`) and the AND/OR tree path (`_evaluate_conditions`), for the active player (`target: "self"`) or a named NPC (`target: "<name>"`).
- The damage effect couldn't be resisted → `handle_damage` now accepts an optional **`save`** param: `{"stat": "DEX", "dc": 12, "on_success": "half"|"none"}`. Success halves (default) or avoids the damage; the `[Save] ...` roll is emitted with the damage message. `target` also accepts an explicit character name.
- No facade access → `VirtualWorld.saving_throw(player, stat, dc)` added (`virtual_world_engine.py`), so effects/triggers/routes can call through `game_state`.
- Editor wiring: `save_throw` appears in the trigger editor condition dropdowns (item library, inspector, graph editor) with stat-or-skill + DC + optional target fields, and in the LLM condition lists.

## Design

### One primitive, everyone funnels through it

`SkillSystem.saving_throw(player, stat_or_skill, dc)` is **the** save API. Callers pass the player object (active or NPC) — no `use_active_player` limitation like `skill_check`.

```
saving_throw(player, "DEX", 12)       # stat save (modifier-based)
saving_throw(player, "Athletics", 12) # skill save (raw skill value)
```

Returns `(success, total, message)`; the roll is logged via `add_log_entry`.

### Trigger condition `save_throw`

```json
{"type": "save_throw", "stat": "DEX", "dc": 12, "target": "self"}
{"type": "save_throw", "skill": "Acrobatics", "dc": 10, "target": "Guard"}
```

Success → condition passes → the trigger's effects fire (e.g. a trap you dodged). Pair with a damage effect's `save` param when you want halved damage instead of an all-or-nothing dodge.

### Damage effect with save

```json
{"type": "damage", "params": {"amount": 8, "target": "self",
  "save": {"stat": "DEX", "dc": 12, "on_success": "half"}}}
```

Failed (or absent) save → full `amount`. Successful save → `amount // 2` (`on_success: "half"`, default) or `0` (`on_success: "none"`). The `[Save] ...` message is emitted alongside the damage line.

### Combat stays attack-vs-defense

Deliberately NOT converted to saves (scope decision 2026-08-07): `player_attack` keeps its attack roll vs DEX defense roll. Saves are for traps/hazards/resistance, not melee hits.

## Files Changed

1. `engine/skills.py` — `saving_throw` unified (stats + skills, negative mods, any player)
2. `virtual_world_engine.py` — facade `saving_throw`
3. `engine/trigger_system.py` — `save_throw` condition (flat + tree), `_resolve_save_target`, `_last_save_msg` surfaced in trigger output
4. `engine/effects.py` — `handle_damage` optional `save` param + named target
5. `static/js/item-library.js`, `static/js/shared/trigger-editor.js`, `static/js/inspector.js`, `static/js/shared/trigger-graph.js` — condition dropdowns + fields
6. `static/js/main.js`, `static/js/shared/ai-generator.js`, `static/js/prompt-docs.js`, `static/js/item-library/ai-generation.js` — LLM condition lists
7. Tests: `tests/test_skills.py::TestSavingThrows`, `tests/test_trigger_system.py::TestSaveThrowCondition`, `tests/test_effects_save.py` (new)

## Testing

- [x] Trap trigger with save can be dodged (`save_throw` condition gates the effect)
- [x] Failed save applies full damage, success applies reduced/zero (`handle_damage` save tests)
- [x] Works for NPCs as well as the active player (`saving_throw` takes any player object; named-target trigger test)
- [x] Roll message appears in event stream (log-entry test + `_last_save_msg` surfacing)
- [x] No regression to existing attack vs defense logic (full suite green)
- [x] Full suite: **585 passed, 1 skipped** (was 549 before this task; +36 save tests)

## Related

- [[review/gameplay/task-4-grapple_restrain_system|task-4: Grapple/Restrain]] — first `saving_throw` consumer (STR saves on grab/escape)
- [[todo/gameplay/task-165-chance-to-stun-on-attack|task-165: Chance to stun on attack]]
