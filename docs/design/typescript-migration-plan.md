# TypeScript migration plan - size-ordered

**Date:** 2026-09-28  
**Companion to:** `docs/design/typescript-migration.md` (the convention; unchanged)  
**Method:** measured inventory of `static/js` - line counts, `window.*` references,
lit-html usage, and coverage against `static/js/types/globals.d.ts`.

The companion doc already has a *semantic* order (leaf -> core -> views). This plan is
the *size* order asked for, and it turns out to agree with the semantic one closely:
small files are leaves with 1-2 globals, large files are views with 6-16. Two things
the semantic order does not tell you, found by measuring:

1. **`window.Lit` is the whole ballgame.** 46 files, 29,813 lines - **46% of the
   corpus** - and it is not declared in `globals.d.ts` at all. It appears in *every*
   wave including the smallest. A pure size sort stalls on it in wave 1.
2. **Only 15 of 151 files convert without editing a shared file.** Nearly every
   conversion touches `static/js/types/globals.d.ts`, which makes it a hub in exactly
   the sense `.kilo/lanes/README.md` uses for `engine/tick_manager.py`.

## Inventory

| | |
|---|---|
| `.js` source files still to convert | **151** |
| Lines | **64,620** |
| Already converted | 2 - `agent/rate-limiter.ts` (72), `graph/graph-background.ts` (1,970) |
| Emitted `.js` committed to git | yes - both converted modules track their `.js` |
| Symbols declared in `globals.d.ts` | ~29, of which **9 are bare `any`** |

### What a single conversion actually touches

| Path | Change | Shared? |
|---|---|---|
| `static/js/<path>.ts` | new | no |
| `static/js/<path>.js` | deleted, re-added as emitted output | no |
| `static/js/types/globals.d.ts` | often, for ambient symbols | **YES - the hub** |
| `templates/index.html` | **no** - the emitted `.js` keeps the path the HTML loads | no |
| `tools/unit/run.cjs` | **no** - only for a *new* module, not a conversion | no |
| `docs/design/js-module-index.md` | only if the `@docs` header text changes | rare |

That profile is unusually clean for a large migration. `templates/index.html` is the
hottest shared front-end file and a conversion never touches it.

## W0 - type `window.Lit` (prerequisite, do this first, one lane)

`window.Lit` gates **46 of 151 files** and **29,813 of 64,620 lines**. It is the single
highest-leverage action in the migration, and it turns out to be a bounded job.

### What lit actually is here

- **Vendored, not CDN**: `static/js/vendor/lit-html/` - 26 files, 23 KB, minified.
  `templates/index.html` holds an **import map** pointing at it.
- **Version 3.2.1**, from `litHtmlVersions.push("3.2.1")` in the vendored bundle.
- **Zero `.d.ts` files.** `tsconfig.json` excludes `static/js/vendor/**`, so `tsc`
  never sees it and cannot infer anything from it.
- `window.Lit` is stamped by exactly **one** file, `static/js/shared/lit-bootstrap.js`,
  as a single object literal of 14 members: `html`, `svg`, `render`, `renderInto`,
  `renderPanel`, `nothing`, `noChange`, `classMap`, `styleMap`, `repeat`,
  `ifDefined`, `guard`, `live`, `unsafeHTML`.

That last point is why W0 is cheap: the type is **enumerable from one 52-line file**,
not something to be discovered across 46 call sites.

### The two decisions

**1. Where do the types come from?**

| Option | Trade-off |
|---|---|
| `npm i -D lit@3.2.1`, then `paths` in `tsconfig.json` | exact version match, real types, no runtime change. Costs a dev dependency and a `paths` entry |
| Hand-declare the 14 members in `globals.d.ts` | zero dependencies, follows the existing `ApiClient` precedent, but must be maintained |
| Copy lit's `.d.ts` into `static/js/types/` | no dependency, pinned copy, but it is vendored code in the repo |

`templates/index.html` already argues for this in a comment: versions are *pinned* on
purpose, because "an unpinned CDN means the app runs on whatever version happens to
be latest". `npm i -D lit@3.2.1` is the same stance in a form `tsc` can consume. Prefer
it; the hand-declared option stays the fallback if adding a dependency is unacceptable.

**2. The no-`import` rule needs one documented exception.**

The convention says converted files must not use `import`/`export`, because the app
loads classic scripts. But `shared/lit-bootstrap.js` is **already an ESM module** - it
has `import { html, ... } from 'lit-html'` and `export function renderPanel`, and it
is deliberately the one deferred load so classic scripts can read `window.Lit`.

So W0 has to state the rule for a second file type, and the answer should be: *the
bootstrap stays ESM and becomes a `.ts` with imports; everything else stays classic*.
Without that written down, the first person to convert a view has to re-derive it.

Incidental find: `lit-bootstrap.js` already uses `@param {TemplateResult}` in JSDoc
without importing that type. Converting it to `.ts` turns that dangling reference into
a real import, which is one of the easier wins in the migration.

**Also in W0, because it is the same file:** narrow the 9 bare `any` globals. `VW`
(26 files), `worldState` (13) and `events` (7) are the most-referenced. Narrowing them
is optional - an `any` does not block a conversion - but it is the difference between
151 typed files and 151 files that merely compile.

## Waves

| Wave | Size | Files | Lines | Lit | New ambient symbols needed |
|---|---|---|---|---|---|
| **W1** | 0-100 | 21 | 1,452 | 4 | `Lit`(4), `SoakState`(1), `SoakUI`(1), `InspectorWayViewTriggers`(1), `SoakApi`(1) |
| **W2** | 100-250 | 56 | 9,727 | 14 | `Lit`(14), `StructuredFormats`(4), `InspectorPanel`(2), `ScenarioStatus`(2), `ScenarioManager`(2) |
| **W3** | 250-500 | 30 | 10,525 | 4 | `Lit`(4), `DatasetCollector`(2), `NLEditor`(2), `TurnSceneView`(2), `GraphBackground`(2) |
| **W4** | 500-1000 | 30 | 20,331 | 14 | `Lit`(14), `InspectorHelpers`(4), `GraphToolbar`(3), `EmbeddingClient`(3), `InspectorTriggers`(3) |
| **W5** | 1000-2000 | 10 | 13,005 | 7 | `Lit`(7), `GraphBackground`(3), `narrationUI`(2), `GraphNetwork`(2), `GraphToolbar`(2) |
| **W6** | 2000+ | 4 | 9,580 | 3 | `Lit`(3), `TriggerGraph`(1), `TriggerTypes`(1), `InspectorAgentView`(1), `InspectorHelpers`(1) |

Size order is the right default here because difficulty tracks size almost perfectly
in this codebase: W1 averages 1.2 `window.*` references per file, W6 averages 8.2.

**The one exception the wave table hides:** `window.Lit` appears in W1 (4 files), W2
(14), W4 (14) and W6 (3). It is the only symbol that spans every wave, which is why
it is W0 rather than a W1 side-quest.

## Ownership - globals.d.ts is a hub

Only **15 of 151 files** (10%) convert with no shared-file edit at all - 2,656 lines,
4% of the corpus.

So this migration cannot be split naively across worktrees. Treat
`static/js/types/globals.d.ts` with the same rule as `engine/tick_manager.py`:

**One lane owns `globals.d.ts`.** Other lanes convert files and either

- bundle their new declarations into one commit on their own branch and hand that
  commit to the owner lane, or
- declare nothing new by widening a local type instead, which is usually the better
  answer and never the wrong one.

This maps onto the lanes already running - it is a spine/arms split, not a new axis.

## Procedure - unchanged

From `docs/design/typescript-migration.md`, step 3 is the one that matters here: **keep
the `@module`/`@contributes`/`@powers`/`@relates`/`@docs` header in the `.ts`**, because
it is emitted into the `.js` and the module index reads the emitted file. Losing a
header breaks `python tools/js_module_index.py --check`.

Do not use `import`/`export`. Emitted files begin with `"use strict";` (TS 7 removed
`alwaysStrict`), so a converted file gets strict semantics - a real behaviour change.

## Verification gate

```
npm run build:ts                 # emit .js next to each .ts
npm run typecheck                # parse all JS + TS, noEmit
npm run lint
node --check static/js/<path>.js  # the emitted file, not the .ts
node tools/unit/run.cjs          # loads the EMITTED .js - that is why it keeps working
python tools/js_module_index.py --check
```

`node tools/unit/run.cjs` is the one that catches a real mistake. It loads emitted
`.js`, so a broken emit fails there and nowhere else.

## Risks

| Risk | Mitigation |
|---|---|
| Two lanes edit `globals.d.ts` | single owner, per the hub rule above |
| A conversion silently drops a header | `js_module_index.py --check` in the gate |
| Emitted `.js` is hand-edited | the build overwrites it; the header comment in the emitted file says so |
| A converted view needs `import {html} from 'lit-html'` and breaks the classic-script model | W0 decision 2 - the bootstrap stays the only ESM module; everything else reads `window.Lit` |
| `tsc` resolves lit to nothing because vendor is excluded | W0 decision 1 - `npm i -D lit@3.2.1` plus a `paths` entry, or hand-declare the 14 members |
| Strict-mode change breaks sloppy-mode code | convert small files first - W1/W2 are where this would surface |
| `strict` is already on for `.ts` but off for `.js` | `tsconfig.check.json` has `strict: false` and `checkJs: false`; a converted file is held to a **higher** bar than the file it replaced |
| The biggest files are the ones nobody converts | W6 is 4 files and 9,580 lines - 15% of the corpus in 4 files. Schedule them as projects, not tickets |

## Appendix - full file list by wave

### W1 - 21 files, 1452 lines (0-100 lines)

| File | Lines | Lit | New ambient symbols |
|---|---|---|---|
| `event-bus.js` | 31 |  | - |
| `soak/soak-app.js` | 31 |  | `SoakState`, `SoakUI` |
| `shared/dom-utils.js` | 42 |  | - |
| `agent/prompt-builder/index.js` | 45 |  | - |
| `inspector/way-view-triggers.js` | 46 |  | `InspectorWayViewTriggers` |
| `shared/lit-bootstrap.js` | 52 | yes | `Lit` |
| `prompt-docs.js` | 62 |  | - |
| `soak/soak-api.js` | 62 |  | `SoakApi` |
| `agent/threat-detector.js` | 63 |  | `ThreatDetector` |
| `agent/agent-state.js` | 66 |  | `AgentState` |
| `stream/stream-turn-cards.js` | 66 | yes | `Lit` |
| `stream/stream-control-mode.js` | 71 |  | - |
| `inspector/panel.js` | 78 | yes | `InspectorPanel`, `Lit` |
| `shared/vital-color.js` | 78 |  | `VitalColor` |
| `graph/edge-types.js` | 85 |  | `EdgeTypes` |
| `shared/embedding-client.js` | 90 |  | `EmbeddingClient` |
| `ui/setup-checklist.js` | 90 |  | `CommandPalette`, `ScenarioWizard`, `SetupChecklist` |
| `agent/prompt-builder/schema-fragments.js` | 97 |  | - |
| `agent/sim-round.js` | 99 |  | `VWSimRound` |
| `stream/stream-persistence.js` | 99 | yes | `Lit` |
| `stream/stream-scrubber.js` | 99 |  | - |

### W2 - 56 files, 9727 lines (100-250 lines)

| File | Lines | Lit | New ambient symbols |
|---|---|---|---|
| `agent/object-responder.js` | 102 |  | `ObjectResponder` |
| `graph/edge-inspector.js` | 106 | yes | `EdgeInspector`, `InspectorPanel`, `Lit` |
| `ui/scenario-status.js` | 107 |  | `ScenarioStatus` |
| `ui/undo-history.js` | 107 |  | `UndoHistory` |
| `soak/soak-presets.js` | 109 |  | `SoakPresets` |
| `agent/prompt-builder/context-sections.js` | 110 |  | - |
| `ui-helpers.js` | 112 |  | `GraphToolbar` |
| `shared/trigger-types.js` | 113 |  | `TriggerTypes` |
| `agent/emote-picker.js` | 118 | yes | `EmotePicker`, `Lit` |
| `item-library/contents-editor.js` | 123 | yes | `ItemLibraryContents`, `Lit` |
| `ui/recent-edits.js` | 123 |  | - |
| `ui/scenario-health.js` | 123 |  | `ScenarioHealth`, `ScenarioManager` |
| `agent/simultaneous.js` | 125 |  | `VWSimultaneous` |
| `ui/edit-feed.js` | 129 |  | `EditFeed` |
| `ui/room-template-palette.js` | 130 |  | `RoomTemplatePalette` |
| `shared/emotion-mapper.js` | 133 |  | `EmbeddingClient`, `EmotionMapper` |
| `shared/template-sync.js` | 141 |  | `InspectorTemplateSync` |
| `soak/soak-format.js` | 142 |  | `SoakFormat` |
| `nl-editor/diff.js` | 149 |  | `NLEditorDiff` |
| `shared/env-presets.js` | 149 |  | `EnvPresets` |
| `agent/response-parser.js` | 159 |  | `ResponseParser`, `__repairStats` |
| `ui/engine-config-view.js` | 159 | yes | `EngineConfigView`, `Lit`, `toastError`, `toastInfo` |
| `agent/vital-thresholds.js` | 166 |  | `VitalThresholds` |
| `graph/tree-view.js` | 170 | yes | `GraphTreeView`, `Lit` |
| `ui/llm-inspector.js` | 170 |  | `DatasetCollector` |
| `context-window.js` | 174 |  | `ContextWindowManager` |
| `shared/ai-generator.js` | 175 |  | `StructuredFormats` |
| `agent/prompt-builder/conversation-context.js` | 177 |  | - |
| `nl-editor/index.js` | 182 |  | `NLEditor`, `ui` |
| `agent/action-normalizer.js` | 184 |  | `ActionNormalizer` |
| `agent/prompt-builder/system-prompt.js` | 184 |  | - |
| `shared/json-utils.js` | 186 |  | `__repairStats` |
| `stream/stream-filters.js` | 189 | yes | `Lit` |
| `agent/plan-manager.js` | 190 |  | `PlanManager`, `StructuredFormats` |
| `ui/timeskip.js` | 191 |  | `Timeskip` |
| `stream/stream-raw-llm.js` | 197 | yes | `Lit`, `_lastRecallStats` |
| `agent/plan-tracker.js` | 198 |  | `PlanTracker` |
| `item-library/placement.js` | 200 | yes | `ItemLibraryPlacement`, `Lit` |
| `shared/json-schemas.js` | 200 |  | `StructuredFormats` |
| `ui/changes-panel.js` | 201 |  | `ChangesPanel`, `ScenarioStatus` |
| `character-art.js` | 207 |  | `CharacterArt`, `InspectorHelpers` |
| `shared/tag-multiselect.js` | 207 | yes | `Lit`, `TagMultiselect` |
| `graph/event-handlers.js` | 213 |  | `GraphBackground`, `GraphEventHandlers` |
| `inspector/lore-view.js` | 215 | yes | `InspectorLore`, `InspectorPanel`, `Lit` |
| `ui/scenario-manager.js` | 217 |  | `ScenarioManager` |
| `graph/projector.js` | 219 |  | `GraphProjector` |
| `shared/search-select.js` | 220 | yes | `Lit`, `SearchSelect` |
| `structures.js` | 227 |  | `structures`, `worldSync` |
| `ui/settings-view.js` | 227 |  | `SettingsView` |
| `agent/memory-manager.js` | 230 |  | `AgentMemory`, `EmbeddingClient`, `StructuredFormats` |
| `graph/node-badges.js` | 230 |  | `NodeBadges` |
| `graph/context-menu.js` | 235 | yes | `GraphContextMenu`, `Lit` |
| `shared/trigger-suggest-ai.js` | 237 |  | `TriggerSuggestAI` |
| `graph/separation.js` | 245 |  | `GraphSeparation` |
| `inspector/way-view-connections.js` | 246 | yes | `InspectorWayView`, `InspectorWayViewConnections`, `Lit` |
| `narration-ui.js` | 249 | yes | `Lit`, `narrationUI` |

### W3 - 30 files, 10525 lines (250-500 lines)

| File | Lines | Lit | New ambient symbols |
|---|---|---|---|
| `agent/involuntary.js` | 263 |  | `Involuntary` |
| `agent/prompt-builder/turn-prompts.js` | 263 |  | - |
| `agent/prompt-builder/helpers.js` | 266 |  | `PlanTracker` |
| `ui/command-palette.js` | 269 |  | `CommandPalette`, `DatasetCollector`, `NLEditor`, `Timeskip` |
| `agent/turn-you-strip.js` | 291 |  | `TurnSceneView`, `TurnYouStrip`, `VitalColor`, `VitalThresholds`, `openVitalModal` |
| `agent/prompt-builder/contextual-actions.js` | 293 |  | - |
| `shared/dataset-collector.js` | 293 |  | `DatasetCollector`, `__datasetSeq`, `__rawSeq` |
| `graph/overlays.js` | 294 |  | `GraphOverlays` |
| `nl-editor/agent-loop.js` | 301 |  | `ContextWindowManager`, `GraphBackground`, `NLEditorAgent` |
| `agent/turn-queue.js` | 303 |  | `TurnQueue` |
| `inspector/way-authoring.js` | 306 |  | `WayAuthoring` |
| `nl-editor/ghosts.js` | 307 |  | `NLEditor`, `NLEditorGhosts` |
| `storage.js` | 310 |  | - |
| `soak/soak-charts.js` | 312 |  | `SoakCharts`, `SoakFormat` |
| `soak/soak-state.js` | 318 |  | `SoakApi`, `SoakFormat`, `SoakState` |
| `world-state.js` | 343 |  | `TurnQueue` |
| `graph/tooltips.js` | 350 |  | `GraphTooltips` |
| `graph/focus.js` | 363 |  | `GraphFocus`, `GraphToolbar` |
| `item-library/ai-generation.js` | 377 | yes | `ItemLibraryAI`, `ItemLibraryTriggerSuggester`, `Lit`, `TriggerSuggestAI`, `TriggerSuggestDiff` |
| `graph/graph-export.js` | 384 |  | `GraphBackground`, `GraphExport`, `devicePixelRatio` |
| `shared/trigger-suggest-diff.js` | 390 |  | `TriggerSuggestDiff` |
| `sky-scape.js` | 392 |  | `SkyScape` |
| `nl-editor/staging.js` | 397 |  | `NLEditorStaging` |
| `world-sync.js` | 418 | yes | `Lit` |
| `nl-editor/ui.js` | 429 |  | `NLEditorUI` |
| `agent/turn-scene-view.js` | 440 |  | `CharacterArt`, `TurnSceneView`, `innerHeight`, `innerWidth` |
| `inspector/known-by.js` | 440 |  | `KnownBySection` |
| `item-library/consumable-triggers.js` | 450 |  | `ItemLibraryTriggerSuggester` |
| `shared/diff-modal.js` | 475 | yes | `DiffModal`, `Lit` |
| `validator-panel.js` | 488 | yes | `InspectorWayView`, `Lit`, `ValidatorPanel` |

### W4 - 30 files, 20331 lines (500-1000 lines)

| File | Lines | Lit | New ambient symbols |
|---|---|---|---|
| `config.js` | 523 |  | `GraphToolbar`, `TurnQueue`, `VWSimultaneous` |
| `agent/prompt-builder/memory-context.js` | 526 |  | `EmbeddingClient`, `EmotionMapper`, `_lastRecallStats` |
| `ui/scenario-wizard.js` | 537 |  | `ScenarioWizard` |
| `agent/prompt-builder/character-state.js` | 543 |  | `PlanTracker`, `VitalThresholds` |
| `inspector/sprite-sheet.js` | 549 |  | `InspectorHelpers`, `SpriteSheet` |
| `llm-client.js` | 567 |  | `DatasetCollector` |
| `inspector.js` | 605 | yes | `InspectorPanel`, `Lit`, `StructuredFormats` |
| `soak/soak-spacetime.js` | 617 |  | `SoakFormat`, `SoakSpacetime` |
| `graph/node-operations.js` | 618 | yes | `GraphNodeOps`, `Lit` |
| `inspector/trigger-helpers.js` | 621 | yes | `InspectorTriggers`, `ItemLibraryTriggerSuggester`, `Lit`, `TriggerSuggestAI`, `TriggerSuggestDiff`, `ValidatorPanel` |
| `ui/create-modal.js` | 629 | yes | `Lit` |
| `ui-controller.js` | 638 | yes | `Lit`, `SkyScape`, `ValidatorPanel`, `VitalThresholds`, `agent` |
| `graph/toolbar.js` | 645 |  | `GraphToolbar`, `matchMedia` |
| `api.js` | 647 |  | `InspectorAgentView`, `runAction` |
| `ui/world-export.js` | 656 |  | `WorldExport`, `chrome`, `open`, `showSaveFilePicker` |
| `inspector/paperdoll-view.js` | 665 | yes | `InspectorPaperdoll`, `Lit`, `innerWidth` |
| `ui/saveload-view.js` | 674 | yes | `Lit`, `SaveLoadView`, `showSaveFilePicker` |
| `ui/help-center.js` | 683 |  | `HelpCenter` |
| `inspector/area-view.js` | 698 | yes | `EnvPresets`, `InspectorAreaView`, `InspectorHelpers`, `InspectorTemplateSync`, `InspectorTriggers`, `Lit`, `libraryBrowser`, `worldSync` |
| `agent-lens.js` | 702 | yes | `CharacterArt`, `Lit` |
| `graph/layout-engine.js` | 721 |  | `GraphToolbar` |
| `inspector/memory-view.js` | 745 | yes | `EmbeddingClient`, `InspectorMemory`, `Lit`, `TagMultiselect` |
| `agent/turn-feed.js` | 749 |  | - |
| `event-stream.js` | 753 | yes | `Lit` |
| `worldpainter/grid-model.js` | 767 |  | `gridModel` |
| `agent/human-turn-composer.js` | 782 | yes | `CharacterArt`, `HumanTurnComposer`, `Lit`, `Timeskip`, `TurnSceneView`, `TurnYouStrip` |
| `inspector/helpers.js` | 802 | yes | `CharacterArt`, `GraphRelativeLayout`, `InspectorHelpers`, `Lit`, `StructuredFormats` |
| `agent/prompt-builder/room-context.js` | 857 |  | `EmbeddingClient`, `EmotionMapper` |
| `inspector/item-view.js` | 882 | yes | `InspectorHelpers`, `InspectorItemView`, `InspectorTriggers`, `Lit` |
| `graph/relative-layout.js` | 930 |  | `GraphRelativeLayout`, `GraphSeparation` |

### W5 - 10 files, 13005 lines (1000-2000 lines)

| File | Lines | Lit | New ambient symbols |
|---|---|---|---|
| `library-browser.js` | 1040 | yes | `DiffModal`, `InspectorAgentView`, `Lit` |
| `inspector/way-view.js` | 1044 | yes | `InspectorHelpers`, `InspectorTemplateSync`, `InspectorTriggers`, `InspectorWayView`, `InspectorWayViewConnections`, `InspectorWayViewTriggers`, `Lit` |
| `main.js` | 1066 | yes | `CreateModal`, `Lit`, `SaveLoadView`, `gridModel`, `innerHeight`, `narrationUI`, `structures`, `worldPainter` |
| `graph-manager.js` | 1188 | yes | `EdgeInspector`, `GraphBackground`, `GraphNetwork`, `GraphToolbar`, `InspectorPanel`, `Lit`, `worldSync` |
| `agent-engine.js` | 1366 |  | `Involuntary`, `StructuredFormats`, `VWSimRound`, `VWSimultaneous`, `narrationUI` |
| `item-library.js` | 1402 | yes | `ItemLibraryTriggerSuggester`, `Lit`, `TriggerSuggestDiff`, `TriggerTypes` |
| `soak/soak-ui.js` | 1415 |  | `SoakApi`, `SoakCharts`, `SoakFormat`, `SoakPresets`, `SoakSpacetime`, `SoakState`, `SoakUI` |
| `nl-editor/tools.js` | 1463 |  | `GraphBackground`, `NLEditorTools` |
| `graph/network-manager.js` | 1503 | yes | `CharacterArt`, `GraphBackground`, `GraphNetwork`, `GraphRelativeLayout`, `GraphToolbar`, `Lit`, `NLEditorGhosts` |
| `inspector/behaviors-view.js` | 1518 | yes | `InspectorBehaviors`, `Lit` |

### W6 - 4 files, 9580 lines (2000+ lines)

| File | Lines | Lit | New ambient symbols |
|---|---|---|---|
| `shared/trigger-editor.js` | 2023 | yes | `Lit` |
| `shared/trigger-graph.js` | 2240 | yes | `Lit`, `TriggerGraph`, `TriggerTypes` |
| `inspector/agent-view.js` | 2288 | yes | `InspectorAgentView`, `InspectorHelpers`, `InspectorMemory`, `InspectorPanel`, `InspectorPaperdoll`, `InspectorTemplateSync`, `KnownBySection`, `Lit`, `PlanTracker`, `StructuredFormats`, `VitalColor`, `VitalThresholds`, `_traitLibrary`, `_traitLibraryAt` |
| `worldpainter/editor.js` | 3029 |  | `Image`, `Konva`, `gridModel`, `worldPainter`, `worldSync` |

