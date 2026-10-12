---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704, task-691, task-714]
blocked_by: [task-800]
---

# task-806: Split traits (capabilities) from personality (decision dials)

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]], [[task-691-memory-mind-interface-dynamics-badges-connections-per-person-profiles-dashboard]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Two homes, two roles: traits keeps capabilities and hooks (dark_vision, hardy, phobias); a NEW personality key holds the 0..1 decision dials. Migrate the personality-ish existing traits.

## Why

The catalogue wants normalized floats but player.traits[tid] is True|str|number, and the personality field is a prose string - three things wearing the name. Separate them or they collide.

## How

Add a personality map (distinct key from the prose personality). Extend engine/traits.py so a trait can be a capability, a dial, or both. Migrate cowardly/patient/curious/etc.

## Steps to verify

1. In the graph editor's character form, edit a character's personality dials beside their prose.
   - expected: the dials save and reload separately from the prose personality string, with no collision.
   - observed: TODO
2. In the 🧠 Mind panel (`InspectorMindView`) for that character.
   - expected: both the prose and the numeric dials are shown.
   - observed: TODO

## Acceptance

- [ ] traits holds capabilities; personality holds dials.
- [ ] The prose personality string is untouched.
- [ ] Existing characters load unchanged (dials default to neutral).

## Files

- `engine/traits.py`
- `engine/serialization.py`
- `player.py`
