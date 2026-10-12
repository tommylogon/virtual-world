---
type: task
status: done
area: docs
priority: medium
effort: M
blocked_by: [task-791]
wiki: "[[Feature Map]]"
---

# task-793: Collapse Commands to a single index page

**Filed:** 2026-10-12
**Related:** 

<!-- deps:start -->
**Blocked by:** [[task-791-feature-mechanic-and-system-page-standard]]
<!-- deps:end -->

## What

Replace the 86 per-verb `docs/virtualWorld/Commands/*.md` pages with a single **Commands index** — every verb and its aliases, grouped, linking each verb to the feature page and section that owns it.

## Why

Verbs are *mechanics*, so they belong on their feature page (`Movement` owns `go`/`dash`/`climb`/`jump`/`crawl`, `Combat` owns `attack`). 86 thin pages duplicate the feature pages at the wrong granularity. The index is a clean lookup convenience; the substance lives on the feature page.

## How

Write `Commands.md`: verb, aliases, status, and which feature/section documents it. Move any verb detail onto the owning feature page. Delete the 86 pages and retarget inbound links (`[[examine]]`, `[[light]]`, `[[fumble around]]` point at `Features/examine`, `Features/light`, and the search/listen pages).

## Steps to verify

1. `python tools/doc_links.py --check`.
   - expected: no new broken links after deletion.
   - observed: TODO
2. Look up `go` from the index.
   - expected: lands on the Movement page section.
   - observed: TODO

## Acceptance

- [ ] one Commands index page lists every verb + aliases
- [ ] verb detail lives on the owning feature page
- [ ] the 86 pages are deleted and no link dangles

## Files

- `docs/virtualWorld/Commands/`
- `docs/virtualWorld/World Building/Movement.md`
- `docs/virtualWorld/World Building/Connections.md`
