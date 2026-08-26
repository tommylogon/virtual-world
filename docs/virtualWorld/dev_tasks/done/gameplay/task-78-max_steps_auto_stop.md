# Max Steps Auto-Stop

**Filed**: 2026-07-20
**Completed**: 2026-07-20
**Priority**: Medium
**Status**: Done

---

## Summary

Add a numeric input next to the Run Simulation button that limits how many turns run before auto-stopping. Prevents infinite credit consumption when letting simulation run unattended.

## Files Changed

| File | Change |
|------|--------|
| `templates/index.html:47` | Added `<input type="number" id="sim-max-steps" value="10" min="0">` after step button |
| `static/css/style.css:178-183` | `.sim-max-steps` styling (40px wide, matches button height, terminal font) |
| `static/js/config.js:50-51` | `config.maxSteps = 10`, `config.stepsRun = 0` |
| `static/js/agent-engine.js:530-535` | `start()` reads input value, resets counter, checks `stepsRun >= maxSteps` per iteration, calls `stop()` |
| `static/js/ui-controller.js:275-276,294-303` | Disables input while running; updates step-display to show `Step: X/Y (N left)` |

## Behavior

- **Default**: 10 — user can edit the number freely
- **0** = unlimited (legacy behavior, runs until manually paused)
- Input is disabled while simulation is running
- Step display switches to `Step: 3/10 (7 left)` during sim, reverts to `Step: idx/total` when stopped
- On auto-stop: logs "Agent stopped.", re-enables play button and input
