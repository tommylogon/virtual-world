---
type: task
status: review
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

## Resolution (2026-10-02)

- `routes/docs_ops.py` builds one in-process index from exactly the two sources:
  module `@docs` headers (`tools/js_module_index.py` parsing, JS + Python) and
  library-entry `docs` fields. `routes/docs.py` is the thin registrar;
  `register_docs_routes` is called from `app.py`.
- `GET /api/docs/resolve?module=...|node=...` returns
  `[{title, path, summary, body_url}]`, or `[]` (200) when nothing matches.
  `body_url` is present only when the note is in the narrative vault.
- `GET /api/docs/body?path=...` serves markdown for `docs/virtualWorld/**`
  excluding `dev_tasks/`; everything else (traversal, absolute, dev-tasks,
  missing) returns the same `{"error": "not found"}` 404.
- Staleness is mtime-based: the index records every source file *and* every note
  it points at, and rebuilds when any mtime or the file count changes.

### Minor fix carried along

`docs_problems` now accepts `@docs none — <reason>` by testing the first token,
so a Python module can declare a reasoned absence without failing the guard.

## Acceptance

- [x] Both lookups return correct results — `tests/test_docs_resolve.py` against
      a fixture corpus, plus a real-repo smoke test
      (`engine/tick_manager.py` -> "Turn Queue & Human Turns").
- [x] The index is built once and reused; a second request does not re-scan
      (asserted via a build counter).
- [x] A `dev_tasks/` path is never served and does not leak its existence: the
      response is byte-identical to a plain miss.
- [x] Traversal attempts (`../../etc/passwd`, absolute paths, encoded `..`,
      `%2F`) are rejected with the same 404.
- [x] Changing a note's mtime rebuilds the index (asserted).
- [x] An unknown module or node returns `[]` with a 200.
- [x] Registered through the `routes/` registrar split, following AGENTS.md.
- [x] `python tools/js_module_index.py --check` still exits 0.

## Non-goals

- Full-text search across the corpus. This is a resolver, not a search engine.
- Rendering markdown to HTML. The UI can do that client-side, and keeping the server out
  of it avoids an XSS surface.
