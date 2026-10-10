---
area: prompting
type: task
status: done
priority: medium
---

# People Presence in Darkness — Sensory Cues

**Filed**: 2026-07-29  
**Priority**: Medium  
**Status**: Done

---

## What

In dim or pitch-black conditions, other characters still exist and make noise. The prompt should list them with sensory cues rather than excluding them entirely.

### Current behavior
In dim light: people are listed normally (visible)  
In pitch black: people are not listed at all  
Observe phase: people sometimes missing entirely while decision phase has them

### Target
- **Pitch black**: List people as audible cues — *"You hear breathing nearby — someone is close."* / *"Footsteps shuffle to your left."*
- **Dim light**: List people as vague shapes — *"A silhouette stands near the stairs — it could be Kayla."* / *"You see movement in the corner of your eye."*
- **Normal light**: Full descriptions as now

### Scope
- `static/js/agent/prompt-builder.js` — `buildRoomContext()` people section
- `static/js/agent-engine.js` — `_buildRoomContext()` people section
- Needs relationship info to identify voices vs unknowns

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
