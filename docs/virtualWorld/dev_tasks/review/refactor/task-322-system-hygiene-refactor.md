---
id: 322
title: System Hygiene Refactor (speech extraction, JS unit harness, threshold dedup, green suite)
status: review
priority: medium
created: 2026-08-21
tags: [refactor, testing, engine, prompt-builder]
---

# task-322: System Hygiene Refactor

**Status** — In Review — all items implemented + verified 2026-08-21

## Summary

Cleanup pass over issues surfaced while landing tasks 92/94/248/133/230. Goal: leave the
system in a state where the next feature work is cheaper and safer.

## What was done

### R1 — narration.py back under the 600-line rule
`engine/speech.py` (new, ~250 lines): `SpeechBroadcaster` owns broadcast_speech end-to-end
(hearing entries, directed whispers, cross-area propagation, social bumps, closeness hooks,
log/turn-event recording, simple-NPC notification). `NarrationSystem.broadcast_speech` is a
thin @deprecated delegate; `narration.py` went 611 → ~445 lines. Move-not-copy per AGENTS.md.

### R2 — one whisper-target resolution path
`SpeechBroadcaster._resolve_whisper_target` now resolves via the shared `NameMatching`
matcher (aliases/partial names) first, then applies the same-area privacy scan. The facade
injects the matcher via `narration.set_name_matcher()` at construction. No more duplicate
leniency logic.

### R3 — clock math dedup
`VirtualWorld.total_game_minutes()` is the single computation; `current_game_hour()`
derives from it and `TickManager.get_current_time()` consumes it (via the facade reference
it already holds). One formula, two consumers.

### R4 — JS unit harness (no server needed)
`tools/unit/run.js`: sandbox whose global object IS `window` (true browser semantics for
`window.Foo = ...` modules), zero-dependency runner. Suites:
- `test_plan_tracker.js` (12) — criticalNeeds, crossing-gated replanning, trackStep
- `test_conversation_context.js` (14) — salience classifier, markers, anti-repeat (restores
  the throwaway harness deleted during task-321)
- `test_response_parser.js` (8) — structured parsing, volume-as-key, fences, error capture

Run: `node tools/unit/run.js` → 34 passed, 0 failed.

### R5 — one vitals threshold table
`static/js/agent/vital-thresholds.js` (new): CRITICAL/WARNING/BLADDER_*/SANITY_SHATTERED +
`isCritical(key, value)`. `describeVitals` and `plan-tracker.criticalNeeds` both read it —
tier numbers can no longer drift between prompt prose and replan logic. Registered in
index.html + prompt-builder manifest + harness.

### R6 — suite green
The 3 "pre-existing" failures were stale test expectations against retuned library data:
- spawn_item tests hardcoded `uses: 3` / `lit` / heating props; library now has `uses: 0`,
  `unlit`, no heating. Tests now read expectations FROM the library entry (the contract
  under test is "spawn copies the library", so compare against the source).
- trigger burn-down test now seeds `uses = 3` before firing on_tick — verifies the mechanic
  without coupling to data tuning.
- spawn_character test hardcoded "Jake Halloway"/`player_Jake_Halloway`; library name is
  "jake halloway". Test derives name + node id from the library file.

## Verification

- `python -m pytest tests/ -q -k "not mcp and not emote"` → **1051 passed, 0 failed**,
  1 skipped (first fully green run this session).
- `node tools/unit/run.js` → 34 passed, 0 failed.
- `node --check` clean on all touched JS.
- Speech/narration/realism subset: 51 passed. Time/clock subset: 43 passed.
- Trigger system: 144 passed.

## Corrections to earlier observations

- task-358/task-351 were already filed in `inprogress/testing|triggers` — earlier "flat in
  root" reading was wrong (recursive listing artifact).
- task-155's two status lines AGREE (`todo` both) — consistent, left as-is.

## Deferred

- `agent-engine.js` (~800) / `virtual_world_engine.py` (~980) modularization →
  task-314 (dedicated pass, per plan).
