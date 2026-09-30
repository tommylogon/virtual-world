---
type: task
status: cancelled
area: library
priority: medium
---

# task-620: Two library registries are empty and have no tab

**Filed:** 2026-09-30
**Related:** 

## Goal

Two of the library registries render empty and have no tab in the library UI, so authored content in them is unreachable.

## Acceptance

- TODO

## Cancellation

Cancelled 2026-09-30. The finding does not reproduce; the registry is reachable
and its empty state is handled properly.

The claim was that "two of the library registries render empty and have no tab
in the library UI, so authored content in them is unreachable."

Measured:

- `GET /api/library/structures` returns `{}` -- genuinely empty.
- `GET /api/library/rooms` returns **HTTP 400** -- no endpoint, so it is not a
  "rendered empty" case at all.
- The Library Browser does have 8 tabs (Items, Characters, Areas, Traits,
  Conditions, Behaviours, Tags, Ways) and none of them is Structures.

That last point looked like confirmation, so the claim was nearly filed on the
strength of it. It was still wrong: **`Build > ðŸ“¦ Structures` opens a Structures
browser** (screenshot `audit/77-structures-entry.png`), which renders:

    ðŸ“¦ Structures
    No structures saved yet. Right-click an area -> "Save as Structure..."
    [Close]

So the registry has a reachable entry, and the empty state is not blank -- it
names the exact action that fills it. That is the right way to handle an empty
collection, and it is the opposite of the reported problem.

Only `rooms` is genuinely odd, and even that is a missing endpoint rather than an
unreachable registry: `data/library/rooms/` holds 3 files with no route to read
them. That is worth a task of its own, not this one.

### Method note

`querySelectorAll('.modal, [role=dialog]')` reported **0 open modals** while
this dialog was plainly on screen -- the Structures browser uses different
markup. That is the tenth DOM-vs-pixels disagreement in this audit, and it
happened *after* I had already written the rule into `AGENTS.md`. Reading the
screenshot first is the habit that has to stick; reading the DOM to decide
*whether to take* a screenshot is the same error in a new costume.