# Light Levels: Align Agent Engine Thresholds with Backend Enum

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: Done (2026-07-17) — Phase 1: Agent prompt alignment

---

## Summary

Area light is a percentage (0-100) with a backend conversion function `_light_to_level()` that maps to 5 enum levels: **pitch_black** (≤20), **dim** (≤40), **normal** (≤70), **bright** (≤90), **blinding** (>90). 

The frontend agent engine had hardcoded numeric thresholds (≤10, ≤25) that didn't match the backend. This caused the agent's prompt to misrepresent what actions the backend would actually allow.

## What Was Done

### Phase 1 — Agent prompt alignment (`2026-07-17`)

1. **Added `_lightToLevel(val)` helper** in `agent-engine.js:659-666`— mirrors the backend's `_light_to_level()` in Python:
   - ≤20 → `pitch_black`
   - ≤40 → `dim`
   - ≤70 → `normal`
   - ≤90 → `bright`
   - >90 → `blinding`

2. **Updated `_buildRoomContext`** (`agent-engine.js:668-698`) to use enum comparison instead of mismatched numeric thresholds:
   - `pitch_black`: "You cannot see anything. Use a light source." + no items shown
   - `dim`: "Only large objects visible. Fine actions limited." + only heavy items (weight ≥ 3)
   - `normal`/`bright`/`blinding`: all non-hidden items shown

### File changed

- `static/js/agent-engine.js`

## Remaining Work (Future Phases)

- Migrate the room property storage from 0-100 integer to enum string everywhere
- Replace the light slider in room inspector with a dropdown
- Update create-room modal and AI generation format hints
- Update trigger condition/effect UI for new enum values
- Update `world_template.json` default values
