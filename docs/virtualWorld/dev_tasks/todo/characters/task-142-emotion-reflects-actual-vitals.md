---
group: Prompt & Narrative Quality
---
# Emotion Should Reflect Actual Vitals/State

**Filed**: 2026-07-30
**Priority**: Medium
**Status**: Design

---

## Problem

The emotion system (`player.emotion`) is currently set via triggers, action outcomes, or API calls — but it doesn't automatically reflect the character's actual physical state. A character can be shivering, exhausted, thirsty, and desperate for a bathroom, yet the prompt says "Kaelen Voss is quite relieved but vigilant."

## Requirements

- Emotion should be dynamically derived from vitals if no explicit emotion has been set recently
- `buildEmotionContext()` (or a new function) should aggregate physical state signals and produce a coherent emotional summary
- Signals to consider:
  - Energy < 25 → tired/irritable
  - Hunger/Thirst < 25 → desperate/focused
  - Entertainment < 25 → bored/restless
  - Sanity < 25 → paranoid/fractured
  - Temperature < 35 → cold/distressed
  - Temperature > 38 → hot/agitated
  - Bladder > 75 → uncomfortable/distracted
  - HP < 50 → pained/weak
  - State is "sleeping" → groggy/disoriented (if woken)
  - State is "dead" → detached/calm (ghost)
- If an explicit emotion was set recently (within N ticks), prefer that

## Scope
- `static/js/agent/prompt-builder.js` — `buildEmotionContext()` or `describeVitals()` 
- Or backend — generate emotion text server-side

## Related
- `developer ideas.md` — emotion not matching vitals
