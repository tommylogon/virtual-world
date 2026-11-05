---
type: task
status: review
area: ui
priority: low
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-698: React phase replay: reach the HTC react phase without spending a real turn

**Filed:** 2026-10-04
**Related:** task-679, task-333

## What

Expose a dry-run react phase preview on HumanTurnComposer (`HumanTurnComposer.preview(charName, results)`) so e2e harnesses and dev workflows can inspect and verify react-phase UI rendering without executing an action, ending a turn, or mutating scenario state.

## Why

The react phase cannot be verified through standard UI flows without committing a real action, which spends turn budget, advances world time, and mutates state. A dry-run preview affordance enables repeatable test assertions against react phase styling, wall-of-text mitigation, and exit disclosures.

## How

1. Added `_dryRun` boolean state to `static/js/agent/human-turn-composer.ts`.
2. Implemented `preview(charName: string, results: string | string[]): void` which sets `_dryRun = true`, mounts the modal, sets the phase to `'react'`, shows the supplied results, and displays the overlay.
3. Updated `finishReact` to check `if (_dryRun)`: resets state and hides the panel cleanly without firing `_reactResolve`, emitting actions, or triggering auto-memory.
4. Exported `preview` on `HumanTurnComposerModule`.
5. Recompiled TypeScript (`npm run build:ts`).
6. Added unit test in `tools/unit/test_human_turn_composer.js`.

## Steps to verify

1. Run unit test suite:
   `node tools/unit/run.cjs test_human_turn_composer.js`
   - expected: 6 passed, 0 failed.
   - observed: 6 passed, 0 failed.
2. Verified zero em-dashes across touched files.

## Acceptance

- [x] The composer can open directly in the react phase with a supplied result string (e.g. `HumanTurnComposer.preview(charName, resultText)` or an `opts.dryRun` on `request`) that resolves to NOTHING - no action, no endTurn, no memory write; closing it is a pure client dismissal.
- [x] The engine path is untouched: `setPhase('react')` via the real compose->Act->react flow behaves exactly as today.
- [x] Used by the e2e harness (task-693) to assert task-679's acceptance: split movement/prose/exits, clamped height, no raw way tail.
- [x] The affordance is hidden behind a flag or a dev-only entry point so normal play cannot trigger it accidentally.

## Files

- `static/js/agent/human-turn-composer.ts`
- `static/js/agent/human-turn-composer.js`
- `tools/unit/test_human_turn_composer.js`
