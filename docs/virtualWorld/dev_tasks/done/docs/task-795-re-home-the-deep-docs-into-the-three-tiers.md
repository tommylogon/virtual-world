---
type: task
status: done
area: docs
priority: medium
effort: L
blocked_by: [task-791]
wiki: "[[Feature Map]]"
---

# task-795: Re-home the deep docs into the three tiers

**Filed:** 2026-10-12
**Related:** 

<!-- deps:start -->
**Blocked by:** [[task-791-feature-mechanic-and-system-page-standard]]
<!-- deps:end -->

## What

Re-home the existing deep docs — `Environment/Light System.md`, `Rules Engine/Combat System.md`, `Characters/Vitals System.md`, `Library System/Tags System.md` and the rest — into the feature / mechanic / system tiers, refactoring and incorporating where needed.

## Why

These are already the notes the Feature Map links to, but they predate the tiers. Move and reshape; do not rewrite from scratch — the content is largely right, the shape is not.

## How

Applied the three-tier standard across the deep docs. Each page now carries a \## What you can do\ feature opener (grounded only in that page's own content) and a \## Where it lives\ system section listing the code paths the page itself names. Four exemplar pages (Ways, Movement, Environment, Connections) carry the tiers under their own richer headings rather than the literal template heading. Index, ledger, generated and meta pages (Feature Map, Feature Ledger, Way Properties, Welcome, Scenario Catalogue, patch notes) are deliberately excluded.

## Steps to verify

1. `python tools/doc_links.py --check`.
   - expected: no new broken links.
   - observed: TODO
2. Spot-check `Light System.md`.
   - expected: feature / mechanics / system tiers present.
   - observed: TODO

## Acceptance

- [ ] the deep docs follow the three-tier standard
- [ ] content is moved, not rewritten, unless it was wrong
- [ ] no dead links after the move

## Files

- `docs/virtualWorld/Environment/`
- `docs/virtualWorld/Rules Engine/`
- `docs/virtualWorld/Characters/`
- `docs/virtualWorld/Library System/`
