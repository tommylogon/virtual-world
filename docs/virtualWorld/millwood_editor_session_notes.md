# Millwood Editor Session Notes

Log of UI behaviors, workflow friction, stale hints, and compiler/layout bugs encountered while building and laying out the `Millwood` scenario (`http://localhost:4444`) strictly through the browser editor and WorldPainter UI.

---

## 1. Initial State Diagnosis (Why Millwood Looked Broken on Map View)

1. **Zero placed handmade areas in child scopes**: All 18 hand-authored areas in `Millwood` had `properties.cell = null` and `area_placements = {}` across all 10 child scopes. None of them had been placed onto child scope cells with WorldPainter's `Area` (`📍 Area`) tool.
2. **Wrong scope ownership on West Millwood homes**: Five West Millwood areas (`area_maple_street`, `area_jake_porch`, `area_jake_bedroom`, `area_side_yard`, `area_sammy_living_room`) were assigned to `suburbs` (`(1, 1)`) instead of `west_millwood` (`(0, 1)`), leaving `west_millwood` completely empty despite `Millwood_ Autumn Town Map.png` placing Maple Street and Birch Lane in column `0`.
3. **Single stray painted cell on `world` collapsed `Whole world` Map view**: Cell `(3, 2)` on `world` carried a single `sparse_forest` biome cell (`area_world_3_2`). In `static/js/graph/layout-engine.ts` (`lines 541-556`), a single painted cell makes `hasPaintedGrid` evaluate to `true` and sets `frame` to a 2-cell margin around `(3, 2)`. Every unplaced hand-authored area whose legacy `x/y` fell outside that tiny frame returned `null` and collapsed into a single overlapping pile near `(0, 0)` on the `Whole world` Map view.
4. **Placeholder cross-town wormhole ways**: Five ways (`way_lockers_to_porch`, `way_maple_to_strip`, `way_maple_to_cemetery`, `way_strip_to_lakeshore`, `way_strip_to_skate`) connected interior hallways or distant sidewalks directly across multiple districts (for example, `B-Wing Lockers` straight onto `Jake's Front Porch`, and `23rd Street Strip Mall` straight inside `Ashford Manor Foyer`).

---

## 2. WorldPainter & Editor Issues Observed Live

### Issue A: False `orphan-placement` BLOCK in `preflight()` when `sibling_traversal` is enabled
- **Where**: `engine/world_compile.py` (`preflight`, around lines 1468-1476) and WorldPainter toolbar (`static/js/worldpainter/editor.ts:2143-2146`).
- **Observed live**: On `world`, `sibling traversal` is checked (`sibling_traversal: true`), meaning `world` is intentionally an unpainted chunk-placement surface where child scopes stitch directly across their facing borders (`task-775`). However, opening `suburbs` (at `(1, 1)` on `world`) displays a red blocker badge (`2 to fix before Generate`, remaining `1 to fix before Generate` even after painting) and sets the `Generate` button tooltip to:
  `"This scope cannot be compiled yet - 'suburbs' sits on cell (1,1) of 'World', which is not painted, so no gateway will ever connect the two."`
- **Mismatch**: `compile_grid()` does not refuse `orphan-placement` (violating `preflight`'s docstring contract at `world_compile.py:1383` that `BLOCK` must match a `compile_grid` refusal), and when `wg.sibling_traversal_enabled(manifest, scope_id)` is true on a child scope with at least one occupied neighbour on the parent grid, an unpainted parent cell is the intended setup rather than an error.

### Issue B: Unpainted scopes with hand-authored areas report as `"already generated"`
- **Where**: WorldPainter Scope Hub and `what next` checklist (`static/js/worldpainter/editor.ts:1911-1912`).
- **Observed live**: Opening `suburbs` (0 painted cells, 0 generated nodes, 5 unplaced hand-authored areas) shows `scope · materialized · 5 areas` in the Scope Hub and marks the final checklist step green:
  `✓ Generate ... -> already generated - Ungenerate to start over`.
- **Why**: `materialized` checks whether `area_ids` is non-empty rather than whether any compiled (`generated`) nodes exist in the scope, misleading the author into thinking the empty grid was already compiled.

### Issue C: Stale Help Center toast contradicts current `baked` scope compilation rules
- **Where**: WorldPainter Help Center card (`WorldPainter - paint a world, then compile it`).
- **Observed live**: The popup card at bottom-right states:
  `"and a scope made with Make this a scope... is baked and can never be generated - + Add feature... is the one that makes a paintable scope."`
- **Why**: `engine/world_compile.py:1425-1435` explicitly removed the refusal on `baked` scopes so promoted scopes can carry both hand-authored areas and painted cells side by side. The onboarding toast still teaches the retired restriction.

### Issue D: Scope Picker Hub puts tree indentation inside a horizontal flex-wrap row
- **Where**: `static/js/worldpainter/editor.ts:1273, 1304, 1308` (`showChooser` / `_scopeCard`).
- **Observed live**: All scopes (`World` plus its child scopes) render as flat horizontal wrapping cards right above `+ New root scope`. Because `_scopeCard` applies `margin-left: depth * 16px` and leading spaces inside a `display: flex; flex-wrap: wrap` row rather than a vertical tree list, tree depth turns into a `16px` horizontal gap between peer cards instead of visual hierarchy.

### Issue E: `settlement` / `town` checklist assumes medieval walled towns
- **Where**: `static/js/worldpainter/editor.ts:1927-1957` (`_checklistSteps`).
- **Observed live**: Every `mode: town` / `settlement` child scope in `Millwood` instructs the author at Steps 4 and 5:
  `Wall it in. Biome layer, value "wall", along the perimeter.` / `Open the gates. Road layer, values "gate" and "bridge", on the wall line where a road leaves.`
- **Impact**: On a modern suburban chunk using `sibling_traversal`, painting `wall` along the perimeter blocks sibling border traversal and triggers `sibling-dead-end` warnings against adjacent open chunks.

### Issue F: Background controls remain focusable behind WorldPainter modal
- **Where**: WorldPainter overlay (`static/js/worldpainter/editor.ts`).
- **Observed live**: While WorldPainter is open full-screen, 53 controls in the underlying main window retain `offsetParent !== null` and remain reachable to unscoped DOM queries / tab order unless focus is explicitly kept inside the overlay.

### Issue G: Child chunk `map_offset` on `Whole world` Map view defaults to `(0, 0)` for all sibling chunks
- **Where**: `static/js/graph/layout-engine.ts:588-612` (`offsetPxFor` / `scopedGridPosition`) and `engine/world_scopes.py:347`.
- **Observed live**: All child scopes placed on `world` (`(0,1)`, `(1,1)`, `(2,1)`, `(3,1)`, etc.) ship with `map_offset: {x: 0, y: 0}`. Until each child scope is manually offset via Grid Adjust (`map_offset`), `Whole world` Map view stacks every child scope's `(0..4, 0..4)` cells at `(0, 0)` on top of each other instead of defaulting unmoved child chunks to their parent placement cell coordinates (`parent_cell * child_grid_size`).

### Issue H: `#create-modal` ships non-empty static HTML under `Lit.render` append semantics
- **Where**: `templates/index.html:853-859` vs `static/js/ui/create-modal.ts`.
- **Observed live**: Unlike `#alert-list` (`templates/index.html:182-185`, which warns that containers owned by `Lit.render` v1 must stay empty), `#create-modal` ships with a static placeholder `.modal-card` containing `#create-modal-submit` and a `Cancel` button. When `CreateModal.open()` renders, `Lit.render` appends `.modal-backdrop` after the static `.modal-card`, leaving duplicate `#create-modal-submit` IDs in the DOM where the first sits behind `.modal-backdrop` and intercepts unscoped queries. Pressing `Escape` also fails to close `#create-modal`.

### Issue I: `_BOUNDARY_SCAN` 8-neighbour generation clips indoor walls and duplicates bespoke ways
- **Where**: `engine/world_compile.py:136, 2342`.
- **Observed live**: Placing hand-authored indoor rooms onto adjacent grid cells (for example, `Jake's Bedroom` beside `Jake's Front Porch`, or `B-Wing Lockers` beside `Chemistry Lab` and `High School Cafeteria`) causes `Generate` to mint extra open passages across all 8 directions (including diagonals through interior walls and across rooms that already share a hand-authored locked/window/stair way). Authors must inspect every placed indoor cell after `Generate` and click `✕` in `[data-role="wp-seams"]` to record `boundary_override` suppressions.

### Issue J: Outdoor ground biomes carry the `"building"` tag in `data/worldpainter/biomes.json`
- **Where**: `data/worldpainter/biomes.json` (`cemetery`, `football_field`, `formal_garden`, `parking_lot`, `courtyard_quad`) and `engine/biomes.py:324-397`, `engine/world_compile.py:990-1055`.
- **Observed live**: Because `biomes.is_building()` checks `"building" in tags`, painting an outdoor `parking_lot`, `football_field`, or `cemetery` cell forces `MERGE_NEVER`, gives the open lot a 2-storey solid sight-blocking height (`height = 2.0, obscurity = 1.0`), and compiles one-way `"enter the ..."` doors with closed building `refusal_message`s instead of open ground traversal.

### Issue K: Three separate confirmation/creation modal systems with inconsistent contracts
- **Where**: `static/js/ui/create-modal.ts` (`#create-modal .modal-backdrop`), `static/js/shared/dialog.ts` (`.vw-dialog-overlay [data-vw-dialog-primary]`), and `static/js/graph/node-operations.ts:23` (`.modal-overlay #modal-confirm-btn`).
- **Observed live**: Deleting a way from the Inspector opens `.modal-overlay #modal-confirm-btn` (no `Escape` key handler), WorldPainter confirmations open `Dialog.confirm` (`.vw-dialog-overlay`, supports `Enter`/`Escape`), and `+ Build` opens `#create-modal` (no `Escape` key handler).

### Issue L (Fixed Live): WorldPainter Cell Inspector crashed on every right-click / Inspect click
- **Where**: `static/js/worldpainter/editor.ts:4326-4335` (`_cellPanel`) vs `static/js/worldpainter/grid-model.ts:1030-1050` (`cellNeighbours`).
- **Observed live**: Right-clicking any cell (or clicking with `🔍 Inspect`) threw `Uncaught TypeError: Cannot read properties of undefined (reading 'road')` and failed to mount `[data-role="wp-cellpanel"]`.
- **Root cause & fix**: `_cellPanel` iterated all 8 compass directions (`['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']`) and checked `if (n === null) return 'map edge'`, while `GM().cellNeighbours` only populated `{N, E, S, W}`, leaving all 4 diagonal keys `undefined`. Fixed in `grid-model.ts` (populating all 8 neighbours) and `editor.ts` (`if (n == null)`), verified with `68/68` passing tests in `tools/unit/test_worldpainter.js`.

### Issue M (Fixed Live): WorldPainter `softRender()` dropped `_areaBar`, `_gridHud` route controls, and `floor` input
- **Where**: `static/js/worldpainter/editor.ts:893-991, 1727-1738, 1991-1998, 2376-2385` (`task-776` regression).
- **Observed live**:
  1. Clicking `📍 Area` in the left tool rail called `_selectTool('area') -> softRender()`, which never mounted `_areaBar(p)` (`[data-role="wp-area"]`), making it impossible to pick an area to place unless a full `render()` was triggered by another action.
  2. Clicking `🧭 Route` never mounted `_gridHud`'s `✓ Paint route` button.
  3. Switching `[data-role="wp-layer"]` to `floor` called `softRender()`, writing tile label text onto the button instead of swapping `_valueControl()` to the numeric storey `<input>`.
  4. `generate()` updated `state.payload` without calling `render()`.
- **Fix**: Updated `_selectTool`, `layerSel` `change`, and `generate()` in `editor.ts` to call `render()` when mounting/unmounting structural toolbar rows or completing compilation.

### Issue N: First paint stroke on an unpainted scope triggers an unawaited `load(scopeId)` mid-stroke
- **Where**: `static/js/worldpainter/editor.ts:3908-3915` (`_commitStroke`).
- **Observed live**: When painting the first cell of an unpainted scope (clearing the `no-paint` blocker), `_commitStroke` fires `load(p.scope.id)` asynchronously after the slim `/paint` ack, wiping the DOM (`Loading grid...`) and remounting the Konva stage ~150ms later while the user is clicking subsequent cells.

### Issue O: Missing `ApiClient.getEquipSlots` method logs boot error on every page load
- **Where**: `static/js/world-state.ts` (`fetchEquipSlots`, compiled `world-state.js:331`) called from `main.js:888`.
- **Observed live**: Every page load logs `Equip slots fetch failed: TypeError: ApiClient.getEquipSlots is not a function`. Caught by `try/catch`, leaving `_equipSlots` empty on client init.

### Issue P: Opening Cell Inspector shrinks `[data-role="wp-grid"]` vertically without refitting the Konva camera
- **Where**: `static/js/worldpainter/editor.ts:960-976, 1455-1465, 2860-2874`.
- **Observed live**: On a `5x5` scope fitted at `scale = 5.36` (`670px` height), right-clicking row `0` inserts `[data-role="wp-cellpanel"]` (~190px tall) below `[data-role="wp-studio-row"]` inside `state.scrollBox`. Because `[data-role="wp-grid"]` is a flex child (`flex: 1 1 auto; overflow: hidden`), its height shrinks by ~190px while `ResizeObserver` updates `stage.height()` without re-centering or scaling `stage`. Lower rows (`y = 3, 4`, at `~453px..571px`) are immediately clipped below the shrunk canvas edge until the user closes the Cell Inspector or clicks `⤢ Fit`.

### Issue Q (Fixed Client-Side Live): Compiling an `unmade` sibling scope fails on shared `way_seam_*` nodes
- **Where**: `engine/generation.py:194-209` (`apply_patch`) and `static/js/worldpainter/editor.ts:2392` (`generate`).
- **Observed live**: When scope A (`north_millwood`) compiled while neighbour scope B (`west_millwood`) was still `unmade` (`state == "unmade"`) or already had border placements/paint, scope A minted the canonical shared border seam `way_seam_north_millwood_west_millwood_...` (`generated: true`, `generator_id` owned by scope A). When the user then opened `unmade` scope B and clicked `⚙ Generate`, `editor.ts` sent `allow_regenerate: false`. Scope B emitted the same canonical `way_seam_*` ID, and `engine/generation.py:206` threw `ValueError: node id 'way_seam_...' already exists and is not a regenerable generated node`. Worse, `editor.ts:2392` only matched `/already materialized/` to show the `Re-run Generation` confirmation dialog, so clicking `⚙ Generate` on an `unmade` scope failed outright with a red status error and offered no retry path.
- **Live fix**: Updated `editor.ts:2392` to match `/already materialized|not a regenerable generated node/` so WorldPainter offers `Re-run Generation` (`allow_regenerate: true`), allowing `apply_patch` to adopt/update the shared generated seam cleanly. Server-side follow-up: `engine/generation.py:206` should allow idempotent co-ownership of `is_generated(existing)` `way_seam_*` nodes even on first-time (`allow_regenerate=False`) compilation of the second sibling scope.

### Issue R: `BLOCKED_WAY_PERCENT = 12` drops wilderness brambles/rockslides/trenches onto `town` front walks with no UI toggle
- **Where**: `engine/world_compile.py:267-325, 2252-2255, 2373-2375, 2808`.
- **Observed live**: Compiling `west_millwood`, `millwood__public_school`, `commercial_district`, and `lakeshore_drive` (`mode: town` settlement scopes) permanently set `current_state = "blocked"` on 12% of outdoor ways (`bramble`, `trench`, `rockslide`). Worse, when a hand-placed area (whose reserved cell has no painted `biome` or `road`) mints a boundary way to an adjacent road cell (`world_compile.py:2373-2375`), `emit_passage` evaluates `terrain_class(cell_biome(cell) or "")` on the unpainted placed-area cell rather than the road neighbour, classifying suburban front walks as `"open"` wilderness (`bramble` / `trench`). WorldPainter exposes no checkbox or scope-mode rule to disable procedural wilderness hazards in `town` or `interior` scopes, forcing authors to open each blocked street way manually in the Way Inspector after `Generate`.

### Issue S: `drainage_channel` carries `"indoor"` in `data/worldpainter/biomes.json` and is hidden in `town` scopes
- **Where**: `data/worldpainter/biomes.json` (`drainage_channel` `tags: ["indoor", "drainage", "water", ...]`) and `static/js/worldpainter/grid-model.ts` (`paletteForMode`).
- **Observed live**: Searching the WorldPainter biome palette for `drainage_channel` inside a `mode: town` scope (`i44_interchange`, to paint a concrete highway drainage ditch) returns zero tiles because `paletteForMode('town', ...)` drops all non-building `"indoor"` tiles as floor-plan rooms.

### Issue T (Fixed Live): Konva `<canvas>` bleeds outside `[data-role="wp-studio-row"]` and intercepts clicks on Cell Inspector header
- **Where**: `static/js/worldpainter/editor.ts:1455, 4300`.
- **Observed live**: After `Generate`, inspecting a hand-placed indoor area (`west_millwood` `(0,3)`) mounts `[data-role="wp-cellpanel"]` containing 8 neighbour rows plus `[data-role="wp-seams"]` rows (~430px total height). Because `[data-role="wp-studio-row"]` had `flex: 1 1 auto; min-height: 0` with no `overflow: hidden` and no minimum height floor, flexbox compressed `wp-studio-row` below `[data-role="wp-grid"]`'s 238px `<canvas>`, causing `<canvas>` to visually overflow downward over `[data-role="wp-cellpanel"]` and intercept pointer events on its `Close the cell panel` (`✕`) button.
- **Fix**: Added `flex: 1 0 420px; min-height: 420px; overflow: hidden;` to `[data-role="wp-studio-row"]` and `flex-shrink: 0; position: relative; z-index: 2;` to `[data-role="wp-cellpanel"]` so `state.scrollBox` scrolls cleanly instead of crushing the studio canvas onto the inspector.

### Issue U: WorldPainter `load(scopeId)` preserves the previous scope's `[data-role="wp-status"]` message
- **Where**: `static/js/worldpainter/editor.ts` (`load` / `_updateStatusBar`).
- **Observed live**: Navigating from an already-generated scope (`north_millwood`) to another scope (`west_millwood`) keeps `⚙ Generated 6 node(s), 12 edge(s)...` from the prior scope rendered in `[data-role="wp-status"]` until a new action overwrites `state.status`.

### Issue V (Fixed Live): Right-clicking to inspect while `📍 Area` or `🏠 Feature` tool is active also fires left-click `_gridClick` (`Unplace`)
- **Where**: `static/js/worldpainter/editor.ts:4053-4068` (`_wireGrid` `stage.on('click tap', ...)`).
- **Observed live**: The `🔍 Inspect` tool button tooltip promises *"Right-click does the same on any tool"*. However, Konva dispatches `click` for secondary mouse buttons (`e.evt.button === 2`) as well as primary clicks. While `state.tool === 'area'` (or `'feature'`, `'route'`, `'move'`), right-clicking an occupied cell fired `_gridClick(p, cell)` alongside `contextmenu`, popping up the `Dialog.confirm` modal to remove/unplace the area right on top of WorldPainter.
- **Fix**: Guarded `stage.on('click tap', ...)` in `editor.ts:4054` with `if (e && e.evt && typeof e.evt.button === 'number' && e.evt.button !== 0) return;` so secondary clicks only trigger `contextmenu -> inspectCell`.

### Issue W: Placed-area canvas labels scale up 5x on small grids and collide across adjacent cells
- **Where**: `static/js/worldpainter/editor.ts` (`_drawFeatures`).
- **Observed live**: On a `5x5` child scope fitted to the viewport (`scale = 5.36`), placed area labels under each green square marker are drawn in uncompensated stage coordinates without clamping width to `CELL` (`22px`). Adjacent placed rooms (`Jake's Garage`, `Maple Street`, `Zoe's House`; `7-Eleven`, `The Grid Arcade`, `23rd Street Strip Mall`) render giant overlapping text strings across three columns.

### Issue X: Child `settlement` scopes display `mode: world` unless manually cycled
- **Where**: `static/js/worldpainter/editor.ts` (`mode:` button in top toolbar) and scope creation defaults.
- **Observed live**: Opening child `settlement` scopes (`west millwood`, `suburbs`, `millwood public school`, `commercial district`) shows `mode: world` in the top-left toolbar pill unless the author manually clicks `mode:` to cycle `world -> town -> interior`, which also changes which biome tiles appear in the palette (`paletteForMode`).

### Issue Y: Action undo toasts stack over bottom-right `LLM inspector` and `dataset` buttons
- **Where**: Global undo toast stack (`+ world/scopes/.../grid/boundary_override [Undo]`).
- **Observed live**: Suppressing several indoor boundary seams in sequence stacks 5-6 undo toast bars in the bottom-right corner directly behind/over the floating `LLM inspector` and `dataset` buttons.

### Issue Z: GraphBackground `▦ Fit to painted grid` on `Whole world` uses parent `5x3` size instead of composite child-scope lattice
- **Where**: `static/js/graph/graph-background.ts:1992` (`fitToPaintedGrid`).
- **Observed live**: When `world` is a `5x3` parent chunk grid holding thirteen `5x5` child scopes (`map_offset = (WX * 5, WY * 5)`, spanning `25x15` total cells = `20000x12000` canvas units), `fitToPaintedGrid` sizes the town reference image to `5 * 800 x 3 * 800` (`4000x2400`, covering only a single child scope in the top-left corner) instead of the `25x15` composite bounds, requiring manual SE-corner handle resizing in `Edit images` mode.

### Issue AA (Fixed Live): Grid Adjust `map_offset` drag compounds `drag.offset` on every `mousemove` event
- **Where**: `static/js/worldpainter/editor.ts:232, 3317, 3431-3434` (`_gridMouseDown` / `_gridDragTo`).
- **Observed live**: Dragging inside a grid frame in `Grid -> Adjust` mode to set `map_offset` wrote `state.gridDrag.offset = { x: drag.offset.x + (cx - drag.start.x), ... }` on every `mousemove` event while `drag` aliased `state.gridDrag`. Over `N` pointer-move events, a drag of `D` cells compounded to `D * N * (N + 1) / (2 * N)` (`4.5x` across 8 steps, or `30x+` during a 1-second human mouse drag), launching `lakeshore_drive` to `map_offset.x = 7868.9` on retry.
- **Fix**: Recorded `startOffset` on `state.gridDrag` at `mousedown` (`editor.ts:3318`) and computed `drag.startOffset.x + (cx - drag.start.x)` in `_gridDragTo` (`editor.ts:3432-3433`).

### Issue AB: Re-generating a scope leaves orphan `way_seam_*` / `way_gateway_*` ways owned by sibling scopes and orphan `on_eat` `logic_trigger` nodes from spawned items
- **Where**: `engine/generation.py` (`apply_patch`) and `engine/world/spawner.py` (`spawn_resources`).
- **Observed live**:
  1. When `suburbs` re-compiled with `merge same-biome` checked (collapsing `area_suburbs_0_1` and `area_suburbs_0_3` into `area_suburbs_1_0`), two earlier `way_seam_suburbs_west_millwood_*` nodes whose `generated.scope_id` belonged to `west_millwood` stayed behind with dangling `area_to` properties until `west_millwood` re-generated or the ways were deleted via `GraphNodeOps.deleteNode`. Similarly, erasing paint on `world` `(3,2)` left `way_gateway_world_east_millwood_and_woods` owned by the child scope.
  2. Re-generating `lakeshore_lake` and `east_millwood_and_woods` removed their generated `res0` resource items (`Lake` / `Sparse Forest` distributions) without removing the companion `trigger_item_*_res0_*` `logic_trigger` nodes (and notice `spawner.py` also serialized a list literal `['on_eat']` into the trigger ID `trigger_item_lakeshore_lake_area_lakeshore_lake_2_1_res0_['on_eat']_0`).

---

## 3. Completed Millwood World Layout Summary

All mutations to `Millwood` were executed through the live browser UI (`http://localhost:4444`) and WorldPainter:
- **Parent `world` Scope**: `5x3` grid (`sibling_traversal: true`, 0 painted parent cells) with all 13 child scopes placed to match `Millwood_ Autumn Town Map.png` (`(1, 0)` and `(2, 0)` intentionally left empty for the High School Campus Guide inset art).
  - Row `0`: `(0, 0)` `north_millwood` | `(3, 0)` `lakeshore_drive` | `(4, 0)` `lakeshore_lake`
  - Row `1`: `(0, 1)` `west_millwood` | `(1, 1)` `suburbs` | `(2, 1)` `millwood__public_school` (`Millwood High School Campus Guide.png` reference attached) | `(3, 1)` `commercial_district` | `(4, 1)` `i44_interchange`
  - Row `2`: `(0, 2)` `cemetery_west` | `(1, 2)` `cementery_east` (renamed `cemetery east`) | `(2, 2)` `south_millwood` | `(3, 2)` `east_millwood_and_woods` | `(4, 2)` `i44_skate_park`
- **Child Scopes & Handmade Areas**: All 13 child scopes sized `5x5` (`map_offset = (WX * 5, WY * 5)` across the `25x15` town lattice), all 28 hand-authored areas placed onto cells via `📍 Area` (including upper-storey `floor = 1` placements for `Zoe's Bedroom Workshop`, `Chemistry Lab`, and `School Library`), connected by merged named streets, woods, cemetery paths, and lakefront, stitched by 26 `way_seam_*` sibling border ways, with indoor wall-clipping boundary ways suppressed via `[data-role="wp-seams"]`.
