---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-700, task-691, task-714]
blocked_by: [task-807]
---

# task-813: MOSIAC: Obligations - the missing letter's data

**Filed:** 2026-10-12
**Related:** task-700

<!-- deps:start -->
**Blocked by:** [[task-807-gimp-the-goal-model-and-its-serialization]]
**Related:** [[task-700-grounded-plan-contract-the-llm-plan-phase-emits-typed-steps-validated-against-world-facts]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Give Obligations a home: the data for what a character owes (missions, promises, duties, appointments), and how an obligation spawns an Intention.

## Why

Obligations are the most demanded letter across the profiles and the least built. An obligation is an input that generates an intention, not a peer of one.

## How

An obligation record (from, to, charge, can accept/alter/refuse/forget, deadline). On accept, spawn an intention; on expiry, drop it. Serialize.

## Steps to verify

1. In the app, offer a character a mission, then accept it.
   - expected: an intention appears, tied to the mission, in the 🧠 Mind panel (`InspectorMindView`).
   - observed: TODO
2. Refuse a mission.
   - expected: no intention is spawned.
   - observed: TODO

## Acceptance

- [ ] An obligation can be accepted, altered, refused or forgotten.
- [ ] Accepting spawns an intention; the mission is the record.

## Files

- `engine/goals.py`
- `engine/serialization.py`
