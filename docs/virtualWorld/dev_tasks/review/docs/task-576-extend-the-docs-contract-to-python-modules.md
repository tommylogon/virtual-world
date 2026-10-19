---
type: task
status: review
area: docs
priority: medium
blocks: [task-578]
---

# task-576: Extend the @docs contract to Python modules

**Filed:** 2026-09-28
**Related:** tools/js_module_index.py, docs/design/js-module-index.md, task-338
**Blocks:** task-578

<!-- deps:start -->
**Blocks:** [[task-578-doc-resolver-route-that-answers-which-docs-cover-this-feature]]
<!-- deps:end -->

## What

Give every `engine/` and `routes/` module the same `@docs` docstring header the JS side
already has, and grow the module index into a language-agnostic feature-to-documentation
map.

## Measured (2026-09-28)

The convention already exists and is already guarded - on one language only.

- **152 of 179** JS modules carry `@docs docs/virtualWorld/...` in their header.
- `tools/js_module_index.py:34` lists `docs` in `TAGS`, so it is part of the enforced
  module contract, and the tool generates a **Docs column** into
  `docs/design/js-module-index.md`.
- **0 of 126** `engine/` + `routes/` modules have any such header. The rules engine -
  where a feature's actual behaviour lives - is entirely outside the convention.

So the link data exists, is machine-readable, and is checked by a test. What is missing is
that it covers half the codebase, and that nothing in the running app can consume it.

## How

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
  accepted - that is the whole value of the contract.
- Prefer extending `tools/js_module_index.py` into a shared, language-agnostic indexer
  over writing a second Python-only tool. The generated table gains a Language column.
  Keeping one tool is what stops the two sides drifting.

## Resolution (2026-10-02)

`tools/js_module_index.py` is now language-agnostic. It scans `engine/` and
`routes/` `.py` modules alongside `static/js`, reads the contract from the real
module docstring (via `ast`, so a header may sit anywhere in a long docstring),
and holds Python to the same guard the front end has. The generated index gained
a **Lang** column; the file keeps its historical `js_` name so
`npm run module:check` and the docs citing it keep working.

Because the back end started from zero headers against 180 modules, the JS
bootstrapping pattern is reused: 18 core engine/route modules are documented
below, and the remaining 162 are recorded in
`docs/design/py-module-baseline.txt`. The guard fails a **new** Python module
that omits the contract; the existing debt ratchets down under task-669.

Documented core modules: `engine/tick_manager`, `engine/foraging`,
`engine/item_reach`, `engine/background_simulation`, `engine/fog`,
`engine/world_compile`, `engine/world_grid`, `engine/trigger_validator`,
`engine/nl_editor_validation`, `engine/promotion`, `engine/lived_log`,
`engine/movement`, `engine/combat`, `engine/soak_telemetry`,
`engine/soak_runner`, `routes/graph_ops`, `routes/library_ops`,
`routes/world_grid_ops`.

## Acceptance

- [x] A new Python module without the header fails the contract check, exactly as
      a new JS module does today - `tests/test_module_index_py.py`.
- [x] A `@docs` path that does not exist on disk is a check failure (a folder
      target included).
- [x] `docs/design/js-module-index.md` is regenerated with Python rows and a
      `Lang` column; every existing JS row is still present.
- [x] `python tools/js_module_index.py --check` exits 0
      (`162 known-uncovered, 0 known-bad-@docs, no new`).
- [~] **Not met as written:** every one of the 180 modules carrying a header.
      18 core modules do; the other 162 are baselined and filed as **task-669**.
      The convention and the guard are live; the backfill is bounded, known
      work rather than an undocumented gap.

## Why

Ensure python engine modules adhere to the documentation contract, maintaining mapped documentation notes for core simulation systems.

## Steps to verify

1. Run documentation contract linter across python modules
   - expected: python module documentation mappings validate cleanly
   - observed: Verified clean lint pass in tools/lint_docs.py

## Files

- `tools/lint_docs.py`

## Browser UI and intended live verification

Intended UI home: Not applicable - this card establishes `@module`/`@contributes`/`@docs` headers and a source-to-documentation index for Python modules; no product screen changes.

Current availability: the card records Python module headers, missing-path/folder-target failures, generated Python rows/Lang column, and a passing `python tools/js_module_index.py --check`. The header contract itself is verified in repository tooling.

Why no browser UI: the acceptance is whether source modules name real documentation notes and the index contains their declarations; a player browser cannot inspect this contract.

Alternative verification steps:
1. Remove a required `@docs` header from a scratch Python module and run `python tools/js_module_index.py --check`.
   - expected: the guard fails with that module path; restoring a real note target or justified `none` declaration restores the check.
2. Point a scratch header at a directory/nonexistent note and rerun the check.
   - expected: the folder/dead target is rejected.
3. Regenerate `docs/design/js-module-index.md` and inspect the Python rows and `Lang` column.
   - expected: all pre-existing JS rows remain, Python modules appear with their declared note, and the generated index matches the source headers.

This section is not a claim that planned tooling is exposed in the browser.
