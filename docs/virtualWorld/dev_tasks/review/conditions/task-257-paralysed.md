---
group: Conditions
---

# Condition: Paralysed (`paralysed`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Rigor-locked — cannot move, act, or speak, and fails STR/DEX saves. Unlike `unconscious`, the character **keeps their grip** on held items.

## Schema (catalog entry)

```python
"paralysed": {
    "name": "Paralysed", "description": "Rigor locked. Can't move or act; fails STR/DEX saves. You keep your grip.",
    "blocks_actions": True, "blocks_movement": True, "blocks_speech": True,
    "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX"],
    "attack_mod": 0, "defense_mod": -5, "speed_mult": 0.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": ["duration"],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": 3,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: blocks actions, movement, speech.
- **Saves/checks**: auto-fails STR/DEX.
- **Combat**: `defense_mod -5` (helpless).
- **Movement**: `speed_mult: 0.0`; **keeps grip** (`drops_held_items: False` — distinct from unconscious).
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"` (a fresh paralysis does nothing if already paralysed), `default_duration: 3` ticks, ends on `duration`. No `ends_on` action removes it early — only the countdown.

## Perception

`known: True` — self-evident; rendered with description.

## Integration points

- `player.py:61-70` — catalog entry.
- `engine/conditions.py` — `get_condition_mods`, `auto_fails_saves`, `effective_speed`.
- `can_act`/`can_speak` via `BLOCKING_CONDITIONS` / `blocks_speech`.
- `process_tick` duration countdown (auto-expires).
- Potential source: poison variants, certain traps/effects.

## Testing

- [ ] Paralysis blocks actions/movement/speech; speed 0.
- [ ] Stronger paralysis does not stack/reset (`stack: noop`).
- [ ] Auto-expires after 3 ticks and removes cleanly.
- [ ] Held items are NOT dropped (keeps grip).

## Open questions / things to work out

- Should anything end paralysis early (e.g. an antidote / `cure` in `ends_on`)?
- Gap vs. unconscious: keep grip vs. drop — confirm that's the intended differentiator.
