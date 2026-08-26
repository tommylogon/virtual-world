---
group: Trigger System
---

# Trigger to Change a Way's Target/Direction/Description

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

## Problem

Want elevators/vehicles/portals that repoint connections dynamically. A way currently points at a fixed area; nothing lets a trigger rewire where a connection leads without manually editing the graph.

## Design

- A way IS a node (`type="way"`); areas connect to it via `EDGE_CONNECTION` edges (graph.py:294).
- The way carries `current_state`, `description`, `tags`, `see_through`, etc.
- Repointing = graph surgery on the connection edges off the way node + mutating its description/state.
- Elevator = an area whose connected way changes by floor.
- Car = a room whose way target changes by location.
- Portal = way target changes by time or conditions.
- Defer a full vehicle queue system for later.

## Files

- `engine/trigger_system.py` — new trigger type that repoints a way's connections
- `engine/effects.py` — effect that rewires edges off a way node
- `graph.py` — helper for reconnecting connection edges safely
- `virtual_world_engine.py` — wiring the new trigger/effect into the engine
