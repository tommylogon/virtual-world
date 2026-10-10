---
area: environment
type: task
status: cancelled
priority: medium
---

# Humidity in Areas

**Filed**: 2026-08-10
**Priority**: Low
**Status**: Todo

---

## Why

Humidity, flooding, and smoke should exist as environmental states in an area. Today an area has no way to express "humid", "flooding", or "full of smoke", so those conditions cannot drive gameplay.

## How

- Model as a condition on the area: `"humid"`, `"flooding"`, `"full of smoke"`.
- Needs a concrete mechanical effect to be worth adding — candidates: drying speed, `effective_temp`, stealth.
- Pick 1–2 uses before adding; do not add a bare flag with no gameplay payoff.

## Files

- `engine/area_description.py` — represent humidity/flood/smoke conditions on an area
- `engine/conditions.py` — define the condition types and their effects

## What

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO
