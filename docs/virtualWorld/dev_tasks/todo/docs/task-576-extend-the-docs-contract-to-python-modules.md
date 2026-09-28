---
type: task
status: todo
area: docs
priority: medium
blocks: [task-578]
---

# task-576: Extend the @docs contract to Python modules

**Filed:** 2026-09-28
**Related:** tools/js_module_index.py, docs/design/js-module-index.md, task-338
**Blocks:** task-578

## Goal

Give every `engine/` and `routes/` module the same `@docs` docstring header the JS side
already has, and grow the module index into a language-agnostic feature-to-documentation
map.

## Measured (2026-09-28)

The convention already exists and is already guarded — on one language only.

- **152 of 179** JS modules carry `@docs docs/virtualWorld/...` in their header.
- `tools/js_module_index.py:34` lists `docs` in `TAGS`, so it is part of the enforced
  module contract, and the tool generates a **Docs column** into
  `docs/design/js-module-index.md`.
- **0 of 126** `engine/` + `routes/` modules have any such header. The rules engine —
  where a feature's actual behaviour lives — is entirely outside the convention.

So the link data exists, is machine-readable, and is checked by a test. What is missing is
that it covers half the codebase, and that nothing in the running app can consume it.

## Design

Mirror the existing JS header, at the top of the module docstring:

```python
"""Turn queue, background simulation, and the shared barrier before the next increment.

@module tick_manager
@contributes the per-turn loop, character ordering, and the shared barrier
@relates background_simulation, player, graph
@docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
"""
```

- `@docs` is a **repo-relative path**, matching today's JS convention. `none` is a valid
  value and must not fail the check.
- A path that does not resolve on disk should be reported by the checker, not silently
  accepted — that is the whole value of the contract.
- Prefer extending `tools/js_module_index.py` into a shared, language-agnostic indexer
  over writing a second Python-only tool. The generated table gains a Language column.
  Keeping one tool is what stops the two sides drifting.

## Acceptance

- Every module under `engine/` and `routes/` has an `@docs` header, or an explicit
  `@docs none` with a one-line reason.
- A new Python module without the header fails the contract check, exactly as a new JS
  module does today.
- A `@docs` path that does not exist on disk is a check failure.
- `docs/design/js-module-index.md` is regenerated and includes Python rows; the JS rows
  are unchanged.
- The tool is renamed or given a neutral name, and `npm run module:check` still works.
