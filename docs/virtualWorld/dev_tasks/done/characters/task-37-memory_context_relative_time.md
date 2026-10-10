---
area: characters
wiki: "[[AI & Narration/Memory System]]"
type: task
status: done
priority: medium
---

# LLM Memory Context: Relative Time Instead of Ticks

**Filed**: 2026-07-17
**Priority**: Medium
**Status**: Implemented / Needs Review

---

## What

LLM-facing memory context (episodic memories in `=== I REMEMBER ===`, reflection prompts, debug output) displayed raw tick numbers like `[Tick 42]`. These now show human-readable relative time like `[5 minutes ago]` or `[2 hours ago]`, giving the LLM a sense of recency.

## How

- Added `EventBus.tickToRelative(tick)` — converts a tick to "just now" / "X minutes ago" / "X hours ago" / "X days ago" based on current world tick and `time_per_tick_minutes`
- Replaced `[Tick N]` in 4 LLM-facing locations:
  - `agent-engine.js` reflection summarization prompt
  - `agent-engine.js` `_buildMemoryContext()` episodic memory list
  - `agent-engine.js` world knowledge insight (hardcoded `[just now]`)
  - `memory-store.js` debug output

## Files

- `static/js/event-stream.js` — added `tickToRelative()` method
- `static/js/agent-engine.js` — 3 `[Tick N]` → relative time
- `static/js/memory-store.js` — 1 `[Tick N]` → relative time

## Why

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO
