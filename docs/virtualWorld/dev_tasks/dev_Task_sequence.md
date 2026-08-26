# Task & Bug Number Sequence

Next available numbers for new task/bug files.

## Current highest

| Type | Highest number | Next available |
|------|---------------|----------------|
| task | 342           | 343            |
| bug  | 25            | 26             |


## Naming convention

- Tasks: `task-<number>-<kebab-case-slug>.md`
- Bugs: `bug-<number>-<kebab-case-slug>.md`

## Locations

New tasks start in `todo/<category>/` (e.g. `todo/items/`, `todo/ui/`).
New bugs start in `todo/bugs/`.

## Note

This file tracks the highest task and bug numbers across all state directories (`todo/`,
`inprogress/`, `review/`, `done/`, `cancelled/`) and categories. Bump the highest number
when adding a new task or bug.
