---
type: task
status: todo
area: refactor
priority: low
wiki: "[[Feature Map]]"
---

# task-441: Split the frontend giants and the trigger test module

**Filed:** 2026-09-21
**Supersedes:** task-314's frontend and test scope
**Related:** task-216 (trigger editor inspector work), task-218 (the module-per-concern shape),
task-440 (the backend counterparts), task-625 (real cross-cutting duplication, which is a
different problem — see "Why this is not a de-duplication task").

## What

Oversized front-end hosts hold more than one concern, so a change in one panel forces reading and risking the whole file. Linecount is the detector; cohesion is the criterion — a file that is cohesive at 900 lines stays at 900 lines, and a file is split only when it holds more than one concern. Remeasured 2026-10-16 with a ≥1500-line scan of `static/js/**/*.ts` (skip emitted `.js` siblings): 12 hosts, topped by `worldpainter/editor.ts` (3,927, still the largest file in the repo), `shared/trigger-graph.ts` (3,029), `inspector/agent-view.ts` (2,778), `graph/graph-background.ts` (2,294), `shared/trigger-editor.ts` (2,184), `graph/network-manager.ts` (2,150, +473 — still regrowing after task-314 wave 1), and `inspector/mind-view.ts` (2,031, NEW entrant). Agent sessions that touch Persona/Mind, WorldPainter, or the trigger editor currently pay the full-host tax in context — `mind-view.ts` alone is ~130k characters — so splitting Persona/Mind (task-852) stops requiring the whole Mind host in context. Test target: `tests/test_trigger_system.py` is 3,029 lines (+580) and still one mega-module, split by subsystem (evaluation, effects, conditions, scheduling). This is cohesion work, not de-duplication: `jscpd` over `.ts` sources found 69 exact clones, 570 lines (1.14%), 61 of 69 intra-file, the largest cross-file block 12 lines. The real duplicated-concept work is the backend dual-store class (task-625) — do not merge the two jobs.

## Measured targets (2026-10-16 remeasure, `.ts` sources)

All front-end files are TypeScript emitting to `.js` (migration complete).
Line counts are the `.ts` source; `.js` is generated and must not be counted or edited.
Measure a candidate with the source, not the sibling.

Remeasured 2026-10-16 with a ≥1500-line scan of `static/js/**/*.ts` (skip emitted
`.js` siblings). Delta vs 2026-10-06 in parentheses. **New entrants** called out.

| File | Lines | Δ | Suggested seam |
|------|------:|:--:|----------------|
| `static/js/worldpainter/editor.ts` | 3927 | +181 | Still the largest file in the repo. Split by tool/panel (brush options, tool handlers, layer/palette UI, import/export) — investigate the real boundaries before choosing. |
| `static/js/shared/trigger-graph.ts` | 3029 | +269 | layout/rendering from node/edge editing |
| `static/js/inspector/agent-view.ts` | 2778 | +84 | sub-views: memory, plans, vitals, relationships, paperdoll (task-314's wave-2 attempt produced an abandoned `inspector/agent/agent-header` orphan, deleted 2026-09-21; restart from the live file, do not resurrect the snapshot) |
| `static/js/graph/graph-background.ts` | 2294 | +186 | background image layering vs coordinate/position logic. Intersects task-625 §1 (layout position stored in two homes) — resolve that source-of-truth question before splitting, or the seam lands in the wrong place |
| `static/js/shared/trigger-editor.ts` | 2184 | +120 | rendering vs validation vs serialization |
| `static/js/graph/network-manager.ts` | 2150 | +473 | **Still regrowing** after task-314 wave 1 (`projector`/`overlays`/`tooltips`/`focus`). Confirm whether this is new concerns or churn before splitting again |
| `static/js/inspector/mind-view.ts` | 2031 | **NEW** | **New entrant.** Persona tab / Mind panel shell (task-830 family, task-852 improvement plan). Split by tab: mind / persona / perception / memories / people — persona alone is a multi-section form that should not keep growing inside the host |
| `static/js/nl-editor/tools.ts` | 1828 | +346 | tool/schema definitions vs the executor |
| `static/js/graph-manager.ts` | 1635 | +324 | state/store vs layout driving |
| `static/js/agent-engine.ts` | 1610 | +224 | regrown after task-218's extraction; identify the new concerns before splitting |
| `static/js/item-library.ts` | 1534 | +123 | list/editor/import from rendering |
| `static/js/soak/soak-ui.ts` | 1518 | +92 | panel rendering vs run/data shaping |
| `static/js/inspector/sprite-sheet.ts` | 1449 | +109 | slicing geometry vs gallery/UI (note task-678 touches the slicer) |
| `static/js/inspector/behaviors-view.ts` | 1406 | +37 | behavior list vs rule editor |
| `static/js/library-browser.ts` | 1327 | +309 | overlaps `item-library.ts` — decide ownership before splitting either |
| `static/js/inspector/helpers.ts` | 1149 | +73 | shared render helpers vs per-view logic |
| `static/js/agent/prompt-builder/room-context.ts` | 1141 | +73 | context assembly vs formatting |
| `static/js/main.ts` | 1109 | +116 | crossed the old ~1000 line; keep tracked, split only if concerns warrant it |

Agent-context note (why this card matters beyond ergonomics): reading any of
the ≥2k hosts whole into a chat burns a large fraction of a session budget.
`mind-view.ts` alone is ~130k characters. Splits are cohesion work first; a
side effect is that Persona/Mind work (task-852) stops requiring the whole
Mind host in context.

### Test targets

| File | Lines | Δ | Suggested seam |
|------|------:|:--:|----------------|
| `tests/test_trigger_system.py` | 3029 | +580 | split by subsystem (evaluation, effects, conditions, scheduling) — still one mega-module |

Secondary test candidates (split only if failures stop isolating): `test_world_compile.py`
(1808, was 1449), `test_world_grid_routes.py` (1347), `test_item_actions.py` (1318).

## Why this is not a de-duplication task

Measured 2026-10-06 with `jscpd` over `.ts` sources only (excluding the generated `.js`):

```
69 exact clones, 570 lines (1.14%) duplicated, 144 files
61 of 69 clones are INTRA-file
 8 of 69 are cross-file; the largest is 12 lines
```

Cross-file duplication in the front end is **eight blocks of ≤12 lines** — noise. The
monoliths are large because they are cohesive forms/editors, not because they copy each
other. Generalising them to kill duplication would be solving a problem the measurement
says barely exists. The real duplicated-concept work is the *backend* dual-store class
(`task-625`): a fact stored in two places with different behaviour. Do not merge the two
jobs.

Caveat on the measurement: `jscpd` catches **exact** clones at ≥50 tokens. Near-duplicate
functions that differ by a name are not counted. If a specific pair looks suspicious,
confirm by reading it — do not treat 1.14% as proof of zero duplication.

## How

1. **One file at a time.** Pick the smallest target first as the proof of pattern.
2. **No behaviour change.** Keep `window.Foo` namespaces and re-export moved members as
   thin delegates where call sites use them (the `graph/projector` pattern from task-314
   wave 1).
3. **Dedup & reuse pass (mandatory per extraction).** While splitting, scan the extracted
   concern and its host for duplicate logic and near-identical helpers; consolidate onto
   one owner instead of copying into the new module. Do not generalise to kill duplication
   that the measurement says barely exists (see "Why this is not a de-duplication task");
   only consolidate where a real duplicate is found while reading.
4. **Agent-experience & cleanliness (mandatory per extraction).** Name modules by
   concern, keep each under ~600 lines where the seam allows, add a one-line module
   docstring stating owner and public surface, and ensure a fresh agent session can
   understand the module without reading the host. No new abstraction unless an existing
   seam already represents the concept.
5. **Edit the `.ts`, never the `.js`.** Add the new module's `<script>` tag in
   `templates/index.html` in the same commit (these are classic browser globals). Task-314
   wave 2 left modules unloaded and threw on open — verify with
   `python tools/ts_convert.py check` (build + typecheck + lint + module check) and
   `node tools/unit/run.cjs` on every touched file.
6. **`node --check` every generated `.js`** before committing.
7. **Record what moved** as a table in this file, per the task-314 wave-1 shape.

## Acceptance

- Each split lands with the host file's line count materially reduced, the new module
  loaded by `templates/index.html` (if browser-global), and no orphan left behind.
- `python tools/ts_convert.py check` clean and `node tools/unit/run.cjs` still green
  except known pre-existing failures.
- For the test split: each new test module runs standalone, and the total test count is
  unchanged.

## Non-goals

- Behaviour changes or UI redesign.
- **Chasing a line-count target.** A cohesive 1200-line file may stay 1200 lines.
- Backend splits (task-440).
- De-duplication of concepts (task-625); this task does not touch it.

## Notes

- Originally measured 2026-09-21 against `.js` files. Refreshed 2026-10-06 to `.ts`
  sources after the TypeScript migration; 12 files not on the original list were added,
  including `worldpainter/editor.ts`, then the largest file in the repo.
- Remeasured 2026-10-16: every prior target grew; `mind-view.ts` (2031) entered the
  ≥1500 set; `network-manager.ts` (+473) and `nl-editor/tools.ts` (+346) are the
  steepest growers; `test_trigger_system.py` is now 3029 lines.

## Why

Oversized front-end hosts hold more than one concern, so a change in one panel
forces reading and risking the whole file. Linecount is the detector; cohesion
is the criterion. Agent sessions that touch Persona/Mind, WorldPainter, or the
trigger editor currently pay the full-host tax in context.

## Steps to verify

1. Remeasure the host and new module after each one-file extraction.
   - expected: host line count materially lower; new module owns one concern;
     both load via `templates/index.html` when browser-global.
   - observed: 2026-10-16 remeasure recorded above; no extraction landed this pass.
2. `python tools/ts_convert.py check` and `node tools/unit/run.cjs` after each split.
   - expected: green (known pre-existing failures only).
   - observed: not run this update (measurement-only card refresh).
3. Live: open the affected surface and exercise its existing controls.
   - expected: same location, same action, same visible result; no orphan module.
   - observed: not applicable until an extraction lands.

## Files

- `static/js/worldpainter/editor.ts` and extracted siblings (when split)
- `static/js/shared/trigger-graph.ts`, `trigger-editor.ts`
- `static/js/inspector/agent-view.ts`, `mind-view.ts`, `behaviors-view.ts`, `sprite-sheet.ts`, `helpers.ts`
- `static/js/graph/graph-background.ts`, `network-manager.ts`, `graph-manager.ts`
- `static/js/nl-editor/tools.ts`, `agent-engine.ts`, `item-library.ts`, `library-browser.ts`, `soak/soak-ui.ts`, `main.ts`
- `tests/test_trigger_system.py` (and secondary test modules if split)
- `templates/index.html` (script registration per new browser-global module)

## Browser UI and intended live verification

Intended UI home: the existing browser surfaces served by `templates/index.html`; this is a cohesion refactor, so each split must preserve the exact controls and behavior where they currently render.

Current availability: remeasured 2026-10-16 — 12 hosts ≥1500 lines in `static/js` (plus several 1k–1499 tracked), topped by `worldpainter/editor.ts` (3927) and `trigger-graph.ts` (3029). New entrant: `mind-view.ts` (2031). Module extraction is still planned; no surface change is intended. This card refresh is measurement-only.

Live steps when available:
1. Open the affected UI before and after each one-file split and exercise its existing controls from the task's host module.
   - expected: controls remain in the same location, trigger the same action, and produce the same visible result; no orphaned or duplicate module behavior appears.
2. For any browser-global module, inspect the loaded script/module registration after page load.
   - expected: the new module is loaded through the existing entry point only when required; `templates/index.html` gains no unnecessary script entry.
3. Run `python tools/ts_convert.py check` and `node tools/unit/run.cjs` after the extraction; run each newly split trigger test module standalone as the card specifies.
   - expected: the front-end gate passes, new test modules run independently, and the total trigger test count is unchanged.

This section is not a claim that the refactor is complete or browser-verified today.
