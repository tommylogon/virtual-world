---
type: task
status: cancelled
area: characters
priority: medium
horizon: next
goal: A relationship can carry a typed role, and a character can hold a relation to a group or faction, not only to another person.
wiki: "[[Persona]]"
related: [task-865, task-619, task-729, task-742]
---

# task-866: Relationships: a typed role, and relations to groups and factions

**Filed:** 2026-10-18
**Related:** task-865, task-619, task-729, task-742

<!-- deps:start -->
**Related:** [[task-865-rename-the-persona-block-key-from-appearance-to-persona]], [[task-619-relationships-stored-in-two-shapes-in-one-field-keyed-by-display-name]], [[task-729-move-relationship-emotional-state-and-memory-add-edit-generate-controls-into-the-mind-panel]], [[task-742-faction-scoped-hostility-and-group-aware-fear-wire-or-retire-the-hostile-trait]]
<!-- deps:end -->

## What

An authored relationship store already exists. `player.relationships[other] = {closeness, last_interaction_tick, interaction_count, label, first_sighting}` (`engine/relationships.py:1-11`) is serialized (`engine/serialization.py:200`, read back at `:499`), and it is edited from the Mind panel People tab (task-729, the "authored store") with a closeness slider, a free-text `label` ("my brother") and a "knows name" checkbox. So "can I author a relationship to a person" is already yes.

What is genuinely missing:

1. A **typed role**. "Who they are to each other" is a free-text `label`, so nothing can read "this is my father" reliably: there is no controlled vocabulary, no reverse side, no family tree.
2. **Group and faction relations.** A relationship is per-character-pair only; there is no way to say "A is loyal to `faction:goblin`" or "A is at war with the guard". A faction is a `faction:<name>` tag (`engine/ownership.py`), and nothing links a character to it as a relation.

## Why

Setting up families, friends and enemies, to people and to factions/groups, is the ask. The person half exists but is unstructured (free text), and the group half does not exist at all. A typed role is what turns a label into something a reader (prompt, fear, social, family tree) can act on; a group relation is what makes faction allegiance more than a flat tag.

## How

1. Add a `relation` type to the existing relationship record, from a controlled vocabulary (parent / child / sibling / partner / friend / rival / enemy, plus `other` with a note). Decide whether a pair is stored once (a mutual edge) or per side; the store is currently per side keyed by the other's name.
2. Keep `label` as free text for what the type does not cover; the type is the machine-readable half.
3. Add a group/faction relation: a relation from a character to a `faction:<name>` target, with its own small vocabulary (member / ally / enemy / leader, ...). Decide the runtime meaning (bias every member's closeness, or prompt-context only) and record it.
4. Do not build a second relationship store. `player.relationships` stays the store; a typed role is a field on it, a group relation is either the same store keyed by the group tag or a small parallel list, decided in this card.
5. Surface both in the Mind panel People tab (the existing editor, task-729) and read them in the agent prompt.
6. Round-trip: roles and group relations survive a scenario save / load.

## Browser UI and intended live verification

Mind panel -> People tab (the existing relationship editor, task-729). Live steps: set a typed role on an existing relation (A -> B = sibling); add a group relation (A -> `faction:goblin` = enemy); confirm a reader (prompt / social) consumes them; save and reload.

## Steps to verify

1. Set a typed role on an existing person relation.
   - expected: the role persists and a reader can name it.
   - observed: TODO
2. Add a relation to a group/faction.
   - expected: it persists and a reader consumes it.
   - observed: TODO
3. Save and reload the scenario.
   - expected: both survive.
   - observed: TODO

## Acceptance

- [ ] A relationship carries a controlled `relation` type alongside the free-text `label`.
- [ ] A character can hold a relation to a group/faction, not only to another character.
- [ ] `player.relationships` remains the single store; no second relationship model.
- [ ] `engine/relationships.py` (`apply_relationship_delta`) remains the only writer of `closeness`.
- [ ] Both round-trip a scenario save / load.
- [ ] Open decision recorded: the runtime meaning of a group relation (bias members, or prompt-context only).

## Files

- `engine/relationships.py`
- `engine/serialization.py`
- `routes/player_ops.py`
- `static/js/inspector/mind-view.ts`
- `tests/test_relationships.py`

## Retracted 2026-10-18

Duplicate of `task-733` (character sheet), which already enumerates the relationship vocabulary (`family{parents,siblings,children,other} connections friends enemies rivals mentors protégés`) and maps `relationships.*` to `relationships` (label + closeness). The store shape is `task-619`; the group/faction relation and its authoring UI are `task-742`.

Two deltas survive and are folded into `task-733`: a machine-readable `relation` type on the relationship record, and a relation target that may be a group or faction tag rather than only a character.
