---
type: task
status: todo
area: world
priority: medium
---

# task-584: Cross-chunk ownership rules for carried items, triggers and delayed events

**Filed:** 2026-09-28
**Related:** task-401, task-581, task-583

## Goal

Decide and implement who owns a character, a carried or equipped item, a live trigger and a delayed event while its scope is unloaded, and make the answer consistent across a save and load round trip. A delayed event aimed at an unloaded node is globally indexed and either loads the scope when due or resolves through an explicit deferred policy; dropping it silently is forbidden.

## Acceptance

- TODO
