---
id: 266
title: Condition: Blind (`blind`) — catalog definition + sensory mode
status: review
priority: high
created: 2026-08-17
tags: [conditions, blind, sensory, catalog]
---

# Condition: Blind (`blind`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: In Review — catalog entry in code (`player.py` `CONDITION_DEFINITIONS`); sensory mode
implemented via **task-287** (2026-08-17). Moved here from `todo/conditions/`.
**Source**: Existing catalog (ties into the Blindness sensory-mode design work)

---

## Purpose

Can't see. Sight checks fail; attacks are clumsy. The canonical `auto_fail_checks` gate for the `sight`
sense. The sensory-mode system built on top of it (task-287) treats blindness as **pitch black
regardless of light** and gates visual data at the source.

## Schema (catalog entry — `player.py:165-174`)

```python
"blind": {
    "name": "Blind", "description": "Can't see. Sight checks fail; attacks are clumsy.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": ["sight"], "auto_fail_saves": [],
    "attack_mod": -2, "defense_mod": -2, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": ["duration", "cure"],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": 5,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: none hard — blindness alone doesn't stop moving or acting (`blocks_*` all `False`).
- **Saves/checks**: auto-fails `sight` checks (`auto_fail_checks: ["sight"]`).
  Note: `fumble` is **touch/hearing-based**, so it is NOT auto-failed — it rolls
  `min(2d20) + Perception` vs DC 12 (see task-287).
- **Combat**: `attack_mod -2`, `defense_mod -2` (presence-based; `defense_mod` is the target's defense).
- **Movement**: catalog says full speed (`speed_mult 1.0`), but task-287 adds a **soft** fail chance:
  blind `go` risks **stumble → `prone`** (DC 12, Perception + cane). Not a hard block — the two coexist.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"` (can't blind an already-blind character); `default_duration: 5`;
  ends on `duration` or `cure`.

## Perception

`known: True` — the agent is told they're blind.

## Integration points

- `player.py:165-174` — catalog entry (verified by `test_condition_definitions_catalog`).
- `engine/conditions.py` — `auto_fails_checks(player, "sight")`, combat mods via `get_condition_mods`.
- **Sensory gating (implemented in task-287)** — driven by `has_condition("blind")`:
  - `static/js/agent/prompt-builder/room-context.js` — `isBlind` branch: strips visual detail; emits
    smell/noise/temp; people by audio/scent; items only if known/discovered; exits as sensed;
    `WHAT HAPPENED` filtered to speech events.
  - `engine/movement.py` — blind `go` stumble→prone (unless cane/led); blind `climb`/`jump` DC penalty.
  - `engine/narration.py` — `fumble_around` blind bypass + `_sensory_aid_bonus()` (cane); `listen()` audio scan.
  - `engine/grapple.py` — `lead()` cooperative grab (guided movement while blind).
  - `data/library/items/guiding_cane.json` — `<sensory_aid>` item, `sensory_bonus: 3`.

## Testing

- [x] Catalog entry present and correct — `test_condition_definitions_catalog` asserts
  `blind` `auto_fail_checks == ["sight"]`.
- [x] When blind, room context omits visual detail; audio/scent/touch remain (task-287 live smoke).
- [x] Blind `go` can stumble → `prone`; `lead` drags a blind character (task-287 live smoke).
- [ ] Sight checks auto-fail while blind (unit test for the `auto_fail_checks` path).
- [ ] `attack_mod`/`defense_mod -2` apply in combat (mods verified via `get_condition_mods`).
- [ ] Blindness expires after `default_duration` (5 ticks) or is cured.

## Open questions / things to work out

- **Resolved (2026-08-17, task-287):**
  - Sensory-mode gating keys off the `blind` condition (`has_condition("blind")`), not a
    sight/perception stat or a separate sensory flag.
  - Interaction with spatial movement: guided movement while blind = `lead` (cooperative grab, no
    resist) + stumble risk on unaided `go`. `blind` × `frightened` interplay is still untested.
- **Still open:**
  - Darkness as a separate pathway, or just a low-light variant of this (task-133 light-level area
    descriptions). Task-287's "pitch black regardless of light" only means blind *overrides* light —
    the two systems are not merged.
