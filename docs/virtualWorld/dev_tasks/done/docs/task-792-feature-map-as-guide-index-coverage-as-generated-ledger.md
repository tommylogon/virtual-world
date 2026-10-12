---
type: task
status: done
area: docs
priority: medium
effort: M
wiki: "[[Feature Map]]"
---

# task-792: Feature Map as guide index; coverage as generated ledger

**Filed:** 2026-10-12
**Related:** 

## What

Split the Feature Map into a clean, themed **guide index** ('here be features — what you can do in viwo, for play and creation') and move the coverage machinery — status (wired/authored/planned), the % documented, the module join — into a generated report. Then retire the generated Features/ stubs (convert `feature_pages.py` from scaffold+gate to report-only, and settle whether that folder is dropped or hand-written).

## Why

The map does two jobs at once — a newcomer's guide and a coverage denominator — and the ledger columns make the guide unreadable. The 77 generated `Features/*.md` stubs are the 'coverage lie' we agreed to kill: they look like docs and carry one link.

## How

Rewrite `Feature Map.md` as a themed index (one line per feature, link to the feature page). Keep status in the generated `docs/design/feature-index.md`. Add the missing **Crafting** row (it is wired, `crafting.*`, but has no row). Strip the scaffold/`--check`-page behaviour from `feature_pages.py` down to a report.

## Steps to verify

1. Read Feature Map.md as a newcomer.
   - expected: a clean themed list of what you can do, no ledger columns.
   - observed: TODO
2. Run `python tools/feature_pages.py --check`.
   - expected: no longer fails on a missing generated stub.
   - observed: TODO

## Acceptance

- [ ] Feature Map reads as a guide index, not a ledger
- [ ] coverage status lives only in the generated report
- [ ] Crafting appears as a feature
- [ ] feature_pages.py no longer scaffolds or gates stub pages

## Files

- `docs/virtualWorld/Feature Map.md`
- `docs/design/feature-index.md`
- `tools/feature_pages.py`
- `tools/feature_index.py`
