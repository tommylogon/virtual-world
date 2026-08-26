# Task 110: See-Through Windows (visible_in_direction for closed doors)

**Status**: Done
**Priority**: High
**Filed**: 2026-07-26
**Implemented**: 2026-07-26
**Files**: `engine/area_description.py`, `engine/lighting.py`, `docs/virtualWorld/World Building/Doors & Connections.md`

---

## Summary

`visible_in_direction` text (the custom "what you see beyond" description on room→door edges) was only shown when the door state was `"open"`. Windows — doors you can see through but not walk through — were impossible without building the description into the door node's `description` field, which conflates the door itself with what's visible beyond it.

## Solution

Added `see_through` boolean property on door nodes. When `true`:

1. **`visible_in_direction` shown regardless of state** — `engine/area_description.py:300-302` checks for `see_through` in the `else` branch (door not open). If both `see_through` and `visible_in_direction` are set, renders the peek-through text instead of the door's description + state.

2. **Light spills through** — `engine/lighting.py:54` now includes `see_through` doors alongside open doors for light propagation.

3. **Documentation** — Windows section added to `Doors & Connections.md` with:
   - Properties table (current_state, see_through, description, cost, visible_in_direction, auto_close)
   - Four patterns: decorative, see-through, skill-gated, light spill
   - Movement flow: windows are closed doors; use `requires_open` trigger with impossible condition to prevent accidental auto-open
   - Light spill mechanics

## Usage

```json
// Door node
{
  "id": "way_bedroom_window",
  "type": "way",
  "name": "bedroom_window",
  "properties": {
    "current_state": "closed",
    "description": "A large window overlooking the garden.",
     "visible_in_direction": "Through the window you see the moonlit garden below.",
    "see_through": true,
    "cost": {"energy": 3, "time": 2}
  }
}

// Room→door edge
{
  "direction": "north",
 
}
```

Exit renders as: `[north] Through the window you see the moonlit garden below.`
