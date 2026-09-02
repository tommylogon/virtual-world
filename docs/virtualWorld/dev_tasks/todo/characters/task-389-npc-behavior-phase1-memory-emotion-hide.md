---
group: Characters
---

# NPC Behavior Phase 1: Memory, Emotion, Flags, Universal Hide

**Filed**: 2026-09-02
**Priority**: High
**Status**: Idea

---

## Summary

Simple NPCs (behavior tree) currently have only 10 action types and cannot write to their own character data. This task adds the foundational actions and conditions that enable NPCs to form memories, track emotions, set flags, and hide — closing the gap with agent/player characters.

Hiding is a **universal action** available to all characters (players, agents, and simple NPCs). Items that can be hidden in/behind/under are marked with a `hideable` tag.

## Current State

`engine/triggers/behaviors.py` (`_execute_behavior_actions`) supports only: `message`, `speak`, `llm_respond`, `set_npc_state`, `damage`, `heal`, `set_environment`, `spawn_item`, `teleport`, `go`.

Characters already have `memories`, `emotion`, `tags`, `npc_state` fields — but no behavior actions write to them.

## New Behavior Actions

### `add_memory`
Append to the character's `memories` array.
```json
{ "type": "add_memory", "text": "player fed me", "importance": 6, "tags": ["player", "food"] }
```
- Writes to `player.memories` (same field agents/players use)
- `importance` 1-10 (default 5)
- `tags` array of single-word strings

### `set_emotion`
Set the character's `emotion` field.
```json
{ "type": "set_emotion", "emotion": "curious", "intensity": 0.7 }
```
- `emotion`: string (calm, alert, fearful, aggressive, curious, angry, etc.)
- `intensity`: 0.0-1.0 (default 0.5)

### `set_flag`
Set a persistent key-value flag on the character.
```json
{ "type": "set_flag", "key": "player_fed_me", "value": true }
```
- Writes to `player.flags` dict (new field, `{}` default)
- Value can be any JSON-serializable type

### Hiding via Edge Relationships

Hiding uses the same spatial edge system as item placement (`in`, `on`, `under`, `behind`). A hidden character has a special `hidden` edge to the container/furniture item.

### `hide_in`
Hide inside a container item.
```json
{ "type": "hide_in", "target": "wardrobe" }
```
- Creates a `hidden` edge from character to item with `relation: "in"`
- Target must be in the same area and have `hideable` tag
- Sets `player.hidden = true`

### `hide_behind`
Hide behind furniture.
```json
{ "type": "hide_behind", "target": "curtain" }
```
- Creates a `hidden` edge with `relation: "behind"`

### `hide_under`
Hide under furniture.
```json
{ "type": "hide_under", "target": "bed" }
```
- Creates a `hidden` edge with `relation: "under"`

### `unhide`
Make the character visible again.
```json
{ "type": "unhide" }
```
- Removes the `hidden` edge
- Sets `player.hidden = false`

## New Behavior Conditions

### `npc_emotion_is`
Check the NPC's current emotion.
```json
{ "type": "npc_emotion_is", "emotion": "angry", "operator": "gte", "value": 0.6 }
```
- `operator`: `eq`, `gte`, `lte` (default `eq`)
- `value`: 0.0-1.0 intensity threshold

### `npc_is_hidden`
Check if the NPC is currently hidden.
```json
{ "type": "npc_is_hidden", "value": true }
```
- Checks `player.hidden` boolean OR presence of `hidden` edge

### `character_has_tag`
Check if a character has a specific tag.
```json
{ "type": "character_has_tag", "tag": "guard", "target": "triggering" }
```
- `target`: `self`, `player`, `triggering` (default `self`)
- Checks `tags` field on the target character

## Required Changes

### Backend (`engine/triggers/behaviors.py`)

Add action handlers for `add_memory`, `set_emotion`, `set_flag`, `hide_in`, `unhide` in `_execute_behavior_actions`.

Add condition evaluators for `npc_emotion_is`, `npc_is_hidden`, `character_has_tag` in `engine/triggers/condition_tree.py`.

### Data Model (`player.py`)

Ensure all Player objects have:
- `flags: dict` (default `{}`)
- `hidden: bool` (default `False`)

Hiding itself is stored as a **graph edge** (`hidden` type) from character to item — consistent with existing spatial edges (`in`, `on`, `under`, `behind`). The `player.hidden` boolean is a fast lookup flag; the edge is the source of truth.

### Hideable Items (new tag)

Items that characters can hide in/behind/under get a `hideable` tag:
```json
{ "name": "Wardrobe", "tags": ["hideable", "furniture", "container"] }
```

When a character hides, the engine:
1. Validates target is in same area
2. Validates target has `hideable` tag
3. Creates `hidden` edge with relation (`in`/`behind`/`under`)
4. Sets `player.hidden = true`

When a character unhides:
1. Removes `hidden` edge
2. Sets `player.hidden = false`

Add new action types to the behavior editor dropdown with appropriate parameter fields.

Add new condition types to the behavior condition editor dropdown.

## Examples

### Cat follows player with fish
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "player_has_tag", "tag": "food" },
    { "type": "npc_emotion_is", "emotion": "curious", "operator": "gte", "value": 0.5 }
  ],
  "actions": [
    { "type": "go", "area": "{player_area}" },
    { "type": "speak", "text": "*meows and rubs against your leg*" }
  ]
}
```

### NPC hides from hostile player
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "character_has_tag", "tag": "hostile", "target": "triggering" },
    { "type": "npc_emotion_is", "emotion": "fearful", "operator": "gte", "value": 0.6 }
  ],
  "actions": [
    { "type": "hide_in", "target": "wardrobe" },
    { "type": "add_memory", "text": "hid from hostile player", "importance": 7, "tags": ["player", "fear"] }
  ]
}
```

### Cat hides under bed when scared
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "sound_above", "threshold": 0.7 },
    { "type": "npc_emotion_is", "emotion": "fearful", "operator": "gte", "value": 0.5 }
  ],
  "actions": [
    { "type": "hide_under", "target": "bed" },
    { "type": "add_memory", "text": "hid under bed from loud noise", "importance": 5, "tags": ["sound", "fear"] }
  ]
}
```

### Player hides behind curtain from guard
```json
{
  "trigger": "on_tick",
  "conditions": [
    { "type": "character_has_tag", "tag": "guard", "target": "triggering" }
  ],
  "actions": [
    { "type": "hide_behind", "target": "curtain" }
  ]
}
```

## Issues to Consider

- Hidden characters: can they be found by `search`? Can they `attack` from hiding? (Recommendation: yes to both — hiding is visual stealth, not invincibility)
- Edge persistence: `hidden` edges must survive save/load via `serialization.py`
- Capacity: should we limit how many characters can hide in one item? (Recommendation: not v1 — tag-based only)
- Hidden edge vs spatial edge: can a character hide in an item that also has spatial edges? (Recommendation: yes — `hidden` is a separate edge type)
- Search interaction: `search wardrobe` should reveal hidden characters inside (Recommendation: yes — search examines contents + hidden edges)

## Audit

**Status**: Ready to implement
**How to test**:
- Create a simple NPC with a behavior using `add_memory` action. Trigger it. Verify the memory appears in the NPC's memory inspector.
- Create a behavior with `set_emotion`. Verify the emotion field updates.
- Create a behavior with `hide_in`. Verify the NPC disappears from the area view.
- Create a behavior with `character_has_tag` condition. Verify it only fires for matching characters.

## Files Affected

- `engine/triggers/behaviors.py` — new action handlers (hide_in, hide_behind, hide_under, unhide, add_memory, set_emotion, set_flag)
- `engine/triggers/condition_tree.py` — new condition evaluators (npc_emotion_is, npc_is_hidden, character_has_tag)
- `graph.py` — ensure `hidden` edge type is supported alongside `in`/`on`/`under`/`behind`
- `player.py` — ensure `flags` dict and `hidden` bool fields exist
- `engine/serialization.py` — persist `hidden` edges and `flags` dict
- `static/js/inspector/behaviors-view.js` — UI for new actions/conditions
- `engine/npc_behaviors.py` — edge cleanup on character death/relocation
