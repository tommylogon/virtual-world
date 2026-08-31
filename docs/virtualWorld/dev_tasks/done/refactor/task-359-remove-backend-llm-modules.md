# Task 359: Remove unused backend LLM modules

**Status**: In Progress
**Priority**: Medium
**Filed**: 2026-07-24

## Summary

After switching "Generate from Equipment" to frontend `llmClient.chat()`, no active feature uses the backend LLM modules anymore. All AI generation now happens browser-side.

## Files Removed

- `config.py`
- `llm_connector.py`
- `llm_providers.py`
- `message_types.py`
- `token_counter.py`
- `benchmark_models.py`

(`agent_config.json` never existed — defaults were hardcoded in config.py)

## Files Cleaned

- `app.py` — removed `llm_connector` import block, `LLM_ENABLED` stays `False`
- `routes/llm.py` — removed entire file (gated by `LLM_ENABLED`, dead)
- `routes/action.py` — removed LLM reinterpretation block (gated by `LLM_ENABLED`, dead)
- `engine/equipment.py` — removed unused `from config` / `from llm_connector` imports
- `engine/narration.py` — removed unused `from config` / `from llm_connector` imports
- `engine/logging_events.py` — removed unused `from config` import
- `engine/skills.py` — removed unused `from config` import
- `tests/test_emote.py` — removed (mocked `llm_connector`, no longer relevant)

## Verification

- Server starts cleanly
- All features use fallback paths (same behavior as before)
