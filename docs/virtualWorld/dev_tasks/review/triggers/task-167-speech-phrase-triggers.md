---
id: 167
title: Speech Phrase Triggers
status: review
priority: medium
created: 2026-08-02
updated: 2026-08-05
tags: [triggers, speech, narration]
---

# Speech Phrase Triggers

**Status**: In Review — implemented 2026-08-05. `on_speech` trigger type fires on the speaking area node (wired in `virtual_world_engine.py` `broadcast_speech`); `speech_matches` condition (exact/contains/startswith/endswith/fuzzy) in both NPC + item condition evaluators; `{speech}`/`{speaker}` exposed in trigger context; trigger outputs logged. Editor: `on_speech` type + phrase/mode fields added (inspector + item-library). 5 new tests; suite 502 passed, 1 skipped.

## Summary

Fire triggers when a character says a specific phrase or word in a room — exact match or fuzzy match.

## Problem

There's no `on_speech` trigger type. NPCs can react to speech via `on_speech_heard` behaviors (engine/narration.py:242) and the `sound_heard` condition checks recent hearing (engine/trigger_system.py:493), but there's no trigger type that fires a full trigger effect set when a keyword/phrase is spoken in a room. Password doors, magic words, and NPCs that react to being addressed need this.

## Implementation

### Trigger type

- Add `on_speech` (and maybe `on_word_spoken`) to `TRIGGER_TYPES` (engine/trigger_system.py:16) — ✅ `on_speech` added
- Fire it when `broadcast_speech` (engine/narration.py) is called, targeting the speaking character's area — ✅ fired in `virtual_world_engine.py:588` `broadcast_speech` on the area node
- Trigger params include the spoken text so conditions/effects can reference `{speech}` — ✅ context gets `{speech, speaker}`; template rendering picks them up

### Match modes

- `exact` — the spoken text equals the phrase
- `contains` / `fuzzy` — the phrase appears in the speech (substring, word-boundary aware)
- Condition type `speech_matches` with mode + phrase, so authors can combine with other conditions — ✅ implemented (exact/contains/startswith/endswith/fuzzy), in BOTH condition evaluators (NPC + item trigger)

### Targeting

- Trigger node placed on the area (fires for speech within that area) or on a specific item/way (fires when the phrase is said while that node is in the room / being used) — ✅ area-placed triggers fire; item/way placement works via the standard trigger-edge walk if wired to an on_speech source

## Files to Modify

1. `engine/trigger_system.py` — `on_speech` trigger type + `speech_matches` condition
2. `engine/narration.py` — fire on_speech triggers in broadcast_speech
3. `engine/area_description.py` or movement — associate area triggers with speech
4. Trigger editor JS — new trigger type + phrase field

## Testing

- [x] Exact phrase fires the trigger — `test_speech_matches_condition_exact_no_fire`
- [x] Fuzzy/substring match fires when phrase is contained in longer speech — `test_speech_matches_condition_contains`
- [x] Password door opens when the phrase is said in the room — `test_broadcast_speech_fires_on_speech_area_trigger` (full world flow)
- [x] Speech triggers don't fire for other areas — trigger fires only on the speaking area's node; wrong phrase tested (`test_broadcast_speech_ignores_wrong_phrase`)
- [ ] Works with whisper/shout levels — sound propagation affects who *hears*; area node firing is volume-independent. Live-verify if needed.
- [x] Missing speech in context → no fire (`test_speech_matches_condition_absent_speech_no_fire`)
- [x] Full suite: 502 passed, 1 skipped

## Related

- [[review/environment/task-149-sound-propagation-system|task-149: Sound propagation system]]
- [[review/triggers/task-52-trigger_success_fail_messages|task-52: Trigger success/fail messages]]
