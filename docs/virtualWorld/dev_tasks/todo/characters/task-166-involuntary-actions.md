---
id: 166
title: Involuntary Actions (Hiccups, Burps, Yelps)
status: todo
priority: low
created: 2026-08-02
tags: [characters, speech, emote, flavor]
---

# Involuntary Actions (Hiccups, Burps, Yelps, Stutters)

## Summary

Add involuntary actions — a hiccup, a burp, a yelp, a stutter, etc. — that can be injected into a character's speech or emote, triggered by conditions, random chance, or specific situations.

## Problem

Speech and emote are always deliberate. Nothing makes a character hiccup mid-sentence, stutter when frightened, or yelp when startled. These little moments add life to the simulation but don't exist.

## Implementation

### Involuntary event sources

- Random chance per turn (low probability, configurable)
- Condition-driven: `frightened` → stutter, poisoned/sick → cough or hiccup, freezing → shiver/stutter (`frightened` is now a catalog entry — see [[review/characters/task-trait-condition-system-v2|task: Trait & Condition System v2]])
- Situation-driven: startled by a loud sound or sudden damage → yelp; eating too fast → burp
- Trait-driven: a `clumsy` or `nervous` trait could raise the chance

### Injection points

- When the agent emits speech, run it through a post-processor that can inject involuntary interruptions (e.g. `"I-I'm fine"`, `"Could you... *hic* ...help me?"`)
- Emote injection: append `*she hiccups*` or `*a small yelp escapes him*` to the emote output
- Keep it non-blocking: involuntary actions never replace the intended action, only flavor it
- Log to the event stream so others in the room see it

### Folded in from the Pleasure System design (v3.1 body reactions)

The erogenous-zone design doc (§Additions #3) lists "body reactions" — goosebumps, shivers, cough, sneeze, hiccup, itch. These overlap this task's hiccup/burp scope. Rather than a separate task:
- Keep hiccup/burp/yelp/stutter as speech/emote injection (this task)
- Add **itch** and **goosebumps** as condition-driven flavor conditions (see `CONDITION_DEFINITIONS` in `player.py` — these are always-active, no mature toggle)
- These are non-erotic and independent of `mature_content`; only the arousal-linked behaviors (nipple hardening, blushing) live in the pleasure system (task-209)

## Files to Modify

1. `static/js/agent-engine.js` or `static/js/agent/prompt-builder.js` — speech/emote post-processing hook
2. New backend helper or `engine/narration.py` — involuntary action generator
3. `engine/conditions.py` / `engine/traits.py` — condition/trait hooks

## Testing

- [ ] Frightened character stutters occasionally
- [ ] Random hiccup/burp appears at low frequency
- [ ] Startled reaction (yelp) fires on loud noise
- [ ] Involuntary text never replaces the real action/speech

## Related

- [[todo/gameplay/task-165-chance-to-stun-on-attack|task-165: Stun conditions]]
- [[done/prompting/task-151-flavor-text-interaction-polish|task-151: Flavor text polish]]
- `todo/pleasure/task-209-arousal-conditions.md` — arousal-linked body reactions (nipple hardening, blushing) live there; keep non-erotic reactions here
