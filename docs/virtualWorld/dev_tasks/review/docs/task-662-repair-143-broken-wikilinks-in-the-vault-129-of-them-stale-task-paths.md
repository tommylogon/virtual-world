---
type: task
status: review
area: docs
priority: medium
---

# task-662: Repair 143 broken wikilinks in the vault, 129 of them stale task paths

**Filed:** 2026-10-01
**Related:** task-576, task-578

## Goal

Measured across all 597 `[[wikilinks]]` in docs/virtualWorld: 143 distinct targets do not resolve, in 74 files. 129 point at dev_task files whose path went stale when tools/tasks.py move relocated them between status folders - the tool renames on disk but does not rewrite inbound links, so every move silently rots the notes that cited the task. 11 point at prose notes that do not exist, mostly a missing folder prefix (Temperature/* are at Environment/Temperature/*) plus three genuinely absent notes (Characters/Equipment Loadouts, UI & Settings/Inspector, World Building/Item System). Two ways to fix: make tools/tasks.py move rewrite inbound `[[...]]` links, or link tasks by stable id rather than by status-folder path. Then add a broken-link check beside tools/tasks.py validate so this cannot rot again.

## Measured reality (2026-10-02, task-662 execution)

The "143" was wrong for one boring reason: most of them were **escaped-pipe
aliases**, not broken links. `[[Items & Inventory/Equipment & Paperdoll\|Equipment
& Paperdoll]]` is the correct way to write an alias inside a markdown table; any
measurement that splits on `|` without unescaping `\|` counts them as missing.
Handling `\|`, `#heading`, `.md`, and Obsidian's basename resolution leaves
**27 broken occurrences in 21 distinct targets** — not 143.

Of those 27:

- 8 were stale task/bug paths fixed mechanically (a moved task is retargeted by
  **id + slug**, so a reused id is never mislinked; old `bug_6-slug` names are
  understood); they are now cited by basename, which a status move cannot break.
- 3 pointed at the three genuinely absent notes, retargeted to the real notes
  (`UI & Settings/Inspector Panels`, `Items & Inventory/Items Overview`,
  `Environment/Temperature System`).
- 5 were broken **folder** links (`[[dev_tasks/todo/]]`), which Obsidian cannot
  resolve at all; replaced with plain labels and a path.
- 6 were malformed "links" wrapping code/test paths, converted to code spans.
- 5 referenced tasks that no longer exist (deleted duplicates with a reused id:
  task-150, task-181; and a never-filed task-163); delinked to plain text.

## Resolution

- New `tools/doc_links.py` — resolves the vault's wikilinks and reports/repairs
  broken ones (`--check`, `--count`, `--report`, `--fix`).
- `tools/tasks.py links` runs the check, and `tools/tasks.py move` rewrites
  inbound links when a move would invalidate them.
- Evidence: `python tools/doc_links.py --count` went from
  `broken occurrences: 27 / broken distinct: 21` to `0 / 0`; `--check` exits 0.

## Acceptance

- [x] Every resolvable broken link is repaired; the vault is at zero.
- [x] `python tools/doc_links.py --check` exits 0.
- [x] A task moved with `tools/tasks.py move` has its inbound links rewritten
      (covered by `tests/test_doc_links.py`).
- [x] The check runs from the task helper: `python tools/tasks.py links`.
- [x] The retraction of the "143" figure is recorded above with the measurement.
