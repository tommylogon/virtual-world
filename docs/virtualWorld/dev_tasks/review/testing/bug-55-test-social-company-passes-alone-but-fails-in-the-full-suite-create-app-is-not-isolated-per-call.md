---
type: bug
status: review
area: testing
priority: medium
---

# bug-55: test_social_company passes alone but fails in the full suite (create_app is not isolated per call)

**Renumbered** 2026-09-28 from bug-54, which was already taken by the weather `WEATHER_LIGHT_MULT` bug in `todo/bugs/`.

**Filed:** 2026-09-27
**Fixed:** 2026-09-29
**Related:** task-551

## Goal

The second create_app() in a process does not behave like the first, so any test file running before test_social_company.py flips three of its seven assertions.

## Measured (2026-09-27, while baselining task-551)

Found by accident: my first full-suite baseline reported **59 failed**, and a run after a change reported **62**. The extra three were all `tests/test_social_company.py`. Re-run with my work stashed (`git stash push --include-untracked`) they still failed, so this is **pre-existing and order-dependent**, not a regression from any change.

Reproductions, all with `-p no:randomly` (so it is not seed order):

| Command | Result |
|---|---|
| `pytest tests/test_social_company.py` | 7 passed |
| `pytest tests/test_social_company.py tests/test_scenario_name.py` | 2 social_company failures |
| `pytest tests/test_social_company.py tests/test_character_identity.py` | 1 social_company failure |
| `pytest tests/test_social_company.py tests/test_templates.py` | 1 social_company failure |

So it is **not** one poisoning file. *Any* earlier `create_app()` call in the process is enough, which points at module-level state rather than a specific test.

The three that flip:

- `test_extrovert_alone_craves_company_more`
- `test_extrovert_company_gains_extra` — `assert extrovert > default` → `83 > 83`
- `test_introvert_alone_keeps_only_baseline`

### What the world looks like

Two `create_app({"TESTING": True})` calls in one process are *not* equivalent. `engine/tick_manager.py:518-537` is where the difference shows: the Social rate is `socail_mult * SOCIAL_COMPANY_GAIN`, and `social_mult` comes from `TraitSystem.get_first_effect(p, SOCIAL_GAIN)`.

Direct probe — identical script run twice in one process, one character plus one companion, 30 ticks:

```
first  tpm=5 social=90
second tpm=5 social=84
```

The two worlds are otherwise indistinguishable: 19 areas each, the same 19 names, `Kitchen` present in both, the same three players (`Kaelen Voss`, `Lyrie`, `rat`), and distinct `VirtualWorld` and `PlayerManager` objects. The leak is therefore in something neither the area list nor the roster exposes — a module-level cache, registry or counter reached from the tick path.

## What it actually was (2026-09-29)

**There is no module-level leak, and `create_app()` is not the problem. The tests were measuring a stochastic world.** Three probes, in order.

**1. Same seed, same answer, three times in one process.** Seeding `random` before each `create_app()` and re-running the filing's own probe gives identical results on every call:

```
seed=1:  first=79 second=79 third=79  agree=True
seed=7:  first=78 second=78 third=78  agree=True
seed=42: first=78 second=78 third=78  agree=True
```

Unseeded, the same script in the same process returns `[75, 79, 78, 98, 98, 79]`. So a second `create_app()` behaves exactly like the first once the dice are pinned — the "90 vs 84" gap was the dice, not a cache.

**2. The measured character is not alone, and never was.** `tests/test_social_company.py` places `Kaelen Voss` in `Blizzard Forest Clearing`, pushes the rest into `Kitchen`, and then runs 30 *full* turns via `world.tick_turn()`. A full turn also runs `npc_behaviors.process_simple_npcs()` and the background simulation (`engine/tick_manager.py:1047-1066`), and the cast wanders:

```
tick 0:  Social=83  alone_ticks=1   co_present=['Lyrie', 'rat']  positions=[Kaelen→Kitchen, ...]
tick 8:  Social=91  alone_ticks=7   co_present=['rat']           positions=[Kaelen→Upstairs Hallway, ...]
tick 15: Social=100 alone_ticks=2   co_present=['rat']           positions=[Kaelen→Upstairs Hallway, ...]
final Social: 100
```

The test's premise — *alone* — dies somewhere around tick 1, and which rooms the cast lands in is a draw. So the run returns 75 or 100 depending on the run, and the assertions that compare two separately-created worlds (`introvert > default`) compare a contaminated world against a clean one. Worse, `_alone_ticks` reads a value the engine owns, so the isolation bonus switches on and off mid-measurement. Every failure value is explicable this way: `83 > 83` is two equal 83s, `84 > 98` is a default that had company, `70 > 85` is an introvert that was alone and a default that was not.

**3. `skip_npcs=True` makes it deterministic.** Ticking with the existing seam (the same one `tests/test_area_major_ticks.py` uses) keeps the per-character decay block and drops the wander:

```
skip_npcs=True unseeded alone x6:            [72, 72, 72, 72, 72, 72]
skip_npcs=True unseeded introvert alone x6:   [78, 78, 78, 78, 78, 78]
skip_npcs=True unseeded default company x6:   [80, 80, 80, 80, 80, 80]
skip_npcs=True unseeded extrovert company x6: [83, 83, 83, 83, 83, 83]
```

Every assertion's premise now holds on every tick, and the ordering the tests care about is visible in the numbers: alone drains, an introvert drains slower, company is maintenance, an extrovert gains. `_run()` in `tests/test_social_company.py` is the one-line change; the engine needed no edit.

## The other half: `test_clearing_the_source_leaves_the_name_alone` is not this bug

`AGENTS.md` grouped it with bug-55 as `create_app()` isolation. It is not — it **fails in isolation** (`pytest tests/test_scenario_name.py` → 1 failed, 7 passed), and no leak is involved. `create_app()` boots with `_scenario_name == "world_template"`, and `set_scenario_source()` documents that an existing name beats the filename, so the test's `named_world` never takes. The same file asserts the opposite rule ten lines earlier in `test_an_existing_name_beats_the_filename`, and `task-408` had already recorded this as a pre-existing failure with the same explanation.

A booted world is not a state any route produces: `routes/saveload.py:43-45` and `:166-168` both build a **fresh** `VirtualWorld()` and load into it, which is exactly the blank-name state the derivation is for. The test fixed that premise instead of the code — set the name blank first, like `test_source_path_supplies_a_missing_name` does.

## Acceptance

- [x] The cause is identified, and it is not a `create_app()` leak: the measured character wanders out of the "alone" area because the test ran full turns with NPC behaviour and the background simulation on. A seeded probe shows repeated `create_app()` calls agree exactly.
- [x] `pytest tests/test_social_company.py` and the full suite agree: 7 passed on five consecutive runs alone, and no `test_social_company.py` failure in any pairing.
- [x] The measurement is now a mechanism assertion, not a stochastic aggregate — alone 72, introvert alone 78, company 80, extrovert company 83, every run.
- [x] The failure count no longer swings by 3; the suite baseline drops to the remaining known failures.
- [x] `test_clearing_the_source_leaves_the_name_alone` is fixed as a test-premise bug and the mis-grouping in `AGENTS.md` corrected.
