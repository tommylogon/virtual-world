---
group: Trigger System
---

# Trigger to Change View-from-Direction

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

## Problem

What you see through a way should change dynamically. Today the view through a connection is static; a trigger cannot update the scene the player perceives when looking through a door, window, or opening.

## Design

- This is way METADATA â€” `see_through`, `description`, and visibility rules live in `area_description.py`, not on the edge itself.
- A trigger can mutate that way metadata so the same connection shows a different scene based on state.
- Overlaps idea #14 (dynamically changing views); coordinate so they share the same mechanism.

## Files

- `engine/area_description.py` â€” expose way metadata (see_through, visibility) as trigger-mutable state
- `engine/trigger_system.py` â€” trigger type that changes the view-from-direction

