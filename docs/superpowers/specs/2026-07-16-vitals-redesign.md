# Vitals/Needs System Redesign

**Date**: 2026-07-16
**Status**: Draft

## Summary

Overhaul the vitals/needs system to make each vital mechanically meaningful, add new interaction loops, and introduce progressive LLM insanity prompts at low Sanity.

## Change List

### 1. Energy = 0 → Unconscious

**Before**: Energy=0 → HP -1/turn  
**After**: Energy=0 → player state flips to `"unconscious"`, `state_timer = 5`

- While unconscious: no vitals decay (body preserves), Energy recovers at +3/turn (same rate as sleeping)
- State timer ticks down each turn; when it hits 0, player wakes with Energy = 10-15
- Other NPCs can wake the player early with a "revive" action
- Remove the HP-drain-at-zero from Energy entirely
- Narrative consequence is incapacitation (collapse from exhaustion), not death

### 2. Hunger/Thirst = 0 → HP Drain (adjusted numbers)

**Before**: Hunger=0 → HP -2/turn, Thirst=0 → HP -5/turn  
**After**:

- Hunger=0 → HP -1/turn (~20 hours to die from full HP at 5 min/turn)
- Thirst=0 → HP -2/turn (~10 hours from full HP)
- Both=0 → HP -3/turn (~6.6 hours from full HP, compounding)

This puts starvation as a multi-day threat and dehydration as more urgent.

### 3. Sanity → HP Drain + LLM Insanity Tiers

**Before**: Sanity=0 → HP loss, death labeled "madness"  
**After**: Keep death path. Add progressive LLM prompt injection:

| Sanity Range | Label | LLM Prompt Injection |
|---|---|---|
| 75-100 | Sound | Normal. Emotion unaffected. |
| 50-75 | Unsettled | "Something feels wrong. You can't shake the feeling you're being watched." Emotion drifts toward **fear/paranoia**. |
| 25-50 | Strained | Mid paranoia: "You hear faint whispers... was that shadow always there?" Emotion drifts toward **irritability/anger**. |
| 10-25 | Fractured | Strong delusions: "Reality feels thin." + sensory hallucinations. Emotion drifts toward **rage/aggression**. |
| 0-10 | Broken | "You no longer trust your own mind." Random false memories, garbled room data (wrong items, wrong exits). Emotion locked to **frenzy/panic**. |

**LLM context**: New `_buildInsanityContext(sanity)` function in `agent-engine.js` generates tier-appropriate injection text. Appended to the prompt before each `step()`. At < 25, the room description sent to the LLM may be randomly garbled (missing items, phantom items, wrong exit names).

### 4. Bladder ↔ Thirst → Hygiene Cycle

**Before**: Bladder decays at -1/turn regardless, Hygiene at -1/turn regardless  
**After**:

Bladder decay rate scales with Thirst:
- Thirst > 75: Bladder -3/turn
- Thirst 50-75: Bladder -2/turn
- Thirst 25-50: Bladder -1/turn
- Thirst < 25: Bladder -0/turn

When Bladder hits 0 → Hygiene -30 (accident).

**Relieve action**: 
- Use a bathroom/latrine/toilet item → Bladder resets to 100, clean
- Relieve in place → spawns `item_puddle` (or similar) in current room with `tags: ["filth", "stench"]` and environmental effect `stench: "urine"` → ongoing Hygiene decay for anyone in the room
- Puddle can be cleaned (use a rag/mop) or dries after N ticks

### 5. Hygiene → NPC Perception

**Before**: No social consequence  
**After**:

- NPC reaction modifier: `-floor((100 - hygiene) / 20)` → -0 at 100, -5 at 0
- LLM prompt injection when interacting with a low-hygiene character: "You notice {name} smells terrible / looks unkempt" at Hygiene < 50

### 6. Social → Conversation Gain

**Before**: Baseline -1/turn, environment alone -1, with others +1, perfume +1  
**After**:

- Talking to another character (including NPC social actions): Social +2 per turn of conversation
- Talking to self (alone, muttering): Social +1 (slower but prevents isolation despair)
- Remove the current "alone = extra -1" environmental penalty (covered by Entertainment model instead)
- Baseline decay stays -1/turn

### 7. Entertainment → Examine/Use Gain

**Before**: Only baseline -1/turn and alone penalty  
**After**:

- Successfully examining a new item: Entertainment +2
- Using an item: Entertainment +1
- Discovering a new room: Entertainment +5 (first-time bonus, tracked by a per-character set of visited areas)
- Baseline decay stays -1/turn

### 8. Social + Entertainment → Sanity Link

**Before**: Being alone → Sanity -1  
**After**:

- Social < 50: Sanity -1/turn
- Social < 25: Sanity -2/turn
- Entertainment < 50: Sanity -1/turn
- Entertainment < 25: Sanity -2/turn
- Both < 50 at same time: Sanity -3/turn (compounding)
- This replaces the simple "alone = -1 Sanity" environmental effect

## Implementation Order

1. **Backend — `tick_turn()` in `virtual_world_engine.py`**:
   - Remove Energy=0 HP drain, add unconscious state transition
   - Adjust Hunger/Thirst HP drain rates
   - Add Bladder decay scaling with Thirst
   - Add Hygiene penalty when Bladder hits 0
   - Add Social gain from conversation (Social → Sanity link)
   - Add Entertainment gain from examine/use (Entertainment → Sanity link)
   - Add puddle item spawning on relieve-in-place
   - Add Hygiene NPC reaction modifier

2. **Backend — `app.py`**:
   - Add `POST /api/action/relieve` endpoint (or integrate into existing action system)
   - Add puddle cleaning action

3. **Frontend — `agent-engine.js`**:
   - Add `_buildInsanityContext(sanity)` function
   - Inject insanity context into LLM prompt before each `step()`
   - Garble room data for LLM at < 25 Sanity
   - Track visited areas per character for Entertainment first-bonus
   - Inject Hygiene description into character context for NPC interactions

4. **Frontend — `ui-controller.js` / `inspector.js`**:
   - Update vital bars display if needed

## Files Changed

| File | Change |
|---|---|
| `virtual_world_engine.py` | `tick_turn()` major rewrite; new `_spawn_puddle()`; new relieve action |
| `app.py` | Add relieve/clean actions if needed |
| `agent-engine.js` | Add `_buildInsanityContext()`; modify `_buildRoomContext()` for garbling; modify `step()` for injection |
| `world_template.json` | May need puddle item template |
