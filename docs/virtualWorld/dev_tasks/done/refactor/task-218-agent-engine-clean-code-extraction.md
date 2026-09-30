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

### Live browser verification (2026-09-30)

Re-verified in a real browser against the running app (port 4444) rather than
inferred from files existing. `agent-engine.js` calls the five modules as
namespaces (`ResponseParser.parseReaction`, `PlanTracker.trackStep`, ...), so
the probe wraps each module method and counts live calls across two turns — a
human turn (player_human_explorer) and an NPC reactive turn (Belne):

| Module | Live calls observed | Path |
|---|---|---|
| `ActionNormalizer` | `normalizeStructuredAction` 3, `extractSpeechVolume` 5, `volVerb` 3, `isValidAction` 2 | human turn + NPC step |
| `ResponseParser` | `extractMemory` 1, `parseReaction` 2, `parseResultReaction` 2 | human turn + NPC step |
| `ThreatDetector` | `getThreatAlert` 4 | NPC `step()` |
| `AgentState` | `isBusy` 2, `clearUnconscious` 2 | NPC `step()` |
| `PlanTracker` | `getPlan` 45, `getProgress` 12, `getFailures` 12, `setPlan` 2, `trackStep` 2, `shouldReplan` 2, `criticalNeeds` 2 | NPC `step()` |

Belne's turn ran the full pipeline in the event stream — `ACT · TAKE BREAD`,
`take Bread`, `✓ You take the bread with your hand right.`, `REACT · REACTING`,
`LLM ➜ result-reaction ~2.1k` — with a populated PLAN (examine → take → eat
Bread) and MEMORIES written. Narration came from LM Studio `qwen/qwen3.5-9b`.
Console reported 0 errors.

### Two extracted functions are dead — pre-existing, not caused by this task

`ResponseParser.parseObservation` and `ResponseParser.parseDecisionWithSpeech`
have **zero call sites**. Across all of `static/` and `templates/` each appears
only at its definition and its export. The combined/non-reactive path also calls
`parseReaction` (`agent-engine.js:837`), not `parseDecisionWithSpeech`.

This is *not* a regression from the extraction: `git show
170d5f1:static/js/agent-engine.js` (the initial public release) contains no
reference to either name either, so neither was ever called from the engine.
Tracked separately rather than fixed here — rewiring the observation phase is
engine behaviour work, out of scope for a readability refactor.

Still not observed firing: `parseObservation`, `parseDecisionWithSpeech`,
`AgentState.markUnconscious` (needs a passing-out character), and
`PlanTracker.resetAll` (only on `agent.reset()`).
