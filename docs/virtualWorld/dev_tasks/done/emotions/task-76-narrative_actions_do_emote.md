# Narrative Actions (Emote / `do` System)

**Filed**: 2026-07-20
**Completed**: 2026-07-20
**Priority**: High
**Status**: Done
**Spec**: `docs/superpowers/specs/2026-07-20-narrative-actions-design.md`

---

## Implementation Summary

All phases implemented and tested (13/13 tests passing):

### Phase 1: Quoted Parameter Parsing
- `tokenize_command()` in `app.py` — handles `'` and `"` quotes
- 10 unit tests in `tests/test_tokenizer.py`
- All command branches use tokenizer: `go`, `open`, `close`, `eat`, `drink`, `use`, `examine`, `take`, `drop`, `rest`, `toggle`, `attack`, `speak`

### Phase 2: `do` Verb (Human Players)
- `do` recognized verb in app.py
- Auto-fallthrough: unrecognized commands become emotes (replaces "Unknown command.")
- Priority: verb matching → item matching → LLM reinterpretation → EMOTE

### Phase 3: Agent `emote` Field
- `ApiClient.emote()` in `api.js`
- Parsing in both `_parseDecisionWithSpeech()` and `_parseReaction()` in `agent-engine.js`
- Execution after action in both reactive (decision) and combined (reaction) paths
- System prompts updated with `emote` in JSON response format
- `'do'` added to `_validateAction()` valid verbs
- Emote command documented in COMMANDS table

### Phase 4: Backend `process_emote()`
- `process_emote()` method in `virtual_world_engine.py` — LLM generates description, logs turn event
- `POST /api/emote` endpoint in `app.py`
- 3 unit tests in `tests/test_emote.py` (returns description, logs room event, LLM failure fallback)

### Phase 5: Display + MCP
- `msg-emote` display type in `event-stream.js` with 🎭 icon
- `.msg-bubble-emote` CSS with pink left-border accent (`#ff79c6`)
- `emote(text)` MCP tool in `mcp_server.py`

## Files Changed

| File | Change |
|------|--------|
| `app.py` | `tokenize_command()`, `do` verb, auto-fallthrough, `POST /api/emote`, all branches updated for tokenizer |
| `virtual_world_engine.py` | `process_emote()` method |
| `static/js/api.js` | `ApiClient.emote()` |
| `static/js/agent-engine.js` | `emote` field parsing (decision + reaction), execution, prompts, `_validateAction()` update |
| `static/js/event-stream.js` | `msg-emote` → `streamType: emote`, 🎭 icon, filter map entry |
| `static/css/style.css` | `.msg-bubble.msg-bubble-emote` border-left accent |
| `mcp_server.py` | `emote(text)` MCP tool |
| `tests/test_tokenizer.py` | 10 new tests |
| `tests/test_emote.py` | 3 new tests |
