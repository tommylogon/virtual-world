# Social Vital: Communication & Interaction

**Filed**: 2026-07-30  
**Priority**: Medium  
**Status**: Design — audit 2026-08-15: conversation tracking (speech_log, recent_hearing) and `on_speech` trigger type already implemented (trigger_system.py:44, virtual_world_engine.py:719). Remaining gaps tracked in task-227.

---

## Problem

The Social vital decays over time but has no natural way to increase except via manual actions. Characters should gain Social from talking (to others or themselves), and traits should modify how this works.

## Requirements

- **Talking to others**: significant Social gain per conversation exchange
- **Talking to self / monologuing**: small Social gain (better than nothing)
- **Being in a room with others** (even without talking): slow passive Social regen
- **Isolation penalty**: being alone in an area for too long accelerates Social decay
- Traits:
  - `extrovert`: larger gain from talking to others, faster decay when alone
  - `introvert`: smaller gain from talking, slower decay when alone, gains Social from solitary activities
  - `loner`: no gain from talking to others, gains Social from being alone
  - `chatty`: extra gain from each conversation exchange
- Track: conversations per tick (who said what to whom), room occupancy
- Event: `on_speech` triggers Social update

## Related

- [[review/characters/task-28-character_needs_system|task-28: Character needs system]]
- `player.py` — vitals, traits
- `engine/tick_manager.py`
