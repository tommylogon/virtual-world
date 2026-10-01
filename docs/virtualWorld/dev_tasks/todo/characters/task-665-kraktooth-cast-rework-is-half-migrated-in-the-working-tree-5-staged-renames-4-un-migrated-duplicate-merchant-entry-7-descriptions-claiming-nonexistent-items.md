---
type: task
status: todo
area: characters
priority: high
---

# task-665: Kraktooth cast rework is half-migrated in the working tree: 5 staged renames, 4 un-migrated, duplicate Merchant entry, 7 descriptions claiming nonexistent items

**Filed:** 2026-10-01
**Related:** task-519, task-619, task-513, bug-516

## Goal

Bring the Kraktooth cast rename + equipment rework to a consistent, recorded state, or revert it. Currently it exists only as staged git renames and half-edited JSON with no task tracking it.

## Acceptance

- [ ] **Every renamed file has its internal `name` matching its filename.**
      Currently only `Harren Cobb` and `Gareth Ollen` do.
- [ ] No duplicate library entries. `Eldenford Merchant.json` (untracked, created
      by a browser save) is either retired or promoted to `Pell Ardin.json`.
- [ ] Every relationship key in every renamed file points at a character that
      exists under its **new** name -- but read task-619 first, because these are
      display-name keys and the migration may be invalidated by that work.
- [ ] No description claims an item the character does not have. Either the
      description changes or the item exists, per character, verified by reading
      `inventory`/`equipped` back after import.
- [ ] The four half-migrated renames are either completed or reverted. Half a
      rename is worse than none: the file name says one thing and the `name`
      field says another, and the registry keys on the id.
- [ ] Gear is authored the way task-519 specifies (library-id references), not as
      hand-embedded item dicts, so the Harren workaround is deleted rather than
      copied five more times.
- [ ] Outcome is stated: completed, or reverted with the working tree clean. This
      task's value is that the state stops being invisible.

## Notes on scope

This is a bookkeeping task in the sense that it exists because the work was
untracked, not because the work is hard. The hard parts are bug-516,
task-519 and task-619. If those are deferred, the honest end state here is a
clean revert, not a partial migration left staged.

One thing already verified and worth keeping: the browser-save direction writes
`data/library/characters/<Live Name>.json`, and the live scenario still holds the
placeholder names (`player_Eldenford_Blacksmith` and the other four, at
`data/scenarios/kraktooth_goblin_camp.json:17440-17526`). So renaming library
files alone guarantees a duplicate on the next save, which is exactly how
`Eldenford Merchant.json` came to exist. The rename cannot be completed in the
library in isolation.
