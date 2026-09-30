---
type: bug
status: todo
area: testing
priority: medium
---

# bug-513: lint_library only covers data/library, so dead interest and fear tags in scenario saves are invisible

**Filed:** 2026-09-30
**Related:** 

## Goal

check_dead_interests and the new check_dead_fears read only the library registries, so a scenario save can carry any number of tags that can never match and nothing reports it. The Kraktooth scenario is the live example: Belne's interest_tags still include wary, lonely, caution, distrust, hope, desperation, and Eldenford Farmer's include hope, courage, resilience, attachment, memory - none of which any item carries, so the room attention list and auto-dress ignore them. The generator now reports which picks cannot work at the moment they are created, but nothing catches tags that were authored by hand or that have since stopped matching. Either extend the lint to scenario/save data or add a check in the scenario integrity test that already runs.

## Acceptance

- TODO
