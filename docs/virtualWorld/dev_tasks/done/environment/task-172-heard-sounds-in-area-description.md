---
id: 172
title: Heard Sounds in Area Description
status: review
priority: low
created: 2026-08-03
updated: 2026-08-07
tags: [environment, sound, narration]
---

# Heard Sounds in Area Description (look output)

**Status**: In Review — implemented (as log/narration lines, see below). Verified against code on 2026-08-07; pending browser E2E of the in-game log output.

---

## Summary

When a character looks around, the area description should mention sounds coming from **adjacent areas** — "You can hear music from the living room." — not just the room's own ambient noise. Follow-up from task-12 (sound propagation) which built the engine but never surfaced heard sounds to the human player.

## Implementation (how it actually landed)

The behavior is implemented via the **event log / narration lines**, not by appending lines inside the `look` area description (the original design in "Design" below was superseded — see "Deviation").

- **Speech** — `broadcast_speech` in `engine/narration.py:185-230`: propagates speech through open doors via `get_areas_hearing_speech`, stores direction-aware entries in each listener's `recent_hearing` (`heard_from`, `distance`), and logs `format_heard_narration(...)` → "You hear someone speaking from the {direction}."
- **Item sound sources** — `_process_sound_sources` in `engine/tick_manager.py:378-449`: each tick, active sound items (`sound_source` tag) propagate via `get_areas_hearing_sound_source`; characters get `recent_hearing` entries, and the active player gets a log line "You hear {sound_pattern} from the {direction}."
- **Reuse**: both paths use `engine/sound.py::format_heard_narration` (line 281) and the propagation helpers (`get_areas_hearing_speech`, `get_sound_sources_in_area`, `get_areas_hearing_sound_source`).
- **Agent side**: `recent_hearing` already feeds agent prompts (`prompt-builder.js:552-554`), so NPCs are aware of distant sounds too.

## Deviation from original design

The task proposed rendering heard sounds inside the `look` description (`engine/area_description.py`). The implementation instead surfaces them as **tick/narration log entries** ("You hear X from the {direction}.") that appear in the player's event stream, plus `recent_hearing` entries. The `look` output still only renders the room's own ambient noise (`area_description.py:229-231`). If we want the literal `look`-output behavior, that's a follow-up — the propagation engine and player-facing narration already exist.

## Verification

- Code paths traced 2026-08-07: speech propagation (narration.py) and item sound propagation (tick_manager.py) both produce `format_heard_narration` log lines for the active player and populate `recent_hearing`.
- Pending: browser E2E — shout/sound-source in an adjacent open-door room and confirm the "You hear … from the …" line appears in the event log.

## Original Design (for reference)

- In `engine/area_description.py`, after building the players/items sections, query `engine.sound` for sounds reaching the current area:
  - Item sound sources from adjacent areas (via `get_sound_sources_in_area` on neighbors + `get_areas_hearing_sound_source` for reachability).
  - Speech `recent_hearing` entries on the active player (already stored by `broadcast_speech`) for recent speech from other rooms.
- Render as lines like `You hear {sound_pattern} from the {direction}.` using `format_heard_narration`.
- Direction comes from the propagation path (`hearing_areas[area_id] = (remaining_pen, direction)`); origin room has no direction → "nearby".
- Keep it short — one or two lines max, only when something is actually audible (penetration > 0).
