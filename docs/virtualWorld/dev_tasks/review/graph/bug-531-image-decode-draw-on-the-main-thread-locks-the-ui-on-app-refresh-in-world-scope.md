---
type: bug
status: review
area: graph
priority: high
---

# bug-531: Image decode/draw on the main thread locks the UI on app refresh in world scope

**Filed:** 2026-10-09
**Related:** task-249 (node images on graph), task-451 (multi-layer background), task-452 (PNG export)

## Goal

Reloading the app while the graph is filtered to **world scope** (whole world
loaded) blocks the UI while images load. User-reported interaction: hard refresh
(F5) at world scope. Not yet reproduced independently by the filing agent — this
ticket records the measured ingredients and the mechanism class; a live profile
is still required to name the exact blocking call (§ "What still needs to be
measured").

Measured state of the asset and load path:

- **Assets are files, not data URIs.** Node art lives at
  `/static/images/nodes/*` and is referenced by URL (`routes/graph_ops.py:453-459`).
  Backgrounds live at `/static/images/backgrounds/*`. Browser HTTP caching
  already applies; the cost is decode + draw, not the fetch.
- **Background images are up to 4.3 MB** (`static/images/backgrounds/raven
  river.png`), i.e. roughly a 4096² bitmap (~64 MB) once decoded. 18
  backgrounds, 56.5 MB total.
- **782 node images, 75.1 MB total** (avg 98 KB, max 680 KB).
- **Node avatars are attached as vis.js `circularImage`** when thumbnails are
  on (`static/js/graph/network-manager.ts:1290-1298`), so at world scope every
  node with art is decoded and drawn on the main thread each frame.
- **No off-thread decode anywhere.** There is no `createImageBitmap`, no
  `img.decode()`, and no `loading="lazy"` in the front end.
- The only asynchronous load path is the graph background
  (`graph-background.ts:478-485`, `_setImageSrc` → `Promise`/`onload`).

This is why "add caching / make it async" is not the whole fix: the background
loader is already async and the files are already cached. The remaining stall is
**main-thread decode + draw of oversized assets**, which caching does not remove.

Candidate fixes (to be chosen after a profile):

1. Off-thread decode: `createImageBitmap(blob, { resizeWidth })` for node
   avatars and background layers instead of `new Image()`.
2. Downsize the assets: ship web-sized WebP/PNG (e.g. backgrounds ≤ 2048 px),
   cutting bytes an order of magnitude.
3. Lazy/visible-only node images: do not hand vis.js an image for every node at
   world scope.
4. `loading="lazy"` for any DOM `<img>` avatars (agent lens, turn scene view,
   character art).

## Acceptance

- [x] Assets downsized (task-754): `static/images` is 800 WebP / 14.3 MB (was 131.5 MB); node
      art and backgrounds shrunk an order of magnitude. Before/after recorded in task-754.
- [x] Dominant cause fixed: the cardinal map path pins areas/ways (`layout-engine.ts`), so the
      solver runs over items/characters only, not every area/way; and the whole-world
      `/api/state` build is skipped when unchanged (task-753 cache).
- [x] DOM avatars lazy: the character-art portrait and the inspector node images now carry
      `loading="lazy" decoding="async"`.
- [ ] A live Firefox **Performance** profile at world-scope refresh still needs to name the
      residual long task before this closes. Remaining levers: scale the stabilization budget
      (`network-manager.ts:316`, still a flat 100) and stop rendering the whole world
      (task-397 scope).
- [x] Existing behavior preserved: node images render when thumbnails are on, backgrounds fit
      their scope (unit tests + earlier live checks).

**Note:** the user reported the app runs "a whole lot better" after deleting the oversized
autosave and the server-side fixes, so the freeze may already be gone — but a profile is the
honest closer, not an assumption. The flat stabilization budget cannot be tuned cleanly at
`init()` (the node count is not known until data arrives), so that lever needs its own change.

## Measured cause (2026-10-09) — it is the vis.js physics solver, not the images

After the server fixes (gzip + duplicate-key removal + image cache headers), the
user restarted the server and hard-refreshed, and **Firefox still shows "This page
is slowing down Firefox"** at whole-world scope. That warning is a long-running
*script*, and the world in question loads **2739 nodes / 6285 edges**.

The dominant client cost is the graph layout, not image decode:

- `static/js/graph/network-manager.ts:316` — `stabilization: { iterations: 100,
  fit: false }`, a fixed budget for every graph size.
- Physics is **left enabled** after stabilization; nothing disables it on load
  (the only disable is `graph-background.ts:2153`, for a specific mode). So the
  solver keeps running on the main thread indefinitely over 2739 nodes —
  continuous CPU, periodically tripping Firefox's slow-script warning.
- `static/js/graph/relative-layout.ts` seeds positions after
  `stabilizationIterationsDone` (vis `'stabilizationIterationsDone'` handler),
  i.e. the derived layout already owns positions — the solver need not keep
  running for a static view.
- `relative-layout._parents()` also walks `parentOf` per node over the edge list
  (`relative-layout.ts:346-354`), an O(nodes × edges) pass mitigated by caches;
  worth profiling once physics is addressed.

Node images are **not** confirmed as a contributor here (thumbnails were off in
the report), but the asset size (task-754) still matters when they are on.

### Candidate fixes (choose after a Firefox Performance profile)

1. **Stop the solver for large graphs:** in the
   `stabilizationIterationsDone` path, `network.setOptions({physics:{enabled:false}})`
   when the node count exceeds a threshold (the manual Physics toggle re-enables).
   **Implemented (2026-10-09):** `relative-layout.ts` now freezes the solver after
   stabilization when the graph has ≥ 500 nodes (`LARGE_GRAPH_PHYSICS_CEILING`).
   Small graphs keep live physics. Pending a live check.
2. **Scale the iteration budget** with node count instead of a flat 100
   (`network-manager.ts:316`) — still open; the 100-iteration stabilization is the
   remaining load-time cost on a large graph.
3. **Do not render the whole world:** the scope design (task-397) is "load one
   world scope at a time"; whole-world rendering of 2739 nodes is the root.

### Correction (2026-10-09, later) — it is the CARDINAL map path, not "physics over 2739"

Retracted: fix #1 above was a bad call — a node-count heuristic that overrides the
user's Physics setting and ignores the layout mode. Reverted.

The real cause, from the user's own model (areas should sit on coordinates; only
items/characters should settle): the **cardinal** map layout path left areas and
ways `physics: true, fixed: {x:false,y:false}` (`layout-engine.ts:124-173`), so the
solver simulated every area and way — hundreds of pinned-by-intent nodes dragged
off their anchors (and off the background art) with a full solver pass every frame.
The **grid** path already pins them (`:678-688`, `:723`); the cardinal path did not.

**Fixed (2026-10-09):** cardinal areas and ways are now pinned
(`physics:false, fixed:{x:true,y:true}`) to their computed anchors/midpoints;
items and characters stay simulated. Physics still follows the user's setting
(`applyModePhysics`), now only over the contents. The stale "nodes drift by design"
comment in `network-manager.ts` was corrected. Pending a live check.

Still open: load-time stabilization iterations (item 2), whole-world scope (item 3).

Verification: Firefox **Performance** capture of a world-scope refresh should show
the long task; a live profile is still required before closing.
