---
group: Gameplay
---
# Relative Facing Map (Forward/Left/Right/Back)

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: Idea

---

## Idea

Map forward, left, right, and back relative to a character, based on cardinal directions and origin ways (where someone is at?)(using the suggested transit tags on areas).

Example (from the ideas doc): if you come from the south, "right" is east and "left" is west; if you come from the west, "right" is south and "left" is north.

## Notes

- Gives the character an orientation derived from the last way/area they entered, so "to your left" resolves to a real direction.
- Builds on the existing cardinal-axis work for areas/ways (`map_editor` cardinal layout) and the character spatial system (`engine/character_spatial.py`).
- Owner note: user believes this is not that hard — likely because the cardinal infrastructure already exists; the remaining work is per-character facing state + direction resolution.

## Related

- `developer ideas.md` lines 20–21
- `engine/character_spatial.py`, map editor cardinal layout, way transit/tags
