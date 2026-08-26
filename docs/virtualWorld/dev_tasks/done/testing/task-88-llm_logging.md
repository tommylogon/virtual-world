---
group: Tech Debt & Testing
wiki: "[[AI & Narration/LLM Providers]]"
---

# Task 88: LLM Request/Response Logging in Event Stream

**Filed**: 2026-07-21 (rewritten 2026-07-29, updated 2026-07-30)
**Priority**: Medium
**Status**: Implemented — pending review

---

## Summary

Every LLM call should log its **full request (prompt) and response** to the event stream so you can see exactly what's being sent and received. Currently only the agent engine does this — 16 other call sites are invisible.

---

## Current state

**Done.** Every LLM call goes through `llmClient.chat()` which logs full request/response to EventStream:

- `llm-client.js:56-58` — `logRawLLMRequest()` before fetch (all call sites)
- `llm-client.js:87-89` — `logRawLLM()` after non-streaming response
- `llm-client.js:143-145` — `logRawLLM()` after streaming response
- `agent-engine.js:559` — Duplicate `events.logRawLLMRequest()` removed, delegates to llmClient

---

## What was done

### Centralized logging in `llmClient.chat()`

Modified `chat()` to emit request/response to EventStream directly. This catches **all 17 call sites** without touching each one. The table below shows the coverage after centralization:

| # | Call Site | Now Logging Via |
|---|-----------|----------------|
| 1-4 | `agent-engine.js` - observe/decision/react/combined | ✅ llmClient.chat() (centralized) |
| 5 | `plan-manager.js` - plan generation | ✅ llmClient.chat() |
| 6 | `memory-manager.js` - memory reflection | ✅ llmClient.chat() |
| 7 | `settings-view.js` - test connection | ✅ llmClient.chat() |
| 8-9 | `inspector.js`/`agent-view.js` - personality gen | ✅ llmClient.chat() |
| 10 | `agent-view.js` - description generation | ✅ llmClient.chat() |
| 11 | `item-view.js` - item improve | ✅ llmClient.chat() |
| 12 | `area-view.js` - area improve | ✅ llmClient.chat() |
| 13-14 | `narration-ui.js` - narration gen | ✅ llmClient.chat() |
| 15-17 | `main.js`/`ai-generation.js` - generate/improve (via AIGenerator) | ✅ llmClient.chat() |

### Changes made

**`llm-client.js`** — Added EventStream logging in `chat()`:
- Before fetch: `VW.events.logRawLLMRequest(model, messages)` (line 56-58)
- After non-streaming response: `VW.events.logRawLLM(model, messages, content)` (line 87-89)
- After streaming response: `VW.events.logRawLLM(model, this._lastMessages, fullContent)` (line 143-145)

**`agent-engine.js`** — Removed duplicate `events.logRawLLMRequest(stepName, final)` from `_callLLM()` since llmClient now handles it.

**`event-stream.js`** — No changes needed (already had `logRawLLMRequest()` and `logRawLLM()` methods).

### Verification

1. ✅ Open event stream — see `📤 LLM` bubble with full prompt, `🤖 LLM` with full response
2. ✅ Click Improve on any item — works
3. ✅ Click Improve on area — works
4. ✅ Generate narration — works
5. ✅ Agent engine phases — still work, logging from llmClient
6. ✅ Toggle `filterRawLLM` — bubbles show/hide correctly

---

## Files to touch

| File | Change |
|------|--------|
| `static/js/llm-client.js` | Add EventStream logging in `chat()` |
| `static/js/agent-engine.js` | Remove duplicate logging (now handled by llmClient) |

## Verification

1. Open event stream
2. Click Improve on any item — should see `📤 LLM` bubble with full prompt, then `🤖 LLM` bubble with full response
3. Click Improve on an area — same
4. Generate narration — same
5. Agent engine phases — same (should still work, just from a different source)
6. Toggle `filterRawLLM` in Settings — bubbles should show/hide
