---
type: task
status: done
area: docs
priority: medium
---

# task-709: Link the vault by what is connected to what: one page per feature, closed tag vocabulary, Connected sections, and four guards

**Filed:** 2026-10-05
**Related:** task-661,task-26,task-91

## Goal

Turn docs/virtualWorld from an index with islands into a connected graph: a Features/ page per Feature Map row, a controlled tag vocabulary, a generated Connected section per note, Obsidian affordances used where they carry meaning, and four gates wired into npm run precommit so it cannot rot back.

## Measured starting point

885 notes · **688 with zero inbound links** · 80 curated pages holding 481 links
· **0 callouts** · 1 real hashtag · 75 tag tokens of which **70 appeared exactly
once** · Feature Map numbering restarting across the two tables, with prose
claiming 74 · two rows whose `Docs` cell read `none` · `Temperature System.md`
duplicated in two folders, making every bare reference ambiguous ·
`_Index.md` indexing 45 of the curated pages.

## What was done

- **Feature Map renumbered** so every `#` is unique (43 in-game, 33 editor, 76
  rows), counts corrected in prose, and a "numbering changed" callout added so an
  old citation ("row 58") stays traceable. `[[Temperature System (redirect)]]`
  removed the duplicate basename that made bare references ambiguous.
- **`Features/`** — 76 pages, one per row, plus `Features Overview.md`. Scaffolds
  are thin but *true*: every sentence is one the Feature Map already asserts.
- **Closed tag vocabulary** (`tools/doc_tags.py`): `system/…`, `surface/…`,
  `status/…`, `topic/…`. Tags are derived from the folder and, for a feature page,
  from the deep doc it links — **How it works only**, because inheriting from the
  `Connected` block's `[[Feature Map]]` link tagged all 76 pages `system/docs`.
- **`## Connected` on every note that has a relation**, generated from four that
  the repo already asserts: Feature Map rows, the 96 task files carrying `wiki:`
  frontmatter, module `@docs` headers, same-folder neighbours — plus a small
  verified `SECTION_REFS` table of heading-level links (the vault had four
  heading refs in 885 notes).
- **Callouts where they carry meaning**: status → `> [!success]`/`> [!caution]`,
  the map's unverified tier → `> [!caution]`, "exists but unreachable" →
  `> [!warning]`.
- **`_Index.md`** brought up to date: it now lists every curated page including
  `Memory Dynamics.md` and the `Features/` entry point.

## Three real bugs found while wiring this

1. **`docs_links` mis-parsed the escaped pipe.** `[[Note\|Alias]]` came back as
   `"Note\\"`, which silently mis-stemmed `doc_connected.features_by_doc` and cost
   that note a whole inbound relation. It now normalises through
   `doc_links.target_key` — one resolver, one answer.
2. **A bare `|` in a Feature Map cell truncated it silently.** Row 23 parsed as
   `[[Environment/Temperature System` and the note it names lost its inbound
   relation with no error anywhere. The cell is now escaped (`\|`, which is what
   Obsidian requires inside a table) and `feature_index.split_cells` splits on
   *unescaped* pipes only.
3. **`way_property_index --write` wiped another tool's work.** The generated page
   carried `doc_tags` frontmatter and a `doc_connected` block that one
   regeneration deleted, after which `--check` failed on a difference nobody could
   see. The writer now carries both over (`merge_page`).

Also: `rate-limiter.ts`'s `@powers` was a sentence rather than a Feature Map name,
so `feature_index --check` was red; and `tests/test_feature_index.py` still
asserted the map had 58 rows.

## Acceptance

- [x] Every Feature Map row has a page, and every page has a row behind it
      (`tools/feature_pages.py --check` → 76 for 76).
- [x] Every curated note is inside one closed tag vocabulary, none untagged
      (157 notes, 28 tags, 0 untagged).
- [x] Every curated note with a relation carries a `Connected` section, and none
      carries an empty one (`tools/doc_connected.py --check`).
- [x] `python tools/doc_links.py --count` → **0 broken**.
- [x] `python tools/doc_links.py --orphans` → **0 of 157** curated notes
      unreachable (was 21).
- [x] All four gates run in `npm run precommit`, with pytest mirrors
      (`tests/test_doc_links.py`, `test_doc_tags.py`, `test_doc_connected.py`,
      `test_feature_pages.py`, plus new cases in `test_feature_index.py` and
      `test_way_property_index.py`) — 66 tests green.
- [x] `python tools/feature_index.py --check` green again; `ts_convert.py check`
      green; `python tools/tasks.py validate` → 0 errors.
- [x] Full suite A/B'd against a clean worktree at the same commit; failure
      **names** identical.

## Out of scope, deliberately

Normalising tags across the 805 task files (huge diff) · `![[embeds]]` anywhere ·
inventing relations the repo does not already assert · enriching the 76 feature
pages with real code paths — they honestly say "Where it lives: not recorded yet"
rather than guessing. `doc_links --orphans --all-notes` reports 635 unreferenced
task files; that is expected, because the task tree is referenced by
`related:` frontmatter rather than by wikilinks.
