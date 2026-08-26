---
group: Tech Debt & Testing
---
# Log Race Condition — Concurrent LLM Response Interleaving

**Filed**: 2026-07-29  
**Priority**: Medium  
**Status**: In Review — implemented 2026-08-05, awaiting verification. Per-call stream isolation in event-stream.js (`_streamSpans` Map keyed by streamId), per-call chunk callback in llm-client.js (`_handleStream(resp, format, onChunk)` via `options.onChunk`, removed shared `_onChunk`), and agent-engine.js generates a unique streamId per LLM call and threads the callback through `chat()`. Static checks pass (no stale refs, `node --check`). Pending: browser E2E — run two agents in parallel and confirm separate, non-interleaved bubbles.

---

## Summary

When multiple LLM agent calls complete at the same tick, their responses can get interleaved/concatenated into a single log entry. Observed in both the event log and mansion log:

```
🤖[08:50] LLM ["Examine the fireplace...", "Check the Dusty Bookshelf..."]{"inner_monologue":"Oh! Oh dear..."}
```

Two separate LLM responses (a plan JSON array + an inner_monologue JSON object) were merged. This corrupts the log display and could affect downstream processing.

### Root cause

Both subagents were dispatched at the same tick, and their streaming/finish callbacks wrote to the same event stream target without synchronization. Likely in:

- `static/js/event-stream.js` — `logRawLLM()` and `finishStreaming()` use the same stream span; concurrent calls overwrite each other
- `static/js/llm-client.js` — concurrent `chat()` calls share `_onChunk` callback

### Scope

- `static/js/event-stream.js` — streaming span isolation per call
- `static/js/llm-client.js` — concurrent call handling
- `static/js/agent-engine.js` — dispatch of concurrent agent steps
