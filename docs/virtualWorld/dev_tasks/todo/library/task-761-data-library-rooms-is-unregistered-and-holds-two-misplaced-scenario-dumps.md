---
type: task
status: todo
area: library
priority: low
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

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
