---
group: Pleasure System
---

# NPC Perception & Reaction Framework

**Filed**: 2026-08-11
**Priority**: Low
**Status**: Todo

---

## Problem

NPCs can't mechanically "notice" another character's state (hard nipples, blushing, arousal) or react to it (disapprove, approach, comment). Perception is currently LLM-flavor only.

## Design

- **Verified gap:** `engine/npc_behaviors.py:23` `process_npcs_on_combat()` is a stub (`pass`). Simple NPCs get `process_simple_npcs()` on tick; the reaction framework is genuinely new.
- `_calculate_perception_difficulty(npc, player, condition)` — base DC 10, modified by NPC traits (observant/oblivious), ambient light (`engine/lighting.py` `get_ambient_light`, verified), distance, and outer clothing coverage/opacity of the target.
- `process_npc_reaction(npc, player, stimulus_type, stimulus_data)` — roll perception → reaction type (`ignore`/`disapprove`/`approach`/`comment`) driven by NPC traits (prudish, open_minded, attracted).
- Reactions emit via existing event-stream/emote paths (log entry + area description) — reuse `logging_events.py`, don't invent a new channel.
- Only runs when `mature_content` on for sexual stimuli; generic (non-sexual) reactions always active.

## Files

- `engine/npc_behaviors.py` — new perception/reaction methods
- `engine/lighting.py` — reuse `get_ambient_light()` for DC calc
- `engine/pleasure_actions.py` — stimulus event entry points

## Testing

- [ ] High light + observant NPC notices exposed state; dark room hides it
- [ ] Prudish NPC disapproves, open-minded approaches (per social)
- [ ] Reactions appear in event stream / area description
- [ ] Mature toggle off → no sexual perception

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §8, Phase 6
- `task-213 mature traits` (observant/oblivious/prudish traits)
