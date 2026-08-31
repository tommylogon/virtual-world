# Task & Bug Number Sequence

Next available numbers for new task/bug files.

## Current highest

| Type | Highest number | Next available |
|------|---------------|----------------|
| task | 386           | 387            |
| bug  | 35           | 36            |

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

## Renumber pass 2026-08-30

Duplicate ids resolved â€” canonical/reference-bearing files kept their numbers; the
duplicate side was renumbered (open/in-review sides; done-side renames only where wiki
links forced it):

- task-109â†’351 (trigger graph editor), 132â†’352 (action economy), 227â†’353 (social vital
  overhaul), 294â†’354 (pack logic), 295â†’355 (select library template; also re-referenced
  296â†’356), 296â†’356 (spawn area trigger), 334â†’357 (structure save/load), 97â†’358
  (playwright upgrade), 99â†’359 (remove backend llm modules, done), 139â†’360 (area events),
  150â†’361 (invalid action retry), 180â†’362 (resistance rework), 181â†’363 (command parser
  multiwindow)
- bug-13â†’32 (spawn effect library drift), bug-22â†’33 (human speech outside turn)
- New work filed: task-364 (scenario wizard, review), task-365 (save modal/autosave,
  done), task-366 (knowledge manager, done), bug-34 (approach-vs-cross, review)

## Known historical duplicates (all terminal â€” left as-is)

- bug-12: `done/bugs/bug_12-virtual-world-mcp-broken.md` +
  `cancelled/bug-12-error message on something.md`
- task-219: `done/refactor/task-219-prompt-builder-shared-fragment-extraction.md` +
  `done/ui/task-219-agent-lens-left-panel.md`

