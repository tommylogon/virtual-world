---
type: task
status: todo
area: testing
priority: medium
---

# task-697: tasks.py validate gate: done requires a checked acceptance box and an evidence note

**Filed:** 2026-10-04
**Related:** task-612,task-677

## What

TODO

## Acceptance

task-612 reached `done` with its Acceptance section still TODO and no live repro;
task-677's checkboxes drifted behind what actually shipped. The task tree is the
project's memory — an unverified `done` poisons the next session's ground truth.

- [ ] `tasks.py validate` fails (or errors — decide warn vs error, warn to start)
      when a task in `done/` has zero checked `- [x]` boxes in Acceptance.
- [ ] It also warns when a `done/` task's body has no evidence marker
      (a line matching /verified|repro|test|screenshot/i).
- [ ] `review/` tasks with zero checked boxes get a softer warning (review
      legitimately includes partial work — task-333/334 style).
- [ ] Existing `done/` files that trip the rule are listed once, and the
      grandfather set is either fixed or accepted via the usual baseline update —
      do not mass-move old tasks silently.
- [ ] `python tools/tasks.py validate` self-test: moving task-612 back to done
      without evidence fails; with the evidence section added, passes.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Not applicable — this card changes the repository task validator, not the game UI.

Current availability: the task records that `done/` cards can lack checked Acceptance boxes or evidence. The validator gate is planned; no new app control is involved.

Why no browser UI: the behavior is a command-line validation rule over Markdown cards. A game browser cannot prove that an invalid done card is rejected.

Alternative verification steps:
1. Create a scratch task card under `done/` with Acceptance left as TODO and run `python tools/tasks.py validate`.
   - expected: validation emits the specified warning/error naming that card and the missing checked acceptance.
2. Add one checked Acceptance item but no evidence marker and run validation again.
   - expected: the checked box alone does not pass; the missing evidence is reported.
3. Add the evidence note required by the rule and validate again.
   - expected: that card's warning clears; unrelated validation warnings remain unchanged.
4. Move the scratch card out of done and repeat.
   - expected: the done-only gate no longer applies while normal schema checks still run.

This section is not a claim that planned task-tool behavior exists or works today.
