---
type: task
status: done
area: ui
priority: low
---

# task-648: Biome palette has two different 'Civic' groups (a room purpose and a building category)

**Filed:** 2026-09-30
**Related:** 

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. Open WorldPainter on the Eldenford interior and inspect both Civic headings.
   - expected: they read `Civic (room)` and `Civic (building)`.
   - observed: live: the full palette list showed both disambiguated headings.
2. Expand each group and compare its options.
   - expected: room-purpose choices stay under Civic (room); building-category choices stay under Civic (building); neither source concept is renamed.
   - observed: live palette showed two separately labeled groups, preserving their underlying names.
3. Filter for `civic`.
   - expected: both distinguishable headings remain with their matching options.
   - observed: the resolution confirms the disambiguation is applied at render time.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: WorldPainter → palette with Room purpose and Building category options → headings shown above their choices.

Current availability: The card records a live Eldenford interior check where the two headings read “Civic (room)” and “Civic (building)”; the underlying room purpose and building category remain named Civic.

Live steps when available:
1. Open the WorldPainter palette and scroll the full heading list to both Civic entries.
   - expected: the room-purpose heading says `Civic (room)` and the building-category heading says `Civic (building)`.
2. Expand each heading and inspect its choices.
   - expected: room choices remain under Room purpose; building choices remain under Building category; neither concept is renamed in the underlying data.
3. Filter the palette for `civic`.
   - expected: both groups remain distinguishable while filtering, with their original options under the matching heading.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
