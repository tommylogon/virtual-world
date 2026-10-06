---
type: task
status: todo
area: refactor
priority: low
---

# task-441: Split the frontend giants and the trigger test module

**Filed:** 2026-09-21
**Supersedes:** task-314's frontend and test scope
**Related:** task-216 (trigger editor inspector work), task-218 (the module-per-concern shape),
task-440 (the backend counterparts), task-625 (real cross-cutting duplication, which is a
different problem — see "Why this is not a de-duplication task").

## Goal

Extract focused modules from the oversized front-end files, and split the single trigger
test module so failures isolate cleanly. **One file per commit, no behaviour change.**

This is a **cohesion** job, not a duplication job. A file that is cohesive at 900 lines
stays at 900 lines; a file is split only when it holds more than one concern.

## Measured targets (2026-10-06, `.ts` sources)

All front-end files are TypeScript emitting to `.js` (migration complete, 158 files).
Line counts are the `.ts` source; `.js` is generated and must not be counted or edited.
Measure a candidate with the source, not the sibling.

| File | Lines | Suggested seam |
|------|------:|----------------|
| `static/js/worldpainter/editor.ts` | 3746 | **Largest file in the repo and not previously tracked.** Split by tool/panel (brush options, tool handlers, layer/palette UI, import/export) — investigate the real boundaries before choosing. |
| `static/js/shared/trigger-graph.ts` | 2760 | layout/rendering from node/edge editing |
| `static/js/inspector/agent-view.ts` | 2694 | sub-views: memory, plans, vitals, relationships, paperdoll (task-314's wave-2 attempt produced an abandoned `inspector/agent/agent-header` orphan, deleted 2026-09-21; restart from the live file, do not resurrect the snapshot) |
| `static/js/graph/graph-background.ts` | 2108 | background image layering vs coordinate/position logic. Intersects task-625 §1 (layout position stored in two homes) — resolve that source-of-truth question before splitting, or the seam lands in the wrong place |
| `static/js/shared/trigger-editor.ts` | 2064 | rendering vs validation vs serialization |
| `static/js/graph/network-manager.ts` | 1677 | **Re-entered the list.** It was split in task-314 wave 1 (`projector`/`overlays`/`tooltips`/`focus`) but has regrown past two files' worth. Confirm whether this is new concerns or churn before splitting again |
| `static/js/nl-editor/tools.ts` | 1482 | tool/schema definitions vs the executor |
| `static/js/soak/soak-ui.ts` | 1426 | panel rendering vs run/data shaping |
| `static/js/item-library.ts` | 1411 | list/editor/import from rendering |
| `static/js/agent-engine.ts` | 1386 | regrown after task-218's extraction; identify the new concerns before splitting |
| `static/js/inspector/behaviors-view.ts` | 1369 | behavior list vs rule editor |
| `static/js/inspector/sprite-sheet.ts` | 1340 | slicing geometry vs gallery/UI (note task-678 touches the slicer) |
| `static/js/graph-manager.ts` | 1311 | state/store vs layout driving |
| `static/js/inspector/helpers.ts` | 1076 | shared render helpers vs per-view logic |
| `static/js/agent/prompt-builder/room-context.ts` | 1068 | context assembly vs formatting |
| `static/js/library-browser.ts` | 1018 | overlaps `item-library.ts` — decide ownership before splitting either |

`static/js/main.ts` (993) is just under the line and was on the original list; keep it
tracked, split only if its concerns warrant it.

### Test targets

| File | Lines | Suggested seam |
|------|------:|----------------|
| `tests/test_trigger_system.py` | 2449 | split by subsystem (evaluation, effects, conditions, scheduling) — 14 classes in one module |

Secondary test candidates (split only if failures stop isolating): `test_world_compile.py`
(1449), `test_item_actions.py` (1039), `test_world_grid_routes.py` (1028).

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

## Approach

1. **One file at a time.** Pick the smallest target first as the proof of pattern.
2. **No behaviour change.** Keep `window.Foo` namespaces and re-export moved members as
   thin delegates where call sites use them (the `graph/projector` pattern from task-314
   wave 1).
3. **Edit the `.ts`, never the `.js`.** Add the new module's `<script>` tag in
   `templates/index.html` in the same commit (these are classic browser globals). Task-314
   wave 2 left modules unloaded and threw on open — verify with
   `python tools/ts_convert.py check` (build + typecheck + lint + module check) and
   `node tools/unit/run.cjs` on every touched file.
4. **`node --check` every generated `.js`** before committing.
5. **Record what moved** as a table in this file, per the task-314 wave-1 shape.

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
  including `worldpainter/editor.ts`, now the largest file in the repo.
