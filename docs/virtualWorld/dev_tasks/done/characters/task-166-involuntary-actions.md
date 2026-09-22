---
id: 166
title: Involuntary Actions (Hiccups, Burps, Yelps)
status: done
priority: low
created: 2026-08-02
tags: [characters, speech, emote, flavor]
---

# Involuntary Actions (Hiccups, Burps, Yelps, Stutters)

## Status — implemented (2026-09-22)

**This is a live-game (attended agent) layer, not a backsim feature.** It runs
where a character's line is emitted, so it applies to the LLM-agent and human
tiers in the browser. Background and simple NPCs have no speech/emote emission
path and intentionally never reach it — the cheap policy stays a valid but
plainer policy ([[Simulation Model]] §Cognition refines). Do **not** push this
into `BackgroundSimulation`.

**Shipped (v1.4.0, `static/js/agent/involuntary.js`):** condition-driven
speech/emote interruption (frightened → stutter, hypothermia → shiver, sick /
poisoned → cough, social_breakdown → hollow mutter, paranoid → stutter,
hallucinating → ramble), `itch` / `goosebumps` emote flavor, a low random
baseline (hiccup/burp/yelp), pronoun rendering, and wiring into
`agent-engine.js` `_speakLine` / `_performEmote`. Never replaces the intended
action; injected before the text is sent so the room and event stream see it.

**Added 2026-09-22:**
- **Trait-driven**: `jittery` (aliases `nervous`, `clumsy`) multiplies every
  involuntary roll ×1.8.
- **Situation-driven startle**: a *new* shout/scream in `recent_hearing` raises
  a yelp. `AgentEngine._detectStartle()` tracks which hearing entries already
  startled a character (so a lingering shout does not yelp forever) and caches
  the result per turn so the speech and the emote agree.
- **Tests**: `tools/unit/test_involuntary.js` (8 cases, `Math.random` pinned),
  loaded by `tools/unit/run.cjs`.

**Deliberately re-worded for the timeframe model:** the roll is **per emitted
line**, not "per turn". A turn is a timeframe of N game minutes containing an
emergent flow of actions ([[Simulation Model]] §Time); a per-turn roll would
silently scale with turn length.

**Still open / optional:**
- `sudden damage → yelp` is not wired: only loud speech startles. The turn-event
  buffer has no target field, so a reliable "was just hurt" signal needs either
  an HP-delta check or an attacker-target field on the event.
- `eating too fast → burp` needs a post-consume hook; deferred (low value).
- Verb conjugation: templates use `{they} scratch` / `{they} grip`, which reads
  "he scratch" for a male character. All templates inherited this; fixing it
  needs per-pronoun verb forms or rephrasing the pools.

---

## Summary

Add involuntary actions — a hiccup, a burp, a yelp, a stutter, etc. — that can be injected into a character's speech or emote, triggered by conditions, random chance, or specific situations.

## Problem

Speech and emote are always deliberate. Nothing makes a character hiccup mid-sentence, stutter when frightened, or yelp when startled. These little moments add life to the simulation but don't exist.

## Implementation

### Involuntary event sources

- Random chance per turn (low probability, configurable)
- Condition-driven: `frightened` → stutter, poisoned/sick → cough or hiccup, freezing → shiver/stutter (`frightened` is now a catalog entry — see [[review/characters/task-trait-condition-system-v2|task: Trait & Condition System v2]])
- Situation-driven: startled by a loud sound or sudden damage → yelp; eating too fast → burp
- Trait-driven: `jittery` (aliases `nervous`/`clumsy`) raises the chance (done)

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

## Files

1. `static/js/agent/involuntary.js` — the generator (condition/trait/startle pools + `speech`/`emote` entry points)
2. `static/js/agent-engine.js` — `_speakLine` / `_performEmote` injection, `_detectStartle`
3. `engine/player_conditions.py` — `itch` / `goosebumps` flavor conditions
4. `tools/unit/test_involuntary.js` + `tools/unit/run.cjs` — tests

## Testing

- [x] Frightened character stutters occasionally
- [x] Random hiccup/burp appears at low frequency
- [x] Startled reaction (yelp) fires on loud noise
- [x] Involuntary text never replaces the real action/speech
- [x] `jittery` raises the chance
- [x] A shout startles only once (no repeated yelp on a lingering entry)

## Related

- [[todo/gameplay/task-165-chance-to-stun-on-attack|task-165: Stun conditions]]
- [[done/prompting/task-151-flavor-text-interaction-polish|task-151: Flavor text polish]]
- `todo/pleasure/task-209-arousal-conditions.md` — arousal-linked body reactions (nipple hardening, blushing) live there; keep non-erotic reactions here
