# Task 353: Social Vital Overhaul — Real Social Mechanics

**Filed**: 2026-08-15  
**Priority**: Medium  
**Status**: Todo

---

## Problem

Social vital currently mixes **social connection** (talking, being with people) with **physical comfort** (humid air penalizes Social, perfume boosts Social). These are separate concerns. The humid/smell effects belong in Hygiene or Entertainment, not Social. Additionally, several defined mechanics are never consumed by the engine.

## Scope

### Remove — physical comfort masquerading as social

| Current behavior | File | Fix |
|-----------------|------|-----|
| `air == "humid"` → `-1 Social/tick` | `tick_manager.py:256` | Move to Hygiene decay (`p.vitals["Hygiene"] = max(0, p.vitals["Hygiene"] - 1)`) |
| `smell == "perfume"` → `+1 Social/tick` | `tick_manager.py:284` | Move to Entertainment boost (`p.vitals["Entertainment"] = min(100, p.vitals["Entertainment"] + 1)`) |

These are sensory/physical comfort effects. A character can be socially fulfilled in a humid room, and miserable in a perfumed one if alone.

### Implement — real social mechanics

#### 1. Isolation timer + accelerated decay

Track consecutive ticks spent alone in an area. After a threshold (e.g., 5 ticks), Social decay accelerates:

```python
# Pseudocode per player per tick:
if len(others_here) == 0:
    p._alone_ticks = getattr(p, "_alone_ticks", 0) + 1
    if p._alone_ticks >= 5:
        p.vitals["Social"] = max(0, p.vitals["Social"] - 2)  # accelerated
else:
    p._alone_ticks = 0
```

Threshold and rate are tunable. Introverts get a higher threshold.

#### 2. Consume SOCIAL_GAIN from traits

Currently everyone gets flat +1/tick near others. Traits should modulate this:

- `extrovert` (SOCIAL_GAIN=2): +2/tick when others present
- `introvert` (SOCIAL_GAIN=0): +0/tick from presence alone (still gains from speech)
- Default (no trait): +1/tick

Replace the hardcoded `+1` in `tick_manager.py:290` with a TraitSystem lookup.

#### 3. Self-talk / monologue social gain

When a character speaks but no other living character is in the same area, give a small Social gain (+1) — better than nothing, but less than real conversation. Hook into `narration.py broadcast_speech()`.

Check after the listener loop: if no listeners received the speech, apply +1 to speaker.

#### 4. New traits

**`loner`** (mental category):
- Gains +1 Social/tick when alone (reverses isolation penalty)
- No SOCIAL_GAIN bonus from presence (same as introvert)
- Conflicts with `extrovert`
- Description: "Solitude recharges you. Being alone restores your social well-being."

**`chatty`** (mental category):
- +2 extra Social gain per speech exchange (so +7 speaker, +5 listeners instead of +5/+3)
- No isolation modifier
- Description: "You talk easily. Conversations come naturally and leave you feeling connected."

#### 5. Behavioral gates at low Social

Low Social should influence AI decision-making, not just narration. Inject into prompt state:

- `< 50`: Add flag `social_need: moderate` — agent should consider speech action more often
- `< 25`: Add flag `social_need: desperate` — agent prioritizes finding people, may ramble/beg/speak without purpose
- `< 10`: Add condition `social_breakdown` — unpredictable behavior, random speech, possible hallucination narration

These flags feed into the agent's decision prompt so the LLM actually acts on them.

### Testing in Labs

Scenario setup: characters with different traits placed in controlled environments.

| Test | Setup | Expected |
|------|-------|----------|
| Baseline speech gain | 2 chars in same room, speak | Speaker +5, listener +3 (or +7/+5 for chatty) |
| Self-talk | 1 char alone, speaks | Speaker +1 (not +5) |
| Presence only | 2 chars silent together, multiple ticks | +1/tick default, +2/extrovert, +0/introvert, +0/loner |
| Isolation | 1 char alone > 5 ticks | Accelerated decay (-2/tick) |
| Loner isolation | Loner alone > 5 ticks | Gains +1/tick instead |
| Introvert group | Introvert in room with 3+ others | No presence gain, energy drain applies |
| Extrovert group | Extrovert in room with 3+ others | +2/tick presence, no energy drain |
| Low Social behavior | Force Social < 25 via cheat | Agent seeks interaction, rambles |
| Humid environment | Character in humid room | Hygiene decays, Social unaffected |
| Perfume environment | Character in perfume room | Entertainment increases, Social unaffected |

---

## Related

- `task-137`: original design doc (conversation tracking + on_speech already done)
- `task-94`: closeness as behavioral gate (complementary social dimension)
- `task-92`: needs-driven autonomous replanning (Social urgency feeds into priority queue)
- `tick_manager.py` — per-tick vital processing
- `narration.py` — speech broadcast with Social gains
- `traits.py` — extrovert/introvert/SOCIAL_GAIN/GROUP_ENERGY_DRAIN
- `character-state.js:150-152` — low Social narration injection
- `game_tools.py:167-168` — advice for low Social
