---
group: Environment & Climate
---
# Task: Add `ambient_light_level` to State Response

**Filed**: 2026-07-30  
**Priority**: Medium  
**Status**: Done  

## Summary

The backend's `LightingSystem.light_to_level()` converts numeric light (0-100) to a 5-level string enum (`pitch_black`, `dim`, `normal`, `bright`, `blinding`). The frontend had duplicate copies of this conversion (`PromptBuilder.lightToLevel` in `prompt-builder.js`, `_lightToLevel` in `agent-engine.js`) with slightly different thresholds — meaning they could drift from the backend's authoritative values.

Fix: Include `ambient_light_level` (the string enum) in the `/api/state` response so the frontend reads the backend's converted value directly.

## Changes Made

### Backend: `engine/serialization.py`
- Added `ambient_light_level` to the area serialization dict, alongside existing `ambient_light`
- Refactored to call `get_ambient_light()` once and reuse the value

### Frontend: `static/js/agent/prompt-builder.js`
- `buildRoomContext()` now reads `currentArea?.ambient_light_level` first, falls back to `lightToLevel()` conversion only when missing

### Frontend: `static/js/agent-engine.js`
- `_buildRoomContext()` same change — reads `ambient_light_level` from state first
- Sensory memory light description now uses `ambient_light_level` with a fallback

## Legacy

The `lightToLevel()` and `_lightToLevel()` conversion functions remain as fallbacks for cases where only raw `environment.light` values are available (e.g., exit descriptions reading from raw graph nodes). The graph overlay's `_lightToInt()` reverse conversion unchanged — that's display-only.

## Files Modified
- `engine/serialization.py`
- `static/js/agent/prompt-builder.js`
- `static/js/agent-engine.js`
- `docs/virtualWorld/Environment/Light System.md`
