---
group: Graph
---
# Graph Editor: Flip Edge Direction

**Filed**: 2026-08-20
**Priority**: Medium
**Status**: In Review — implemented 2026-08-20

## Implementation

Added a "Flip Edge" option to the graph editor's edge context menu (right-click on an edge).

Backend (`routes/graph.py`):
- New `POST /api/graph/edge/flip` endpoint that swaps source/target of an edge while preserving type and properties.
- Blocks flipping of `connection`, `triggers`, and `requires` edges (returns 400).

Frontend (`static/js/`):
- `api.js`: added `ApiClient.flipEdge(source, target, type)`.
- `graph/context-menu.js`: added "🔀 Flip Edge" to edge context menu and `flip_edge` case in `ctxAction()`.
- Frontend also blocks `connection`/`triggers`/`requires` edges before calling the API.

## Verification

- JS syntax check passed for `context-menu.js`, `api.js`, `network-manager.js`
- Python tests pass (same 3 pre-existing failures in `test_trigger_system.py`, unrelated)

---

## Idea

Add a "Flip Edge" button/action to the graph editor that reverses the direction of a selected edge (swaps source and target).

Context:
- Currently edges are directed (e.g. `in`, `on`, `carrying`, `equipped`, `connection`).
- Some edge types are semantically directional and flipping them makes no sense (e.g. `connection` between areas, or `triggers`).
- Other edges are naturally bidirectional or may be connected the wrong way around during editing.
- A right-click context menu item on edges would be the natural place for this.

## Notes

- Should only flip edges where direction is meaningful to reverse (not `connection`, `triggers`, etc.).
- The edge type itself should probably stay the same — only source/target swap.
- Backend endpoint needed: `POST /api/graph/edge/flip` (or reuse `edge/update` with a `flip` flag).
- Frontend: add menu item in `static/js/graph/context-menu.js` edge context menu, wire through `api.js` and `graph-manager.js`.

## Related

- `routes/graph.py` edge endpoints
- `static/js/graph/context-menu.js`
- `static/js/api.js`
