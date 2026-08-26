---
group: Conditions
---

# Condition: Dead (`dead`)

**Filed**: 2026-08-17
**Priority**: High
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Terminal state. The character cannot act, cannot move, and drops everything they hold. Hardest of the hard gates.

## Schema (catalog entry)

```python
"dead": {
    "name": "Dead", "description": "Lifeless. No longer part of the living.",
    "blocks_actions": True, "blocks_movement": True, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": ["STR", "DEX", "CON"],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 0.0,
    "movement_mode": None, "drops_held_items": True,
    "periodic": {}, "ends_on": [],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: `blocks_actions` and `blocks_movement` True; `blocks_speech` False (a corpse can't speak as a mechanical rule, but the gate is left off — verify whether that's intended).
- **Saves/checks**: auto-fails STR/DEX/CON.
- **Combat**: neutral mods, but `speed_mult: 0.0` locks movement entirely.
- **Movement**: `drops_held_items: True` — held items drop on death (hooked at combat death).
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`, `default_duration: None`, `excludes: []` — nothing is removed when death applies.
- **Revival**: not handled by this condition alone; a reviver would need to remove `dead` and restore vitals (see `dead`-keyed triggers and the "ally-administered" cure pattern).

## Perception

`known: True` — rendered to observers/agents as lifeless.

## Integration points

- `player.py:41-50` — catalog entry.
- `engine/conditions.py` — `_PERCEPTION_SKIP` (not rendered as a symptom).
- Combat death path → applies `dead` + drops items.
- Cures: `remove_condition dead` via ally-administered items (`target: "target"` + `on_use_on`) per `Conditions System.md` §4.
- `ghost_mode` (dead characters can act) at the system level, not the catalog.

## Testing

- [ ] Death sets `blocked_actions`/`blocked_movement` and speed 0.
- [ ] Holding items drop into the area on death.
- [ ] `remove_condition dead` + vital restore actually revives (with vitals above 0).

## Open questions / things to work out

- Should `blocks_speech` be True for a corpse, or is leaving it off intentional?
- Should `dead` auto-clear all other conditions (many catalogs make death exclusionary)? Currently `excludes: []`.
- Where is the canonical revive flow (which trigger/effect removes `dead`)?
