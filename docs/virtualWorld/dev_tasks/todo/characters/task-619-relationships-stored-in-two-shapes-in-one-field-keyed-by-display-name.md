---
type: task
status: todo
area: characters
priority: high
---

# task-619: Relationships are keyed by display name, not node id

**Filed:** 2026-09-30
**Related:** 

## Goal

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

## Acceptance

- TODO
