---
id: 173
title: Room Inspector Sounds Heard Here
status: todo
priority: low
created: 2026-08-03
tags: [environment, sound, ui]
---

# Room Inspector "Sounds Heard Here" Section

## Summary

Add a "Sounds heard here" section to the room/area inspector showing which sounds reach this area from adjacent areas. Follow-up from task-12 (sound propagation), which built the engine propagation but never added the inspector display.

## Problem

Task-12's original design listed a frontend item: *"In the room inspector, show 'Sounds heard here' section listing sounds from adjacent areas."* It was never built — the inspector only shows the room's own `noise` environment value.

## Design

- In `static/js/inspector/area-view.js`, add a "Sounds heard here" block alongside the existing environment display.
- Data source: a small backend route (e.g. `GET /api/areas/<area_id>/sounds`) that calls `engine.sound.get_sound_sources_in_area` on adjacent areas and filters by `get_areas_hearing_sound_source` reachability, returning `{pattern, direction, level}` entries. (Or compute client-side if the graph data is already available in `worldState` — prefer reusing existing state, mirroring how light/heat overlays work.)
- Display: `You hear {pattern} from the {direction}` per entry, or "Nothing audible from adjacent areas." when empty.
- Read-only display; no editing needed.

## Files Affected

- `static/js/inspector/area-view.js` — new section.
- Optional backend route for the sound query (or reuse graph data client-side).
- `static/js/world-state.js` / `static/js/api.js` — data plumbing if a route is added.

## Notes

- Mirror the existing environment info pattern in area-view.js (temperature/light/noise rows) for visual consistency.
- Pure read-only view — this is a debugging/authoring aid, not a gameplay surface.
