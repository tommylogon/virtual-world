# Task 218 — agent-engine.js clean-code extraction

## Status
Done — implemented 2026-08-12

## Summary
Split `agent-engine.js` (892 lines) into focused modules following the existing modularization plan.

## Files changed
- `static/js/agent/action-normalizer.js` — new
- `static/js/agent/response-parser.js` — new
- `static/js/agent/threat-detector.js` — new
- `static/js/agent/agent-state.js` — new
- `static/js/agent/plan-tracker.js` — new
- `static/js/agent-engine.js` — slimmed from 892 to ~480 lines
- `static/js/agent/plan-manager.js` — updated to use PlanTracker
- `static/js/shared/json-utils.js` — added `repairJSON()`
- `static/js/event-stream.js` — raw LLM bubbles inside turn cards + filter recursion
- `templates/index.html` — added script tags for 5 new modules

## What was extracted

| Module | Methods moved | Lines saved |
|--------|--------------|-------------|
| `action-normalizer.js` | `_validateAction`, `_normalizeStructuredAction`, `_extractSpeechVolume`, `_volVerb` | ~80 |
| `response-parser.js` | `_parseObservation`, `_parseReaction`, `_parseResultReaction`, `_parseDecisionWithSpeech`, `_extractMemory` | ~120 |
| `threat-detector.js` | `_getThreatAlert` | ~50 |
| `agent-state.js` | `_isBusy`, resting/unconscious maps | ~60 |
| `plan-tracker.js` | `_trackPlanStep`, `_shouldReplan`, plan state maps | ~60 |

## agent-engine.js now owns
- `step()` orchestrator (reactive + non-reactive)
- `_runDashFollowUp`
- `_callLLM` / `_callLLMMessages` / `_showManualPrompt`
- `start()` / `stop()` / `reset()` / `stepOnce()`
- `getHistory` / `nudge`
- `_surfaceRejectedAction`
- `_checkCancel`

## Verification
- `node --check` passes on all 8 modified/new JS files
- Backend pytest: 856 passed (11 pre-existing trigger_system failures, unrelated)
- Frontend LLM tests: 16/19 passed (3 failures need running server, pre-existing)
