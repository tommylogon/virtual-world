---
type: doc
tags: [system/ui]
---

# Frontend Rendering & Module Layout

## What you can do

Read this before you change how the UI is wired. It is not a feature you use - it
is the map of how the browser side is put together: the lit-html rendering
system, the classic-script versus deferred-module bootstrap, the graph module
split, the inspector/sync/DiffModal V3 workbench, and the WorldPainter overlay.
TypeScript sources (`static/js/**/*.ts`) compile via `npm run build:ts` to
sibling `.js` files loaded by `templates/index.html`. The ordering rule that
keeps `window.Lit` from racing `main.ts` init is the reason this page exists.

## Rendering: lit-html via `window.Lit`

All UI rendering goes through **lit-html** (vendored in `static/js/vendor/lit-html/`, no CDN).
The one entrypoint is `static/js/shared/lit-bootstrap.ts` (compiled to `lit-bootstrap.js`),
a deferred ES **module** that imports lit-html and stamps the API onto `window.Lit`:

```js
window.Lit = { html, svg, render, renderInto, renderPanel, nothing, noChange,
               classMap, styleMap, repeat, ifDefined, guard, live, unsafeHTML };
```

Every view file is a **classic (non-module) script** that captures the tag lazily:

```js
const viewHtml = (strings, ...values) => window.Lit.html(strings, ...values);
```

Classic scripts can't `import`, and module scripts are deferred - which is exactly why the tag is
captured lazily *inside functions*, never at parse time. Referencing `window.Lit.html` at module
load would crash because the module hasn't run yet.

### Why event handlers work in templates

`@click=${fn}`, `?selected=${bool}`, `.property=${value}` bindings are part of `lit-html`'s tag
itself - no extra directive needed. The `live`, `guard`, `classMap` etc. **directives** are
separate and only needed when you want reactive re-render behavior.

### XSS stance

lit-html escapes interpolations by default. Markup-injective content (LLM output, stored
descriptions) must go through `window.Lit.unsafeHTML(...)` **explicitly** - search for it when
checking new UI code. String-concat `innerHTML` builds are legacy; prefer lit-html templates.

## The classic/module race (and the fix)

`lit-bootstrap.ts` (loaded as `lit-bootstrap.js` via `<script type="module">`) executes **after**
all classic scripts on the page. `main.ts` (`main.js`) is classic and its async `init()` ran
immediately - the first init path that touched `window.Lit` (`events.restoreLog()`, restoring the
event stream from IndexedDB) crashed when the module hadn't stamped `window.Lit` yet:

```
event-stream.js:206 Uncaught TypeError: Cannot read properties of undefined (reading 'render')
```

Fix (2026-08-20):
- `static/js/main.ts` - `init()` now **polls for `window.Lit`** (up to 5 s) before restoring the
  event log:
  ```ts
  while (!window.Lit && Date.now() < litDeadline) await sleep(20);
  ```
- `static/js/event-stream.ts` + `static/js/stream/stream-persistence.ts` - `events.restoreLog()`
  delegates to `this._persist.restore()`, which returns early if `window.Lit` is still missing, so
  a module-load failure degrades gracefully instead of killing startup.

**Rule for future init paths:** anything that renders via `window.Lit` during startup must either
wait for the bootstrap or be deferred to a user action (like Engine Config's lazy load on tab
click). Do not call `window.Lit.*` from top-level classic-script code.

## Event Stream & Human Turn Composer

- `static/js/event-stream.ts` (`EventBus` v2): slimmed core with extracted collaborators in
  `static/js/stream/` (`stream-filters.ts`, `stream-turn-cards.ts`, `stream-raw-llm.ts`,
  `stream-persistence.ts`, `stream-scrubber.ts`, `stream-control-mode.ts`, `stream-sandbox.ts`).
  Uses lazy `window.Lit.html` / `window.Lit.render` / `window.Lit.unsafeHTML` for stream bubbles,
  collapsed LLM payload chips, and area dividers.
- `static/js/agent/human-turn-composer.ts` (`HumanTurnComposerModule`): continuous multi-action
  v4 human turn panel using `window.Lit.html` lazily (`htcPanelTag`), exposing `request()`,
  `react()`, and `closeTurn()` to `agent-engine.ts`.

## Graph module layout

The graph editor used to be one `network-manager` monolith (1,496 lines). It was split into
focused modules (task-314); `graph/network-manager.ts` keeps the shell + thin `@deprecated`
delegates so existing call sites keep working:

| Module | Owns |
|--------|------|
| `graph/projector.ts` | Pure visibility projection (node/edge visibility, no vis.js) |
| `graph/overlays.ts` | The 5 ambient overlays (light/heat/sound/trigger/cardinal) + change-cached lighting |
| `graph/tooltips.ts` | Node/edge tippy tooltips |
| `graph/focus.ts` | Search reveal + camera fit + bounded physics kick (debounced) |
| `graph/layout-engine.ts`, `graph/node-badges.ts`, `graph/toolbar.ts`, `graph/separation.ts` | Layout, badges, toolbar, overlap separation |

Load order in `templates/index.html` matters: modules that only reference globals at call time
can load before the objects they use, but keep dependencies load-order-stable or lazily global.

## Tune - graph physics at the canvas (the Tune popover)

**Status: implemented, wired, tested** (`tools/unit/test_graph_toolbar.js` parity tests,
`tools/unit/test_graph_tuning.js` apply-path pins).

**What it does.** The Settings -> Graph tab, rendered as a popover in the graph toolbar's
*Look* zone (`btn-tuning` / `#graph-tuning-menu`), so physics, separation, edge and camera
parameters can be dragged while the graph reacts. `GraphToolbar.TUNING_GROUPS` is the field
spec - 5 groups, 15 controls, grouped the way you think while tuning rather than the way the
engine names its forces: **Length of connections** (contents length, snappiness), **Pushing
apart** (the spread force, then the overlap guard with its strength and range), **Look**
(node size, edge width, arrows), **Engine (advanced)** (settle speed, solver, improved
layout), **Camera** (focus zoom). `buildTuningMenu()` renders it once on first open and
`syncTuning()` re-reads config every time it opens - **config stays the single source of truth
for values**; the Settings modal keeps its own static markup over the same keys (same groups,
same labels, same bounds). The parity tests read the modal's markup out of
`templates/index.html` and fail if the two surfaces drift apart (same keys, same min/max/step,
`gt-`-prefixed ids so they cannot collide).

**Live audit (2026-10-04, measured in the browser).** Every knob was exercised at both
extremes against a graph metric. Because the automation pane stops servicing animation frames
when idle, the solver was advanced with explicit `network.physics.physicsTick()` steps - both
arms of every pair use the same harness. (A backgrounded pane is *paused*, not dead: nodes move
normally in any foreground browser.)

| Knob | Effect | Evidence |
|---|---|---|
| Spread | strong | graph extent 1852 -> 6133 (-5 vs -500) |
| Contents length | strong | mean attachment distance 138 vs 421 (was 0% until the refresh below) |
| Node size | strong | character/item group sizes 24->38.4 / 18->28.8 at 1.6x, camera bit-identical |
| Snappiness | strong | rest length 100: soft (0.01) settles at mean distance 144, rigid (0.15) at 114 |
| Settle speed | strong | after an identical 250px kick, residual path 2429px at damping 0.05 vs 346px at 0.95 |
| Solver | strong | identical parameters: extent 4766 (Force Atlas 2) vs 3662 (Barnes-Hut) |
| Focus zoom | strong | `focusNode()` with the knob at 2.0 lands the camera at scale exactly 2.0 |
| Edge width / arrows | delivered + visual | option payload confirmed off `buildOptions()`; rendered A/B pair (0.5 vs 5) in the audit transcript |
| Improved layout | build-time by design | affects initial placement only - nothing to see at runtime, applies on the next data load |
| Guard strength / range / Pull strays back | weak - one-shot nudge | min free-pair distance 117-124 across the whole range: the guard displaces overlaps, then the running solver re-collapses them. The solver has the final word by design |
| **Edge length (global)** | **dead - removed from both surfaces** | attachment distances moved ~4% across its full 20-300 range: connection edges are stamped per edge in the dataset (label-sized or a per-way `edge_length`) and attachments use Contents length, so the solver's global spring length reaches only rare edges with no length of their own. The config key stays an engine fallback |

**Not everything a knob feeds is a solver option.** Per-edge rest lengths are stamped in the
dataset and the overlap guard runs once per layout pass, so replacing the full rebuild with an
in-place apply silently stranded Contents length and the guard knobs ("nothing happens until
the next reload"). `applyGraphSettings(rebuild = false)` now re-derives them whenever one of the
arrangement knobs (contents length, guard on/strength/min/max/pull, node size) changed -
`GraphNetwork.refreshEdgeLengths()` restamps the live edge options, and
`GraphRelativeLayout.resolveSeparation()` re-runs the guard over the graph as it stands, with
pull targets taken from the parents map (a displaced stray is reeled toward its holder's
current position, no ring re-seed).

**Two knobs this surfaced that the engine had but no UI exposed:** `graphRepelStrength` (the
overlap guard's push strength, clamped 0.05-1, default 0.6 - `graph/separation.ts:spec()` had
been reading it for years) and `graphNodeScale` (Node size, 0.5-2 - multiplies the drawn size
of item/way/character nodes and area card padding via `GraphNetwork.nodeSizeScale()`, applied
to the group options, image-node sizes and compact dots; fonts deliberately stay unscaled;
`separation.radiusOf` multiplies its type radii by the same value so the guard grants bigger
nodes more room). Group-option sizes apply live through `setOptions`; image-node sizes refresh
on the next data load.

**Applying settings - two paths, one writer.** `GraphNetwork.applyGraphSettings()`:

- **Default (slider ticks): in place.** `setOptions(buildOptions())` + `startSimulation()` -
  the new forces act on the graph *as it is on screen*: nodes keep their positions and settle,
  the camera never moves. Deliberately no refetch, no `_lastSig` blanking, no ring reseed, no
  restabilize - the old unconditional rebuild re-fit the camera ~1s after every slider tick,
  which read as the graph reloading under the user.
- **`rebuild` (Levels/Free switch via `toggleLayoutMode`): full re-derivation.** Reload +
  reseed + restabilize, because the switch changes *what* is laid out, not how it settles.

**Placement.** The menu is 640px wide and `#center-viewport` clips `overflow: hidden`, so CSS
placement alone loses its left column under the left panel whenever the trigger sits near it.
`GraphToolbar.placeTuningMenu()` runs on every open: right-align to the trigger, then clamp
into the center viewport's box, shrinking if the viewport itself is narrow.

**Camera group.** `graphFocusZoom` (Focus Zoom, 0.5-3, default 1.15) is the zoom vis.js uses
when a node is focused from a list, the outline, a search hit or the command palette - read at
click time by `graphManager.focusNode()`, which used to hardcode `scale: 1.15`. It is a camera
setting, not a physics one, so changing it only persists; the next focus uses it.

**Character drift note.** A character's resting distance from their room is the equilibrium of
their edge spring vs repulsion from the room's other contents - heavy carriers (elena vance:
12 carried/worn items) sit farthest out. "Pull strays back" only reels back nodes the overlap
guard displaced, and edge-joined nodes are exempt from it, so ordinary spread drift has no
counterweight knob yet (candidates: a character leash strength, or including edge-joined
pairs in the pull). Not implemented - by design for now; tune Spread / Snappiness /
Contents length to shrink the equilibrium.

## Inspector, Template Sync & DiffModal V3 Architecture

### Inspector Panel & Views (`static/js/inspector/`)

- `panel.ts` (`InspectorPanel`): the single render owner for `#inspector-panel`. Mixing raw
  `innerHTML` writes with lit-html corrupts lit's part tracking, so views hand `TemplateResult`s
  to `InspectorPanel.render()` / `renderStatic()` / `clear()`. On first bind it clears pre-lit
  static children once (`dataset.litBound`) and appends `DocPanel.section()` when `DocPanel` is
  available.
- `inspector-view-base.ts` (`InspectorViewBase` / `InspectorView`): base class providing
  lifecycle hooks (`show`, `hide`, `refresh`, `dispose`), microtask render coalescing
  (`_renderQueued`), breadcrumb integration (`_pushCrumb`), and safe `worldState` access.
- Entity & character views:
  - `agent-view.ts` (`InspectorAgentView`): full character inspector with `Inventory`, `Bio`,
    `Persona`, `Images`, and `Advanced` tabs; uses `helpers.ts`, `paperdoll-view.ts`,
    `memory-view.ts`, and `behaviors-view.ts`.
  - `mind-view.ts` (`InspectorMindView`): full-surface memory dynamics dashboard (timeline
    ribbon, category filters, dynamics badges, memory detail pane with connections, per-person
    derived profiles from `/api/players/<n>/memories/people`, and accessibility/decay panel).
  - `persona-view.ts` (`InspectorPersonaView`): extracted from `mind-view.ts` to separate
    authoring from runtime Mind inspection; schema-driven editor for character persona,
    appearance, identity, and narrative definitions backed by `GET/PUT /api/players/<n>/record`
    and preview compiler `POST /api/players/<n>/record/compile`.
  - `way-view.ts` (`InspectorWayView`): door/passage inspector with radial compass, state/skill
    options, connections, and triggers; delegates to `way-view-connections.ts` and
    `way-view-triggers.ts`.
  - `area-view.ts` (`InspectorAreaView`): room/area inspector for description, environment
    (light/noise), scope membership via `ApiClient.getWorldScopes`, and AI room improvement.
  - `item-view.ts` (`InspectorItemView`): item inspector for actions, parameters, tags, state,
    move, contents, and AI item improvement.

### Shared Template Sync (`static/js/shared/template-sync.ts`)

`InspectorTemplateSync` provides the shared "Library Template" footer pattern for node
inspectors (`way`, `area`, `character`), mirroring item-view's template-selector +
Refresh-from-Library flow:

- `register(type, cfg)` registers per-type world payload builders, diff sections, and optional
  save callbacks.
- `renderTemplateRow()` renders the template search input/datalist, variant and override badges,
  Refresh from Library button, optional Save to Library button, and Break Link button (shown
  only when `library_id` is set, with provenance note if previously unlinked).
- `populateSelector()` loads the type's library registry with a 30 s TTL cache and deduplicates
  aliases via `dedupeLibraryEntries()`.
- `refreshFromLibrary()` fetches the library entry, builds the world payload, opens
  `DiffModal.show(libEntry, worldPayload, cfg.sections, { direction: 'to-world', ... })`, and
  applies selected sections/entries via `/api/library/refresh-to-world`.
- `breakTemplateLink()` unbinds the node via `/api/library/break-template-link` while preserving
  all current node data.

### DiffModal V3 Hybrid Merge Workbench (`static/js/shared/diff-modal.ts`)

`DiffModal` handles world <-> library conflict resolution via
`DiffModal.show(current, incoming, sections, options)`, resolving to `null` (cancel),
`{ action: 'update', sections, entries }`, or `{ action: 'duplicate', name, id, sections, entries }`.

V3 Hybrid Merge Workbench capabilities:

- Fluid widescreen layout (`clamp`/`vh`) with sticky header, KPI bar, and dry-run summary footer.
- Hides identical (`=`) sections, entries, and axes by default with a KPI toggle.
- Inline word-level LCS diff (`wordDiff`) for prose fields and memory text.
- Full untruncated memory text with metadata pills and `#tag` facet chips.
- World-only / target-only items (especially seed memories detected by `isSeedMemory`) are
  protected as Keep Safe by default unless explicitly unlocked and marked for removal.
- Per-axis Smart Merge (`buildAxisRows`) for structured objects (`stats`, `skills`,
  `relationships`, `vitals`, `decay_rates`, `conditions`, `equipped`).
- Clear direction banner (`Library -> World` vs `World -> Library`) and UndoHistory refresh hook
  on Apply.

## WorldPainter Architecture (`static/js/worldpainter/`)

WorldPainter is a plain-DOM + Konva overlay (no Lit, no deferred module ordering constraints)
for editing 3-mode recursive scope grids (`world`, `town`, `interior`), backed by
`routes/world_grid_ops.py` (`/api/world/scopes/<id>/grid*`) and `engine/world_grid.py`:

| Module | Owns |
|--------|------|
| `worldpainter/grid-model.ts` | Pure view-model (no DOM, no network): cell keys, drill-down mode suggestion, render rows, layer colours, storey `floor` indices, cell names, placed areas, compile estimates, palette grouping/filtering |
| `worldpainter/editor.ts` | Overlay controller, `WpState`, scope selection and drill-down, mutation POSTs (re-renders from server responses so the editor holds no divergent manifest copy) |
| `worldpainter/editor-canvas.ts` | Konva 5-layer (`ref`, `bg`, `paint`, `decor`, `select`) rendering passes, grid lines, vision decor, paint stroke accumulation |
| `worldpainter/editor-handles.ts` | Interactive frame boundary, corner resize, and reference image handles |
| `worldpainter/editor-palette.ts` | Floating tile palette dock, category rail, search filter, tile detail panel |
| `worldpainter/editor-dialogs.ts` | Modal and popover dialogs for grid dimensions, heightmap import/export, scope generation |

## Report a bug (the Report dialog)

**What it does.** Turns whatever you are looking at *right now* into a real dev-task file -
`docs/virtualWorld/dev_tasks/todo/<area>/bug-N-<slug>.md` - with the evidence attached, so the
next reader does not have to go and reproduce it. It writes a file; it does not send anything
off-machine.

**How to use it.** Click **Report** in the graph toolbar's *Look* zone, next to **PNG**
(`templates/index.html`, `btn-report-bug`). Then:

1. **Area** - which dev-task folder the report lands in (`bugs` by default; the 13 areas are the
   same list `tools/tasks.py` uses).
2. **Short title** - optional. Left blank, the first line of the message becomes the title, which
   is also what the filename slug is made from.
3. **What went wrong, and what did you expect instead?** - the only required field. It becomes the
   task's **Goal** verbatim.
4. **Screenshot** - any of three ways, all ending up as the same single `screenshot` field:
   - **Capture view** composites the graph `<canvas>` with the map background, exactly as the
     PNG export does. Good for "the layout is wrong". It does **not** capture the DOM chrome
     around it, and it cannot capture a graph node - those are drawn, not DOM.
   - **Attach image**, or just **paste with `Ctrl+V` while the dialog is open**. This is the only
     way to get the whole window, panels and modals included, because no DOM rasteriser is vendored
     anywhere in this repo (no html2canvas, no `toDataURL` outside tests).
   - **Clear** removes the current image. Limit: 8 MB; `png`, `jpg`, `jpeg`, `webp`, `gif`.
5. **Pick an element** - for "the inspector looked wrong", which on its own is not a report. The
   dialog hides itself so it cannot swallow the click you are trying to make; a dashed cyan box
   follows the cursor; click to record that element, or **Esc** to cancel. Each pick stores the CSS
   selector path, box geometry, ancestor chain, ~17 computed properties, visible text and truncated
   `outerHTML`. Up to 12 per report; picking the same element twice is rejected, and each row has a
   **x**. **The picker is DOM-only** - `document.elementFromPoint` over the graph container resolves
   to the container, never a node, because vis.js draws to a canvas. For a graph node, select it
   first: the capture already records the selected node ids.
6. **File bug** - the dialog closes and a toast names the file it wrote.

**Context is captured for you.** You do not have to write down what mode you were in: the report
records the timestamp, URL, viewport, device pixel ratio, user agent, layout mode, physics state,
view mode, camera scale and position, selected nodes, and map spacing.

**What lands where.** The task file's frontmatter matches `tools/tasks.py new` (`type: bug`,
`status: todo`, chosen `area`, `priority: medium`), the message is the **Goal**, **Acceptance** is
`- TODO` for the fixer to fill in, and an **Evidence** section holds the screenshot, the context
JSON and one block per picked element. The screenshot PNG is saved under
`static/images/bug-reports/` - *not* beside the task file, because `routes/docs_ops.py` refuses to
serve anything under `dev_tasks`, so an image next to the task could not be rendered by the docs
reader. Ids come from `tools/tasks.py`, and the file is created with an exclusive `open('x')` so two
reports filed in the same instant retry instead of overwriting each other.

**Where it is wired:** `static/js/bug-report.ts` (dialog, picker, multipart POST),
`routes/bug_reports.py` + `routes/bug_reports_ops.py` (the handler), `templates/index.html`
(modal markup and the toolbar button). Covered by `tests/test_bug_reports.py` (11 tests, passing).

## File-size rule

`AGENTS.md` enforces production files < 600 lines and prioritizes extracting concerns into
modules over appending to a monolith. Follow the "move, don't copy" extraction pattern: keep the
old public symbol as a thin `@deprecated` delegate, add the new module's script tag, compile with
`npm run build:ts` / check with `npx tsc --noEmit`, and verify with `node --check` (emitted JS) /
`pytest` (Python) after each move.

## Related

- [[Settings & Configuration]] - settings modal + browser-side config
- [[Inspector Panels]] - inspector views (lit-html consumers)
- [[Engine Config]] - schema-driven lit-html editor (backend constants)

## Where it lives

- `static/js/vendor/lit-html/` (vendored lit-html, no CDN)
- `static/js/shared/lit-bootstrap.ts` (deferred ES module, stamps `window.Lit` API)
- `static/js/shared/template-sync.ts` (`InspectorTemplateSync` library template footer + sync)
- `static/js/shared/diff-modal.ts` (`DiffModal` V3 Hybrid Merge Workbench)
- `static/js/main.ts` (classic script, polls for `window.Lit` before `init()`)
- `static/js/event-stream.ts`, `static/js/stream/stream-persistence.ts` (`EventBus` v2 + IndexedDB restore guard)
- `static/js/agent/human-turn-composer.ts` (`HumanTurnComposerModule` v4 continuous turn panel)
- `static/js/graph/projector.ts` (pure visibility projection)
- `static/js/graph/overlays.ts` (5 ambient overlays: light/heat/sound/trigger/cardinal, change-cached lighting)
- `static/js/graph/tooltips.ts` (node/edge tippy tooltips)
- `static/js/graph/focus.ts` (search reveal, camera fit, bounded physics kick)
- `static/js/graph/layout-engine.ts`, `static/js/graph/node-badges.ts`, `static/js/graph/toolbar.ts`, `static/js/graph/separation.ts`
- `static/js/graph/network-manager.ts` (shell + thin `@deprecated` delegates)
- `static/js/inspector/panel.ts` (`InspectorPanel` single render entrypoint)
- `static/js/inspector/inspector-view-base.ts` (`InspectorView` base class)
- `static/js/inspector/agent-view.ts`, `mind-view.ts`, `persona-view.ts`, `way-view.ts`, `area-view.ts`, `item-view.ts` (entity & character inspector views)
- `static/js/worldpainter/grid-model.ts`, `editor.ts`, `editor-canvas.ts`, `editor-handles.ts`, `editor-palette.ts`, `editor-dialogs.ts` (WorldPainter overlay)
- `static/js/bug-report.ts` (dialog, picker, multipart POST)
- `routes/bug_reports.py`, `routes/bug_reports_ops.py` (bug report handler)
- `templates/index.html` (script load order, modal markup, toolbar buttons)
- `static/js/ui/engine-config-view.ts` (lazy-loaded Engine Config tab)
- `tools/unit/test_graph_toolbar.js`, `tools/unit/test_graph_tuning.js` (parity/apply-path tests)

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply`  -  relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features**  -  [[command-palette|Command palette]] (#60), [[help-centre|Help centre]] (#61), [[agent-overview|Agent overview]] (#69), [[action-menu|Action menu]] (#70), [[report-a-bug|Report a bug]] (#76)

**Dev tasks**  -  [[dev_tasks/done/ui/task-405-llm-raw-request-response-inspector|task]], [[dev_tasks/done/ui/task-544-soak-lab-space-time-view-swimlanes-by-area-with-condition-ribbons|task]], [[dev_tasks/review/ui/task-384-per-edit-undo-feed|task]], [[dev_tasks/review/ui/task-592-one-hierarchy-scopes-at-the-top-of-the-outline-tab|task]], [[dev_tasks/review/ui/task-612-person-context-menu-is-orphaned-when-the-turn-modal-closes-leaving-a-stale-full-page-scrim|task]], [[dev_tasks/review/ui/task-655-equipment-readout-renders-weapon-damage-as-1dd-8-doubled-d|task]] … +19 more

**Neighbouring notes**  -  [[Code Search & Graph]], [[Engine Config]], [[Event Log Export]], [[Event Stream]], [[Inspector Panels]], [[NL Editor]]

<!-- connected:end -->
