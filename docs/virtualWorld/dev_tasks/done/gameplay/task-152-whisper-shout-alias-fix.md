---
group: Tech Debt & Testing
---
# Task 152: Fix Whisper/Shout Clobbered by Alias Normalization

**Filed**: 2026-07-31  
**Priority**: High  
**Status**: Done  

---

## Summary

The `whisper` and `shout` speech commands were silently degrading to normal speech because the verb alias normalization in `routes/action.py` rewrote them to `say` before the speech handler ever saw them. Only `scream` survived (it wasn't in the alias map).

## The Bug

In `routes/action.py`, the alias map contained:

```python
("yell ", "say "),
("shout ", "say "),     # ← clobbered shout → normal speech
("whisper ", "say "),   # ← clobbered whisper → normal speech
```

So `whisper psst` became `say psst` → normal level. `shout hey` became `say hey` → normal level. The sound propagation system (task 149) was built and tested but the commands that feed it were broken at the entry point. Both the direct command route AND the MCP tools (`whisper()`, `shout()`) were affected since they all go through the same `/api/action` handler.

## The Fix

`routes/action.py` alias map:

```python
("yell ", "shout "),  # yell now correctly escalates to shout
```

- `shout` and `whisper` now pass through untouched to the speech handler
- `yell` maps to `shout` (semantically correct — yelling IS shouting)

## Verification

Command parsing now produces the correct levels:

| Command | Level |
|---------|-------|
| `whisper psst` | whisper |
| `shout hey` | shout |
| `scream help` | scream |
| `say hello` | normal |
| `yell fire` | shout |

## Tests

Added 5 regression tests to `tests/test_sound.py` (class `TestSpeechCommandParsing`) that mirror the alias normalization + dispatch logic:
- whisper survives alias map
- shout survives alias map
- scream survives alias map
- yell maps to shout
- say stays normal

**Result**: 26 tests passing in test_sound.py

## Files Modified

1. `routes/action.py` — removed `shout`/`whisper` from alias map, changed `yell` → `shout`
2. `tests/test_sound.py` — added `TestSpeechCommandParsing` regression tests

---

## Quick Win: Sound Source Perception

**Files**: `engine/tick_manager.py`, `static/js/agent/prompt-builder.js`

Two related gaps in the sound propagation system:

1. **Same-area sound sources were inaudible.** `_process_sound_sources()` only notified characters in *adjacent* hearing areas, so a character standing next to a ringing alarm clock got no hearing entry. Fixed by adding the origin area to the notification set (`hearing_areas[area_id] = (sound_level, "")`) before the loop.

2. **Sound sources never appeared in WITNESSED.** The prompt builder filtered out `type === 'sound_source'` entries from `recent_hearing`, so even when a sound propagated, the character never perceived it. Fixed by rendering them as `[Heard from the X from the alarm clock] piercing alarm.`
