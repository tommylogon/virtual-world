# Lanes — parallel dev-task worktrees

Four worktrees, branched from `master`. One is a **serial spine**, three are
**parallel arms**. Do not run the arms and the spine in the same files.

| Lane | Worktree | Owns | Tasks | Merges |
|---|---|---|---|---|
| WT-0 | `wt-0-spine` | the 8 hub files + world scale | 42 (a queue) | last |
| WT-A | `wt-a-perception` | perception, sound, light, world presentation | 11 | first |
| WT-B | `wt-b-items` | items, inventory, equipment, data migrations | 9 | first |
| WT-C | `wt-c-characters` | characters, NPC behaviour, social, speech | 11 | first |

Read `docs/design/worktree-parallelisation-plan.md` for the analysis behind this split.

## Hub files — one owner

These eight are the merge magnets. **Only WT-0 edits them.** An arm that needs a hub
change must not make it inline; it should finish everything else, note the hub change,
and hand it to WT-0.

| Hub | Claimed by (queued tasks) | Claimed by (review tasks) |
|---|---|---|
| `engine/tick_manager.py` | 13 | 12 |
| `engine/serialization.py` | 10 | 10 |
| `virtual_world_engine.py` | 9 | 18 |
| `routes/library_ops.py` | 9 | 2 |
| `routes/action_handlers.py` | 8 | 4 |
| `player.py` | 5 | 7 |
| `routes/action.py` | 1 | 15 |
| `app.py` | 1 | 6 |

## Shared append-only files — anyone may append

These are touched constantly but are lists, so concurrent edits merge cleanly. Append,
do not reorganise.

- `templates/index.html` — the `<script>` tag list
- `tools/unit/run.cjs` — the module list at the top of the runner
- `tools/js_module_index.py` — generated; run `--write`, never hand-edit

## Rules that apply to every lane

1. **Never `git stash`.** Stashes are shared across worktrees and will bite. For a
   conflict, rebase or merge `master` into your worktree, resolve there, then merge or
   Apply.
2. **Claim tasks as you go.** `python tools/tasks.py move --id N --status inprogress`,
   then `--status review` when the work is done. Two lanes must never hold the same task.
3. **The gate.** Before proposing a merge, all of these must be clean:
   ```
   python -m pytest -q                       # baseline ~60 failed / 3239 passed
   node tools/unit/run.cjs
   npm run lint
   npm run typecheck
   python tools/js_module_index.py --check   # --write if you added a module
   ```
   The pytest baseline is dirty on `master`. Do **not** chase those failures; compare
   against the baseline and only investigate what your change moved.
4. **New JS module?** It needs an `@module` / `@contributes` header, a script tag in
   `templates/index.html`, a line in `tools/unit/run.cjs`, and a sibling
   `tools/unit/test_<name>.js`.
5. **Re-run the gate after any rebase.** A clean merge can still break a test.
6. **Post to the board** before starting a task and after finishing one, so the other
   lanes can see what is in flight.

## Cross-lane dependencies

| Task | Waits on | Lane |
|---|---|---|
| task-409 (background schedules) | task-408 (goblin scenario consolidation) | WT-A |
| task-414 (batch time advance) | task-409, task-411 | WT-A → WT-0 |
| task-426 (plan archetypes) | task-409 | WT-C |
| task-569 (biome distribution) | task-504 (item quantity) | WT-B |
| task-556 (snow accumulation) | task-553 (per-area temperature, in `review`) | — promote 553 first |

## Merge order

1. WT-A, WT-B, WT-C — one at a time, rebase each onto `master` first.
2. WT-0 last. It reabsorbs the arms' hub requests and re-resolves in its own worktree.

## Do not parallelise these

- **397 → 398 → 400 → 401 → 402** — strictly ordered, all WT-0.
- **416 → 418, 416 → 419** — same, all WT-0.
- Anything that edits `engine/tick_manager.py` or `engine/serialization.py`.
