---
type: task
status: done
area: characters
priority: high
---

# task-474: Full skill list on the base sheet

**Filed:** 2026-09-23
**Related:** task-472, task-471

## What

Every skill in the vocabulary lives on Player.skills so a setting or character can grant/train any of them; specialist skills (Arcana, History, Religion, Nature, Investigation, Medicine, Insight, Deception, Intimidation, Performance, Animal Handling, Sleight of Hand) default to 0 and the six adventuring basics stay at 1. Save/load and library character definitions merge over the defaults instead of replacing the dict, so an older save or a sparse library entry still ends up with the full sheet.

## Acceptance

- TODO

## Progress 2026-09-23 - landed (review)

- [x] The base sheet carries the full 18-skill vocabulary: six adventuring basics at 1 (Athletics, Acrobatics, Stealth, Perception, Survival, Persuasion) and twelve specialists at 0.
- [x] Save/load (`engine/serialization.py`) and library character definitions (`engine/effects.py`) MERGE over those defaults instead of clobbering the skills dict.
- [x] Abilities live in `player.stats` (STR/DEX/CON/INT/WIS/CHA, default 10) with `ability_mod = (score-10)//2`, supplied by task-472.

## Steps to verify

`python -m pytest tests/test_skills.py -q` -> passed (including the 62 pre-existing exact-math/message assertions); 289-passed soak/timeskip/checks/conditions slice.

## Why

TODO

## Skills are free strings (2026-10-15, crafting schema)

Skill names are NOT a closed enum. `player.skills` is a plain dict; `skill_check` reads `skills.get(name, 0)` and `engine/checks.py` `SKILL_ABILITY` maps known names to abilities while unknown names key off no ability (modifier 0) — homebrew names work with no code change. The 18 D&D names on the base sheet are defaults, not the vocabulary. Settings and recipes may mint `Cooking`, `Smithing`, `Woodcraft`, `Leatherwork`, etc.; they default to 0 until a scenario, library character, or `teach` action grants them. Recipe authors: use the name that reads right, and note the grant source.

## How

TODO

## Files

- TODO
