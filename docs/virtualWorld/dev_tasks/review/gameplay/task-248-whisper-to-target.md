# Task-248: Whisper to a Target

**Status:** In Review — implemented 2026-08-21, moved from todo/
**Source:** `dev_tasks/developer ideas.md` (whisper to target)

## Implemented (2026-08-21)

- `narration.py` `broadcast_speech(..., whisper_target=)` — lenient same-area name resolution; ONLY the
  target gets the hearing entry with content. Everyone else gets a content-free gesture turn event
  (`whispers something to <target>`), so WITNESSED shows the act without the words. No cross-area
  propagation for directed whispers.
- `virtual_world_engine.py` — directed whispers SKIP on_speech area triggers (a door cannot eavesdrop
  on an aside; magic-word puzzles keep using say/undirected whisper).
- `routes/action.py` — human command `whisper to <name>: text` (also `to <name> text`); unresolved
  target falls back to a normal room-wide whisper. `re` import added.
- Frontend `_speakLine(charName, player, speech, volume, target)` — composes `whisper to <t>: ...`
  when volume=whisper + target; wired into human/decision/non-reactive speech paths (react phase stays
  room-wide — its schema has no target field).
- System prompt SPEECH & VOLUME section documents the DIRECTED WHISPER rule.
- Synergy: task-321 salience marks the whispered line `[Heard → addressed to you]` for the target.
- Tests: `tests/test_realism_perception.py::TestDirectedWhisper` (4 tests) + closeness hooks (2).

## Goal

Allow a whisper directed at a specific character/player instead of only a room-wide
whisper — a private aside that only the target hears (currently `whisper` is heard by the
whole room).

## Notes / open questions

- Extend whisper with an optional target (`whisper to <name>: ...`), so a directed whisper
  reaches one listener while an undirected whisper stays room-wide.
- Sound/speech path: does a directed whisper carry through doors for its target, and is it
  shown only to that character (privacy) in the event stream?
- Update prompt examples + COMMANDS table; confirm the LLM schema field for the target.