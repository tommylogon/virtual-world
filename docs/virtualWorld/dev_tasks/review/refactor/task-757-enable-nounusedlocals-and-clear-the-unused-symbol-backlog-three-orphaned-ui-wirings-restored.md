---
type: task
status: review
area: refactor
priority: medium
---

# task-757: Enable noUnusedLocals and clear the unused-symbol backlog (three orphaned UI wirings restored)

**Filed:** 2026-10-09
**Related:** task-756

## What

Turn on tsconfig noUnusedLocals (strict does not include it) so an orphaned local/type is a build error - the class that let _referenceControl vanish (0dc60c48). Clears ~59 unused locals + 2 unused types. Three are dropped wiring, restored not deleted: durabilityChip (paperdoll slot modal ReferenceError, silenced by a globals.d.ts declare), initScenarioNameEditor (missing from saveload-view's export so main.ts's guarded call was a no-op), renderVitalMetrics (never called by renderCharts; #soak-vital-metrics never rendered). Also removes the dead shadowed doorTags local (new system uses way tags) and the duplicate emotion plumbing in the memory-edit modal (home is the Mind view, task-756).

## Why

`strict: true` does **not** include `noUnusedLocals`, so a local or type that is
declared and never read compiles clean. That is exactly how `_referenceControl`
(commit `0dc60c48`) survived as an orphaned function while the WorldPainter HUD
silently lost its image picker. The compiler knew; we told it not to say.

## How

- `tsconfig.json`: add `noUnusedLocals: true`. `tsconfig.check.json` is left
  alone on purpose — it includes the generated `.js`, which would double every
  finding; the `.ts` build is the gate.
- Delete the unused locals/types. Three are **not** dead — they are dropped
  wiring, restored instead:
  - `durabilityChip` hoisted from `renderPaperdollEquipmentHtml` to module scope
    in `inspector/paperdoll-view.ts`; the `showSlotModal` call was out of scope
    and threw `ReferenceError`, silenced by `declare const durabilityChip` in
    `globals.d.ts`. That declare is now dead but harmless.
  - `initScenarioNameEditor` added to the `SaveLoadView` return object
    (`ui/saveload-view.ts`) so `main.ts`'s guarded call resolves.
  - `renderVitalMetrics()` called from the `vitals` case in `renderCharts()`
    (`soak/soak-ui.ts`).
- Remove the shadowed `doorTags` local (`room-context.ts`) — the new system
  reads way tags, not area tags.
- Remove the duplicate emotion plumbing in the memory-edit modal; its home is
  the Mind view (task-756). The per-action intimacy intensities were literal
  duplicates of `kissIntensity` (one `Intensity` select per action row), so they
  are removed too; per-region behaviour lives backend-side
  (`engine/pleasure_actions.py` + `where`).

## Steps to verify

1. `npx tsc -p tsconfig.json --noEmit` — no `TS6133`/`TS6196`.
   - expected: no output
   - observed: no output
2. `npm run build:ts` then `node tools/unit/run.cjs`.
   - expected: build ok, 632 passed
   - observed: build ok, 632 passed
3. `python tools/ts_convert.py check` — build/typecheck/lint/unit/header/window ok.
   - expected: only the pre-existing `module:check` py failure
   - observed: only the pre-existing `module:check` py failure
4. Live: paperdoll slot modal opens (no ReferenceError); click the scenario-name
   chip to rename; the soak vitals tab shows the chip strip.

## Acceptance

- [x] `noUnusedLocals` is on and the front-end build fails on a declared-but-unread local/type.
- [x] The 59 unused locals + 2 unused types are resolved.
- [x] The three dropped wirings are restored, not deleted.
- [ ] Live: slot modal / scenario-name rename / soak vitals chips (needs a reload).

## Files

- `tsconfig.json` — `noUnusedLocals: true`
- `static/js/agent/**`, `static/js/inspector/**`, `static/js/shared/**`, `static/js/soak/**`, `static/js/ui/**`, `static/js/nl-editor/ghosts.ts`, `static/js/bug-report.ts`, `static/js/agent-engine.ts` — deletions
- `static/js/inspector/paperdoll-view.ts`, `static/js/ui/saveload-view.ts`, `static/js/soak/soak-ui.ts` — restored wiring
- `tools/window-usage-reviewed.json` — `way-view.js::Lit` verdict
- `tools/unit/test_worldpainter.js` — `_referenceControl` regression guard (earlier)
