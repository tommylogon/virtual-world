---
group: Conditions
---

# Condition: Blushing (`blushing`)

**Filed**: 2026-08-17
**Priority**: Low
**Status**: Planned — task-209 (Arousal State Conditions & Threshold Triggers)
**Source**: Proposed (not yet in `player.py`)

---

## Purpose

A **visual-only** signal — the character is visibly flushed with embarrassment or arousal. Notably, task-209 defines it as having **no mechanical effect**; it exists for appearance/perception.

## Proposed schema

```python
"blushing": {
    "name": "Blushing", "description": "A hot flush spreads across your face.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {},
    "ends_on": ["calm"],
    "known": True,
    "symptoms": {1: "Your cheeks are burning red."},
    "stack": "noop",
    "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown (proposed)

- **Gates**: none.
- **Saves/checks**: none.
- **Combat**: neutral.
- **Movement**: full speed.
- **Periodic**: **none** — no drains or feeds. Purely cosmetic.
- **Lifecycle**: `stack: "noop"`; `default_duration: None` (couple of turns); ends on calming down.

## Perception

`known: True` and **observer-visible** — the value is that *other* characters/agents can perceive the blush even if the character tries to hide it. This is a perception/social signal, not a self-state.

## Integration points space

- `engine/player.py` — `CONDITION_DEFINITIONS` entry.
- Observer perception — does the room/agent description surface a blushing character's state to others?
- Applied by embarrassment/elevated-arousal triggers.

## Testing (proposed)

- [ ] No vitals change while blushing (pure cosmetic).
- [ ] Visible to observers in the room/agent prompt.
- [ ] Clears after calming.

## Open questions / things to work out

- Confirmation this is purely cosmetic (no perception/concentration penalty for embarrassment).
- How other characters perceive it — same `perceived_conditions` path or an observer-facing line?
