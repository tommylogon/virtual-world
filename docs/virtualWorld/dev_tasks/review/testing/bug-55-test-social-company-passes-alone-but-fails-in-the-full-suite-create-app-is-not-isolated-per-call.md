---
type: bug
status: todo
area: testing
priority: medium
---

# bug-55: test_social_company passes alone but fails in the full suite (create_app is not isolated per call)

**Renumbered** 2026-09-28 from bug-54, which was already taken by the weather
`WEATHER_LIGHT_MULT` bug in `todo/bugs/`.

**Filed:** 2026-09-27
**Related:** task-551

## Goal

The second create_app() in a process does not behave like the first, so any test file running before test_social_company.py flips three of its seven assertions.

## Measured (2026-09-27, while baselining task-551)

Found by accident: my first full-suite baseline reported **59 failed**, and a run
after a change reported **62**. The extra three were all
`tests/test_social_company.py`. Re-run with my work stashed (`git stash push
--include-untracked`) they still failed, so this is **pre-existing and
order-dependent**, not a regression from any change.

Reproductions, all with `-p no:randomly` (so it is not seed order):

| Command | Result |
|---|---|
| `pytest tests/test_social_company.py` | 7 passed |
| `pytest tests/test_social_company.py tests/test_scenario_name.py` | 2 social_company failures |
| `pytest tests/test_social_company.py tests/test_character_identity.py` | 1 social_company failure |
| `pytest tests/test_social_company.py tests/test_templates.py` | 1 social_company failure |

So it is **not** one poisoning file. *Any* earlier `create_app()` call in the
process is enough, which points at module-level state rather than a specific
test.

The three that flip:

- `test_extrovert_alone_craves_company_more`
- `test_extrovert_company_gains_extra` — `assert extrovert > default` → `83 > 83`
- `test_introvert_alone_keeps_only_baseline`

### What the world looks like

Two `create_app({"TESTING": True})` calls in one process are *not* equivalent.
`engine/tick_manager.py:518-537` is where the difference shows: the Social rate is
`socail_mult * SOCIAL_COMPANY_GAIN`, and `social_mult` comes from
`TraitSystem.get_first_effect(p, SOCIAL_GAIN)`.

Direct probe — identical script run twice in one process, one character plus one
companion, 30 ticks:

```
first  tpm=5 social=90
second tpm=5 social=84
```

The two worlds are otherwise indistinguishable: 19 areas each, the same 19 names,
`Kitchen` present in both, the same three players (`Kaelen Voss`, `Lyrie`, `rat`),
and distinct `VirtualWorld` and `PlayerManager` objects. The leak is therefore in
something neither the area list nor the roster exposes — a module-level cache,
registry or counter reached from the tick path.

### Acceptance

- The leaking module-level state is identified, or the per-`Player` state it
  leaks into is scoped so a second `create_app()` behaves like the first.
- `pytest tests/test_social_company.py` and the full suite agree, and the full
  suite's failure count is stable across runs rather than swinging by 3.
- Until then: **compare against your own baseline, and re-baseline if the count
  moves by exactly these three.**

## Acceptance

- TODO
