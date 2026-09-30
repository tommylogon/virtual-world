---
type: task
status: todo
area: library
priority: medium
---

# task-646: Rename space-separated registry ids (52 total) and resolve the hidden door collision

**Filed:** 2026-09-30
**Related:** [task-601]

## Goal

task-601's lint check now reports 52 offenders: 36 characters (Arix, Croak-Mother, Old Iron-Back, the butcher...), 15 tags (frozen thicket, hidden door...), and 1 item (baker's_bread). load_registry keys entries by filename verbatim, so none resolve by their snake_case form. NOT a rename-and-done: the spaced ids are referenced in 20+ places across areas/characters/items/rooms/ways, and 'hidden door' would MERGE into the existing 'hidden_door' -- decide whether they are the same tag first. Character display names are unaffected (the name field is separate), so this is safe to do but needs the references updated in the same change.

## Acceptance

- TODO
