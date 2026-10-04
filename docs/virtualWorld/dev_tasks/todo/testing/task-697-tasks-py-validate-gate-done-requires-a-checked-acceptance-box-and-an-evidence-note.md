---
type: task
status: todo
area: testing
priority: medium
---

# task-697: tasks.py validate gate: done requires a checked acceptance box and an evidence note

**Filed:** 2026-10-04
**Related:** task-612,task-677

## Goal

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

