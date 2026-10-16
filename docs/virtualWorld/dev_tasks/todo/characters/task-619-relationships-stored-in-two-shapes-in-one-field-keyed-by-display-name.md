---
type: task
status: todo
area: characters
priority: high
---

# task-619: Relationships are keyed by display name, not node id

**Filed:** 2026-09-30
**Related:** 

## What

Relationships are keyed by display name, not by node id, so renaming a
character orphans its relationships.

CORRECTED 2026-09-30 after live testing. The original claim was that
relationships are "stored in two shapes in one field". **That half is wrong.**
All 23 characters expose a single object shape:

    {"Gribba": {"closeness": 20, "first_sighting": false}, ...}

The other half reproduces. Counting every relationship key across all 23
characters: 65 of 67 are display names ("Gribba", "Krikka", "Mikka", "Rikka",
"Thrazz", "Vekka"), 1 looks like an id, 1 is ambiguous.

Why it matters: `AGENTS.md` states "Node identity is an opaque ID. Display names
are a resolution layer." Keying a persisted record by the display name inverts
that -- rename a character and every relationship pointing at it is orphaned,
with no id left to re-resolve from. The same class as the id leaks in
task-624/task-638, on the write side rather than the display side.

Scope note: migrating the key to an id is not a one-liner. It needs a
serialization migration, a read path that tolerates the old name-keyed form, and
a decision about whether the two-key state (1 id-keyed entry already present) is
a partial migration that is half done or a legitimate second representation.

The relationship field holds two record shapes and is keyed by display name rather than id, so a rename orphans the relationship.

Status note (previously free text in the status field): this card is out of date and needs its measurements redone and its goal re-authored before work starts.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: select a character → Mind panel → Relationships. The panel
should resolve each relationship by the other character's opaque node ID and
display the current character name as a label.

Current availability: the measured card evidence says all 23 characters use
one object shape, but 65 of 67 relationship keys are display names. The
relationship-key migration and Mind-panel resolution are not claimed as
implemented by this card.

Live steps when available:
1. In a scratch scenario, inspect Character A's relationship entry to
   Character B in the Mind panel and record B's node ID and displayed name.
   - expected: the relationship resolves to B by node ID and displays B's
     current name and closeness.
2. Rename B's character node, reload the scenario, and reopen A's Mind panel.
   - expected: A's relationship still points to the same node ID and renders
     B's new name; no orphaned relationship appears under the old name.
3. Rename another character to B's former display name and inspect A's
   relationship list.
   - expected: the relationship remains attached to B's ID and is not
     reassigned to the character who inherited the old name.
4. Save and reload again; inspect the serialized relationship record.
   - expected: the stored key is B's opaque ID, with the relationship facts
     preserved once and no duplicate display-name keyed record.

These steps define the intended Mind-panel verification. The task's current
acceptance and data migration still need to be completed.

This section is not a claim that planned UI exists or works today.
