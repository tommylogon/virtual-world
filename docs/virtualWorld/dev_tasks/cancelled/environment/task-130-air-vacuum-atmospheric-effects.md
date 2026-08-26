---
group: Environment & Climate
---
# Air Levels, Vacuum & Atmospheric Effects

**Filed**: 2026-07-30  
**Priority**: Low  
**Status**: Design  

---

## Summary

Add air quality/atmosphere as an environmental property for areas. Areas can have no air (vacuum), thin air, poison gas, smoke, or other atmospheric conditions that affect characters over time.

---

## Problem

Currently areas have temperature and light but no concept of air quality. You can't model vacuum in space, smoke-filled rooms, poison gas, or suffocation hazards.

## Requirements

### Area Properties
- `environment.air` — enum or string: `"breathable"` (default), `"thin"`, `"vacuum"`, `"poison"`, `"smoke"`, `"stale"`
- `environment.air_visibility` — visibility range: `"clear"`, `"hazy"`, `"fog"`, `"obscured"` (affects what characters can see/describe)

### Effects on Characters
- **Vacuum / no air**: suffocation damage per tick (HP drain), speech impossible
- **Thin air**: energy drain, speech difficult
- **Poison gas**: HP or vital damage per tick based on gas type
- **Smoke**: coughing (interrupts speech), visibility reduced, eventual suffocation
- **Stale**: minor discomfort, hygiene penalties

### Propagation
- Air can move between connected areas (e.g. smoke spreads from a fire room)
- Use an existing tick-based propagation similar to heat
- Air quality changes when doors open/close

### Interactions
- Items that affect air quality: gas mask (immunity to poison/smoke), air tank (temporary breathable air in vacuum), fan (clears smoke)
- Triggers: `on_air_change`, `on_suffocation`
- UI: show air quality indicator in area description and graph tooltips

## Related

- [[review/environment/task-5-heat_propagation|task-5: Heat propagation]]
- [[review/environment/task-126-tag-based-light-and-heat-sources|task-126: Tag-based light and heat sources]]
