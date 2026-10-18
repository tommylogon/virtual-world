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

Capture the one-tick drive harness (the `drive_ticks*.ps1` pattern used to verify task-701 live) as a repo asset, and hand the timeskip / world-advance testing lane the operating facts it needs to share the world with it.

The harness is pure HTTP against the app's own routes, no code touched:

1. `POST /api/reset` - reloads the scenario file on disk, re-parks the cast from their containment edges.
2. `PATCH /api/players/<name>/vitals/<vital>` - the demo fixture: Energy to its ceiling, Hunger/Thirst/Bladder to 0, Social to 100 (resources fill; drives empty). Re-applied mid-drive whenever values decay under thresholds.
3. One `POST /api/turn/apply` per loop call, sampling area, plan index, leaves and vitals to a JSONL every N ticks.
4. Stop condition on the pursued outcome, then a stop record: lived-log tail, final pursuit state, relevant memories of the recipient.

## Why

Live verification needs more than unit tests: the pursue-delivery demo failed six times on operating properties a unit test cannot see. A second lane driving the same server will hit the same facts, some the hard way:

1. One `/api/turn/apply` call advances one tick; measured ~0.3-0.6 calls/s wall under state-fetch load (~2.5 MB per sample).
2. `/api/timeskip` degenerates to ~1 tick per call when the subject has per-tick salient events: not usable as a bulk driver.
3. `POST /api/load` is NOT a reload from disk: its body is treated as the world dict. An empty payload replaced the live world with an empty one, wrote `unnamed.json`, and poisoned the resolve-source pointer. `/api/reset` is the reload-from-disk call; `/api/undo` `{steps: 2}` recovered that exact accident (all 27 players back, mounted pursuit intact).
4. The server has no auto-reloader (`app.py`: `debug=os.environ.get('VW_DEBUG') == '1'`): engine edits do not apply until a manual restart. task-701's run 10 was measured against the pre-fix executor for exactly this reason.
5. Plan-stall semantics (task-701's fix): a refused crossing now stalls a plan instead of failing it; `_STALL_ACTIONS` = 36 consecutive refusals before the approach admits failure. A soak counting `plan:<label>:failed` lines should expect fewer of them than before, plus a `_stall` key on live plan dicts.
6. Ladder ordering in `background_simulation._act`: needs and the social company branch spend the minutes before the plan advance; with Social at or below 50 the plan gets no minutes at all.

## How

1. Give the driver script a checked-in home under `tools/` with a parameter: target outcome, tick cap, sample cadence, stop-record path.
2. Document it in a short page (or extend the Background Simulation machinery page) with the facts above.
3. Post on the shared board at `.kilo/lanes/README.md` that one-tick drills and timeskip soaks share the world and take turns on the tick order.

## Steps to verify

1. A fresh drive from `PATCH /api/reset` + fixture produces the samples file and a stop record whose claims reproduce on a rerun.
   - expected: same chain shape (mount, legs, stop), same failure or delivery mode.
   - observed: task-701's runs 1-10 (see that card).
2. Restart the server after an engine edit and confirm the new behavior is live before measuring anything.
   - expected: run 10 versus run 11 execute the same code.
   - observed: run 10 measured the old executor; run 11 was cancelled for the lane coordination before launching.

## Acceptance

- [ ] Driver script checked in under `tools/` with its knobs parameterised.
- [ ] Facts page exists in the vault (or the Background Simulation extension).
- [ ] Board note posted for the timeskip lane.
- [ ] Next drive run confirmed to execute the current executor.

## Files

- `tools/drive_ticks.ps1` (to check in; the working copy lives at `%TEMP%\opencode\drive_ticks9.ps1`)
- `docs/virtualWorld/Characters/Background Simulation.md` (facts page extension)
- `.kilo/lanes/README.md` (board note)

