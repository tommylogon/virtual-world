---
group: Combat & Abilities
wiki: "[[Environment/Light System]]"
---
# Proximity-Based Detection (EMF Reader, Future Tools)

**Filed**: 2026-07-18
**Priority**: Medium
**Status**: Not Started

## Summary

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
