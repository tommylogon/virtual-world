---
group: Conditions
---

# Condition: Unconscious (`unconscious`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Knocked out, asleep, or collapsed from exhaustion. Incapacitated until woken or revived. Doubles as the engine-managed sleep/energy-collapse state (`source: "sleep"` has `blocks_speech: False`).

## Schema (catalog entry)

```python
"unconscious": {
    "name": "Unconscious", "description": "Knocked out. Incapacitated until woken or revived.",
    "blocks_actions": True, "blocks_movement": True, "blocks_speech": True,
    "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX"],
    "attack_mod": 0, "defense_mod": -5, "speed_mult": 0.0,
    "movement_mode": None, "drops_held_items": True,
    "periodic": {}, "ends_on": ["wake", "damage", "timer"],
    "known": True, "symptoms": {}, "stack": "refresh", "default_duration": None,
    "excludes": ["awake"],
}
```

## Behavior breakdown

- **Gates**: blocks actions, movement, and speech. Sleep keeps speech open via instance override (`blocks_speech: False`).
- **Saves/checks**: auto-fails STR/DEX.
- **Combat**: `defense_mod -5` — helpless (attacker effectively +5).
- **Movement**: `speed_mult: 0.0`; `drops_held_items: True`.
- **Periodic**: none here — Energy recovery during sleep/unconscious is **engine-managed** in `tick_manager`, not `ConditionsSystem.process_tick`. It is in `engine_managed = {"unconscious"}`.
- **Lifecycle**: `stack: "refresh"`, `default_duration: None`. Ends on `wake` (state clears), `damage` (being hurt wakes), or `timer` (countdown expires). Excludes `awake`.

## Perception

`known: True` but skipped in `_PERCEPTION_SKIP` — not rendered as a symptom line.

## Integration points

- `player.py:51-60` — catalog entry.
- `engine/player.py` `state` property — unconscious is second-highest in `CONDITION_HIERARCHY` (below `dead`).
- `engine/tick_manager.py` — unconscious state machine: recover Energy while `state_timer > 0`, wake at 0.
- `engine/conditions.py` `process_tick` — skipped via `engine_managed`.
- `activities.py` sleep — applies `unconscious` instance with `source: "sleep"`.
- Energy collapse path — applies `unconscious` and drops held items.
- Combat death vs knock-out — `damage` in `ends_on` differentiates.

## Testing

- [ ] Knock-out: `blocks_actions`/`blocks_movement`/`blocks_speech` True, `defense_mod -5`.
- [ ] Sleep instance leaves speech enabled.
- [ ] `state_timer` countdown wakes the character at 0.
- [ ] Taking damage wakes a knocked-out character.
- [ ] Held items drop on unconsciousness.

## Open questions / things to work out

- Should fight-damage always wake someone, or should a heavy blow keep them down (currently `damage` in `ends_on`)?
- Relationship between `drops_held_items` on unconscious vs. keeping grip (compare `paralysed`, which keeps grip).
