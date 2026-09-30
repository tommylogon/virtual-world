---
type: task
status: todo
area: refactor
priority: low
---

# task-657: ResponseParser.parseObservation and parseDecisionWithSpeech have zero call sites

**Filed:** 2026-09-30
**Related:** 

## Goal

Two functions extracted from agent-engine.js in task-218 are dead: across all of static/ and templates/ each appears only at its definition and export. git show 170d5f1:static/js/agent-engine.js shows neither was ever called from the engine, so this is pre-existing dead code, not an extraction regression. Either wire the observation phase through parseObservation (the observation memory written as src:observation evidently comes from another path) or delete both exports.

## Acceptance

- TODO
