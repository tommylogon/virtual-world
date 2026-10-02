---
type: bug
status: review
area: testing
priority: medium
---

# bug-513: lint_library only covers data/library, so dead interest and fear tags in scenario saves are invisible

**Filed:** 2026-09-30
**Related:** 

## Goal

check_dead_interests and the new check_dead_fears read only the library registries, so a scenario save can carry any number of tags that can never match and nothing reports it. The Kraktooth scenario is the live example: Belne's interest_tags still include wary, lonely, caution, distrust, hope, desperation, and Eldenford Farmer's include hope, courage, resilience, attachment, memory - none of which any item carries, so the room attention list and auto-dress ignore them. The generator now reports which picks cannot work at the moment they are created, but nothing catches tags that were authored by hand or that have since stopped matching. Either extend the lint to scenario/save data or add a check in the scenario integrity test that already runs.

## Acceptance

- [x] `tools/scenario_tag_check.py` runs the same interest/fear rule semantics
      over `data/scenarios/*.json`: interests against **item** tags, fears against
      item ∪ area ∪ character tags plus trait keys (what `engine/fear.py` reads),
      with the scenario's own node/player tags added to the vocabulary. `--report`
      / `--check` / `--update-baseline`, matching the other shape gates.
- [x] Existing debt is baselined (`docs/virtualWorld/World Building/scenario-tag-baseline.txt`,
      **198 findings across 22 scenarios**); a newly authored dead tag fails
      `--check`.
- [x] `tests/test_scenario_tag_check.py` pins the rules (including the one most
      likely to be got wrong: an interest matching only an area tag is dead) and
      runs the checker against the shipped scenarios inside `pytest`.
- [x] `npm run scenario-tags:check` (and `npm run precommit`) exposes the gate.

## Outcome (2026-10-02)

The premise is confirmed and larger than filed: scenario players carry **140 dead
interest tags and 58 dead fear tags** across the shipped scenarios, none of which
`tools/lint_library.py` could see because it only opens `data/library/`.
Kraktooth's `Eldenford Elder` alone has `people`, `goblins`, `harvest`, `the_roads`
(and more) that no item carries, and the `Eldenford Farmer`'s `silence`,
`forgotten`, `abandoned`, `ghost`, `darkness`, `isolation`, `dread` and `goblins`
fears can never fire.

Saves live in `data/scenarios/` (`routes/saveload.py:692`); there is no
`data/saves/`. The tag registries themselves are not vocabulary sources — a fear
tag matching only `data/library/tags/ghostly.json` is still dead, exactly as the
runtime ignores a bare registry entry.

The library lint was **not** edited. It is a separate concern with its own funding
of dead-interest debt (24 library characters currently fail `dead_interests`), and
this bug is about the input source, not the rules; the new tool reuses the rules
without forking them. See `tests/test_scenario_tag_check.py` for the pinned
semantics.
