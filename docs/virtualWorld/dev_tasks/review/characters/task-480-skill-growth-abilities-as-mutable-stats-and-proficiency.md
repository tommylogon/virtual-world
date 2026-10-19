---
type: task
status: review
area: characters
priority: low
related: ['task-476', 'task-519']
---

# task-480: Skill growth, abilities as mutable stats, and proficiency

**Filed:** 2026-09-23
**Related:** task-472, task-474

<!-- deps:start -->
**Related:** [[task-476-npc-skill-profiles-from-traits-and-roles]], [[task-519-character-starting-loadouts-from-the-item-library]]
<!-- deps:end -->

## What

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

## Progress - 2026-09-24

Implemented and tested; moving to review.

- **`data/library/skill_packs.json`** (new) + **`engine/skill_progress.py`** -
  `apply_pack` / `proficiency_bonus` / `record_use` / `growth_enabled` /
  `growth_threshold` + `validate`.
- **`player.py` / `engine/serialization.py`** - `proficiency` (default 0) and
  `skill_progress` (default `{}`) fields, serialized and restored.
- **`engine/checks.py`** - proficiency merged into the one modifier pipeline as
  its own source (default 0 ⇒ no change).
- **`engine/skills.py` / `virtual_world_engine.py`** - `SkillSystem` takes an
  optional `game_state`; `skill_check` grows the skill only behind
  `skill_growth`, logging the improvement. Existing two-arg constructions are
  unaffected.
- **`engine/effect_handlers/vitals.py`** - new `adjust_stat` effect registered in
  the dispatch map.
- **`tests/test_skill_progress.py`** (17) - pack apply/idempotence/validate,
  proficiency inert-by-default and in the breakdown, growth threshold/failure/
  cap, opt-in on/off and no-world, and `adjust_stat` clamping/casing/unknown.

Remaining for this task: authoring follow-ups only - a scenario would set
`skill_growth` and apply packs on load, and richer pack vocabulary is data.

## Why

Skills were completely static, preventing characters from improving proficiencies through practice and repeated successful actions.

## How

Added `skill_growth` toggle, tracking per-skill attempt/success counters and advancing proficiency when threshold curves are met.

## Steps to verify

1. Run `python -m pytest tests/test_skill_progress.py` and review the cases for
   pack idempotence, zero proficiency, successful-use thresholds, failed-use
   handling, caps, opt-in, and stat adjustment.
   - expected: progress advances only on successful checks with growth enabled;
     proficiency 0 adds no modifier and invalid stat adjustments are ignored.
   - observed (card record, 2026-09-24): 17 focused skill-progress tests
     passed; the task's setting-authorship follow-up remains.
2. In a disposable scenario with `skill_growth` enabled, use `find Survival`
   until one character reaches the configured threshold; then inspect Bio →
   Skills and the event stream.
   - expected: the skill value rises once, the improvement is logged, and the
     progress counter resets; a failed check does not advance it.
   - observed: no browser run is recorded; the mechanism is currently verified
     by the focused test module.

## Files

- `engine/skills.py`
- `models/player.py`
- `tests/test_skill_progress.py`

## Browser UI and intended live verification

Intended UI home: Character Inspector → Bio → Skills for the skill value;
Game command input → `find Survival` → event stream for the roll and growth
message.

Current availability: Skill progression and proficiency are implemented and
covered by `tests/test_skill_progress.py`. The inspector currently displays
numeric skills, but this card does not claim that it displays `proficiency` or
the per-skill progress counter. Use a disposable scenario with
`skill_growth: true` and a low test threshold; the default path remains
unchanged when growth is off.

Live steps when available:
1. Load that fixture with one character below the Survival cap and an area
   where `find Survival` succeeds. Record the displayed Survival value, run
   successful `find Survival` checks until the configured threshold is reached,
   then reopen the character's Skills section.
   - expected: the character's Survival value increases once, the event stream
     reports the growth, and the progress counter resets at the raise.
2. Repeat one failed `find Survival` check, then load the same fixture with
   `skill_growth` disabled and run a successful check.
   - expected: a failed check does not advance progress; with growth disabled,
     neither the skill value nor progress changes.
3. Inspect the roll breakdown for a character with proficiency 0 and one with
   a non-zero proficiency value.
   - expected: zero proficiency adds no modifier; the other character shows a
     separate `proficiency` source in the same check breakdown.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
