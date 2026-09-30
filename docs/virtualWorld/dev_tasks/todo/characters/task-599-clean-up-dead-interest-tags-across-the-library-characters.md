---
type: task
status: todo
area: characters
priority: medium
---

# task-599: Clean up dead interest tags across the library characters

**Filed:** 2026-09-30
**Related:** 

## Goal

tools/lint_library.py reports 23 dead_interests errors today (for example characters/Vekka: maps, routes, secrets; characters/Zikka: weapons, training, prestige). interest_tags is matched against item tags and item names by the room attention list and by auto-dress, so these do nothing. Decide per character whether the intent was a real interest that needs an item to carry the tag, or a tag that should be dropped. Note that several are plural/case drift of a live tag (weapons -> weapon, maps -> map), which is a fix rather than a deletion.

## Acceptance

- TODO
