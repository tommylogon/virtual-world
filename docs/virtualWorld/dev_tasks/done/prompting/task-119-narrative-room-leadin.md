---
group: Prompt & Narrative Quality
---
# Narrative Room Lead-in for Prompts

**Filed**: 2026-07-29  
**Priority**: Medium  
**Status**: Done

---

## Summary

Replace the bare room name header in LLM prompts with a narrative lead-in sentence.

### Current
```
Living Room
A cold living room with wooden floors...
```

### Target
```
You are currently in the Living Room. The air is cold and still, dust hanging in the dim glow from the hearth.
```

The lead-in should combine:
- Room name
- Light level feel (dim, pitch black, bright, etc.)
- Temperature feel (cold, warm, biting, etc.)
- A key atmospheric detail from the room description

Full room description follows below as before.

### Scope
- `static/js/agent/prompt-builder.js` — `buildRoomContext()` function
- `static/js/agent-engine.js` — `_buildRoomContext()` function
