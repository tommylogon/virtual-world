---
group: Conditions
---

# Condition: Charmed (`charmed`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

Magically (or socially) compelled by someone. You can't bring yourself to hurt them. Hidden by default so the charmed character doesn't necessarily know they've been influenced.

## Schema (catalog entry)

```python
"charmed": {
    "name": "Charmed", "description": "Magically compelled by someone. You can't bring yourself to hurt them.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": 0, "defense_mod": 0, "speed_mult": 1.0,
    "movement_mode": None, "drops_held_items": False,
    "periodic": {}, "ends_on": [],
    "known": False, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: none hard (no `blocks_*`).
- **Saves/checks**: none.
- **Combat**: neutral stat mods — the "can't hurt the charmer" is a **behavioral/source gate**, not a stat mod (mirroring `frightened`'s source-held gating). The charmer is tracked in `source`.
- **Movement**: full speed.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`; `default_duration: None`; `ends_on: []`.

## Perception

`known: False` — hidden. No symptoms defined yet, so the agent currently gets **nothing** from `charmed`. This is deliberate for subtle compulsion, but "nothing" may need review.

## Integration points

- `player.py:205-214` — catalog entry.
- `engine/conditions.py` — `perceived_conditions` (hidden; no symptoms → no line).
- Source: charmer (`source`), likely `source_type: "character"`.
- Behavior/action gating: blocking attacks on the charmer is similar to `frightened_block` but not yet wired — needs an explicit gate or prompt-level handling.

## Testing

- [ ] Charmed character is unable to harm the charmer.
- [ ] Hidden (`known: False`) with no symptoms → agent perceives nothing from the condition.
- [ ] Charmed does not block acting/moving generally.

## Open questions / things to work out

- **How is "can't hurt the charmer" actually enforced?** Currently no gate uses `charmed` the way `frightened_block` uses `frightened`. Needs a `charmed_block` (or source-gate) + possibly `auto_fail` on attack-rolls against the source.
- Should `charmed` render *some* subtle symptom ("you feel oddly fond") vs. total silence?
- Interaction with `frightened` (both source-gated, could compose).
