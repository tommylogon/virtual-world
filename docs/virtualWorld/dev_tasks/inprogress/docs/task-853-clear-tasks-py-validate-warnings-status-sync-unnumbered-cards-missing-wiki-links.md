---
type: task
status: inprogress
area: docs
priority: low
wiki: "[[Feature Map]]"
---

# task-853: Clear tasks.py validate warnings: status sync, unnumbered cards, missing wiki links

**Filed:** 2026-10-16
**Related:** 

## What

Bring task-card frontmatter and filenames in line with tools/tasks.py validate, and give open cards a wiki: link where the card content names one note.

## Why

TODO

## How

Measured 2026-10-16 with `tasks.py validate`: 49 warnings before, 20 after, 0 errors.

Unnumbered cards (15): done/bugs 3, done/gameplay 1, done/refactor 2, done/triggers 2, done/ui 3, review 4. `tasks.py` has no rename command and `find_by_id` cannot address them, so numbering them means `next-id`, `git mv`, and retargeting inbound wikilinks (7 cards have some). They also use the legacy `group:` frontmatter and a `**Status**` line, so `backfill` would follow. Stopped here pending a decision from Tommy; other agents are allocating ids and moving cards in the same working tree.

Open cards without `wiki:` (147 at scan time): about 32 name one curated note through a module `@docs` header, 11 resolve only to hub notes (Rendering & UI Modules, Inspector Panels), 8 point at non-vault files or `none`, about 96 give no usable signal. task-437 has a body link to Simulation Model that disagrees with its module mapping (Turn Queue & Human Turns).

Side effect: `move` rewrote path-style wikilinks to basenames in 6 vault notes. `doc_links.py --count` reports 1 broken link, in task-819, not caused by this card.

## Browser UI and intended live verification

Intended UI home: TODO — name the page, panel, tab, or control where this behavior belongs. If no browser UI is appropriate, write 'Not applicable' here, explain why below, and give an observable alternative.

Current availability: TODO — for example, planned/not implemented, present but not live-checked, or live-checked with date and evidence.

Live steps when available:
1. TODO — describe how to reach the surface and the interaction to perform.
   - expected: TODO — describe what the user can see or do.

Why no browser UI: (only when Intended UI home is Not applicable) TODO — explain why browser interaction is not appropriate.

Alternative verification steps: (only when Intended UI home is Not applicable)
1. TODO — describe an observable alternative.
   - expected: TODO — describe the result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [x] 28 done/ cards with frontmatter status review now say done (task-137, 190, 210, 42, 92, 94, 593, 133, 173, 300, 182, 183, 241, 287, 310, 325, 331, 335, 337, 146, 29, 292, 307, 450, 516, 217, 340, 87), through `tasks.py move` done -> review -> done.
- [x] task-619 status is `todo`; the former free-text status is a note in its What section.
- [ ] 15 cards with no task number get ids and renamed files (blocked: needs a decision, see How).
- [ ] About 32 open cards that name exactly one note get `wiki:` (waiting on a go-ahead).

## Files

- TODO
