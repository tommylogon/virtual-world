---
group: Trigger System
wiki: "[[World Building/Doors & Connections]]"
---

# `requires_open` Trigger Type for Doors

**Filed**: 2026-07-19
**Priority**: Low — review / optional
**Status**: Implemented but unused

## Summary

A new trigger type `requires_open` was added to the door movement system in `virtual_world_engine.py`. When a door has a `triggers` edge with `trigger_type: "requires_open"`, its conditions are evaluated before auto-opening. If any condition fails, the door stays shut and a fail message is shown.

This is redundant with `needs_open` (a property on the door node that gates passage behind a skill check). Both serve the same purpose — preventing auto-open — just through different mechanisms.

## Current Behavior

When `go [direction]` hits a closed door:

```
if state == "locked":          → blocked, key required
if needs_open.enabled:         → blocked, skill check (Athletics DC N)
if requires_open triggers:     → blocked if conditions fail (new, redundant)
else:                          → auto-open, walk through
```

## Review Question

Should `requires_open` be kept as an alternative approach for door gating? It allows conditions (like `has_item`, `state_equals`) rather than just skill checks. But `needs_open` already covers the most common case. If kept, update the door editor UI in the inspector to support adding `requires_open` trigger edges.

## Files Affected

- `virtual_world_engine.py` — `move_to_area()`: added `requires_open` trigger check before auto-open