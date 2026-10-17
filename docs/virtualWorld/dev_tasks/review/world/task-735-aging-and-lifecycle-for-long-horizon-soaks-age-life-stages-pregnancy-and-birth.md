---
type: task
status: review
area: world
priority: medium
related: ['task-670', 'task-733', 'task-685', 'task-846', 'task-295', 'task-537']
---

# task-735: Aging and lifecycle for long-horizon soaks: age, life stages, pregnancy and birth

**Filed:** 2026-10-08
**Related:** task-670, task-733, task-685

<!-- deps:start -->
**Related:** [[task-670-one-human-timeskip-soaks-the-whole-cast-not-just-the-ordering-character]], [[task-733-character-sheet-a-full-page-worldgraph-style-person-form-that-compiles-into-viwo-primitives]], [[task-685-memory-dynamics-memories-that-reinforce-fade-contradict-and-change-the-character]], [[task-846-pregnancy-gestation-and-birth]], [[task-295-spawn-character-trigger-effect]], [[task-537-spell-effect-and-condition-catalogue-review-list]]
<!-- deps:end -->

## What

Make a 10-year soak credible: a character has an age that advances with sim time (birth tick + elapsed), passes through life stages, and can conceive, gestate and bear children, with the offspring becoming real characters. This is the clock and demographics a long-horizon simulation needs, not just two fields.

## Grounding (measured 2026-10-07)

- A ViWo character has `size` and `species` (`player.py:280-288`) but **no `age`**
  and **no pronoun**.
- There is **no aging mechanic**. The only `age` in the tree is `age_effect`
  (task-537), which is a spell effect, not lifecycle.
- Time advances via timeskip and the soak (`docs/design/long-horizon-simulation-progress.md`,
  task-670). So a 10-year soak currently changes nothing about who ages, who can
  bear children, or who dies of old age.

## Built 2026-10-16 (this pass)

- `engine/lifecycle.py` (new): birth_tick resolution (authored age → date,
  once), effective age (species rate, goblin 3x per race bible), stages,
  species lifespans, annual probabilistic mortality, `on_clock` hook,
  `status()` read model. Clock = `world.time_ticks` (the sim clock;
  TickManager is constructed with the world in that seat).
- Wiring: `birth_tick`/`life_stage`/`last_mortality_year` on Player,
  serialized in saves, stripped from scenario files; `on_clock` runs
  in `advance_clock` (turns, ticks, timeskips, rest); `advance_age`
  effect shifts the birth tick too; `GET /record` serves `lifecycle`
  status for prompts.
- `tests/test_lifecycle.py`: 9 tests (resolution-once, thresholds,
  transition events, mortality gating/yearliness, clock hook,
  advance-age agreement, save round-trip).
- Open design questions answered: age is runtime (birth tick on the
  Player) with authored age resolving once; year length from the
  calendar config (default 360d).

## How

`age` only means something with a clock. The system:

- **Age** — a birth tick (or an authored starting age resolved to a birth tick
  from the world's current date), so `age = elapsed / year`. Advances with sim
  time, not wall time.
- **Life stages** — child / adolescent / adult / elder, gating behaviour,
  capability and fertility. Feeds prose and prompts (task-733's `age` field).
- **Fertility + pregnancy** — conception given willingness, fertility by stage,
  gestation over sim time, birth, and the outcome (a child) becoming a real
  character (spawn-character, task-295) placed at the parent's location.
- **Death by age** — lifespan by species, so a 10-year soak actually loses people.

This is a demographics/lifecycle layer over the background simulation, not two
fields. `pronouns` (task-733) is the prose side and is trivial by comparison.

## Scale note

A 10-year soak with the now-permanent memory model is its own problem: memories
are never trimmed (task-727/lived-log work), so a decade of events is a large
per-character memory set. Aging/pregnancy must not add another unbounded store
per character.

## Open questions

- Is `age` a definition field (authored) or runtime (birth tick + elapsed)? The
  answer decides whether it lives on the node (task-724) or the Player.
- Does the world have a real calendar/date, or only `time_ticks`? Aging needs a
  year length.
- Pregnancy, birth, and child characters are a large content surface (do children
  get behaviours/plans?). Confirm scope before building.

## Acceptance

- [x] A soak advances a character's age; life stage changes at defined thresholds.
  (`engine/lifecycle.py`: birth_tick + elapsed sim time; child/adolescent/adult/elder; transitions emit turn events. 9 tests in `tests/test_lifecycle.py`.)
- [ ] Fertility/willingness can result in pregnancy → gestation → birth over sim
  time, and the child exists as a character afterwards.
  (Split to task-846 — consent-gated system of its own, not clock work.)
- [x] Death by old age is possible.
  (Annual probabilistic roll past species lifespan via `world.kill_player`; bounded to one roll per game-year.)
- [x] `age` and `pronouns` are available to prose/prompts.
  (Authored age resolves to a birth tick once; `lifecycle.status()` read model served on `GET /record`; pronouns explicit-first.)
- [x] No additional unbounded per-character store is introduced.
  (Three scalars: birth_tick, life_stage, last_mortality_year. Serialized in saves, stripped from scenario files.)
- [x] Live: run a timeskip across a life-stage threshold and observe the change.
  (2026-10-16 live on :4444: Arix null → age 12/child via PUT,
  date jump year 1→7 → age 18/adult in `GET /record lifecycle`;
  reverted after (DELETE + year restore). Two fixes fell out:
  `set_game_date` now runs `on_clock` (date jumps are time travel),
  and DELETE clears derived clock state (prose-only is fully
  prose-only again). Both backend-tested; live re-verify on restart.
  Note: live Arix still carries the pre-fix birth_tick (invisible,
  resolves on next restart + DELETE).)

## Why

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: select a character → Character Inspector/Bio for age and pronouns; after a long timeskip, reopen Mind/Bio and inspect life stage, pregnancy, birth, and any age-related death events.

Current availability: age/life-stage transitions, fertility, gestation, birth, and old-age death are proposed for long-horizon simulation. Age and pronouns are not claimed as a complete lifecycle mechanic by this card.

Live steps when available:
1. Create a scratch character just before an authored life-stage threshold and record age, birth tick, pronouns, and current life stage in Bio and `/api/state`.
2. Advance simulation time across the threshold using a timeskip, then reopen Bio and inspect the event stream and prompt context.
   - expected: age advances from elapsed simulation time and the life stage changes at the documented threshold; pronouns and age are available to prose/prompt generation.
3. Run a controlled fertility/gestation sequence across the authored duration.
   - expected: pregnancy and birth are visible as events and the child is a real character node with a valid location and private Player state.
4. Advance an elderly character through the old-age mortality check.
   - expected: death can occur through the documented age rule and appears in the character's existing life/memory surfaces.
5. Inspect saved state size across the long run.
   - expected: lifecycle tracking uses bounded existing character state and does not create an unbounded per-character event store.

This section is not a claim that the lifecycle system is implemented today.
