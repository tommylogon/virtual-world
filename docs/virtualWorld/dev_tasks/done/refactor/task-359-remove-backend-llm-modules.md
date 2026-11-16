---
type: task
status: done
area: refactor
priority: medium
---

# Task 359: Remove unused backend LLM modules

**Status**: In Progress
**Priority**: Medium
**Filed**: 2026-07-24

## What

After switching "Generate from Equipment" to frontend `llmClient.chat()`, no active feature uses the backend LLM modules anymore. All AI generation now happens browser-side.

## Files Removed

- `config.py`
- `llm_connector.py`
- `llm_providers.py`
- `message_types.py`
- `token_counter.py`
- `benchmark_models.py`

(`agent_config.json` never existed - defaults were hardcoded in config.py)

## Files Cleaned

- `app.py` - removed `llm_connector` import block, `LLM_ENABLED` stays `False`
- `routes/llm.py` - removed entire file (gated by `LLM_ENABLED`, dead)
- `routes/action.py` - removed LLM reinterpretation block (gated by `LLM_ENABLED`, dead)
- `engine/equipment.py` - removed unused `from config` / `from llm_connector` imports
- `engine/narration.py` - removed unused `from config` / `from llm_connector` imports
- `engine/logging_events.py` - removed unused `from config` import
- `engine/skills.py` - removed unused `from config` import
- `tests/test_emote.py` - removed (mocked `llm_connector`, no longer relevant)

## Erratum (2026-11-12)

The historical premise in this task that "all AI generation now happens browser-side" led to unintended fragility:
1. Purely browser-side storage (IndexedDB/localStorage) subjected users to regular credential and configuration loss whenever browsers cleared site storage or updated versions.
2. Direct browser-to-provider networking exposed frontend calls to CORS restrictions and prevented centralized telemetry.

This premise was formally superseded by task-910 (`routes/profiles.py`) and task-945, which establish backend provider profile and credential persistence (`data/config/profiles.json` and `.env`) with automated synchronization from the UI. Server-side profile persistence and backend-controlled LLM data is the canonical architecture going forward.

## Steps to verify

- Server starts cleanly
- All features use fallback paths (same behavior as before)

## Why

TODO

## How

TODO

## Acceptance

- [ ] TODO

## Files

- TODO
