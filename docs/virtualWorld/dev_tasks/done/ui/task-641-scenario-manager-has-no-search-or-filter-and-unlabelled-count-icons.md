---
type: task
status: done
area: ui
priority: medium
---

# task-641: Scenario Manager has no search or filter and unlabelled count icons

**Filed:** 2026-09-30
**Related:** 

## Goal

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
