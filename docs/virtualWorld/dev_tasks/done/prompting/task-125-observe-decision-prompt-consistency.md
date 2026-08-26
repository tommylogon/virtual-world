---
group: Agent AI & Behavior
---
# Observe/Decision Prompt Consistency

**Filed**: 2026-07-29  
**Priority**: Medium  
**Status**: Done

---

## Summary

Ensure the observe phase and decision phase prompts agree on what information is available. Currently they can show different data (e.g., observe has no people/items, decision has full list).

### Root causes
1. **Light level mismatch** — observe uses raw `env.light`, decision might use different path. Partially fixed by ambient_light serialization change.
2. **Different context builders** — `PromptBuilder.buildRoomContext()` vs agent-engine's inline `_buildRoomContext()` may differ
3. **Area state changes between calls** — if the observe prompt is built before tick processing and decision after

### Fixes
- Ensure both phases use the same `buildRoomContext` function with the same state data
- Verify ambient_light is consistently available (backend serialization fix)
- People should be listed in all phases even in dim/pitch black (see task-121)

### Scope
- `static/js/agent-engine.js` — observe and decision prompt building
- `static/js/agent/prompt-builder.js` — unified context builder
