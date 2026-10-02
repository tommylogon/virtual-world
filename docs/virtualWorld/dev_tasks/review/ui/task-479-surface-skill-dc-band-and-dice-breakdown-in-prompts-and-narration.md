---
type: task
status: review
area: ui
priority: medium
---

# task-479: Surface skill, DC band and dice breakdown in prompts and narration

**Filed:** 2026-09-23
**Related:** task-472, task-475

## Goal

Show the player what they are rolling and how it went: the skill, the DC band, advantage/disadvantage and the d20 breakdown in the prompt and narration, plus why an auto-fail happened and what could be found in a given area (a light hint), so checks are legible rather than hidden numbers.

## Acceptance

- [x] A check line names the **skill**, the **DC band**, the **d20 breakdown**
  (`roll=R + mods = total => tier`) and the **advantage/disadvantage mode**.
  (`SkillSystem.skill_check` / `saving_throw`, `checks.resolve`.)
- [x] Advantage/disadvantage names the **condition** that caused it
  (`[advantage: keen_senses]`), instead of a bare `[advantage]` that a blinded
  and a focused archer both produce.
- [x] An **auto-fail names the responsible condition**
  (`AUTO-FAIL (a condition prevents it: paralysed)`), for both checks and saves.
- [x] The breakdown reaches the **prompt**: `PromptBuilder.summaryLine` (the
  `=== RECENTLY ===` line) now keeps a `[Skill Check]` / `[Save]` / `[Check]` /
  `[Grab]` line even when it is not the first line of a multi-line result, so
  the model can narrate *why* an outcome happened.
- [x] Existing message contracts are **not weakened**: `test_checks.py`'s
  "breakdown shows values, not sources" assertion still holds (modifier sources
  stay out of the roll math); the 62 skill-message assertions still pass.
- **"What could be found in a given area"** is `foraging.findable_hint()`
  (task-483), which already exists and owns its own HUD-display task; this task
  does not duplicate it.

## Verification (2026-10-02)

Engine (mechanism + regression):

```
python -m pytest tests/test_checks.py tests/test_skills.py tests/test_conditions.py -q
  -> 140 passed
python -m pytest tests/test_ghost.py tests/test_grapple.py -q
  -> 66 passed
```

New assertions: `condition_sources` names `focused`/`dazed`;
`AUTO-FAIL … test_fail` in `resolve`; `[advantage: focused]`;
`AUTO-FAIL … paralysed` in `saving_throw`.

Prompt surfacing (JS units):

```
node tools/unit/run.cjs -> 491 passed, 0 failed (35 test files)
```
`tools/unit/test_turn_prompts.js` pins `summaryLine` keeping a check line from
any position, recognising `[Skill Check]`/`[Save]`/`[Check]`/`[Grab]`.

Live deploy check (`VW_PORT=4463`, Playwright):

```
SUMMARY_LINE_TYPE function
SUMMARY_LINE_DEMO
  "[Skill Check] Investigation vs DC 12 (medium): roll=18 + 2 = 20 => success — You search the debris."
POST /api/action {character, command:"search"} -> 200
  "You search the room thoroughly but find nothing hidden."
```

## Files

- `engine/checks.py` — `condition_sources`, richer `resolve` message.
- `engine/skills.py` — named advantage/auto-fail reason in `skill_check` /
  `saving_throw`.
- `engine/conditions.py` — `auto_fail_save_sources`.
- `static/js/agent/prompt-builder/turn-prompts.js` — `summaryLine` keeps a check
  line from any position; exported as `PromptBuilder.summaryLine`.
- `tests/test_checks.py`, `tests/test_skills.py`, `tools/unit/test_turn_prompts.js`,
  `tools/unit/run.cjs`.

