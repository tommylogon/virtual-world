---
type: task
status: todo
area: characters
priority: high
---

# task-605: Make size a real character property tied to the graph editor character form

**Filed:** 2026-09-30
**Related:** 

## Goal

engine/size.py has 6 tiers (tiny..titanic) as a size_* TRAIT, but 0 of 69 library characters and 0 world characters carry one, and size_tier() is called from exactly one place: the way max_size passage gate. Promote size to a character property surfaced in the graph editor character form.

## Acceptance

- TODO
