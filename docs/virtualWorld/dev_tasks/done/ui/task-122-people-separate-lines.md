---
group: Prompt & Narrative Quality
---
# Separate People Lines in Prompt Context

**Filed**: 2026-07-29  
**Priority**: Low  
**Status**: Done

---

## Summary

Character descriptions are currently concatenated into one comma-separated paragraph, making them hard to parse:

```
People here: Kayla Jenkins (awake): A sixteen-year-old Black girl..., Kyrie Johansen (awake): A sixteen-year-old white girl..., ...
```

Should be one line per person with clear separation:

```
People here:
- Kayla Jenkins (awake) — A sixteen-year-old Black girl...
- Kyrie Johansen (awake) — A sixteen-year-old white girl...
- John Smith (unknown to you) (awake) — Someone is here but you haven't met them yet.
```

**Note**: Unknown characters are shown with their actual name followed by "(unknown to you)" so the agent can still target them by name in actions (e.g., `attack John Smith`), while conveying the character hasn't met them yet.

### Scope
- `static/js/agent/prompt-builder.js` — `buildRoomContext()` people output format
- `static/js/agent-engine.js` — `_buildRoomContext()` people output format
