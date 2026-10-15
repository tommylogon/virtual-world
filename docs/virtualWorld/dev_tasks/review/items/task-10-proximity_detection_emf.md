---
area: items
wiki: "[[Environment/Light System]]"
type: task
status: review
priority: medium
---

# Proximity-Based Detection (EMF Reader, Future Tools)

**Filed**: 2026-07-18
**Priority**: Medium
**Status**: Not Started

## What

Items like Elena's EMF reader should be able to detect nearby entities (characters, items, ways, areas) based on proximity in the graph. The EMF reader currently just has a static examine message.

## Requirements

1. **Proximity detection**: When an item has a `proximity_effect` tag or property, it should detect nearby:
   - Characters (living or dead)
   - Special items (the skull, etc.)
   - Doors with certain states
   - Rooms with certain environments

2. **EMF Reader specifically**: On use or examine, check the distance from the player's current room to nearby entities. If a "hotspot" entity (like the crystal skull) is within N areas, the EMF needle flickers more.

3. **Extensible**: The system should support future detection tools (motion sensors, dowsing rods, etc.)

## Design Notes

- Graph distance: number of room-to-room edges between current room and target's room
- Detection threshold: configurable per item (EMF: 3 areas)
- Output: narrative description of the readings
- If the target is in the same room: strong reading
- If adjacent (1 room away): moderate
- If 2+ areas away: faint/unreliable

**Deferred**: Post-merge feature branch. This branch is refactoring/testing only.

## Refactoring Impact (July 2026)

Engine is modular. Create engine/proximity.py following DI. Wire in virtual_world_engine.py. Depends on player position and item graph positions. UI in static/js/inspector/.

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

## Browser UI and intended live verification

Intended UI home: put Elena's EMF reader in inventory → use/examine it from an area with nearby characters, items, ways, and areas → inspect the returned detection list and event stream.

Current availability: the card says the EMF reader currently returns a static examine message. Proximity-based detection is not claimed as implemented.

Live steps when available:
1. Place one character, one item, and one way within the authored detection radius; place a second item outside it. Use the EMF reader.
   - expected: the result identifies only entities inside the range and reports their correct kinds/locations; the outside item is absent.
2. Move the inside character outside the radius and use the reader again.
   - expected: the character disappears from the result while the remaining nearby entities stay listed.
3. Move the reader user to a different connected area and repeat.
   - expected: detection uses graph proximity from the current location, not a stale cached list or display-name guess.
4. Compare the UI result with the graph node IDs and the reader's authored range.
   - expected: every reported entity resolves to the matching node and the static examine sentence is replaced by observed proximity output.

This section is not a claim that proximity detection is implemented today.
