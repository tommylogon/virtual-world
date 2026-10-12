---
type: task
status: done
area: refactor
priority: medium
effort: M
wiki: "[[Feature Map]]"
---

# task-797: Require wiki on task cards and generate per-feature changelogs

**Filed:** 2026-10-12
**Related:** 

## What

Make `wiki:` required on new task cards, and generate a `## Changelog` on each feature page from the tasks whose `wiki:` points at it — so every feature carries a real, dated history of what changed and why.

## Why

The task <-> feature edge already exists (`doc_connected.py` reads task `wiki:` frontmatter) but it is optional, so the join is patchy. The goal is a wiki where each dev task is tied to its feature and the page shows the history.

## How

Have `tasks.py validate` warn (then error) on a missing `wiki:`. Add a generator that reads the task tree, groups by `wiki:` target, and writes each page's `## Changelog` between markers (like `doc_connected`). Wire it into the vault guards when stable.

## Steps to verify

1. File a task with no `wiki:`.
   - expected: `tasks.py validate` warns.
   - observed: TODO
2. Run the changelog generator, open `Movement.md`.
   - expected: a dated changelog of the tasks that touched movement.
   - observed: TODO

## Acceptance

- [ ] new task cards are required to carry `wiki:`
- [ ] feature pages show a generated, dated changelog
- [ ] the changelog is built from the task tree, never hand-maintained

## Files

- `tools/tasks.py`
- `tools/doc_connected.py`
