# Task-249: Images on Nodes — Optional Display on Graph

**Status:** In Review — implemented 2026-08-17; static checks + endpoint tests pass, pending browser E2E of the graph toggle/inspector UI.
**Filed:** 2026-08-16 from developer ideas backlog.
**Source:** `dev_tasks/developer ideas.md` (add images to nodes, optional display on graph?)

## Goal

Allow nodes (areas, items, characters, ways) to carry an image, with an optional display on
the graph so a scenario can show icons/thumbnails instead of (or alongside) text labels.

## Implemented (2026-08-17)

### Backend — `routes/graph.py`

- `POST /api/graph/node/<node_id>/image`: accepts multipart `file`, validates the extension
  (`png/jpg/jpeg/gif/webp/svg/bmp/ico`), saves a bundled asset under
  `static/images/nodes/<node_id>-<ms>.<ext>` (served at the same URL — offline-safe), sets the
  node `image` property to `/static/images/nodes/<filename>`, and best-effort removes the
  previous uploaded file for that node.
- Clearing an image uses the existing `PATCH /api/graph/node/<node_id>` with
  `properties: { image: null }` (no schema change needed — arbitrary node properties).

### Frontend

- `api.js`: `uploadNodeImage(nodeId, file)` (FormData POST) and `removeNodeImage(nodeId)`.
- `graph/network-manager.js`:
  - Node `image` property is part of the reload-dedup signature (so image changes refresh the graph).
  - `buildNodeConfig` renders `shape:'circularImage'` with the node image when the
    `graphManager._showImages` toggle is on AND the node has an `image` property; nodes without
    an image keep their normal group shape/color. The label stays, so names remain readable.
  - `toggleImages()` toggles the pref, persists it to `localStorage` (`vw_graphShowImages`), and
    reloads.
- `graph-manager.js`: `_showImages` initialised from localStorage in the constructor.
- `templates/index.html`: added a `🖼 Images` toolbar toggle button (`#btn-images`).
- `inspector/helpers.js`: shared image widget — `renderImageSection(nodeId, props)` with a
  file upload (bundled) OR a pasted URL/path field, a live preview + inline remove, wired up by
  `setNodeImage` / `setNodeImageUrl` / `clearNodeImage`.
- Inspector views wired: `area-view.js`, `item-view.js`, `way-view.js` (Tags & More tab),
  `agent-view.js` (Advanced tab).

### Testing

- `tests/test_node_image.py` (new, 3): upload binds property + persists file; rejects
  unsupported types; clear via PATCH unbinds. → passed.
- `tests/test_graph_move.py` (existing 5) still passes.
- Live smoke on `:4444`: upload → property set + static GET `200 image/png`; cleared back.

## Notes / open questions / next

- **Default image mapping by node type/tag** — not implemented yet. Could map
  `data/library/items/<id>.png` or a tag→image fallback so nodes without an explicit `image`
  still get a default thumbnail. Decide the mapping + where defaults live before adding.
- **Browser E2E** (pending): `node tools/test_*.cjs` — toggle the 🖼 Images button, upload in
  the inspector for each node type, confirm graph thumbnails render + labels persist and that
  the overlay views (light/heat) still have readable borders over image nodes.
- Clearing an image via PATCH doesn't delete the orphaned file on disk (only the upload route's
  replace path cleans up). Optional follow-up: a DELETE takes an `image` and removes the file.
- Image mode switches small items/ways/characters/areas to circular thumbnails; verify area
  text still easy to read at a glance (label under image).