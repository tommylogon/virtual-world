---
group: Environment & Climate
wiki: "[[Environment/Light System]]"
---
# Sound Propagation Between Rooms

**Filed**: 2026-07-15
**Priority**: Low
**Status**: Done — verified 2026-08-03. Engine propagation built and load-bearing (whisper/shout/scream ranges, NPC hearing). Two optional display items not built (see below).

---

## Summary

Sounds propagate between adjacent areas. A character playing loud music in the living room can be heard in the kitchen — with propagation reduced by door/way state.

## Current State

Originally filed as "sounds are room-local". That is no longer true — a full propagation system exists.

## Implementation (Approach B — built-in propagation) ✅

**`engine/sound.py`** — graph-scan sound propagation:
- `SPEECH_LEVELS` (whisper 0 / normal 1 / shout 2 / scream 3) and `WAY_BARRIERS` (open 0 / closed 1 / locked+blocked+hidden 2).
- `get_way_barrier` — see-through ways (windows, grates) are partial (0.5).
- `get_area_noise_level` — base environment noise minus `sound_absorbing` tagged items.
- `propagate_sound` — BFS through `EDGE_CONNECTION` edges, accumulating barriers per path; returns hearing areas with remaining penetration + direction.
- `get_areas_hearing_speech` / `get_areas_hearing_sound_source` — ambient-noise-dampened entry into propagation.
- `get_sound_sources_in_area` — active items tagged `sound_source` with `sound_level` / `sound_pattern`.
- `format_heard_narration` — direction-aware "You hear X from the north."

**Wiring:**
- `engine/narration.py:125-178` — `broadcast_speech` propagates speech to adjacent hearing areas and stores entries in each listener's `recent_hearing`.
- `engine/tick_manager.py:375-411` — `_process_sound_sources()` emits item sound sources and distributes to hearing areas.
- `static/js/agent/prompt-builder.js:552-554` — `recent_hearing` fed into agent prompts (cross-room sound awareness).
- `engine/tick_manager.py:225` — sleeping characters wake from loud/dripping/scratches noise.
- Tests: `tests/test_sound.py` (incl. `TestSpeechCommandParsing`, propagation cases).

## Not built (optional nice-to-haves, recorded)

- **`look` output** — area description only renders the room's own noise ("The area is noisy with X sounds.", `engine/area_description.py:229`); it does NOT add "You can hear music from the living room." lines for heard sounds from adjacent areas. Agent awareness covers this via prompts.
- **Room inspector "Sounds heard here" section** — no such UI exists.

## Files Affected

- `engine/sound.py` (new, built) ✅
- `engine/narration.py`, `engine/tick_manager.py`, `static/js/agent/prompt-builder.js` (wiring) ✅
- `engine/area_description.py`, room inspector — the two unbuilt display items above, if desired later.

## Related

- Project decision: sound propagation lives in the Python backend (drives NPC awareness, narration, triggers).
- `todo/environment/task-174-fire-mechanic-heat-source.md` (F6) and task-170 fire work use the same graph-scan pattern.
- task-152 (whisper/shout alias + sound-source fixes) builds on this system.
