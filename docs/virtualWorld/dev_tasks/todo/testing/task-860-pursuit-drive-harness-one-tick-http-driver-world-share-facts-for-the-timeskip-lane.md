---
type: task
status: todo
area: testing
priority: medium
wiki: "[[Background Simulation|Background Simulation]]"
---

# task-860: pursuit drive harness: one-tick HTTP driver + world-share facts for the timeskip lane

**Filed:** 2026-10-17
**Related:** task-701

## What

Provide a first-class HTTP simulation driver tool (`tools/drive_sim.py`) that executes stepped integration runs against the live server (`/api/turn/apply`, `/api/state`, `/api/reset`). This replaces the ad-hoc PowerShell scripts (`%TEMP%\opencode\drive_ticks*.ps1`) that were previously hacked together during task-701 testing.

The standardized driver provides:
1. Scenario reset and baseline setup via `POST /api/reset` and vital conditioning via `PATCH /api/players/<name>/vitals/<vital>`.
2. Step-by-step or batched execution through `POST /api/turn/apply` without relying on the timeskip endpoint for granular telemetry.
3. Telemetry capture: writes structured JSONL logs capturing character location, plan index, active pursuit progress, and lived_log reasons.
4. Definable stop conditions: target delivery, time cap, character death, or plan failure.

## Why

Relying on ad-hoc PowerShell scripts in `%TEMP%` is fragile, non-portable, and disconnected from the repo's Python tooling ecosystem. Live soak and pursuit testing requires reproducible HTTP driving against live server instances to catch race conditions, needs cascade preemption, and plan stall issues that isolated pytest unit tests cannot exercise. Checking in a clean, parameterized Python tool standardizes simulation driving across developer and test lanes.

## How

1. Author `tools/drive_sim.py` using Python's standard `urllib.request` / `requests` or `httpx` if available in the repo environment.
2. Provide command-line arguments: `--ticks <N>`, `--character <name>`, `--pursuit <name>`, `--sample-every <N>`, `--out <path>`, `--freeze-vitals` (to prevent hunger/sleep cascading while testing specific pursuit paths).
3. Record progress and assertions cleanly in JSONL.
4. Document the driver usage and simulation operational caveats (ladder priorities, stall action limits) in `docs/virtualWorld/testing/` or `Background Simulation.md`.

## Browser UI and intended live verification

Intended UI home: Not applicable. This is a developer test harness and CLI simulation driver.

Why no browser UI: The tool exercises the server HTTP endpoints directly from the command line to simulate unattended background runs and collect high-cadence telemetry.

Alternative verification steps:
1. Run `python tools/drive_sim.py --ticks 10 --character Vekka --out test_drive.jsonl` against a running server.
   - expected: Tool connects, steps 10 ticks via `/api/turn/apply`, logs telemetry to `test_drive.jsonl`, and exits 0.

## Steps to verify

1. Start the server on `:4444`.
2. Run `python tools/drive_sim.py --ticks 20 --character Vekka --out scratch_run.jsonl`.
   - expected: Output JSONL contains 20 state samples with valid character positions and tick counts.
   - observed: TODO
3. Test stop conditions (e.g. `--stop-on-arrival <area>`).
   - expected: Driver stops immediately when character enters target area.
   - observed: TODO

## Acceptance

- [ ] `tools/drive_sim.py` exists as a clean, parameterized Python script (no temporary `%TEMP%` ps1 dependencies).
- [ ] Supports stepping ticks, sampling state, vital freezing, and target stop conditions.
- [ ] Telemetry outputs clean, parseable JSONL.
- [ ] Operating documentation updated in `docs/virtualWorld/Characters/Background Simulation.md`.

## Files

- `tools/drive_sim.py`
- `docs/virtualWorld/Characters/Background Simulation.md`

