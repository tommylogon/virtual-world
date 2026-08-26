# Temperature Trigger Integration

## Conditions

The trigger system (`trigger_system.py`) supports two temperature-related condition types:

### `temperature_below`

```python
{
    "type": "temperature_below",
    "value": "10"
}
```

Returns `True` if current room temperature is below the threshold.

### `temperature_above`

```python
{
    "type": "temperature_above",
    "value": "30"
}
```

Returns `True` if current room temperature is above the threshold.

Both look up room temperature from `game_state._get_current_area_id()` → room node → `environment.temperature`.

## Effects

| Effect | What it does |
|--------|--------------|
| `set_environment` | Override temperature (absolute), e.g. `{temperature: 22}` |
| `adjust_environment` | Increment/decrement temperature (relative), e.g. `{temperature: 5}` |

### `set_environment` (`effects.py:241`)

```python
{"type": "set_environment", "params": {"temperature": 35}}
```

Replaces the temperature value entirely. Also sets other environment properties (light, smell, noise).

### `adjust_environment` (`effects.py:357`)

```python
{"type": "adjust_environment", "params": {"temperature": 10}}
```

Adds 10 to the current temperature, clamped to -50..100 range.

## Heat Source Examples

| Source | Effect | How |
|--------|--------|-----|
| Fireplace (lit) | `set_environment` temp=22°C, on_tick +1°C until 28°C | Trigger effect |
| Radiator | On_tick `adjust_environment` +temperature | Trigger effect |
| Open freezer door | On_tick `adjust_environment` -temperature | Trigger effect |

The fireplace uses:
- `on_use` trigger: `set_environment` (temp=22, light=80, noise="crackling fire", smell="woodsmoke")
- `on_tick` trigger: `adjust_environment` (temperature+1), conditioned on `temperature_below: 28`

## Key Code Locations

| Concern | File | Lines |
|---------|------|-------|
| Temperature trigger conditions | `trigger_system.py` | 557-597 |
| Environment trigger effects | `effects.py` | 278-308, 394-428 |
