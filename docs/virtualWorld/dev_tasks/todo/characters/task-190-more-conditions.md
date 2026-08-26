---
group: Characters
---

# More Conditions (wet, injured, bleeding, hypothermia, suffocating, petrified)

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

## Problem

Only basic conditions exist, so there's no way to represent rich states like a body part being wet, an injury, active bleeding, sickness, or hard gates like suffocation and petrification. These states are core to the narrative and currently can't be modelled.

## Design

- Conditions are already multi-instance lists carrying `duration`, `source`, `level`, `periodic`, `symptoms`, `ends_on`, and `gate` fields — build on this existing shape rather than adding new fields.
- **Wet**: attach to an equip slot / garment and feed into the existing insulation math (a wet coat provides less insulation).
- **Injured**: uses `level` (light/moderate/severe) plus `ends_on: ["fix"]` so healing removes it.
- **Bleeding**: uses a `periodic` symptom that spawns a `blood_pool` item and a go-hook that leaves blood trails as the character moves.
- **Hypothermia**: a sickness condition built from the sickness family.
- **Suffocating** / **Petrified**: gate conditions that block or restrict actions.
- **Killer extension**: conditions currently apply to players only; extend them so they can attach to items, ways, and areas too (e.g. a flooded way, an area filling with water).

## Files

- `engine/conditions.py` — extend condition model/processing for new types and item/way/area targets.
- `engine/player.py` — apply wet to insulation math, bleeding symptoms, sickness family.
- `engine/item_actions.py` — condition interactions with items and garments.
- `engine/movement.py` — blood trail go-hook, movement gating.
