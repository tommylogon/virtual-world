---
group: UI
---

# Trigger/Behavior Graph Editor Overhaul: Pan, Zoom, Wire Clarity, Editing Power

**Filed**: 2026-09-02
**Priority**: High
**Status**: **Phase 1 implemented & tested** (2026-09-02) — Option A chosen; viewport rework live
in `trigger-graph.js`, verified by `tools/test_trigger_graph_viewport.cjs` (19/19 PASS).
**Predecessor**: [[task-351-trigger-graph-editor]] built the editor itself (in progress — its
Phase 2 blueprint browser and Phase 3 engine-side runtime compile are still open; this doc's
compile-honesty findings in defects #9–#11 feed directly into that Phase 3).

---

## Summary

`static/js/shared/trigger-graph.js` (the 🧠 Behavior Graph / 🔀 Trigger Graph modal) is a hand-rolled
node editor: absolutely-positioned `<div>` nodes + one SVG layer for wires. It has **no pan and no
zoom** (the Fit button is the only viewport control, and it corrupts the coordinate model), **wires
cannot be deleted or told apart** (all render as identical blue, including YES vs NO branches), and
several compile paths **silently drop user-wired data** on save. This doc is the research: current
state, defect list with line references, three enhancement options, a recommendation, and a phased plan.

## Current State

- Single IIFE `window.TriggerGraph`, ~1,520 lines, no build step (script tag in `templates/index.html:991`).
- Nodes are DOM `<div class="tg-node">` with live form fields inside (lit-html templates per node type
  in `NODE_DEFS`). Wires are cubic beziers in `#tg-svg`, positioned via `getBoundingClientRect()` math.
- Two modes sharing one editor:
  - `trigger` (⚡ Trigger → ❓ Condition → ⚡ Effect), compiled by `TG.compileToEngine`, with
    server-side Test/Validate (`/api/triggers/test`, `/api/triggers/validate-definition`).
  - `behavior` (🧠 Behavior → ❓ Condition → 🛠 Action / 🎭 State), compiled by
    `TG.compileToBehaviors`; **priority is derived from node Y position** on save, not from the
    Priority field shown in the node.
- Callers: `trigger-editor.js` ("🧩 Graph" button hands off / back), `behaviors-view.js`
  `openGraphEditor()` (all behaviors of a character at once).
- Graph format `{nodes:[{id,type,x,y,w,props}], wires:[{id,from:[node,socket],to:[node,socket]}]}`
  is persisted in blueprint library + character behaviors. It is fine and worth keeping.

## Defects Found (research audit)

### A. Viewport (the user-facing blockers)

1. **No pan.** Only `⊞ Fit` sets one CSS transform on `#tg-canvas` (`_fitView`, line ~800). Empty-canvas
   drag just deselects (`_onCanvasMouseDown`). No way to move the view.
2. **No zoom.** No wheel handler anywhere. Fit computes a scale the user cannot control or change.
3. **No grid/background.** Plain dark canvas — with no visual anchor, panning/zooming (once added)
   would feel floaty; today it just makes large graphs unreadable.
4. **Coordinate model breaks under any non-identity transform.** Fit is not just missing features —
   it actively corrupts interactions:
   - Node drag uses raw screen deltas (`n.x = sx + e.clientX - mx`, line ~1004) without dividing by
     scale → at Fit scale 0.6, nodes move 40% slower than the cursor.
   - `_getSocketCenter` returns *post-transform visual* coords, but SVG path coords are interpreted in
     *pre-transform canvas-space* and get the canvas transform applied again → any wire redrawn after
     Fit (node move, resize) detaches from its sockets. Fit looks right only until you touch anything.
   - Right-click node creation uses `clientX - rect.left` without inverse transform → new nodes spawn
     far from the cursor at zoom ≠ 1.
   - Root cause: screen space and world space are conflated. There is no `screenToWorld()`.

### B. Wires (clarity + the biggest functional gap)

5. **Wires cannot be deleted.** `Del` only deletes the selected node (`_onKeyDown`); the SVG layer has
   `pointer-events:none` and paths have no handlers; the context menu only opens on bare canvas.
   A single mis-wire forces deleting whole nodes.
6. **All wires are identical blue `#58a6ff`.** Condition nodes expose green ✓ / red ✗ sockets, but
   wires from both render the same — in the screenshot you cannot tell which branch a wire leaves.
   No arrowheads either; direction is guesswork on long wires.
7. **No cycle prevention.** `_onCanvasMouseUp` accepts any side-differing socket pair; the recursive
   tracers (`_traceGraph`, `_traceBehavior`) would infinitely recurse on save → stack overflow.
8. **Duplicate/reversed wires accepted.** Wiring input→output stores the reversed direction which the
   tracers then silently ignore; double-wiring the same pair creates two identical wires.

### C. Silent data loss on save (compile honesty)

9. **Fan-out is dropped.** `_traceGraph`/`_traceBehavior` follow only the *first* wire from an output
   (`wires.find(...)`). If a user wires one output to two actions, the second branch vanishes on save
   with no warning.
10. **Behavior-mode NO branches are discarded.** `_traceBehavior` explicitly ignores NO-branch actions
    (comment ~line 1317: "we don't fold NO actions into the YES path") — the editor happily renders
    and saves graphs that compile to less than they show. Trigger mode keeps only a NO-branch
    `message` as `fail_message`; all other NO effects are dropped.
11. **Behavior priority: UI lies.** The node shows an editable Priority field, but
    `compileToBehaviors` overwrites priority from sorted Y position (`count - rank`). Moving a behavior
    node vertically silently changes gameplay order; typing a priority does nothing.

### D. Interaction/rendering quality

12. **Full DOM rebuild on every click.** Node mousedown calls `_rerenderCanvas()` → all node DOM is
    destroyed and recreated (focus loss, flicker, O(n) per interaction). Selection should be a class
    toggle, not a rebuild.
13. **Field values commit on `onchange` only** — the model can be stale when Test/Validate/Save runs
    right after typing without blurring in the "right" order; combined with #12's rebuild-on-click
    this is race-prone.
14. **Escape closes the editor with no unsaved-changes guard** (`_onKeyDown` → `_close()`). Work lost.
15. **Missing editor power tools:** no multi-select / box-select, no copy/paste/duplicate, no
    undo/redo, no node collapse (`_expanded` is stored but never used), no snap-to-grid or alignment,
    no minimap, no canvas-wide node search (only the add-node menu has search), 16px socket targets,
    no touch support, no keyboard nudge, `prompt()`/`alert()`/`confirm()` for blueprint names.
16. Minor: `_collectBehaviorStates` builds a throwaway `entry` with a placeholder priority (dead code);
    node width fixed at 260px with no text overflow strategy.

## Options Considered

### Option A — Incremental overhaul of trigger-graph.js  ✅ Recommended

Keep the DOM-nodes + SVG architecture, node schemas, and compile pipeline. Add a real viewport layer
and wire interaction model.

- **Viewport**: one `#tg-world` container (nodes + svg inside) transformed by `{panX, panY, zoom}`;
  canvas stays untransformed. All pointer math goes through `screenToWorld()/worldToScreen()`.
  Wheel = zoom-to-cursor (0.25–2.0), empty-canvas or middle/space drag = pan, Fit = F, +/- buttons,
  zoom % indicator, dot-grid background sized by zoom, per-graph saved viewport.
- **Wires**: color per source socket (✓ green / ✗ red / gold trigger-behavior / blue action), arrowhead
  markers, invisible fat hit-path per wire → hover highlight, click-select, Del/right-click to delete.
  Reject cycles + duplicates at creation time with a toast.
- **Honesty**: badge or gutter warning on wires/branches that will not compile (fan-out beyond first
  wire, behavior NO-branch actions, reversed wires). Either warn or make the engine support them —
  but stop saving less than what is shown.
- **Rendering**: incremental updates (selection = class toggle; pan/zoom = one transform update;
  only wires recompute on node drag). Commit field values on `input` (debounced) instead of `change`.
- **Guard rails**: unsaved-changes guard on Esc/close, `localStorage` draft autosave, replace
  `prompt/alert/confirm` with the app's modal/toast helpers.
- **Layout**: keep authored positions, add a "✨ Tidy" button (simple layered column layout per
  behavior chain), snap-to-grid, align-selected.

Effort: ~700–1,000 lines changed/added, zero new dependencies, blueprint format untouched.
Risk: low-medium; the compile/trace code is only touched to add warnings, not to change semantics.

### Option B — Adopt a graph library

**vis-network** (already loaded for the world map) was evaluated first since it ships pan/zoom,
clickable edges, and a hierarchical LR layout for free — but it is a graph *viewer*, not a
blueprint *editor*: no port/socket model (edges bind node-to-node, so YES/NO branch attachment
points are lost unless socket nodes are faked and kept in sync during drags), no drag-to-connect
gesture (edge creation is data-driven only), and nodes are canvas-painted so the inline form
fields — a deliberate task-351 Phase 1 goal — cannot live inside nodes. Using DOM overlays glued
via `canvasToDOM` rebuilds the current architecture on top of vis with two systems to keep in
sync. A vis-based redesign is only attractive if the product moves to compact summary nodes +
a details panel (Unreal-style), giving up inline editing.

Other candidates:

- **Drawflow** — DOM-based like ours, HTML content inside nodes (fits the field-heavy nodes), built-in
  pan/zoom/wire deletion. Downside: effectively unmaintained; we'd still keep all compile code; styling
  to match the app is work; LGPL-ish MIT fine.
- **Rete.js v2** — excellent architecture (area plugin = pan/zoom/minimap, undo plugin, rearrange
  plugin), renderer-agnostic in theory. Downside: CDN/ESM-only integration in a no-build globals
  codebase is awkward (needs Vue render plugin for stock rendering); steepest learning curve.
- **LiteGraph.js** — the ComfyUI engine; canvas-rendered, insanely feature-complete (subgraphs, minimap,
  multi-select). Downside: canvas nodes make our rich HTML forms (datalists, periodic-drain grids,
  textareas) a fight; visual restyle is hard.
- React Flow / Baklava / JointJS / GoJS — wrong framework or license/commercial constraints.

Verdict: every option still requires keeping `compileToEngine`/`compileToBehaviors` and re-implementing
the field forms in the library's node format. We'd pay migration cost + dependency risk to get a
subset of Option A's list. Not worth it unless the editor grows subgraphs/macros.

### Option C — Full custom canvas engine (PIXI/LiteGraph-style)

Overkill for graphs of this size (dozens of nodes, not thousands). DOM nodes give us forms, datalists,
and Bootstrap styling for free. Rejected.

## Phased Plan (Option A)

### Phase 1 — Viewport: pan, zoom, fit, grid (the big visible win)
- Viewport state `{x, y, k}` + single transform container; `screenToWorld` used by every handler
  (fixes node-drag speed, wire geometry, and context-menu spawn positions in one sweep).
- Wheel zoom-to-cursor, drag/Middle/space pan, Fit (recompute + recenter), zoom controls + % badge,
  dot-grid background, persist viewport per graph in `localStorage`.
- Acceptance: after Fit, dragging a node keeps wires attached and tracks the cursor 1:1; new nodes
  appear under the mouse; smooth at 60fps with ~100 nodes.

### Phase 2 — Wires: clarity, deletion, safety
- Per-source-socket colors + arrowheads + animated dash on hover; fat invisible hit paths.
- Wire selection, Del deletion, right-click wire menu (delete); cycle & duplicate rejection with toast.
- Compile-honesty warnings (fan-out drop, behavior NO-branch drop, reversed wire) as badges in-canvas
  plus entries in the existing test/validate panel.
- Acceptance: every wire visible on screen can be identified by color and deleted without deleting nodes.

### Phase 3 — Editing power
- Undo/redo (serialize snapshot stack — cheap because the graph is already plain JSON).
- Multi-select (shift-click, box-select), group-drag, copy/paste/duplicate (Ctrl+C/V/D).
- Node collapse (`_expanded` finally used → header-only summary card), canvas node search (Ctrl+F),
  snap-to-grid + align, keyboard nudge (arrows), unsaved-changes guard, draft autosave.
- Field commits on debounced `input`; kill rebuild-on-click (class-toggle selection).
- Replace `prompt/alert/confirm` with app modals/toasts.

### Phase 4 — Scale & polish
- Minimap (bottom-right, click-to-jump), zoom-based LOD (collapse fields to summary line below ~0.6
  zoom, ComfyUI-style), render only nodes intersecting the viewport.
- Touch gestures (pinch zoom), node width auto-fit, state panel polish.

### Phase 5 — Behavior-mode UX (design decision needed)
- Replace priority-from-Y with an explicit, visible mechanism (drag-reorder lane or rank badges +
  authoritative Priority field), since silent Y-position priority is a gameplay footgun (#11).
- Consider a "Tidy" auto-layout per behavior chain (columns: behavior → conditions → actions).

## References

- Editor: `static/js/shared/trigger-graph.js`
- Form editor hand-off: `static/js/shared/trigger-editor.js:573-600`
- Behavior entry: `static/js/inspector/behaviors-view.js:1410-1427`
- Engine semantics: `engine/triggers/behaviors.py` (NO-branch/fan-out limits are engine model, not editor)
- World-map graph (separate system, vis-network, already has pan/zoom): `static/js/graph-manager.js`

---

# Part 2 — Form Editors, Interop, Saving, Testing (research round 2)

Scope added after round 1: the form editors, form↔graph conversion, saving flows, test
animation, dialogs, and socket direction conventions.

## The four catalogs (the structural problem)

The engine's trigger/behavior vocabulary exists in **four drifting copies**:

| Catalog | Triggers | Conditions | Effects | Behavior actions | Source |
|---|---|---|---|---|---|
| Engine | 33 | 27 + 11 behavior | 42 + 5 | ~100 | `constants.py`, `engine/triggers/behaviors.py` |
| `TriggerTypes` registry (form editor dropdowns) | 33 | 20 | 41 | — | `static/js/shared/trigger-types.js` |
| Trigger form editor | ← registry | nested AND/OR/NOT tree UI | ← registry + save-gate branches + snippets | — | `static/js/shared/trigger-editor.js` |
| Graph editor (`NODE_DEFS`) | **17** | **20** | **24** | **11** | hardcoded in `trigger-graph.js` |
| Behavior form editor | — | 12 behavior | — | **~100** | `static/js/inspector/behaviors-view.js` |

The graph editor is the *least* capable of the four, yet it writes the same saved data.
The cheat sheet (`docs/Trigger-Condition-Effect-Cheat-Sheet.md`) is the authoritative catalog.

### New defects (continuing round-1 numbering)

17. **Behavior graph save is destructive for ~89% of actions.** `behaviorsToGraph` maps *every*
    action to an `action` node, but `NODE_DEFS.action` knows only 11 types and
    `_buildActionFromNode` re-emits only recognized params — saving from the graph editor strips
    all params of any of the other ~89 action types (e.g. `kiss` → `{type:'kiss'}`, losing
    target/where/intensity). Worse, the Type dropdown shows "message" for unknown types (no
    matching `<option>`), so they're mislabeled on screen too.
18. **Behavior-only conditions don't round-trip.** `npc_emotion_is`, `npc_is_hidden`,
    `character_has_tag` etc. exist in the behavior form editor but not in the graph's condition
    fields; `_conditionToGraphProps`/`_buildConditionFromNode` keep only generic keys — `emotion`
    and friends are lost on graph save.
19. **Form→graph conversion is lossy by design.** `triggerToGraph` keeps only `conditions[0]`
    (drops the rest of the tree), only `trigger_type[0]` (multi-type triggers lose the rest),
    cannot express OR/NOT groups (graph conditions chain = AND only), and the `save` effect's
    `on_success`/`on_fail` branches have no node representation. Opening a rich form trigger in
    the graph and applying destroys structure with no warning.
20. **Blueprints are under-specified.** Saved blueprints store `{name, description, graph}` only:
    no mode marker (a behavior blueprint loads into the trigger editor as garbage and vice
    versa), no form-level name/success_message/fail_message, silent overwrite when the id
    collides, no tags/search, and the load picker is a raw floating div.
21. **No visual execution trace on Test.** `/api/triggers/test` already returns per-condition
    `passed` flags and ordered `outputs` — everything needed to animate the graph — but both
    editors render it as a flat text panel. The graph doesn't even scroll to / highlight the
    nodes that fired.
22. **Native `prompt()`/`alert()`/`confirm()`** for blueprint save/load, apply-anyway, and
    close-without-save across `trigger-graph.js` (the app has modal + toast patterns to reuse,
    e.g. `shared/diff-modal.js`, `toastInfo`).
23. **Condition YES/NO sockets both exit the bottom** (45%/55% positions) — wires leave
    downward then hook around, producing the awkward S-curves visible in practice; violates
    left-in/right-out dataflow convention; 16px dots are small targets; ✓/✗ labels only exist
    as `title` tooltips.
24. **Both editors write the same data with no interlock.** Behavior form modal and graph
    editor both end in `ApiClient.updateCharacter({behaviors})` — last writer wins, no
    dirty-checking, no diff preview (the diff-modal exists but isn't used here).

### What's good (keep)

- Trigger form editor is genuinely strong: nested condition tree with ALL/ANY groups, grouped
  effect registry with icons, snippet recipes (task-380), SearchSelect/TagMultiselect pickers
  with library + world data, live dry-run test with fireability hints.
- `TriggerTypes` was built (per its header) to be the single source of truth — the graph editor
  just never adopted it.

### Recommendations

- **One registry to rule them all:** extend `shared/trigger-types.js` into a full catalog —
  every trigger/condition/effect/action with its param schema (label, input type, datalist,
  default, applies-to mode). Generate: form editor rows, graph `NODE_DEFS` fields, behavior
  form cards, and the validate dropdowns from it. New engine types then appear everywhere at
  once. This is the prerequisite for defect #17/#18 to even stay fixed.
- **Conversion honesty:** `triggerToGraph`/`behaviorsToGraph` must round-trip or refuse —
  when a trigger/behavior contains anything the graph can't represent (OR groups, extra
  trigger types, unknown actions), show a modal listing what will be lost with
  "Edit in form instead" / "Convert anyway" options. Never silently degrade.
- **Graph→form is the safe direction** (graph ⊂ form). "📝 Form" button should work in
  behavior mode too (currently bridge is trigger-mode only).
- **Left-in / right-out everywhere:** move condition YES/NO outputs from bottom to the right
  edge (✓ top-right, ✗ bottom-right); input left. Every wire then flows left→right, chains
  read naturally, and layered auto-layout becomes trivial. Bottom edge stays free for future
  (else-branch, subgraph ports). Socket dots: 20px+, visible ✓/✗ labels beside the dot.
- **Test animation:** on Test in the graph, walk the compile trace: pulse the trigger node,
  animate the wire dash downstream (SVG `stroke-dashoffset` transition), light each condition
  node green/red per the API's per-condition results (staggered ~200ms), then flash effect
  nodes in `outputs` order. Pure CSS/JS on the existing DOM; no new deps. The text panel
  stays as the detailed log. Later (bigger): a behavior *simulation* mode reusing the same
  animation against a live or dry-run engine context.
- **Proper dialogs:** blueprint save dialog (name, description, tags, mode badge, overwrite
  warning), load browser (searchable list, mode filter — this is task-351 Phase 2, reuse it),
  unsaved-changes confirm on Esc/close, and apply-with-errors confirm. All in-app modals.

### Revised phased plan (supersedes Part 1 plan)

| Phase | Scope |
|---|---|
| 1 — Viewport | pan/zoom/fit/grid + `screenToWorld` (unchanged from Part 1) |
| 2 — Wires & flow | colored typed wires, deletion, cycle guard, **left-in/right-out socket layout** (#23), compile-honesty badges (#9–#11) |
| 3 — Registry | unify catalogs into `trigger-types.js` param schemas; generate graph node fields + behavior form cards from it; fixes #17/#18 structurally |
| 4 — Interop | lossless-or-warned form↔graph conversion (#19), blueprint mode marker + metadata + proper save/load dialogs (#20, #22), graph→form bridge in behavior mode |
| 5 — Editing power | undo/redo, multi-select, copy/paste, collapse, unsaved guard, autosave (Part 1 Phase 3) |
| 6 — Test animation | execution-trace animation in graph test (#21); later behavior simulation |
| 7 — Scale & polish | minimap, LOD, culling, touch (Part 1 Phase 4); behavior priority UX (Part 1 Phase 5) |

## Implementation Log

### Phase 1 — Viewport (DONE, 2026-09-02)

Architecture: `#tg-canvas` is now an untransformed viewport; a single `#tg-world` child
(nodes + wires SVG) carries the one transform `translate(pan) scale(k)`. All gesture math runs in
world coordinates via `_screenToWorld()`. The wires SVG uses `overflow:visible` so world-space
paths work without a giant SVG box, and wire geometry no longer needs re-rendering on pan/zoom/resize.

- **Pan**: drag empty canvas, middle-mouse anywhere (incl. over nodes), space+drag; grab/grabbing cursors.
- **Zoom**: wheel zoom-to-cursor (0.25×–2.0× clamp, exponential factor so trackpads feel even),
  bottom-left control cluster (− / % badge / + / ⤢ Fit; badge click = reset 100%), keyboard
  `+`/`-`/`F`. Fit and button zooms animate (CSS transition class); gestures stay immediate.
- **Grid**: dot grid drawn on the viewport, position+size synced to the transform each frame.
- **Fixed by the new coordinate model**: node drag now tracks the cursor 1:1 at any zoom (was
  screen-delta at world speed), wires stay glued to sockets after Fit (was: double-transformed),
  context-menu nodes spawn under the cursor at any zoom, and **the add-node-after-search-filter
  bug** (menu re-render passed 0,0 as spawn position) is fixed.
- **Wires** now inherit their source socket's color (YES green, NO red, trigger/behavior gold,
  action blue) — first slice of Phase 2's wire clarity work, effectively free during the rewrite.
- **Selection** is a class toggle (`.tg-sel` via injected stylesheet + `--tg-c`/`--tg-glow` custom
  props) instead of a full canvas DOM rebuild per click — no more focus loss/flicker on select.
- **Drags are document-scoped** while active (fast mouse / release outside the canvas can't strand
  a drag; previously a mouseup outside the canvas stuck the editor in drag state).
- **Viewport persistence**: per-mode `localStorage` key, debounced; restored on open only if it
  still shows part of the graph, otherwise auto-Fit (also auto-Fit after loading a blueprint).
- **Fixed en route — id-collision corruption (pre-existing, defect #25)**: loading a graph never
  seeded `nodeIdCounter`/`wireIdCounter`, so the first node/wire added reused `n0`/`w0` and
  silently *replaced* existing ones. `_seedCounters()` runs on load/blueprint-import and id
  generation now skips taken ids. Also: right-button no longer starts node drags.
- **Compile pipelines verified intact** (`triggerToGraph`→`compileToEngine`,
  `behaviorsToGraph`→`compileToBehaviors` round-trips re-checked after the rewrite). This probe
  re-exposed defect #19's family: `_conditionToGraphProps` drops the `skill` param of
  `skill_check` (form→graph loses DEX/STR etc., silently defaults to Athletics).

**Test**: `tools/test_trigger_graph_viewport.cjs` (Playwright, headless, client-side only — no
backend writes). 19 checks: auto-fit bounds, grid sync, badge, cursor-anchored zoom, 1:1 drag at
zoom, wire glue + color after zoom+drag, three pan modes, pan/world separation, context-menu
spawn-at-cursor after filtering, zoom clamps, Fit, viewport persistence, zero page errors.
Note for future test authoring: the help-center tip cards (`.hc-card`) float above everything and
eat mouse events — dismiss them before interacting.

### Follow-up fixes (2026-09-02, same day)

- **Behavior form editor was broken for ALL behavior edits** — `weighItem is not defined` thrown
  while building any action card (the hold/weigh/inventory/carry field group at
  `behaviors-view.js:690` referenced `weighItem`/`inventoryItem`, which were never declared next
  to their `holdItem`/`carryItem` siblings; the template literal evaluates every `${}` at build
  time, so any edit-behavior click crashed). Both consts added.
- **New regression test**: `tools/test_behavior_action_cards.cjs` — calls
  `buildBehaviorActionCard` for all **119** action types with a kitchen-sink param object and
  fails on any throw. This is the net that would have caught the above.
- **behaviorsToGraph re-layout**: was one tall column (all behaviors at x=50, 180px apart) with
  chains overflowing their slot into the next behavior — the rat's 14 behaviors opened as a
  25%-zoom smear. Now a priority-ordered row-major **grid** (≤3 columns, 920px cells,
  behavior → conditions column → actions column, per-block heights, 150px chain spacing).
  Result on the same 14-behavior set: fit zoom 0.38 (was 0.25), zero overlapping node rects,
  priority round-trip exact (14→1 in order — grid rows share Y and `compileToBehaviors`'s stable
  Y-sort keeps load order for ties). Chain wire semantics unchanged.

- **Scattered/detached wires on open (Phase 1 regression, fixed 2026-09-02)**: wires are
  world-space paths computed against the live viewport, but `_show()` drew them *before*
  applying the saved viewport / auto-fit — every path baked in the previous session's transform
  and was left offset (often far off-content) once the view moved. `_applyBlueprint` had the
  same latent bug (render, then animated Fit). Fix: redraw wires after the viewport settles in
  `_fitView()` and at the end of `_show()`. Regression check #20 added to
  `test_trigger_graph_viewport.cjs`: all wires glued to sockets immediately after reopen,
  no interaction (20/20 PASS).
- **Trigger form editor had no Escape** (2026-09-02): `trigger-editor.js` gained a capture-phase
  Escape handler (works while a field is focused) + backdrop-click cancel, cleaned up in
  `close()` so it can't double-fire against the graph editor's own Escape.
- **Field type-ahead + condition socket layout (2026-09-02, first Phase 2 slice)**:
  - Graph node fields were plain free-text; they now carry `list=` datalists fed from world
    state + libraries (areas, world+library items, character names *and* character library ids,
    traits, tags, vitals, skills, NPC states, node states, env stats, weather, conditions) —
    refreshed every open, library lists loaded async. Still free-form (unknown values keep
    working); full SearchSelect retrofit stays in Phase 3's registry work.
  - Condition ✓/✗ sockets moved from their ambiguous bottom 45%/55% pair to the dataflow split:
    **✓ YES exits the right edge** (upper, flow continues sideways), **✗ NO drops from
    bottom-center** — with visible color-coded labels (`✓ yes` / `✗ no`) so branches read
  without hovering. Socket ids and wire topology unchanged, so saved graphs and the compile
  pipeline are untouched; a side effect of the move is that nonsense same-side connections
  (e.g. behavior output → condition YES) are now rejected by the existing side-differing rule.

### Form↔graph catalog parity + two editor-killing bugs (2026-09-02, later)

Full sweep against the cheat sheets and the trigger form editor's `_collectData`:

- **CRITICAL pre-existing bug: graph field edits never persisted.** Two stacked defects:
  1. Every field's inline handler referenced `TG._onFieldChange` — but `TG` lives only inside the
     module closure, so every `change` event threw "TG is not defined" and the value never reached
     node props. All 141 inline handlers now reference the global `TriggerGraph`.
  2. `_renderNode`'s id substitution `replace(/'NODEID'/g, node.id)` matched *including the
     quotes* and substituted the bare id — `('NODEID')` became `(e2)` — so type-switch re-renders
     threw "e2 is not defined" too. Now replaces with `'/id/'` quoted.
  Net effect of the two: in the original editor, **typing into a node and saving silently
  compiled stale values, and switching a node's type always crashed its re-render.**
- **Trigger node = form parity**: full 33-type catalog pulled from `window.TriggerTypes`
  (same source as the form), **Ctrl+click multi-select** (props store an array, engine accepts
  it), and the `target_state` field for on_state_enter/exit (compiled through).
- **Condition node = catalog parity +**: grouped dropdown (General/Character/Item/Area/NPC) now
  includes `item_relationship`, `vital_above/below`, `temperature_above/below` and the
  behavior-only trio `npc_emotion_is` / `npc_is_hidden` / `character_has_tag`, each with proper
  fields and compile branches (`_buildConditionFromNode` + `_conditionToGraphProps` round-trip).
- **Effect node = full form catalog and beyond**: grouped dropdown with the form's 41-effect
  list. New param blocks: **save gate** (ability/skill + DC + per-branch on_success/on_fail
  editors: none/message/apply_condition(+duration/source/source_type)/damage + advanced JSON,
  compiled to the exact `on_success`/`on_fail` arrays `_buildSaveBranchEffect` produces),
  schedule_trigger, llm_respond (max_words/cooldown/name), scry, consume_item, remove_item,
  rename, unlock_way (way datalist), set/append_description, spawn into/capture, add/remove_tag
  message, environment presets (light/air/noise selects, smell, target_node), memory effects
  (surface/suppress/unblock — the form has these in its dropdown with *no* fields; the graph
  edits them), and spawn_way/set_way_target/set_way_view/spawn_area (also fieldless in the form).
  Key fixes to match `_collectData` exactly: spawn `display_name` (was `name`), damage target
  self/other (was player/self), adjust_vital target, `_normalizeEffectParams` mirrors the form's
  serialization (target_by normalization, boolean coercion for hidden/see_through/param, empty
  strings dropped, symptoms/extra_conditions JSON parsed, `effect_type` stripped).
- Verified: 10-check compile parity probe (save gate structure, multi-type, normalize, key
  parity) + DOM probes (field blocks render, type-switch re-renders, a real change event lands
  in props and survives the save path) + both suites green (20-check viewport, 119-type cards).
