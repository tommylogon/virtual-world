---
type: task
status: todo
area: docs
priority: medium
wiki: "[[Feature Map]]"
---

# task-669: Backfill @docs headers on the 162 baselined Python modules

**Filed:** 2026-10-02
**Related:** task-576, task-578

## What

task-576 put the @module/@contributes/@docs contract and its guard over engine/ and routes/, and documented 18 core modules. The remaining 162 live in docs/design/py-module-baseline.txt. Each needs a real @module/@contributes/@docs header naming the note that documents it (or an explicit @docs none with a one-line reason for a thin registrar or pure utility). The guard already fails a NEW Python module without the header, so this is a ratchet-down of existing debt, not a new mechanism. Work in batches and remove each path from the baseline as it lands; use python tools/js_module_index.py --check to confirm.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — this task adds machine-readable documentation headers to Python source modules; it does not change player or authoring behavior in the browser.

Current availability: 162 Python module paths are recorded in `docs/design/py-module-baseline.txt`. The task's stated guard is `python tools/js_module_index.py --check`; this is a source-contract maintenance task, not a UI feature.

Why no browser UI: a browser interaction cannot prove that every Python module declares the correct `@module`, `@contributes`, and `@docs` relationship or an intentional `@docs none` reason.

Alternative verification steps:
1. Add the header to one baselined module, pointing it at the note that documents that module, or use `@docs none` with the required one-line reason for a thin registrar/utility.
   - expected: the header describes that file's actual responsibility and the baseline entry for that exact path is removed.
2. Run `python tools/js_module_index.py --check` after each batch and inspect the remaining baseline paths.
   - expected: the completed paths no longer appear as missing contracts; an unrelated module is not removed from the baseline.
3. Open the named documentation note and inspect its `## Connected` block.
   - expected: the module-to-note relationship resolves to an existing note and the generated connection is current.

This section is not a claim that planned UI exists or works today.
