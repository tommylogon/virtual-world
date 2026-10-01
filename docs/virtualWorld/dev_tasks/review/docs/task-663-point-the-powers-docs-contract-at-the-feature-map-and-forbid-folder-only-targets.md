---
type: task
status: review
area: docs
priority: medium
---

# task-663: Point the @powers/@docs contract at the Feature Map, and forbid folder-only targets

**Filed:** 2026-10-01
**Related:** task-576, task-578, task-661, task-664

## Goal

The front-end module contract lets a module satisfy @docs by naming a folder: 26 of 43 unresolved declarations are things like 'docs/virtualWorld/Library System/', so the contract passes with nothing readable existing. 16 declare 'none' and 1 declares nothing. Now that docs/virtualWorld/Feature Map.md is the canonical feature list, point @powers at feature names in that file and have js_module_index --check fail on a folder target. This is the front-end half of task-576 (extend the contract to Python, 147 modules currently unguarded) and gives task-578 (a doc resolver route) something to resolve against.

## Acceptance

- [x] A canonical feature list exists and is the denominator — `docs/virtualWorld/Feature Map.md`, 58
      user-facing features, each with a status and the note that documents it or `none`. A feature is
      deliberately **not** a module.
- [x] A guard joins the front-end contract to it — `tools/feature_index.py`. `--check` fails when a new
      module's `@powers` names no feature; `--report` prints the join both ways; `--write` regenerates
      `docs/design/feature-index.md`; `--update-baseline` accepts today's debt.
- [x] `@docs` may no longer name a folder — `js_module_index.py --check` fails on a folder target and
      on a dead path, with its own baseline (`docs/design/js-docs-baseline.txt`).
- [x] The 28 offending headers are **fixed, not just recorded** — every folder target now points at a
      real note, and the two that pointed at task files which had moved between status folders point at
      the current paths (task-461 is in `inprogress/graph`, task-464's behaviour is documented in
      `Simulation Model.md`).
- [x] Both gates are documented in `AGENTS.md` beside the existing guards.
- [x] The honest numbers are recorded in `Feature Map.md` rather than glossed: **68 of 156** modules
      name a feature, **88** name none, and **32 of 58** features have no module naming them. Filed as
      task-664 — the headers are gerund phrases and the map is noun phrases, so the two only partly
      join.
- [x] The gates are **proven to bite**, not assumed: a BOM-free probe module with a folder `@docs` is
      rejected ("folder target — a directory is not a note"), a dead path is rejected ("does not
      resolve to a file"), a probe whose `@powers` names no feature is rejected by `feature_index`, and
      the 16 existing `none` declarations still pass — a declared absence is a decision, not a
      broken target.

## Not done here

- **task-576** — the back end's 147 modules still have no contract and no guard.
- **task-664** — the 88 unmapped headers, and the 32 features nothing claims.
- The 143 broken wikilinks in the vault are **task-662**; 129 of them are task paths that went stale
  when `tools/tasks.py move` relocated a file without rewriting inbound links, so this task's own
  `@docs` values will rot the same way until that tool is fixed.

