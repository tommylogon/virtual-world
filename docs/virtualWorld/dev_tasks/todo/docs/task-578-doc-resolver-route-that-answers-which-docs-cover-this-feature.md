---
type: task
status: todo
area: docs
priority: medium
blocked_by: [task-576, task-577]
blocks: [task-579]
---

# task-578: Doc resolver route that answers which docs cover this feature

**Filed:** 2026-09-28
**Related:** task-576, task-577
**Blocked by:** task-576 (module `@docs` index), task-577 (node `docs` field)
**Blocks:** task-579

## Goal

Expose one HTTP endpoint that indexes the documentation corpus and answers *"which pages
cover this module path or this node id"*, so the app never reads `docs/` off disk.

## Problem

`docs/` is not under `static/`, so the browser cannot reach the markdown today. Any
authoring UI that wants to show documentation needs a route — and a naive one (serve the
file, or scan the tree per request) would be both slow and unsafe, because the corpus
contains 660 dev-task files and authored content that should not all be public.

## Design

- One index, built once, cached. Sources are exactly the two from the upstream tasks:
  the `@docs` header (task-576) and the node `docs` field (task-577). Do not add a third
  source in this task.
- Two lookups behind one endpoint, or one endpoint with a typed key:
  ```
  GET /api/docs/resolve?module=engine/tick_manager.py
  GET /api/docs/resolve?node=way_4f2a
  ```
  Response: title, path, one-line summary, and the path to fetch the rendered body.
- **Serve a body only for an allowlist of the narrative pages.** `docs/virtualWorld/*`
  excluding `dev_tasks/` is the allowlist. The dev-task tree is internal working material
  and must not become fetchable over HTTP.
- Cache invalidates on file mtime, not on a timer. A stale index in a dev tool is worse
  than no index.
- Return an empty list, not a 404, for an unknown key. "This feature has no docs" is a
  normal answer that the UI must be able to render.

## Acceptance

- Both lookups return correct results, covered by tests against a fixture corpus.
- The index is built once per process and reused; a second request does not re-scan the
  tree (assert this, do not assume it).
- A `dev_tasks/` path is never served, and requesting one does not leak its existence
  through the response shape.
- A path traversal attempt (`../../etc/passwd`, absolute paths, encoded separators) is
  rejected.
- Changing a markdown file's mtime rebuilds the index.
- An unknown module or node returns `[]` with a 200.
- The route registers through the existing `routes/` registrar split, and follows
  AGENTS.md conventions.

## Non-goals

- Full-text search across the corpus. This is a resolver, not a search engine.
- Rendering markdown to HTML. The UI can do that client-side, and keeping the server out
  of it avoids an XSS surface.
