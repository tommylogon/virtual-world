---
type: task
status: cancelled
area: characters
priority: medium
horizon: next
goal: An imported skill lands on an existing skill id where one exists; a new id is a decision, not an accident.
wiki: "[[Persona]]"
related: [task-865, task-476]
---

# task-868: Map imported skills onto the existing skill ids

**Filed:** 2026-10-18
**Related:** task-865, task-476

<!-- deps:start -->
**Related:** [[task-865-rename-the-persona-block-key-from-appearance-to-persona]], [[task-476-npc-skill-profiles-from-traits-and-roles]]
<!-- deps:end -->

## What

`player.skills` is the numeric skill sheet. The import has no mapping, so a source skill string ("ASMR", "graph databases", "swordplay") is either dropped or becomes an arbitrary new id.

This card maps source skills onto the skill ids we already have, and treats free-text "things I am good at" as prose, not a new skill.

## Why

The import must prefer the existing vocabulary, or every file grows the skill list with synonyms. A free-text self-description is not a skill id; conflating them makes the sheet meaningless.

## How

1. Enumerate the existing skill vocabulary in one place and state the count; do not infer the set from one member (see the property-set rule in AGENTS).
2. Add a mapping (source name / normalised -> skill id) applied during import.
3. Add a new id only when a source skill is genuinely absent, and record it as a decision, not silently.
4. Free-text self-description stays a prose list in the personality block; it does not create ids.

## Browser UI and intended live verification

N/A for the mapping itself. Observable path: import a file whose skills name both a known skill and an unknown one, and confirm the sheet gains the mapped id while the unknown is reported, not invented.

## Steps to verify

1. Import a file with a known skill name.
   - expected: the matching sheet id is set.
   - observed: TODO
2. Import a file with an unknown skill name.
   - expected: it is surfaced for a decision, not silently added or dropped.
   - observed: TODO
3. Import a free-text strengths list.
   - expected: it lands as prose, not as skill ids.
   - observed: TODO

## Acceptance

- [ ] Source skills map to existing ids where one exists.
- [ ] Genuinely new skills are surfaced for a decision, not auto-added.
- [ ] Free-text skill prose stays prose.
- [ ] The mapping table is the single place the vocabulary is declared.

## Files

- `static/js/character-import.ts`
- `engine/skills.py`
- `tests/test_skills.py`

## Retracted 2026-10-18

Duplicate. Skills projection is `task-733` (`capabilities.skills` -> `skills`/`traits`), and the import mapping is `task-843`, which already reads `update_krakotooth_cards.py`'s field mapping and forbids a second one. A separate skills-mapping card would be exactly that forbidden second mapping. Folded into `task-733`/`task-843`.
