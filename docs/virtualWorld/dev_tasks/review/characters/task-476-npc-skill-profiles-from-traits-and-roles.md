---
type: task
status: review
area: characters
priority: medium
---

# task-476: NPC skill profiles from traits and roles

**Filed:** 2026-09-23
**Related:** task-472, task-474, task-475, task-213

## What

Make checks differ per character without an LLM: role/trait skill biases (hunter -> Survival/Nature/Animal Handling, guard -> Perception/Insight/Intimidation, thief -> Sleight of Hand/Stealth, healer -> Medicine/Insight, scholar -> History/Religion/Arcana, smith -> Athletics/craft), feeding the existing TraitSystem.get_skill_check_mods seam so a goblin trapper out-forages a child in the same wood.

## Acceptance

- [ ] `data/library/roles.json` defines `role -> skill biases` (hunter, trapper,
  guard, thief, healer, scholar, smith, cook, farmer, scout, merchant, ...), each
  naming skills that exist in `engine/checks.SKILL_ABILITY`.
- [ ] `engine/roles.py` loads it, resolves a character's roles from the existing
  **namespaced tag** `role:<id>` (the `faction:guard` precedent — no new Player
  field, no serialization change), and returns additive per-skill mods. A
  character with no `role:` tag is unchanged, so existing behaviour is
  preserved until a data pass authors roles.
- [ ] Role mods flow through the one modifier pipeline
  (`engine/checks.skill_modifiers`), so `skill_check`, `resolve` and `opposed`
  all see them; they appear in the breakdown with source `role` and are the only
  new source (no second check path).
- [ ] Proof: same area, same roll and stats — a `role:trapper` character
  out-forages a roleless child on Survival, and a `role:guard` beats a
  `role:cook` on Perception.
- [ ] Data-only extension: adding a role is a JSON edit; `validate()` flags
  unknown skills, missing names and empty bias maps.
- [ ] Deterministic: role mods never use RNG or an LLM, and a hand-authored
  `role:` tag survives save/load through the existing tag serialization.

## Progress — 2026-09-24

Implemented and tested; moving to review.

- **`data/library/roles.json`** (new) — 13 roles (hunter, trapper, fisher,
  guard, scout, thief, healer, scholar, smith, cook, farmer, merchant, miner,
  performer) mapping to real `checks.SKILL_ABILITY` skills.
- **`engine/roles.py`** (new) — `load` / `roles` / `role` / `character_roles` /
  `skill_mods` / `validate`. Roles resolve from the namespaced `role:<id>` tag
  (the documented `faction:guard` shape), so a bare `cook`/`farmer` tag stays
  inert and **no existing character's checks change** until a data pass authors
  roles. No new Player field, no serialization change.
- **`engine/checks.py`** — `skill_modifiers` merges `roles.skill_mods(player)`
  as a `role` source, so `skill_check`, `resolve` and `opposed` all see it in one
  pipeline.
- **`tests/test_roles.py`** (15) — shipped table validates clean; bare tags
  inert; `role:` resolution is case-insensitive and additive across roles;
  unknown roles ignored; the `role` source appears in the breakdown; and the
  proof — a `role:trapper` out-forages a roleless child on Survival and a
  `role:guard` beats a `role:cook` on Perception, same roll and stats.
- Full suite: 61 failed / 3560 passed — the 61 are the documented pre-existing
  failures; no new ones. Related suites (checks/skills/traits/foraging/backsim/
  social/promotion, 212 tests) pass.

Remaining for this task: the authoring data pass that puts `role:` tags on the
cast (a scenario/library edit per character, deferrable) — the *mechanism* and
its acceptance are complete.

## Why

TODO

## How

TODO

## Steps to verify

1. Run `python -m pytest tests/test_roles.py`, then inspect the two fixed-roll
   comparisons in the test output: `role:trapper` versus roleless on Survival,
   and `role:guard` versus `role:cook` on Perception.
   - expected: both role sources appear in the one modifier breakdown and the
     role-tagged character wins the authored comparison.
   - observed (card record, 2026-09-24): 15 role tests passed; the cast-level
     role-tag authoring pass remains deferred.
2. In the intended browser flow, load a disposable scenario with those same
   role tags and issue `find Survival` and the Perception check from the Game
   command input.
   - expected: the event stream shows the `role` modifier for tagged
     characters and no role modifier for the roleless child.
   - observed: no browser E2E is recorded; the fixed-roll mechanism is covered
     by the targeted test above.

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Character Inspector → Bio → Skills for authored skill values;
Game command input → `find Survival` → event stream for the role-aware check.

Current availability: The role modifier pipeline is implemented and the card
records 15 passing `tests/test_roles.py` cases. Cast role tags have not been
authored as part of this task, so use a disposable fixture with explicit
`role:trapper` / `role:guard` tags; do not infer that the shipped cast exercises
the rule.

Live steps when available:
1. Load a scratch scenario with a role-tagged trapper and a roleless child in
   the same forage area. Run `find Survival` for each and inspect the event
   stream's check breakdown.
   - expected: the trapper's breakdown includes the `role` modifier; the
     roleless character has no role modifier, and both use the same forage
     action path.
2. Load a second scratch pair tagged `role:guard` and `role:cook`, then run
   `search` for each so both make the existing Perception check.
   - expected: the breakdown names `role` as the modifier source and the guard
     receives the authored Perception bias; no roleless character changes.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
