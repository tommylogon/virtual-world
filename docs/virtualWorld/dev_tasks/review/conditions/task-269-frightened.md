---
group: Conditions
---

# Condition: Frightened (`frightened`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Terrified of a specific thing. You can't fight it off and won't go back near it. The most source-aware condition — each instance carries `source` + `source_type` (way/area/item/character) that gate the matching action.

## Schema (catalog entry)

```python
"frightened": {
    "name": "Frightened", "description": "Terrified of something. You can't fight it off and won't go back near it.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": -2, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": [],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: none hard at the condition level — the **source** gates actions via `frightened_block`:
  | `source_type` | Gate |
  |---|---|
  | `way` | Won't use that passage again |
  | `area` | Won't re-enter the area |
  | `item` | Won't touch the item |
  | `character` | Won't approach or attack the character |
- **Saves/checks**: none.
- **Combat**: `attack_mod -2`.
- **Movement**: full speed except source-gated areas/ways.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`; `default_duration: None` (persistent until source is dealt with / removed). `ends_on: []` — no action auto-ends it.

## Perception

`known: True`. With a source, renders specially: `"Terrified of {source}."`

## Integration points

- `player.py:195-204` — catalog entry.
- `engine/conditions.py` — `frightened_block(player, source_type, source_id, source_name)` (line 123); `perceived_conditions` special-cases `frightened` with a source.
- `save` trigger effect (`{"type": "save", "params": {"stat": "WIS", "dc": 12, ...}}`) — applies `frightened` with the node's name as source.
- `save_on` trait events: crawl/climb/jump → `"way"`, enter_area/loud_noise → `"area"`, see_item → `"item"`, combat takes_damage → `"character"`.

## Testing

- [ ] Frightened of a way blocks re-using it; area blocks re-entry; item blocks touching; character blocks approach/attack.
- [ ] Each instance gates only its own source (fear of room A doesn't block room B).
- [ ] `attack_mod -2` while frightened.
- [ ] Perception shows "Terrified of {source}."

## Open questions / things to work out

- How does fear clear (no `ends_on`)? Should a resolve/save, the source being removed, or time clear it?
- Multiple sources of fear → multiple instances; should the strongest dominate?
- Confirmation that `can_speak`/movement truly only gate the matching source type.
