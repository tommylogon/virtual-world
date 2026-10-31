---
type: task
status: todo
area: refactor
priority: low
wiki: "[[Feature Map]]"
---

# task-441: Split the frontend giants and the trigger test module

**Filed:** 2026-09-21
**Updated:** 2026-10-31
**Supersedes:** task-314's frontend and test scope
**Related:** task-216, task-218, task-440, task-625, task-901

## What

Oversized front-end hosts hold more than one concern, forcing agents and developers to read and risk an entire file for a local change. Line count is the detector; cohesion is the criterion. A file that is cohesive at 900 lines stays intact; a file is split when it holds multiple distinct sub-panels or responsibilities.

Remeasured 2026-10-31 with a scan of `static/js/**/*.ts` (excluding emitted `.js` siblings):
- `worldpainter/editor.ts` has grown to 5,348 lines (largest file in repo).
- `library-browser.ts` grew steeply to 2,863 lines.
- `inspector/agent-view.ts` is 2,852 lines.
- `inspector/mind-view.ts` grew to 2,784 lines following recent Persona additions (tasks 915-924). It is the highest-value agent-context target: extracting `persona-view.ts` frees up context across all Mind/Character work.
- `shared/trigger-graph.ts` shrank to 2,538 lines after task-901 began the extraction seam with `trigger-def.ts`.
- `tests/test_trigger_system.py` is 3,129 lines and remains a monolithic test suite needing division by subsystem (evaluation, effects, conditions, scheduling).

## Measured targets (2026-10-31 remeasure, `.ts` sources)

All front-end files are TypeScript emitting to `.js`. Line counts are taken from `.ts` sources.

| File | 2026-10-16 | 2026-10-20 | 2026-10-31 | Net Trend | Suggested seam |
|------|-----------:|-----------:|-----------:|:---------:|----------------|
| `static/js/worldpainter/editor.ts` | 3927 | 5002 | **5348** | Growing | Brush options, tool handlers, palette UI, import/export |
| `static/js/library-browser.ts` | 1327 | 1220 | **2863** | +1643 | Catalog browser vs item inspector vs import flows |
| `static/js/inspector/agent-view.ts` | 2778 | 2637 | **2852** | Regrowing | Memory, plans, vitals, relationships sub-views |
| `static/js/inspector/mind-view.ts` | 2031 | 2240 | **2784** | +544 | Extract `persona-view.ts` (Persona form, diff preview, compile buttons) from Mind shell |
| `static/js/shared/trigger-graph.ts` | 3029 | 2854 | **2538** | Shrinking | Layout/rendering vs edge editing (task-901 split out `trigger-def.ts`) |
| `static/js/shared/trigger-editor.ts` | 2184 | 2063 | **2396** | Growing | Render vs validation vs serialization |
| `static/js/graph/graph-background.ts` | 2294 | 2154 | **2309** | Growing | Background image layering vs coordinate logic |
| `static/js/graph/network-manager.ts` | 2150 | 2008 | **2251** | Growing | Core network vs node styling decorators |
| `static/js/agent-engine.ts` | 1610 | 1568 | **1982** | Growing | Turn queue vs prompt building vs cycle ticks |
| `static/js/nl-editor/tools.ts` | 1828 | 1791 | **1889** | Growing | Tool schema definitions vs execution |
| `static/js/graph-manager.ts` | 1635 | 1515 | **1708** | Growing | State/store vs layout orchestration |
| `static/js/soak/soak-ui.ts` | 1518 | 1425 | **1695** | Growing | Panel rendering vs soak run metrics |
| `static/js/item-library.ts` | 1534 | 1411 | **1537** | Growing | List/filter vs item creation editor |
| `static/js/inspector/sprite-sheet.ts` | 1449 | 1348 | **1470** | Steady | Slicing geometry vs sprite picker UI |
| `static/js/inspector/behaviors-view.ts` | 1406 | 1361 | **1435** | Steady | Behavior list vs rule card rendering |
| `static/js/agent/prompt-builder/room-context.ts` | 1141 | 1121 | **1244** | Growing | Context assembly vs prompt formatting |
| `static/js/inspector/helpers.ts` | 1149 | 1085 | **1154** | Steady | Shared DOM builder helpers |
| `static/js/main.ts` | 1109 | 1026 | **1134** | Steady | Core bootstrap and event routing |

### Test targets

| File | 2026-10-16 | 2026-10-20 | 2026-10-31 | Suggested seam |
|------|-----------:|-----------:|-----------:|----------------|
| `tests/test_trigger_system.py` | 3029 | 2649 | **3129** | Split into `test_trigger_eval.py`, `test_trigger_effects.py`, `test_trigger_conditions.py` |

## Why

Reading giant files whole burns session context windows and risks unintentional side effects across unrelated sub-panels. Splitting cohesive components into distinct files improves agent efficiency and human readability.

Priority 1 candidate: `mind-view.ts` (2,784 lines). The Persona sub-panel (schema forms, compile hooks, revert snapshotting, diff preview) accounts for over 1,200 lines and is completely distinct from the Mind tab's vitals, memories, and perception inspectors. Extracting `persona-view.ts` cleanly separates Persona authoring from Mind runtime state.

## How

1. **One file at a time.** Pick one high-value candidate (e.g. `persona-view.ts` out of `mind-view.ts`).
2. **Preserve namespaces and API contracts.** Re-export moved functions or attach them to existing global namespaces where needed.
3. **Update script tags and module index.** If adding a new browser-global file, register it in `templates/index.html` and verify with `python tools/js_module_index.py --check`.
4. **Compile and verify.** Run `npm run build:ts`, `python tools/ts_convert.py check --lenient-guards`, and `node tools/unit/run.cjs`.
5. **For test splits:** Ensure total test count remains unchanged and each split test module runs standalone via `pytest`.

## Acceptance

- [ ] High-priority host file (`mind-view.ts`) reduced in line count by extracting `persona-view.ts`.
- [ ] No regressions in browser functionality; UI renders exactly as before.
- [ ] TypeScript compiles cleanly (`npm run build:ts`) and module index checks pass.
- [ ] Test monolith `test_trigger_system.py` split into cohesive sub-modules with identical total test coverage.

## Files

- `static/js/inspector/mind-view.ts` (extract `persona-view.ts`)
- `static/js/shared/trigger-graph.ts`, `static/js/shared/trigger-editor.ts`
- `static/js/worldpainter/editor.ts`
- `tests/test_trigger_system.py`
- `templates/index.html`

## Browser UI and intended live verification

Intended UI home: The existing browser surfaces served by `templates/index.html`. As a cohesion refactor, each split must preserve exact controls, layout, and event wiring.

Live steps when available:
1. Open the affected panel (e.g. Character Inspector -> Mind / Persona tab).
2. Exercise each input, button, and preview modal.
3. Verify that all actions perform identically with zero console errors.

## Refactor discipline (applies to this task)

1. **Dedup & reuse pass (mandatory).** Scan touched concerns for duplicate logic; consolidate onto one owner.
2. **Agent-experience & cleanliness (mandatory).** Keep modules under ~600 lines where seams allow; add one-line module docstrings.
3. **No behaviour change unless the card says so.** Extraction and consolidation only.
4. **One file/concern at a time**, verified with a targeted test selection.

## Reconnaissance (2026-10-31)
- Measured: `worldpainter/editor.ts` reached 5,348 lines; `mind-view.ts` reached 2,784 lines; `library-browser.ts` reached 2,863 lines; `tests/test_trigger_system.py` reached 3,129 lines. Task-901 demonstrated extraction pattern by creating `trigger-def.ts`.
- Verdict: STILL_VALID. `mind-view.ts` -> `persona-view.ts` is the top priority seam. Status remains todo.
