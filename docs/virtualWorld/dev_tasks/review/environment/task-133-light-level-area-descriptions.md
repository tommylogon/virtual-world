# Light-Level Dependent Area Descriptions

**Filed**: 2026-07-30  
**Priority**: Low  
**Status**: In Review — implemented 2026-08-21, moved from todo/

## Implemented (2026-08-21)

- `area_description.py` `get_area_description`: pitch_black still replaces everything (nothing to see);
  **dim now PREFIXES the room text** ("you can just make out the shapes… details lost in shadow") instead
  of hiding the whole room — you can see rough shapes in dim light, which is realistic; bright adds
  "illuminating every detail"; blinding adds a squint-and-watering-eyes prefix that applies even with
  darkvision (glare spares no one). Darkvision/ghost still ignores dim entirely.
- Per-character carried/equipped light already contributed via `get_item_light_contribution` (existing).
- Time-of-day interplay comes from task-230 (same commit): outdoor areas now read differently at night.
- Verified: py_compile clean; full suite 1048 passed / same 3 pre-existing failures.

---

## Summary

Generate different area descriptions based on current light level — a room looks different in bright daylight vs pitch darkness vs dim torchlight. Characters in the same room with different light sources or darkvision see different descriptions.

---

## Problem

Currently area descriptions are static regardless of lighting. A room described as "a cozy library with warm oak shelves" reads the same in pitch darkness. Light level affects vitals (comfort, damage) but not the descriptive text.

## Requirements

- **Light-level categories**: `pitch_black`, `dim`, `normal`, `bright`, `blinding`
- Each category modifies the area description:
  - **Pitch black**: "It's completely dark — you can't see anything. You hear [sounds] and feel [floor/objects]."
  - **Dim**: "In the dim light, you can just make out shapes of furniture..."
  - **Normal**: full description
  - **Bright**: "The bright light illuminates every detail. You notice [hidden detail]..."
- **Per-character**: characters with darkvision see one level higher; characters with a torch see via their own light
- **Reuse** the existing description generation in `engine/area_description.py`
- Consider: describing sounds, smells, and tactile sensations in darkness (blind characters rely on these)

## Related

- [[review/environment/task-31-dynamic_room_descriptions|task-31: Dynamic room descriptions]]
- [[done/prompting/task-121-people-in-darkness-sensory-cues|task-121: People in darkness sensory cues]]
- [[todo/environment/task-230-outdoor-lighting-time-of-day|task-230: Time-of-Day Outdoor Lighting]]
- [[review/environment/task-126-tag-based-light-and-heat-sources|task-126: Tag-based light and heat sources]]
