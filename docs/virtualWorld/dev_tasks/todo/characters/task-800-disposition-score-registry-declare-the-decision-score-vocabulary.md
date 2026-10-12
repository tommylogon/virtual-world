---
type: task
status: todo
area: characters
priority: high
wiki: "[[Character Pursuits]]"
related: [task-704, task-691, task-714]
blocked_by: [task-799]
---

# task-800: Disposition score registry: declare the decision-score vocabulary

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-799-disposition-spike-do-three-unrelated-soak-decisions-fit-one-score-registry]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

One module declares every decision score the disposition reads: its name, kind (utility / multiplier / threshold / salience), base value and range. This is the shared currency that traits, needs, emotion, memories, obligations and GIMP's goal all write into.

## Why

The 200-modifier catalogue named scores that do not exist in the code. Until each score declares a kind, base and range, 'add_delta' is ambiguous and 'clamp to the declared range' is undefined.

## How

Create engine/disposition.py owning the registry as a single declaration, in the manner of tools/way_properties.py. Add a --check gate (tools/disposition_index.py) so a card referencing an unknown score fails. Seed from task-799's spike.

## Steps to verify

1. Registry gate: a modifier names a score that is not declared.
   - expected: `python tools/disposition_index.py --check` fails, naming the unknown score.
   - observed: TODO
2. In the app, open the 🧠 Mind panel (`InspectorMindView`) for any character.
   - expected: the character's decision scores are listed, each with its kind, base and range from the registry.
   - observed: TODO

## Acceptance

- [ ] Every score has a declared kind, base and range.
- [ ] A --check tool flags references to undeclared scores.

## Files

- `engine/disposition.py`
- `tools/disposition_index.py`
