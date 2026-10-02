# Overnight Worktree Sweep — 2026-10-02

Goal: fan the todo backlog out across parallel Agent Manager git worktrees,
**grouped by feature / file area** to keep merges clean. Each worktree owns a
disjoint task set and a disjoint set of files wherever possible.

Rules every worktree session must follow (from AGENTS.md):
- Never `git stash` (shared across worktrees).
- Never `npm install` / run JS gates without reverting `package-lock.json`.
- Never infer runtime behavior from existence — check caller, object, auth*ored
  data, and guard signature first.
- UI claims require a real interaction (hover/click/typed input), not a screenshot
  or a DOM read. `canvas` has no DOM.
- Skip `tests/test_tick_time_scaling.py` (hangs).
- Commit path-limited (`git commit -- <files>`) per task on the worktree branch.
- Move task files with `python tools/tasks.py move --id N --status ...`; only
  `review` when verified, `done` only after a live-browser check.
- Run the relevant gate before committing: `python -m pytest tests/test_<x>.py`,
  `node tools/unit/run.cjs`, `python tools/js_module_index.py --check`,
  `python tools/feature_index.py --check`, `python tools/way_property_index.py --check`,
  `python tools/character_loadout_check.py --check`, `npm run lint`, `npm run typecheck`.

## Worktree roster (12)

| # | branch | port | focus / files | tasks |
|---|--------|------|---------------|-------|
| 1 | `wt/docs-contract` | 4460 | `docs/`, `tools/*_index.py`, `@docs`/`@powers` | task-661, task-662, task-664, task-658, task-542, task-576, task-577, task-578, task-579, task-492 |
| 2 | `wt/library-data` | 4461 | `data/library/**`, `routes/library_ops.py` | task-645, task-646, task-649, task-573, task-667, task-588, task-589, task-590, task-591, task-659, bug-512 |
| 3 | `wt/items-library` | 4462 | `data/library/items+characters`, `routes/library_ops.py` | task-571, task-599, task-513, task-514, task-519, bug-516 |
| 4 | `wt/inspector-ui` | 4463 | `static/js/inspector/**`, `templates/index.html` | task-521, task-610, task-635, task-479, task-512, task-448, task-598, task-580, task-443 |
| 5 | `wt/graph-render` | 4464 | `static/js/graph/**`, `graph.py`, `routes/graph_ops.py` | task-614, task-617, task-618, task-622, task-527, task-642, task-638, task-640 |
| 6 | `wt/worldpainter` | 4465 | `static/js/worldpainter/**`, `engine/world*.py` | task-595, task-596, task-597, bug-511, task-650, task-651, task-524, task-520, task-536, task-540, task-541 |
| 7 | `wt/characters-engine` | 4466 | `engine/characters/**`, `player.py`, `engine/vital*` | task-487, task-488, task-489, task-545, task-546, task-538, task-549, task-606, task-215, task-652, task-653, task-654 |
| 8 | `wt/items-engine` | 4467 | `engine/items/**`, `engine/combat*` | task-450, task-473, task-516, task-518, task-433, task-537, task-604, task-607 |
| 9 | `wt/world-engine` | 4468 | `engine/world/**`, chunk/scope, `engine/matching.py` | task-401, task-582, task-583, task-584, task-585, task-439, task-581, task-569, task-570, task-533 |
| 10 | `wt/triggers-verbs` | 4469 | `engine/triggers/**`, `routes/trigger*`, `engine/actions*` | task-502, task-442, task-332, task-491, task-509, task-636 |
| 11 | `wt/testing-infra` | 4470 | `tests/**`, `tools/**` | task-572, task-586, task-587, task-444, task-513, task-666, task-574, bug-55 |
| 12 | `wt/small-bugs` | 4471 | bugs + dead-code refactors | bug-509, bug-510, bug-514, bug-515, bug-26, bug-37, bug-38, bug-39, bug-40, bug-42, bug-45, bug-46, bug-48, task-656, task-657, task-83, task-625, task-453, task-430, task-429 |

## Deferred (too large / design-heavy for one session, left in todo)
task-99, task-290, task-352, task-388, task-402, task-404, task-409, task-414,
task-422, task-435, task-437, task-455, task-456, task-467, task-477, task-482,
task-491(dup), task-543, task-555, task-556, task-594, task-619 — each is a
multi-session architecture effort. Their worktrees can be a second wave.

## Merge strategy
Each branch is based on `master` (02a8ab1). Merge in roster order, path-limited,
re-running the matching gate after each. Conflicts expected only where two
clusters touched the same file; the file ownership above is chosen to avoid that.

## Coordination
- Each session posts `RESULT` to `main` on the board when a task reaches `review`,
  with the exact command output / screenshot that proves it.
- Same session posts `HOLD` to `main` if blocked (missing LLM key, missing data,
  ambiguous source of truth).
