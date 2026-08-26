# Equipment & Temperature

## Insulation

Equipped items with an `insulation` property shift the effective ambient temperature before it affects the player:

```python
effective_temp = ambient_temp + sum_of_all_insulation
```

Positive insulation warms (traps body heat), negative cools (wicks heat away). Values **stack** across worn items.

### Examples

| Items | Total Insulation | At -12°C Feels Like | At 35°C Feels Like |
|-------|-----------------|---------------------|---------------------|
| Fur coat (`insulation: 14`) | +14 | 2°C | 49°C |
| Coat + scarf (`14 + 3`) | +17 | 5°C | 52°C |
| EVA suit (`insulation: 15`) | +15 | 3°C | 50°C |

Insulation helps in cold but hurts in heat — the same coat that keeps you warm in a blizzard will cook you in a desert.

## Damage Resistances

Items with the `resistance` tag define type-based damage reduction. These **do not affect temperature** — they only reduce damage from typed attacks:

```json
{ "resistances": { "fire": 5, "cold": 3 }, "tags": ["resistance"] }
```

Applied in:
- **Combat** — when weapon has `damage_type`
- **Environment** — toxic air damage

## Toxic Air Protection

Toxic air damage (HP -3/tick) is mitigated by `toxic_resistant` resistance:

```python
damage = max(0, 3 - toxic_resistance)
```

Any equipped item with the `toxic_resistant` tag grants resistance 3 (fully blocking standard toxic air).

## Migration Notes

Per-type tags (`fire_resistant`, `cold_resistant`, `vacuum_sealed`, etc.) are removed. Use the single `resistance` tag + `resistances` dict instead.

## Key Code Locations

| Concern | File | Lines |
|---------|------|-------|
| Equipment bonuses (insulation) | `equipment_bonuses.py` | 34-99 |
