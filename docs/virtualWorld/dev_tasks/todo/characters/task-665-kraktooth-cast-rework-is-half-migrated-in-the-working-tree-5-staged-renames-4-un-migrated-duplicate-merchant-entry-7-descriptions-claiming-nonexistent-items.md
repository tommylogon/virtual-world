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

## Measured consequence (2026-10-01, found during task-660 verification)

**The rename does not merely leave a duplicate file. It breaks the live node's
template resolution, and a refresh then applies the wrong character's data.**

Found in the browser log: `Refreshed "Eldenford Blacksmith" from library` logged
a successful apply, and immediately afterwards the Eldenford Blacksmith node was
carrying **the merchant's** personality and description — which is what the
auto-dress LLM was then shown, twice, so it dressed the blacksmith like a
trader.

Measured, keeping the unproven part separate:

- **Established:** no Eldenford node carries `library_id` or `template_ref`
  (checked all five), so a character node resolves its template **by name
  alone**. `Eldenford Blacksmith` is no longer a library key — the entry is
  `Harren Cobb`, and `/api/library/characters` no longer returns the old key.
  The step immediately before the wrong data is the node-level
  `template-sync.js:181` refresh.
- **Established:** live state is *correct now*. All five Eldenford characters
  carry their own personality and description. The wrong personality was
  transient — present during the run, gone after the later engine
  re-initialisation. So this corrupts state rather than persisting it, which is
  worse than a visible break because nothing reports it.
- **Not established:** the exact fallback that produced the merchant. Either the
  client resolved `libId` unexpectedly, or server-side
  `resolve_template_id` (`engine/sync.py:170`, `guess="node_name"`) did. Both
  are plausible; neither was isolated.

This is the concrete cost of a half-rename, and it decides the order of work:
the rename has to be finished **in the live world first** — or the node bindings
rewritten — not in the library files with the nodes left to guess.

**Partially mitigated on 2026-10-01.** All five Eldenford nodes now carry an
explicit `library_id`, pinned through the sanctioned path
(`POST /api/library/refresh-to-world` with `sections: []`, which applies nothing
and still runs `sync.link` at `routes/library_ops.py:1145`):

    Eldenford Blacksmith          -> Harren Cobb
    Eldenford Elder               -> Gareth Ollen
    Eldenford Farmer              -> Tobin Marsh
    Eldenford Merchant            -> Pell Ardin      (NOT the untracked duplicate)
    Eldenford Road Guard Captain  -> Corvin Hale

So the cast can be synced now without any name matching, and the Merchant
resolves to the renamed template rather than to `Eldenford Merchant.json`. This
is a pin on filename-shaped keys, so it does not survive a future rename — that
is task-667.

Note what this does **not** fix: the three files with a stale `name` field
(`Corvin Hale`, `Pell Ardin`, `Tobin Marsh`) will still have their `name` applied
to the live player if `name` is among the refreshed sections, which would
diverge `player.name` from the graph node's name. Refresh those three with
`name` deselected, or fix the fields first.

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
- [ ] **Every renamed character node carries an explicit `library_id` or
      `template_ref`.** All five Eldenford nodes currently resolve by name only,
      which is how the rename produced a refresh that applied the merchant to the
      blacksmith. Resolving by name is what made the rename load-bearing.
- [ ] A refresh on each renamed character is exercised and the applied data is
      read back, confirming it is *that* character's personality and not a
      neighbour's.
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
