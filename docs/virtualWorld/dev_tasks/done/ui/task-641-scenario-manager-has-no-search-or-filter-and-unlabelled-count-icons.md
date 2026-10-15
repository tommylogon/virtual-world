---
type: task
status: done
area: ui
priority: medium
---

# task-641: Scenario Manager has no search or filter and unlabelled count icons

**Filed:** 2026-09-30
**Related:** 

## What

At this scenario's size the unfiltered list is unusable and the count icons carry no label.

## Acceptance

- [x] The Scenario Manager has a filter that narrows the list live
- [x] A match count is shown, so it is clear the list is filtered
- [x] A filter with no matches says so distinctly from "no scenarios exist"
- [x] Each count carries a `title` naming what it counts
- [x] Typing keeps focus in the filter across repaints
- [x] Verified live: typed "pin" -> 1 of 22, only `pines` listed

## Resolution (2026-09-30)

Both halves confirmed at source, in `static/js/ui/scenario-manager.js`, then
fixed.

**The counts were one flat string.** `renderList` built a single text node:

    stats.textContent = `<house> ${sc.areas} Â· <sprout> ${sc.players} Â· ${fmtSize(...)} Â· ${fmtAge(...)}`

so the two numbers had to be decoded from two glyphs. Verified there was no
disclosure available: a whole-document scan for digit-only elements carrying a
`title` or `aria-label` returned **zero**. The pattern the top bar already uses
(`title="Next forecast change"`, `title="Scenario source"`) was absent here.
Each count is now its own element with a `title` -- "23 areas", "21 characters",
"File size on disk", "Last modified".

**There was no filter at all**, and the registry holds **22 scenarios** in a
`max-height:60vh` scroller, so the list really is unusable unfiltered. Added a
live filter over name, plus an exact match on either count, a "N of M" counter,
and a distinct "No scenario matches ..." message -- without that last one, a
filtered-to-nothing list is indistinguishable from an empty registry, which is
the same class of defect as the one task-620 was retracted for.

**One encoding note for whoever touches this file.** The emoji are stored
mojibake'd (`Ã°Å¸` sequences, i.e. UTF-8 bytes read as Latin-1), so an edit that
types a real emoji in `oldString` will not match. The glyphs are therefore built
from `String.fromCharCode(0xD83C, 0xDFE0)` / `(0xD83C, 0xDF3F)` to match the
existing bytes exactly rather than "fixing" the encoding in passing.

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. Open Scenario Manager and type `pin` in its filter.
   - expected: one of 22 scenarios remains, named `pines`, and focus remains in the filter.
   - observed: live: `pin` → `1 of 22`, only `pines` listed.
2. Type a query with no matches, then clear it.
   - expected: the UI says no scenario matches, distinctly from an empty registry; clearing restores all rows.
   - observed: implemented and recorded in the resolution; repeat the browser pass when changing this surface.
3. Hover each count in a scenario row.
   - expected: area count, character count, file size, and last-modified values each name what they represent.
   - observed: the card records titles “23 areas”, “21 characters”, “File size on disk”, and “Last modified”.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Game menu → Scenario Manager modal → filter field and scenario rows/count icons.

Current availability: The card records a live pass over 22 scenarios: typing `pin` produced `1 of 22` and only `pines`; the count icons now have titles and filtering preserves keyboard focus.

Live steps when available:
1. Open Scenario Manager and type `pin` into its filter.
   - expected: the counter reads `1 of 22` and only `pines` remains; typing does not lose focus during repaint.
2. Replace the filter with a string that matches no scenario, then clear it.
   - expected: the modal distinguishes “no scenario matches” from an empty scenario registry; clearing restores the full list.
3. Hover each row's area count, character count, file size, and last-modified value.
   - expected: each has a title identifying exactly what it counts or describes.
4. Filter by an exact area/player count.
   - expected: the matching scenario rows remain and the displayed count agrees with the row total.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
