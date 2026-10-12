---
type: task
status: done
area: refactor
priority: medium
effort: M
wiki: "[[Feature Map]]"
related: [task-792]
---

# task-796: Module header contract: gate @docs, demote @powers

**Filed:** 2026-10-12
**Related:** 

<!-- deps:start -->
**Related:** [[task-792-feature-map-as-guide-index-coverage-as-generated-ledger]]
<!-- deps:end -->

## What

Settle the front-end module header contract: keep `@docs` as the gated module -> note edge, and demote `@powers` to optional prose (or make it a controlled field that must name a Feature Map label verbatim). Build the feature <-> module index from `@docs`, not from `@powers`.

## Why

`@powers` is free-text prose (266 distinct strings across 156 modules) that `feature_index.py --check` pretends to check — a module can name the wrong feature and nothing catches it, because nothing runtime-linked reads it. `@docs` is a real path to a vault note and `js_module_index.py` already fails on a dead/folder target. The useful half is the join; the gate is theatre.

## How

Relax the `@powers` gate in `tools/feature_index.py`; source the feature->module reverse index from each module's `@docs` target. Regenerate `docs/design/feature-index.md`.

## Steps to verify

1. `python tools/feature_index.py --check`.
   - expected: passes without the prose word-match.
   - observed: TODO
2. `python tools/feature_index.py --report`.
   - expected: feature -> modules built from `@docs`.
   - observed: TODO

## Acceptance

- [ ] the `@powers` gate no longer fails on free prose
- [ ] `@docs` remains the gated, checkable module -> note edge
- [ ] the feature -> module join is built from `@docs`

## Files

- `tools/feature_index.py`
- `tools/js_module_index.py`
- `docs/design/feature-index.md`
