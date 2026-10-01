---
type: task
status: todo
area: docs
priority: medium
---

# task-664: Rename @powers prose to Feature Map feature names so the two vocabularies join

**Filed:** 2026-10-01
**Related:** task-663

## Goal

tools/feature_index.py joins each module's @powers against docs/virtualWorld/Feature Map.md and reports the honest result: of 156 modules, 68 name a feature and 88 name none, and 32 of the 58 features have no module naming them. The cause is a vocabulary mismatch, not absent effort - the headers are gerund phrases ('keeping and restoring your world', 'seeing and changing what a character is wearing') and the map is noun phrases ('Save / load', 'Wear / equip'). The 88 are baselined so the gate is green and ratchets. Two ways to close it: rewrite the headers to name features from the map (a 156-file sweep, mechanical but wide), or publish the feature names as a controlled vocabulary and have the map and the headers both use it. Either way the join should reach most modules, and the features nothing claims should be reviewable - a feature no module names may be a feature nobody can reach.

## Acceptance

- TODO
