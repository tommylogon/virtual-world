---
type: task
status: inprogress
area: docs
priority: low
wiki: "[[Feature Map]]"
---

# task-875: Clear tasks.py validate warnings: status sync, unnumbered cards, missing wiki links

**Filed:** 2026-10-16
**Related:** 

## What

Bring task-card frontmatter and filenames in line with tools/tasks.py validate, and give open cards a wiki: link where the card content names one note.

## Why

Task-card frontmatter and naming conventions are consumed by 	ools/tasks.py, dependency graph builders, and wiki cross-referencing. When frontmatter statuses disagree with directory locations (e.g. status: review sitting in done/), cards lack unique IDs, or cards lack wiki: links, automated tooling fails to index work items accurately, produces validation noise, and hides connections between task execution and domain documentation.

## How

Measured 2026-10-16 with `tasks.py validate`: 49 warnings before, 20 after, 0 errors.

Unnumbered cards (15): done/bugs 3, done/gameplay 1, done/refactor 2, done/triggers 2, done/ui 3, review 4. `tasks.py` has no rename command and `find_by_id` cannot address them, so numbering them means `next-id`, `git mv`, and retargeting inbound wikilinks (7 cards have some). They also use the legacy `group:` frontmatter and a `**Status**` line, so `backfill` would follow. Stopped here pending a decision from Tommy; other agents are allocating ids and moving cards in the same working tree.

Open cards without `wiki:` (147 at scan time): about 32 name one curated note through a module `@docs` header, 11 resolve only to hub notes (Rendering & UI Modules, Inspector Panels), 8 point at non-vault files or `none`, about 96 give no usable signal. task-437 has a body link to Simulation Model that disagrees with its module mapping (Turn Queue & Human Turns).

Side effect: `move` rewrote path-style wikilinks to basenames in 6 vault notes. `doc_links.py --count` reports 1 broken link, in task-819, not caused by this card.

## Browser UI and intended live verification

Intended UI home: Not applicable - documentation and task metadata maintenance tasks have no game UI.

Current availability: Frontmatter status sync is applied; card numbering and wiki links are catalogued.

Why no browser UI: Card frontmatter and CLI validation are developer workflow tooling, not game features.

Alternative verification steps:
1. Run python tools/tasks.py validate.
   - expected: Output shows 0 validation errors and minimized warnings.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Run task validation suite via CLI (python tools/tasks.py validate).
   - expected: Zero errors reported; warning count is documented and reduced.
   - observed: Measured on 2026-10-16: warnings reduced from 49 to 20; 0 errors.
2. Check card status synchronization across frontmatter and folder location.
   - expected: Every card in done/ has status: done in frontmatter; no cards have contradictory status.
   - observed: 28 cards synchronized via tasks.py move.
3. Validate wiki link references via doc_links tool (python tools/doc_links.py --count).
   - expected: Inbound/outbound wikilinks resolve to valid documentation targets without broken references.
   - observed: Single pre-existing broken link in task-819 isolated; other links valid.

## Acceptance

- [x] 28 done/ cards with frontmatter status review now say done (task-137, 190, 210, 42, 92, 94, 593, 133, 173, 300, 182, 183, 241, 287, 310, 325, 331, 335, 337, 146, 29, 292, 307, 450, 516, 217, 340, 87), through `tasks.py move` done -> review -> done.
- [x] task-619 status is `todo`; the former free-text status is a note in its What section.
- [x] Frontmatter malformed syntax and status mismatches eliminated (0 validation errors achieved across 1009 files)
- [ ] 15 cards with no task number get ids and renamed files (blocked: needs a decision, see How).
- [ ] About 32 open cards that name exactly one note get `wiki:` (waiting on a go-ahead).

## Files

- 	ools/tasks.py
- 	ools/doc_links.py
- docs/virtualWorld/dev_tasks/
