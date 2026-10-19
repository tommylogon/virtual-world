# Bug 11: "Generate from Equipment" → 500 / no-op — dual LLM config problem

**Filed**: 2026-07-24
**Priority**: High
**Status**: Fixed — switched to frontend LLM client (same path as item/room/door generation)

## Summary

Clicking "Generate from Equipment" in the character inspector bio tab either returns a 500 or silently does nothing (description unchanged). No LLM request appears in the event stream.

## Root Cause — Two Separate Issues

### Issue 1: Wrong object passed as logger (FIXED)

`virtual_world_engine.py:101` was passing `self` (VirtualWorld) as the `logging_events` argument to `EquipmentSystem.__init__` instead of `self.game_logger` (GameLogger). This caused `AttributeError: 'VirtualWorld' object has no attribute 'log_llm_call'` → 500.

Fix applied: changed `self` → `self.game_logger` on that line.

### Issue 2: Dual LLM config — frontend vs backend (REMAINING)

The app has **two completely separate LLM config paths**:

| Feature | Config source | Provider |
|---------|-------------|----------|
| **Agents** (browser-side) | Browser Settings UI → `config.apiBase/key/model` (localStorage) | Whatever user configured in Settings |
| **Item/Area/Way AI gen** (browser-side) | Same — `AIGenerator.generate()` → `llmClient.chat()` | Same |
| **Generate from Equipment** (backend-side) | `config.get_config()` → reads `agent_config.json` or hardcoded defaults | Default: `lmstudio` at `localhost:1234/v1` |

The backend LLM path uses `config.py` → `agent_config.json` (which doesn't exist) → hardcoded defaults with `default_provider: "lmstudio"` and `llm_logging: False`. If LM Studio isn't running, the call fails silently (`except Exception: pass` in `_update_equipment_description`), and the fallback just sets `description = base_description` — no visible change.

Meanwhile, every other "generate" feature (items, areas, ways, narration) calls the LLM directly from the browser using `llmClient.chat()`, which uses the user's Settings UI config (e.g. OpenRouter, OpenAI, Gemini) — and those all work fine.

## Fix (Option B selected)

Make "Generate from Equipment" work like everything else — call `llmClient.chat()` directly in the browser, then save the result via `ApiClient.updateCharacter()`.

This eliminates the backend LLM dependency entirely for this feature.

### Changes needed

**`static/js/inspector/agent-view.js`** (~line 835-875):
- Replace the backend API call with `llmClient.chat()` using same prompt as backend
- Use `AIGenerator` pattern: build prompt from `base_description + equipment`, call LLM, parse response
- Save result via `ApiClient.updateCharacter` (already exists)

**Backend route `routes/players.py`** (optionally):
- Can keep or remove `/api/players/<name>/generate-description` endpoint — probably keep for now, the route won't be called anymore

## Files

- `virtual_world_engine.py:101` — wrong logger (FIXED)
- `engine/equipment.py:341-414` — `_update_equipment_description` uses backend config, silent failures
- `config.py:29-90` — hardcoded defaults with `default_provider: "lmstudio"`, `llm_logging: false`
- `llm_connector.py` — backend LLM calls go through here
- `static/js/inspector/agent-view.js:835-875` — frontend needs rework
- `static/js/shared/ai-generator.js` — pattern to follow (browser-side LLM call)
- `static/js/api.js:70-77` — `ApiClient.updateCharacter()` endpoint already exists
