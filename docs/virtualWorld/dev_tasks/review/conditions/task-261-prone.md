---
group: Conditions
---

# Condition: Prone (`prone`)

**Filed**: 2026-08-17
**Priority**: Medium
**Status**: In code — `player.py` `CONDITION_DEFINITIONS`
**Source**: Existing catalog

---

## Purpose

On the ground. You can only crawl and fight clumsily. Distinct per-instance semantics matter here (a broken leg `prone` vs. a knock-down `prone`).

## Schema (catalog entry)

```python
"prone": {
    "name": "Prone", "description": "On the ground. You can only crawl and fight clumsily.",
    "blocks_actions": False, "blocks_movement": False, "blocks_speech": False,
    "auto_fail_checks": [], "auto_fail_saves": [],
    "attack_mod": -2, "defense_mod": -2, "speed_mult": 0.5,
    "movement_mode": "crawl", "drops_held_items": False,
    "periodic": {}, "ends_on": ["stand"],
    "known": True, "symptoms": {}, "stack": "noop", "default_duration": None,
    "excludes": [],
}
```

## Behavior breakdown

- **Gates**: none hard — you can still act, move (crawl), and speak.
- **Saves/checks**: none autofailed by the condition.
- **Combat**: `attack_mod -2`, `defense_mod -2`.
- **Movement**: `speed_mult 0.5` and `movement_mode: "crawl"` — `go` becomes crawling; climb/jump are refused in `move_to_area`.
- **Periodic**: none.
- **Lifecycle**: `stack: "noop"`. `default_duration: None`. Ends on `stand`. Per-instance `ends_on` matters: `fix` ends only the broken-leg `prone` instance while `stand` ends a knock-down instance (`end_instances` resolves per instance).

## Perception

`known: True` — self-evident.

## Integration points

- `player.py:101-110` — catalog entry.
- `engine/conditions.py` — `effective_speed`, combat mods; `_PERCEPTION_SKIP` not set (rendered).
- `engine/movement.py` — `movement_mode: "crawl"` gating in `move_to_area` (climb/jump refused).
- `player.end_instances("stand")` / `end_instances("fix")` for per-instance resolution.

## Testing

- [ ] Prone forces crawl movement; climb/jump refused.
- [ ] `speed_mult 0.5` applies; combat mods `-2`/`-2`.
- [ ] `stand` ends a knock-down instance only; `fix` ends a broken-leg instance only.

## Open questions / things to work out

- How is a permanent/broken-leg `prone` distinguished at author time (instance `ends_on: ["fix"]`)?
- Should re-application ever refresh (stack `noop` seems right — you're already down).
