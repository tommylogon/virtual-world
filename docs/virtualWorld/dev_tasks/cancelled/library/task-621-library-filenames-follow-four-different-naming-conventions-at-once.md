---
type: task
status: cancelled
area: library
priority: low
---

# task-621: Library filenames follow four different naming conventions at once

**Filed:** 2026-09-30
**Related:** 

## Goal

mixed case, kebab-case, snake_case and spaced names coexist across data/library registries.

## Acceptance

- TODO

## Cancellation — duplicate of task-601 (check) and task-646 (the rename)

The claim is true, and it is **the same problem** already measured under
task-601, so carrying it as a second ticket only inflates the backlog.

Measured, per registry:

| registry | n | has uppercase | has spaces | other | hyphen | underscore |
|---|---|---|---|---|---|---|
| `characters` | 69 | **28** | **11** | 0 | 10 | 2 |
| `items` | 1915 | 0 | 0 | **1** (`baker's_bread`) | 0 | **1439** |
| `tags` | 591 | 0 | **15** | 0 | 0 | 29 |

So all four named conventions really do coexist -- mixed case, kebab, snake and
spaced -- and there are five ids that are mixed-case *and* hyphenated at once:
`Croak-Mother`, `Old Iron-Back`, `Rag-Tail`, `Shadow-Pelt`, `Silver-Talon`.

**Why this is a duplicate rather than a second finding.** task-601's
`tag_id_charset` lint check already reports every id in this table, by name:

    items:      1   baker's_bread
    characters: 36   Arix, Croak-Mother, Old Iron-Back, the butcher, ...
    tags:       15   frozen thicket, hidden door, willow hollow, ...
    COLLISION:  'hidden door' and 'hidden_door' both normalise to 'hidden_door'

and task-646 owns the actual rename, including the cross-registry reference
update and the collision decision. The root cause is the same single line --
`routes/helpers.py::load_registry` keys entries by filename verbatim with no
normalisation.

Splitting one root cause across two tickets is the failure mode the audit's own
filing discipline warns about: the tree would claim 52 ids are outstanding twice
and no one could tell which ticket owns the `hidden door` collision.