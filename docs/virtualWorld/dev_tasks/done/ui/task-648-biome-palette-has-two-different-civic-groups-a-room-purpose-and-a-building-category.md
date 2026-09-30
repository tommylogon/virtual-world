---
type: task
status: done
area: ui
priority: low
---

# task-648: Biome palette has two different 'Civic' groups (a room purpose and a building category)

**Filed:** 2026-09-30
**Related:** 

## Goal

Civic appears in both ROOM_PURPOSES and CATEGORIES in worldpainter/editor.js, so the palette renders two separate 'Civic' headings -- one with 2 options under Rooms, one with 4 under Buildings. An author cannot tell from the heading which they are picking, and the room/building distinction is the whole reason the palette is grouped.

## Acceptance

- [x] Two sections that share a name are distinguishable
- [x] The disambiguation does not rename either concept
- [x] Verified live: the palette headings read "Civic (room)" and "Civic (building)"

## Resolution (2026-09-30)

`civic` is legitimately **both** a room purpose (a town hall is a room) and a
building category (a civic building), so the palette rendered two headings with
the identical name. Filtering for "civic" showed both, and the heading said
nothing about which was which -- in a palette whose whole justification is that
the author is asking a *purpose* question, not a tile question.

Disambiguated at render time rather than by renaming either concept, because
both are right: a label that appears more than once in one palette is suffixed
once as `(room)` and once as `(building)`.

**Verified live**, full heading list on the Eldenford interior:

    Circulation, Living, Sleeping, Cooking, Eating, Storage, Workshop, Worship,
    Records, Trade, Civic (room), Service, Outdoor, Residential, Religious,
    Commercial, Civic (building), Craft, Industrial, Military, Rural,
    Transport, Structure

plus 16 wild-terrain tiles loose at the top.

- TODO
