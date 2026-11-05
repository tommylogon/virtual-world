---
type: task
status: todo
area: library
priority: low
wiki: "[[Library System/Library System Overview]]"
---

# task-761: data/library/rooms is unregistered and holds two misplaced scenario dumps

**Filed:** 2026-10-09
**Related:** task-589, task-645, task-568

## What

data/library/rooms/ holds 3 files but 'rooms' is not in REGISTRY_TYPES and no route reads the dir. fighting_pit.json is a room template {name, description, environment}; mansion.json and world_template.json are full scenario dumps (top-level current_area/players) misfiled there. Decide per file: migrate the room into the registered indoor vocabulary (task-568's data/library/biomes) or register a rooms type; move the two scenario dumps to the right place or delete them with a recorded reason. Do NOT delete rooms on the strength of being unregistered.

## Why

TODO

## How

TODO

## Steps to verify

1. Inspect all three files under `data/library/rooms/` and record which schema
   each contains: the room-shaped `fighting_pit.json` or the two full scenario
   dumps (`mansion.json` and `world_template.json`).
   - expected: each file has a recorded destination decision; no file is
     removed just because its directory is unregistered.
2. After choosing whether rooms become a registered library type or are
   migrated to the existing indoor vocabulary, run the corresponding library
   checker and request the registered catalog from the app.
   - expected: the selected room template is discoverable through the chosen
     registry/API, while neither scenario dump appears as a room template.
3. Load the relocated scenario files only from their selected scenario
   location and confirm they still pass scenario loading.
   - expected: the two scenario definitions remain valid scenario data and are
     not exposed through a room-template catalog.

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Library Browser → room/indoor template catalog, if the
registry decision registers `fighting_pit` there. The two scenario dumps
remain in Scenario Manager's scenario list, not that catalog.

Current availability: the card says `rooms` is absent from `REGISTRY_TYPES`
and no route reads the directory. Therefore no current browser flow can list
these files as room templates, and this card does not invent one before the
registry decision is made.

Live steps when available:
These steps apply after the registry decision is implemented.
1. Open the Library Browser and inspect the registered room/indoor template
   catalog.
   - expected: `fighting_pit` appears once under the selected registered type;
     `mansion` and `world_template` do not appear as templates.
2. Open Scenario Manager and inspect the scenario list.
   - expected: `mansion` and `world_template` appear only if retained as
     scenarios in the chosen scenario location; neither is listed as a room.
3. Select `fighting_pit` from its catalog and use the existing placement or
   creation flow for that chosen library type.
   - expected: the selected template's room name, description, and environment
     are used; no full-scenario player/current-area fields are imported as a
     room.

The browser destination is intentionally conditional on the registry choice;
the current card records no shipped browser surface for this directory.

This section is not a claim that planned UI exists or works today.
