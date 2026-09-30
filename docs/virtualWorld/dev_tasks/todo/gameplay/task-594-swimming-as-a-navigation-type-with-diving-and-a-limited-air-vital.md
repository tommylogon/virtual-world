---
type: task
status: todo
area: gameplay
priority: medium
---

# task-594: Swimming as a navigation type, with diving and a limited air vital

**Filed:** 2026-09-30
**Related:** 

## Goal

Add swimming as a movement/navigation type alongside walking. Moving over water should be possible at the surface; deep water should require diving, which costs air. Dive duration is bounded by a new Air vital that depletes underwater and refills at the surface, and reaching zero has a defined consequence (drowning damage, forced surfacing, or death - the design decision is the point of the task). Check whether an existing vital or condition can carry this before adding anything new, and reuse the existing movement/action machinery rather than branching inside it.

## Acceptance

- TODO
