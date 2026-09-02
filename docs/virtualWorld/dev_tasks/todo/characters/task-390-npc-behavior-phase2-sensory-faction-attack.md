---
group: Characters
---

# NPC Behavior Phase 2: Sensory Triggers, Faction Logic, Attack

**Filed**: 2026-09-02
**Priority**: High
**Status**: Idea
**Depends**: Phase 1 (task-xxx-npc-behavior-phase1-memory-emotion-hide)

---

## Summary

Builds on Phase 1 to add sensory awareness (smell, sight, sound), tag-based faction logic, and the `attack` behavior action. This enables NPCs to react to what they sense, form factions, and engage in combat — all without LLM agents.

## Current State

Phase 1 adds `add_memory`, `set_emotion`, `set_flag`, `hide_in`, `unhide` + conditions. Phase 2 adds sensory triggers, `player_has_tag`, `flag_equals`, `attack`, and schedule support.

## New Behavior Actions

### `attack`
Make the NPC attack a target.
```json
{ "type": "attack", "target": "player" }
```
- Delegates to `CombatSystem.attack(char_name, target_name)`
- Uses existing combat resolution (skill checks, damage, equipment)
- `target`: `player`, `self`, or specific character name

## New Behavior Conditions

### `player_has_tag`
Check if the player has an item with a specific tag in inventory.
```json
{ "type": "player_has_tag", "tag": "food" }
```
- Scans `player.inventory` + `player.equipped` for items where `tags` includes the value
- Works on the active player

### `flag_equals`
Check a flag value on any character.
```json
{ "type": "flag_equals", "key": "player_fed_me", "value": true, "target": "self" }
```
- `target`: `self`, `player`, or character name
- Reads from `player.flags` dict (added in Phase 1)

### `sound_above`
Check if a sound's strength exceeds a threshold.
```json
{ "type": "sound_above", "threshold": 0.6 }
```
- Reads `player.recent_hearing` or a sound event in context
- Only valid during `on_tick` or sound-related triggers

## New Triggers

### `on_tick`
Already exists. Used for all sensory/polling checks.

### `schedule_tick` (new)
Fires on a time-based schedule for routines.
```json
{ "trigger": "schedule_tick", "time": "09:00" }
```
- `time`: HH:MM string
- Fires once per day at the specified time
- Alternative: `schedule` array on NPC with `{time, area, activity}` entries

## Sensory Model

### Smell Detection

NPCs detect items with specific tags in their current area.

**Condition** (polled via `on_tick`):
```json
{ "type": "smell_detected", "tag": "food", "range": 0 }
```
- `tag`: item tag to detect (e.g. "food", "blood", "smoke")
- `range`: 0 = same area, 1 = adjacent areas, etc.
- Checks items in area (and adjacent areas if range > 0) for matching tags

### Sight Detection

NPCs detect what the player is holding or wearing.

**Condition**:
```json
{ "type": "sight_holds", "tag": "weapon" }
```
- Checks if the active player has an equipped/carried item with the tag
- Same-area only (NPC must "see" the player)
- Hidden players are NOT visible — returns false if target player is hidden

### Sound Detection

NPCs react to sounds above a threshold.

**Condition**:
```json
{ "type": "sound_above", "threshold": 0.5 }
```
- Fires when a sound event occurs in the same/adjacent area
- Threshold filters minor sounds (footsteps) from major ones (screams, explosions)

## Faction Logic Example

Guard NPC attacks non-faction characters:
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "character_has_tag", "tag": "faction_guards", "target": "triggering" }
  ],
  "actions": [
    { "type": "message", "text": "Halt! You're not one of us." },
    { "type": "add_tag", "tag": "hostile", "target": "self" },
    { "type": "attack", "target": "triggering" }
  ]
}
```

## Routine/Schedule Example

Shopkeeper opens at 9, closes at 6:
```json
{
  "trigger": "schedule_tick",
  "time": "09:00",
  "conditions": [],
  "actions": [
    { "type": "go", "area": "Shop" },
    { "type": "speak", "text": "The shop is now open!" }
  ]
}
```

## Required Changes

### Backend

1. `engine/triggers/behaviors.py` — add `attack` action handler
2. `engine/triggers/condition_tree.py` — add `player_has_tag`, `flag_equals`, `sound_above`, `smell_detected`, `sight_holds` evaluators
3. `engine/triggers/constants.py` — add new condition types to `CONDITION_TYPES`
4. `engine/npc_behaviors.py` — add schedule evaluation (check time, fire behaviors)
5. Sound propagation — ensure sounds reach adjacent areas for `sound_above`

### Frontend

1. `static/js/inspector/behaviors-view.js` — add new action/condition types to editor dropdowns
2. `static/js/shared/trigger-types.js` — expose new conditions in JS editor

### Data Model

1. `player.py` — ensure `recent_hearing` or sound event infrastructure exists
2. `engine/scene_snapshot.py` — expose sound data for condition evaluation

## Issues to Consider

- **Sound propagation**: How far do sound travel? Through closed doors? Need clear rules.
- **Smell range**: Checking adjacent areas requires iterating edges — keep performance in mind.
- **Attack from hidden**: Can a hidden NPC `attack`? (Recommendation: yes — hiding is stealth, not pacifism)
- **Schedule precision**: `schedule_tick` fires once per day at the time. What if the NPC is in combat/sleeping? (Recommendation: skip if busy)
- **Faction tags on players**: Players need a way to gain faction tags. This could be via triggers (e.g., `add_tag` when wearing a uniform) or manual assignment.

## Audit

**Status**: Ready to implement after Phase 1
**How to test**:
- Create a guard NPC with faction logic. Have a player with/without faction tag enter. Verify reaction differs.
- Create a cat NPC with `smell_detected` condition for "food" tag. Give player a food item. Verify cat approaches.
- Create an NPC with `schedule_tick` at a specific time. Advance time. Verify routine fires.
- Create an NPC with `attack` action. Trigger it. Verify combat initiates.

## Files Affected

- `engine/triggers/behaviors.py` — `attack` action
- `engine/triggers/condition_tree.py` — new conditions
- `engine/triggers/constants.py` — register new conditions
- `engine/npc_behaviors.py` — schedule evaluation
- `static/js/inspector/behaviors-view.js` — UI for new types
- `static/js/shared/trigger-types.js` — JS condition definitions
- `player.py` — ensure sound/faction infrastructure
