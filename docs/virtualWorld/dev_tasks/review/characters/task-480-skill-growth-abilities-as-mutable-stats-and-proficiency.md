---
type: task
status: review
area: characters
priority: low
---

# task-480: Skill growth, abilities as mutable stats, and proficiency

**Filed:** 2026-09-23
**Related:** task-472, task-474

## Goal

Give characters a progression model: use-based skill advancement (rolling a skill can raise it), abilities as mutable stats changed by play, and an optional proficiency term so the sheet expresses trained + ability separately. Also define setting skill packs so a new setting can grant its own skills to the relevant characters on top of the base list.

## Acceptance

- [ ] **Setting skill packs:** `data/library/skill_packs.json` +
  `engine/skill_progress.py`; `apply_pack` raises skills only toward the pack
  value (idempotent, never lowers unless asked) and `validate` flags unknown
  skills, non-positive values and over-cap values.
- [ ] **Proficiency:** an optional, separate term (`player.proficiency`, default
  0) merged into `engine/checks.skill_modifiers` as a `proficiency` source, so
  the sheet expresses trained value and proficiency independently; 0 is exactly
  the pre-task-480 result (task-472 left the term out).
- [ ] **Use-based advancement:** `record_use` counts *successful* uses, raises
  the skill at the threshold, resets the counter on a raise, caps at `MAX_SKILL`,
  and ignores failures.
- [ ] **Opt-in:** `SkillSystem.skill_check` grows a skill only when the world
  sets `skill_growth`; the threshold is configurable; with no world (or the flag
  off) nothing changes, so no existing save or soak moves.
- [ ] **Abilities as mutable stats:** the `adjust_stat` effect trains or drains
  a core ability in play, clamped to [1, 30], reusing the player's existing key
  casing, and ignoring unknown stats.
- [ ] **Persistence:** `proficiency` and `skill_progress` serialize and load.
- [ ] Deterministic; no LLM.

## Progress — 2026-09-24

Implemented and tested; moving to review.

- **`data/library/skill_packs.json`** (new) + **`engine/skill_progress.py`** —
  `apply_pack` / `proficiency_bonus` / `record_use` / `growth_enabled` /
  `growth_threshold` + `validate`.
- **`player.py` / `engine/serialization.py`** — `proficiency` (default 0) and
  `skill_progress` (default `{}`) fields, serialized and restored.
- **`engine/checks.py`** — proficiency merged into the one modifier pipeline as
  its own source (default 0 ⇒ no change).
- **`engine/skills.py` / `virtual_world_engine.py`** — `SkillSystem` takes an
  optional `game_state`; `skill_check` grows the skill only behind
  `skill_growth`, logging the improvement. Existing two-arg constructions are
  unaffected.
- **`engine/effect_handlers/vitals.py`** — new `adjust_stat` effect registered in
  the dispatch map.
- **`tests/test_skill_progress.py`** (17) — pack apply/idempotence/validate,
  proficiency inert-by-default and in the breakdown, growth threshold/failure/
  cap, opt-in on/off and no-world, and `adjust_stat` clamping/casing/unknown.

Remaining for this task: authoring follow-ups only — a scenario would set
`skill_growth` and apply packs on load, and richer pack vocabulary is data.
