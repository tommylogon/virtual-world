---
type: task
status: review
area: refactor
priority: high
---

# task-472: Central dice and check resolution

**Filed:** 2026-09-23
**Related:** task-471, task-470, task-468, task-159

## Goal

One place that answers what to roll, what modifies it, and how good the result is. Dice expressions, d20 with advantage/disadvantage (both cancel), the six ability scores and the skill->ability map, one auditable modifier pipeline (ability mod + skill/stat + traits + condition effects), degrees of success and criticals, opposed checks, and named DC bands. Call sites stop re-inventing pieces; SkillSystem.skill_check/saving_throw become thin adapters keeping their old tuple/message format, and skill checks finally include the ability modifier.

## Acceptance

- TODO

## Progress 2026-09-23 — landed (review)

`engine/checks.py` + `tests/test_checks.py`; `SkillSystem` now delegates.

- [x] **Dice**: `roll_dice`, `parse_dice` (`"2d6+3"`, `"d20"`, flat `"4"`), `roll`,
      and `roll_d20` with **advantage/disadvantage** (two d20, keep high/low; both
      cancel). An injectable `roll_fn` keeps `SkillSystem.roll_dice` patchable.
- [x] **Abilities**: `ability_mod` (`(score-10)//2`, never clamped), `STAT_NAMES`,
      `SKILL_ABILITY` (the 5e skill→ability map, 18 skills), `SKILL_NAMES`.
- [x] **Modifier pipeline**: `skill_modifiers` / `save_modifiers` collect ability
      mod + skill/stat value + trait mods into one auditable list; `resolve(...)`
      adds arbitrary extras with their sources.
- [x] **Conditions feed the roll**: a condition definition may carry
      `check_advantage`, `check_disadvantage` or `auto_fail_checks` naming skills,
      abilities or `"attack"`/`"*"` (with aliases: dexterity→DEX, sight/hearing→
      Perception, willpower/concentration/self_control→WIS). `restrained` now
      actually gives attacks disadvantage, as its description always claimed.
- [x] **Outcomes**: `success`/`fail`, `strong_success` (margin ≥ 5),
      `crit_success`/`crit_fail` on a kept 20/1, and `auto_fail`. `dc_band`
      preserves the legacy labels; `DCS` gives named DCs.
- [x] **Opposed checks**: `opposed(a, b, kind=...)` with ties to the defender —
      the shape theft-vs-Perception and social-vs-Insight need.
- [x] **Adapters**: `SkillSystem.skill_check` / `saving_throw` keep their
      `(success, total, message)` tuple and message format, so all existing call
      sites (combat, movement, crafting, ghost, triggers, items) gained ability
      mods + condition advantage + auto-fail for free. `tests/test_skills.py`'s
      62 exact-math/message assertions still pass unchanged.

## Remaining

- [ ] Migrate combat (`engine/combat.py`) and grapple onto `resolve`/`opposed`
      so attack rolls get advantage from conditions too.
- [ ] Use `DCS`/`dc_band` at the remaining hardcoded call sites (ghost/movement
      still pass literal 15s).
- [ ] Surface the skill+band and the d20 breakdown in the player prompt/narration.
- [ ] Optional: the six abilities are currently read but never *changed* by play;
      no proficiency term yet (the skill value is the trained number).

## Verification

`python -m pytest tests/test_checks.py tests/test_skills.py -q` → 63 passed.
Targeted checks/skills/conditions/foraging/movement/grapple → 241 passed.

Also fixed a soak flake found here: `engine/foraging._candidate_entries` now
restricts candidates to entries satisfying `want_tags`, so a food search cannot
spawn a herb the character then cannot eat (15/15 repeat runs clean).
